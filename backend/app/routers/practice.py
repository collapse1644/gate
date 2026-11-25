from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Attempt,
    Paper,
    PracticeSession,
    Question,
    QuestionConcept,
    RevisionItem,
    Subject,
    Subtopic,
    Topic,
)
from app.schemas import PracticeAnswer, PracticeCreate
from app.serializers import question_summary
from app.services.progress import record_attempt

router = APIRouter(tags=["practice"])


@router.get("/papers")
def list_papers(db: Session = Depends(get_db)) -> dict:
    papers = db.scalars(select(Paper).order_by(Paper.year.desc(), Paper.session)).all()
    return {
        "items": [
            {
                "id": p.id,
                "year": p.year,
                "session": p.session,
                "label": p.label,
                "question_count": p.question_count,
                "total_marks": p.total_marks,
            }
            for p in papers
        ]
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _base_query():
    return select(Question).where(Question.import_status == "approved")


@router.post("/practice/sessions")
def create_session(payload: PracticeCreate, db: Session = Depends(get_db)) -> dict:
    paper = None
    query = _base_query()
    if payload.mode == "full_paper":
        if not payload.paper_id:
            raise HTTPException(status_code=400, detail="Full-paper mode requires a paper_id.")
        paper = db.get(Paper, payload.paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        query = query.where(Question.paper_id == paper.id).order_by(Question.question_no)
    else:
        if payload.subject_id:
            query = query.where(Question.subject_id == payload.subject_id)
        if payload.topic_id:
            query = query.where(Question.topic_id == payload.topic_id)
        if payload.subtopic_id:
            query = query.where(Question.subtopic_id == payload.subtopic_id)
        if payload.concept_id:
            query = query.where(
                Question.id.in_(
                    select(QuestionConcept.question_id).where(
                        QuestionConcept.concept_id == payload.concept_id
                    )
                )
            )
        if payload.year:
            query = query.where(Question.year == payload.year)
        if payload.year_from:
            query = query.where(Question.year >= payload.year_from)
        if payload.year_to:
            query = query.where(Question.year <= payload.year_to)
        if payload.question_type:
            query = query.where(Question.question_type == payload.question_type)
        if payload.marks is not None:
            query = query.where(Question.marks == payload.marks)
        if payload.difficulty_min is not None:
            query = query.where(Question.difficulty >= payload.difficulty_min)
        if payload.difficulty_max is not None:
            query = query.where(Question.difficulty <= payload.difficulty_max)
        if payload.verification_status:
            query = query.where(Question.verification_status == payload.verification_status)

        if payload.mode == "incorrect":
            latest = (
                select(Attempt.question_id, func.max(Attempt.completed_at).label("last"))
                .group_by(Attempt.question_id)
                .subquery()
            )
            query = query.join(latest, latest.c.question_id == Question.id).join(
                Attempt,
                (Attempt.question_id == latest.c.question_id)
                & (Attempt.completed_at == latest.c.last),
            ).where(Attempt.is_correct.is_(False))
        elif payload.mode == "unattempted":
            query = query.where(~Question.id.in_(select(Attempt.question_id)))
        elif payload.mode == "revision":
            query = query.join(RevisionItem, RevisionItem.question_id == Question.id).where(
                RevisionItem.due_at <= _utcnow()
            )
        query = query.order_by(Question.year.desc(), Question.question_no.asc())

    rows = db.scalars(query).all()
    if payload.mode != "full_paper":
        if payload.shuffle:
            rows = list(rows)
            random.shuffle(rows)
        if payload.limit and len(rows) > payload.limit:
            rows = rows[: payload.limit]
    if not rows:
        raise HTTPException(status_code=404, detail="No approved PYQs match these filters.")
    question_ids = [q.id for q in rows]
    session = PracticeSession(
        mode=payload.mode,
        filters=payload.model_dump(exclude={"limit", "shuffle", "preserve_order"}),
        question_ids=question_ids,
        paper_id=paper.id if paper else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_payload(session, db, include_answers=False)


def _session_payload(session: PracticeSession, db: Session, include_answers: bool) -> dict:
    questions = []
    by_id = {
        q.id: q
        for q in db.scalars(select(Question).where(Question.id.in_(session.question_ids))).all()
    }
    caches = {
        "subjects": {s.id: s for s in db.scalars(select(Subject)).all()},
        "topics": {t.id: t for t in db.scalars(select(Topic)).all()},
        "subtopics": {s.id: s for s in db.scalars(select(Subtopic)).all()},
    }
    for qid in session.question_ids:
        question = by_id.get(qid)
        if not question:
            continue
        summary = question_summary(question, db, caches)
        if not include_answers:
            summary["official_answer"] = None
            summary.pop("answer_explanation", None)
        questions.append(summary)
    paper = db.get(Paper, session.paper_id) if session.paper_id else None
    return {
        "id": session.id,
        "mode": session.mode,
        "paper": (
            {
                "id": paper.id,
                "year": paper.year,
                "session": paper.session,
                "label": paper.label,
            }
            if paper
            else None
        ),
        "current_index": session.current_index,
        "answered_count": session.answered_count,
        "correct_count": session.correct_count,
        "total_questions": len(session.question_ids),
        "questions": questions,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.get("/practice/sessions")
def list_sessions(db: Session = Depends(get_db)) -> dict:
    sessions = db.scalars(
        select(PracticeSession).order_by(PracticeSession.started_at.desc()).limit(30)
    ).all()
    return {
        "items": [
            {
                "id": s.id,
                "mode": s.mode,
                "total_questions": len(s.question_ids or []),
                "answered_count": s.answered_count,
                "correct_count": s.correct_count,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ]
    }


@router.get("/practice/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = db.get(PracticeSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    return _session_payload(session, db, include_answers=False)


@router.post("/practice/sessions/{session_id}/answer")
def answer_question(
    session_id: int, payload: PracticeAnswer, db: Session = Depends(get_db)
) -> dict:
    session = db.get(PracticeSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if payload.question_id not in (session.question_ids or []):
        raise HTTPException(status_code=400, detail="Question is not part of this session.")
    question = db.get(Question, payload.question_id)
    if question is None or question.import_status != "approved":
        raise HTTPException(status_code=404, detail="Question not available.")
    attempt = record_attempt(
        db,
        question=question,
        selected_answer=payload.selected_answer,
        mode=f"practice:{session.mode}",
        time_spent_seconds=payload.time_spent_seconds,
        working_text=payload.working_text,
    )
    session.answered_count += 1
    if attempt.is_correct:
        session.correct_count += 1
    index = (session.question_ids or []).index(payload.question_id)
    session.current_index = min(index + 1, len(session.question_ids or []))
    if session.current_index >= len(session.question_ids or []):
        session.completed_at = _utcnow()
    db.commit()
    return {
        "attempt_id": attempt.id,
        "is_correct": attempt.is_correct,
        "official_answer": question.official_answer,
        "question_type": question.question_type,
        "explanation": question.answer_explanation,
        "session": {
            "id": session.id,
            "answered_count": session.answered_count,
            "correct_count": session.correct_count,
            "current_index": session.current_index,
            "completed": session.completed_at is not None,
        },
    }
