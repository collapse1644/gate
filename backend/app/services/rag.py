from __future__ import annotations

import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app.models import Attempt, Concept, Formula, Question, Subject, Subtopic, Topic


def _fts_query(value: str) -> str:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", value.lower())
    seen = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return " OR ".join(seen[:18])


def related_questions(db: Session, question: Question, limit: int = 8) -> list[Question]:
    candidates: dict[int, Question] = {}
    query = _fts_query(question.question_text)
    if query:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT q.id FROM questions q
                    JOIN question_fts f ON f.rowid = q.id
                    WHERE question_fts MATCH :match
                      AND q.import_status = 'approved'
                      AND q.id != :qid
                    ORDER BY bm25(question_fts)
                    LIMIT :limit
                    """
                ),
                {"match": query, "qid": question.id, "limit": limit * 3},
            ).all()
            for (qid,) in rows:
                item = db.get(Question, qid)
                if item:
                    candidates[item.id] = item
        except Exception:  # noqa: BLE001 - FTS syntax/path failure must not break tutoring
            db.rollback()

    if question.subtopic_id:
        rows = db.scalars(
            select(Question)
            .where(
                Question.import_status == "approved",
                Question.id != question.id,
                Question.subtopic_id == question.subtopic_id,
            )
            .order_by(Question.year.desc(), Question.question_no)
            .limit(limit)
        ).all()
        for item in rows:
            candidates.setdefault(item.id, item)
    if question.topic_id and len(candidates) < limit:
        rows = db.scalars(
            select(Question)
            .where(
                Question.import_status == "approved",
                Question.id != question.id,
                Question.topic_id == question.topic_id,
            )
            .order_by(Question.year.desc(), Question.question_no)
            .limit(limit)
        ).all()
        for item in rows:
            candidates.setdefault(item.id, item)
    result = list(candidates.values())[:limit]
    result.sort(key=lambda q: (q.subtopic_id == question.subtopic_id, q.year or 0), reverse=True)
    return result


def _taxonomy_label(db: Session, question: Question) -> str:
    parts = []
    if question.subject_id:
        subject = db.get(Subject, question.subject_id)
        if subject:
            parts.append(subject.name)
    if question.topic_id:
        topic = db.get(Topic, question.topic_id)
        if topic:
            parts.append(topic.name)
    if question.subtopic_id:
        sub = db.get(Subtopic, question.subtopic_id)
        if sub:
            parts.append(sub.name)
    return " > ".join(parts) or "unclassified"


def build_question_context(
    db: Session,
    question: Question,
    *,
    working_text: str | None = None,
    include_related: bool = True,
) -> dict:
    concepts = [c.name for c in question.concepts]
    related = related_questions(db, question) if include_related else []
    related_payload = [
        {
            "year": item.year,
            "question_no": item.question_no,
            "session": item.session,
            "topic": _taxonomy_label(db, item),
            "excerpt": item.question_text[:260].replace("\n", " "),
            "id": item.id,
        }
        for item in related
    ]
    formulas = []
    if question.subtopic_id or question.topic_id:
        filters = [Formula.verification_status.in_(["verified", "approved"])]
        if question.subtopic_id:
            filters.append(Formula.subtopic_id == question.subtopic_id)
        else:
            filters.append(Formula.topic_id == question.topic_id)
        rows = db.scalars(select(Formula).where(*filters).limit(6)).all()
        formulas = [
            {
                "name": row.name,
                "latex": row.latex,
                "units": row.units,
                "applicability": row.applicability,
            }
            for row in rows
        ]
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.question_id == question.id)
        .order_by(Attempt.started_at.desc())
        .limit(5)
    ).all()
    verification_note = (
        f"Question verification status: {question.verification_status}. "
        "Do not claim independent verification beyond recorded checks."
    )
    assets = [
        {
            "id": asset.id,
            "path": asset.path,
            "kind": asset.kind,
            "page": asset.page,
            "interpretation_status": asset.interpretation_status,
            "interpretation": asset.interpretation,
        }
        for asset in question.assets
    ]
    return {
        "question_id": question.id,
        "question_text": question.question_text,
        "options": question.options or [],
        "year": question.year,
        "session": question.session,
        "question_no": question.question_no,
        "question_type": question.question_type,
        "marks": question.marks,
        "official_answer": question.official_answer,
        "taxonomy": _taxonomy_label(db, question),
        "concepts": concepts,
        "related_questions": related_payload,
        "formulas": formulas,
        "attempts": [
            {
                "selected_answer": a.selected_answer,
                "is_correct": a.is_correct,
                "mode": a.mode,
                "working_text": (a.working_text or "")[:600],
            }
            for a in attempts
        ],
        "working_text": working_text,
        "verification_note": verification_note,
        "assets": assets,
    }
