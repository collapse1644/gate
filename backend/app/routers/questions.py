from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

import pymupdf

from app.ai import prompts
from app.ai.router import generate
from app.config import settings
from app.db import get_db
from app.models import (
    Attempt,
    ClassificationBenchmark,
    Concept,
    Question,
    QuestionConcept,
    QuestionSecondaryTopic,
    Subject,
    Subtopic,
    Topic,
)
from app.schemas import (
    ApproveRequest,
    BenchmarkCreate,
    BookmarkUpdate,
    ClassificationAIRequest,
    ClassificationUpdate,
    QuestionPatch,
    RejectRequest,
    AttemptCreate,
)
from app.serializers import question_detail, question_summary
from app.services.classifier import benchmark_report, classify_question
from app.services.ingestion import approve_question, reject_question, update_classification
from app.services.progress import is_correct_answer, record_attempt
from app.services.rag import related_questions

router = APIRouter(tags=["questions"])


def _caches(db: Session) -> dict:
    return {
        "subjects": {s.id: s for s in db.scalars(select(Subject)).all()},
        "topics": {t.id: t for t in db.scalars(select(Topic)).all()},
        "subtopics": {s.id: s for s in db.scalars(select(Subtopic)).all()},
    }


def _fts_query(value: str) -> str:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", value)
    return " OR ".join(dict.fromkeys(terms[:16]))


@router.get("/questions")
def list_questions(
    q: str | None = None,
    subject_id: int | None = None,
    topic_id: int | None = None,
    subtopic_id: int | None = None,
    concept_id: int | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    session: str | None = None,
    paper_id: int | None = None,
    question_type: str | None = None,
    marks: float | None = None,
    difficulty_min: float | None = None,
    difficulty_max: float | None = None,
    verification_status: str | None = None,
    review_status: str | None = None,
    import_status: str | None = Query(default=None),
    include_staged: bool = False,
    bookmarked: bool | None = None,
    sort: str = "recent",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    conditions = []
    if not include_staged:
        conditions.append(Question.import_status == (import_status or "approved"))
    elif import_status:
        conditions.append(Question.import_status == import_status)
    if subject_id:
        conditions.append(Question.subject_id == subject_id)
    if topic_id:
        conditions.append(Question.topic_id == topic_id)
    if subtopic_id:
        conditions.append(Question.subtopic_id == subtopic_id)
    if concept_id:
        conditions.append(
            Question.id.in_(
                select(QuestionConcept.question_id).where(QuestionConcept.concept_id == concept_id)
            )
        )
    if year:
        conditions.append(Question.year == year)
    if year_from:
        conditions.append(Question.year >= year_from)
    if year_to:
        conditions.append(Question.year <= year_to)
    if session:
        conditions.append(Question.session == session)
    if paper_id:
        conditions.append(Question.paper_id == paper_id)
    if question_type:
        conditions.append(Question.question_type == question_type)
    if marks is not None:
        conditions.append(Question.marks == marks)
    if difficulty_min is not None:
        conditions.append(Question.difficulty >= difficulty_min)
    if difficulty_max is not None:
        conditions.append(Question.difficulty <= difficulty_max)
    if verification_status:
        conditions.append(Question.verification_status == verification_status)
    if review_status:
        conditions.append(Question.review_status == review_status)
    if bookmarked is not None:
        conditions.append(Question.is_bookmarked.is_(bookmarked))

    ids_from_search: list[int] | None = None
    if q and q.strip():
        fts = _fts_query(q)
        if fts:
            try:
                rows = db.execute(
                    text(
                        "SELECT rowid FROM question_fts WHERE question_fts MATCH :q LIMIT 300"
                    ),
                    {"q": fts},
                ).all()
                ids_from_search = [row[0] for row in rows]
            except Exception:  # noqa: BLE001
                db.rollback()
        if ids_from_search is None:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(Question.question_text.ilike(pattern), Question.concept_text.ilike(pattern))
            )
        elif not ids_from_search:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        else:
            conditions.append(Question.id.in_(ids_from_search))

    query = select(Question).where(*conditions)
    count_query = select(func.count(Question.id)).where(*conditions)
    if sort == "year_asc":
        query = query.order_by(Question.year.asc(), Question.question_no.asc())
    elif sort == "marks":
        query = query.order_by(Question.marks.desc().nullslast(), Question.year.desc())
    elif sort == "question_no":
        query = query.order_by(Question.year.desc(), Question.question_no.asc())
    else:
        query = query.order_by(Question.year.desc(), Question.question_no.asc())
    total = int(db.scalar(count_query) or 0)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    caches = _caches(db)
    return {
        "items": [question_summary(item, db, caches) for item in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question_detail(question, db)


@router.get("/questions/{question_id}/pdf-page")
def question_pdf_page(
    question_id: int,
    dpi: int = Query(default=200, ge=72, le=400),
    db: Session = Depends(get_db),
):
    """Render a source PDF page as a PNG image at the requested DPI.

    The original PDF is used as the source of truth. No OCR, no redraw,
    no AI-generated replacement. The page is rendered on demand and not
    cached to avoid storing redundant copies of every page.
    """
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if not question.source_pdf:
        raise HTTPException(status_code=404, detail="No source PDF associated with this question.")
    page_num = question.source_page or 1
    pdf_path = Path(question.source_pdf)
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="Source PDF file is missing on disk.")

    data_root = settings.data_dir.resolve()
    candidate = pdf_path.resolve()
    if data_root not in candidate.parents and candidate != data_root:
        raise HTTPException(status_code=400, detail="Invalid PDF path")

    try:
        doc = pymupdf.open(pdf_path)
        if page_num < 1 or page_num > doc.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Page {page_num} is out of range (document has {doc.page_count} pages).",
            )
        page = doc[page_num - 1]
        mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="q{question_id}_p{page_num}.png"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF rendering failed: {exc}")


@router.patch("/questions/{question_id}")
def patch_question(question_id: int, payload: QuestionPatch, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if payload.needs_review is not None:
        question.needs_review = payload.needs_review
    if payload.review_notes is not None:
        question.review_notes = payload.review_notes[:5000]
    if payload.difficulty is not None:
        question.difficulty = payload.difficulty
    if payload.official_answer is not None:
        question.official_answer = payload.official_answer.strip()
    if payload.question_type is not None:
        question.question_type = payload.question_type
    db.commit()
    return question_detail(question, db)


@router.post("/questions/{question_id}/bookmark")
def bookmark(question_id: int, payload: BookmarkUpdate, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    question.is_bookmarked = payload.is_bookmarked
    db.commit()
    return {"id": question.id, "is_bookmarked": question.is_bookmarked}


@router.post("/questions/{question_id}/classification")
def manual_classification(
    question_id: int, payload: ClassificationUpdate, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        update_classification(
            db,
            question,
            subject_id=payload.subject_id,
            topic_id=payload.topic_id,
            subtopic_id=payload.subtopic_id,
            concept_ids=payload.concept_ids,
            reason=payload.reason,
            accept=payload.accept,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return question_detail(question, db)


@router.post("/questions/{question_id}/classify")
async def classify_now(
    question_id: int, payload: ClassificationAIRequest, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    base = classify_question(
        db,
        text=question.question_text,
        options=question.options or [],
        review_threshold=0.55,
        accept_threshold=0.72,
    )
    llm_recommendation = None
    llm_error = None
    if payload.use_llm:
        system, prompt = prompts.classification_prompt(
            question.question_text, question.options or [], base.candidates
        )
        try:
            result = await generate(
                db,
                task="classification",
                system=system,
                prompt=prompt,
                json_mode=True,
                question_id=question.id,
            )
            llm_recommendation = json.loads(result.text)
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)[:500]
    if llm_recommendation:
        base = classify_question(
            db,
            text=question.question_text,
            options=question.options or [],
            llm_recommendation=llm_recommendation,
            review_threshold=0.55,
            accept_threshold=0.72,
        )
    question.subject_id = base.subject_id
    question.section_id = base.section_id
    question.topic_id = base.topic_id
    question.subtopic_id = base.subtopic_id
    question.classification_confidence = base.confidence
    question.classification_method = base.method
    question.review_status = base.review_status
    question.needs_review = base.review_status in {"pending", "out_of_syllabus"} or base.ambiguous
    names = []
    db.query(QuestionConcept).filter(QuestionConcept.question_id == question.id).delete()
    for cid in list(dict.fromkeys(base.concept_ids)):
        concept = db.get(Concept, cid)
        if concept:
            names.append(concept.name)
            db.add(QuestionConcept(question_id=question.id, concept_id=cid))
    db.query(QuestionSecondaryTopic).filter(
        QuestionSecondaryTopic.question_id == question.id
    ).delete()
    for tid in base.secondary_topic_ids:
        db.add(QuestionSecondaryTopic(question_id=question.id, topic_id=tid))
    question.concept_text = ", ".join(names)
    question.review_notes = (
        f"{base.explanation}\nCandidates: {json.dumps(base.candidates[:5])}\n"
        + (f"LLM recommendation: {json.dumps(llm_recommendation)}\n" if llm_recommendation else "")
        + (f"LLM error: {llm_error}" if llm_error else "")
    ).strip()
    db.commit()
    return {
        "question": question_detail(question, db),
        "classification": {
            "subject_id": base.subject_id,
            "section_id": base.section_id,
            "topic_id": base.topic_id,
            "subtopic_id": base.subtopic_id,
            "concept_ids": base.concept_ids,
            "confidence": base.confidence,
            "method": base.method,
            "review_status": base.review_status,
            "ambiguous": base.ambiguous,
            "out_of_syllabus": base.out_of_syllabus,
            "candidates": base.candidates,
            "explanation": base.explanation,
        },
        "llm_used": bool(llm_recommendation),
        "llm_error": llm_error,
    }


@router.post("/questions/{question_id}/approve")
def approve(question_id: int, payload: ApproveRequest, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    approve_question(db, question, payload.reviewer)
    return question_detail(question, db)


@router.post("/questions/{question_id}/reject")
def reject(question_id: int, payload: RejectRequest, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    reject_question(db, question, payload.reviewer, payload.reason)
    return {"id": question.id, "import_status": question.import_status}


@router.post("/questions/{question_id}/attempts")
def submit_attempt(
    question_id: int, payload: AttemptCreate, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    is_preview = payload.mode == "preview"
    if not is_preview and question.import_status != "approved":
        raise HTTPException(status_code=409, detail="Approve the question before practising it.")
    attempt = record_attempt(
        db,
        question=question,
        selected_answer=payload.selected_answer,
        mode=payload.mode,
        time_spent_seconds=payload.time_spent_seconds,
        working_text=payload.working_text,
        confidence=payload.confidence,
    )
    if not is_preview and payload.practice_session_id:
        from app.models import PracticeSession

        session = db.get(PracticeSession, payload.practice_session_id)
        if session:
            session.answered_count += 1
            if attempt.is_correct:
                session.correct_count += 1
            db.commit()
    return {
        "attempt_id": attempt.id,
        "is_correct": attempt.is_correct,
        "official_answer": question.official_answer,
        "question_type": question.question_type,
        "explanation": question.answer_explanation,
        "selected_answer": attempt.selected_answer,
        "preview": is_preview,
    }


@router.get("/questions/{question_id}/related")
def related(question_id: int, db: Session = Depends(get_db)) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    caches = _caches(db)
    return {
        "items": [
            question_summary(item, db, caches) for item in related_questions(db, question, limit=10)
        ]
    }


@router.get("/review/queue")
def review_queue(
    view: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    conditions = []
    if view == "classification":
        conditions.append(
            or_(
                Question.review_status.in_(["pending", "out_of_syllabus"]),
                Question.classification_confidence < 0.72,
            )
        )
    elif view == "extraction":
        conditions.append(
            or_(Question.extraction_confidence < 0.72, Question.needs_review.is_(True))
        )
    elif view == "answers":
        conditions.append(Question.official_answer.is_(None))
    elif view == "staged":
        conditions.append(Question.import_status == "staged")
    else:
        conditions.append(
            or_(
                Question.import_status == "staged",
                Question.needs_review.is_(True),
                Question.review_status.in_(["pending", "out_of_syllabus"]),
                Question.extraction_confidence < 0.72,
                Question.official_answer.is_(None),
            )
        )
    query = select(Question).where(*conditions).order_by(
        Question.extraction_confidence.asc(), Question.created_at.asc()
    )
    total = int(db.scalar(select(func.count(Question.id)).where(*conditions)) or 0)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    caches = _caches(db)
    counts = {
        "staged": int(
            db.scalar(select(func.count(Question.id)).where(Question.import_status == "staged")) or 0
        ),
        "needs_review": int(
            db.scalar(select(func.count(Question.id)).where(Question.needs_review.is_(True))) or 0
        ),
        "missing_answers": int(
            db.scalar(select(func.count(Question.id)).where(Question.official_answer.is_(None))) or 0
        ),
        "low_extraction": int(
            db.scalar(
                select(func.count(Question.id)).where(Question.extraction_confidence < 0.72)
            )
            or 0
        ),
        "low_classification": int(
            db.scalar(
                select(func.count(Question.id)).where(Question.classification_confidence < 0.72)
            )
            or 0
        ),
    }
    return {
        "items": [question_summary(item, db, caches) for item in rows],
        "total": total,
        "counts": counts,
        "view": view,
    }


@router.post("/questions/{question_id}/benchmark")
def upsert_benchmark(
    question_id: int, payload: BenchmarkCreate, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    row = db.scalar(
        select(ClassificationBenchmark).where(ClassificationBenchmark.question_id == question_id)
    )
    if row is None:
        row = ClassificationBenchmark(question_id=question_id)
        db.add(row)
    row.expected_subject_id = payload.expected_subject_id
    row.expected_topic_id = payload.expected_topic_id
    row.expected_subtopic_id = payload.expected_subtopic_id
    row.expected_concepts = payload.expected_concepts
    row.notes = payload.notes
    row.label_source = payload.label_source
    row.reviewer = payload.reviewer
    from datetime import datetime, timezone
    row.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "question_id": question_id}


@router.delete("/questions/{question_id}/benchmark")
def delete_benchmark(question_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(
        select(ClassificationBenchmark).where(ClassificationBenchmark.question_id == question_id)
    )
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.get("/review/benchmark")
def get_benchmark(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(ClassificationBenchmark)).all()
    return {
        "items": [
            {
                "question_id": row.question_id,
                "expected_subject_id": row.expected_subject_id,
                "expected_topic_id": row.expected_topic_id,
                "expected_subtopic_id": row.expected_subtopic_id,
                "notes": row.notes,
            }
            for row in rows
        ],
        "report": benchmark_report(db),
    }
