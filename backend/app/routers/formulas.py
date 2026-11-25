from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Formula, Question, Subject, Subtopic, Topic
from app.schemas import FormulaCreate, FormulaUpdate
from app.serializers import formula_payload

router = APIRouter(tags=["formulas"])


@router.get("/formulas")
def list_formulas(
    subject_id: int | None = None,
    topic_id: int | None = None,
    subtopic_id: int | None = None,
    status: str | None = None,
    bookmarked: bool | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    conditions = []
    if subject_id:
        conditions.append(Formula.subject_id == subject_id)
    if topic_id:
        conditions.append(Formula.topic_id == topic_id)
    if subtopic_id:
        conditions.append(Formula.subtopic_id == subtopic_id)
    if status:
        conditions.append(Formula.verification_status == status)
    if bookmarked is not None:
        conditions.append(Formula.is_bookmarked.is_(bookmarked))
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                Formula.name.ilike(pattern),
                Formula.latex.ilike(pattern),
                Formula.related_concepts.ilike(pattern),
            )
        )
    total = int(db.scalar(select(func.count(Formula.id)).where(*conditions)) or 0)
    rows = db.scalars(
        select(Formula)
        .where(*conditions)
        .order_by(Formula.subject_id, Formula.topic_id, Formula.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [formula_payload(f) for f in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/formulas")
def create_formula(payload: FormulaCreate, db: Session = Depends(get_db)) -> dict:
    formula = Formula(**payload.model_dump())
    formula.reviewed_by = "user" if payload.verification_status == "verified" else None
    db.add(formula)
    db.commit()
    db.refresh(formula)
    return formula_payload(formula)


@router.patch("/formulas/{formula_id}")
def update_formula(formula_id: int, payload: FormulaUpdate, db: Session = Depends(get_db)) -> dict:
    formula = db.get(Formula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Formula not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(formula, key, value)
    if payload.verification_status == "verified":
        formula.reviewed_by = "user"
    db.commit()
    return formula_payload(formula)


@router.post("/formulas/{formula_id}/bookmark")
def bookmark_formula(formula_id: int, db: Session = Depends(get_db)) -> dict:
    formula = db.get(Formula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Formula not found")
    formula.is_bookmarked = not formula.is_bookmarked
    db.commit()
    return {"id": formula.id, "is_bookmarked": formula.is_bookmarked}


@router.get("/formulas/sheet")
def revision_sheet(subject_id: int, include_proposed: bool = False, db: Session = Depends(get_db)) -> dict:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    conditions = [Formula.subject_id == subject_id]
    if not include_proposed:
        conditions.append(Formula.verification_status == "verified")
    formulas = db.scalars(select(Formula).where(*conditions).order_by(Formula.topic_id, Formula.name)).all()
    topics = {t.id: t for t in db.scalars(select(Topic)).all()}
    subtopics = {s.id: s for s in db.scalars(select(Subtopic)).all()}
    grouped: dict[str, list] = {}
    for formula in formulas:
        topic = topics.get(formula.topic_id)
        key = topic.name if topic else "Unmapped"
        grouped.setdefault(key, []).append(
            {
                **formula_payload(formula),
                "topic": topic.name if topic else None,
                "subtopic": subtopics.get(formula.subtopic_id).name if subtopics.get(formula.subtopic_id) else None,
            }
        )
    return {
        "subject": {"id": subject.id, "name": subject.name, "color": subject.color},
        "groups": [{"topic": key, "formulas": value} for key, value in grouped.items()],
        "count": len(formulas),
        "note": "Only verified formulas are included unless include_proposed=true.",
    }


@router.get("/formulas/flashcards")
def flashcards(
    subject_id: int | None = None,
    topic_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    conditions = [Formula.verification_status == "verified"]
    if subject_id:
        conditions.append(Formula.subject_id == subject_id)
    if topic_id:
        conditions.append(Formula.topic_id == topic_id)
    cards = db.scalars(select(Formula).where(*conditions).order_by(func.random()).limit(min(limit, 100))).all()
    return {
        "cards": [
            {
                "id": f.id,
                "name": f.name,
                "latex": f.latex,
                "units": f.units,
                "applicability": f.applicability,
                "common_mistakes": f.common_mistakes,
            }
            for f in cards
        ]
    }


@router.get("/formulas/{formula_id}")
def get_formula(formula_id: int, db: Session = Depends(get_db)) -> dict:
    formula = db.get(Formula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Formula not found")
    payload = formula_payload(formula)
    payload["pyqs"] = []
    for qid in formula.pyq_references or []:
        question = db.get(Question, qid)
        if question:
            payload["pyqs"].append(
                {
                    "id": question.id,
                    "year": question.year,
                    "question_no": question.question_no,
                    "session": question.session,
                    "text": question.question_text[:260],
                }
            )
    return payload
