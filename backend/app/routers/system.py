from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.router import provider_status
from app.db import get_db
from app.models import (
    Concept,
    Question,
    QuestionConcept,
    Subject,
    Subtopic,
    SyllabusSection,
    SyllabusVersion,
    Topic,
)
from app.schemas import SettingsUpdate
from app.services.analytics import weightage
from app.services.classifier import taxonomy_tree
from app.services.taxonomy_validation import validate_taxonomy
from app.services.progress import (
    overall_stats,
    progress_payload,
    recent_activity,
    subject_progress,
    topic_progress,
    weak_strong_topics,
    due_revisions,
)
from app.settings_service import get_all_settings, update_settings
from app.utils import utcnow

router = APIRouter(tags=["system"])


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(select(1))
        database = "ok"
    except Exception as exc:  # noqa: BLE001
        database = f"error: {exc}"
    startup = getattr(request.app.state, "startup", None)
    warnings = []
    if isinstance(startup, dict) and startup.get("error"):
        warnings.append(str(startup["error"]))
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "time": utcnow().isoformat(),
        "app": "GATE CS 2027 Tutor",
        "startup": startup,
        "warnings": warnings,
    }


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)) -> dict:
    return {
        "settings": get_all_settings(db),
        "notes": {
            "gemini_model": "Model string is configurable. Verify current free-tier eligibility and quotas in Google AI Studio.",
            "local_only": "When ai_mode=local_only, cloud providers are never contacted.",
            "secrets": "The Gemini API key is stored encrypted locally and is never returned in full.",
        },
    }


@router.put("/settings")
def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> dict:
    update_settings(db, payload.values)
    return {"settings": get_all_settings(db)}


@router.get("/syllabus")
def syllabus(db: Session = Depends(get_db)) -> dict:
    version = db.scalar(
        select(SyllabusVersion).where(
            SyllabusVersion.year == 2027, SyllabusVersion.paper_code == "CS"
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Syllabus has not been seeded.")
    sections = db.scalars(
        select(SyllabusSection)
        .where(SyllabusSection.version_id == version.id)
        .order_by(SyllabusSection.display_order)
    ).all()
    return {
        "version": {
            "id": version.id,
            "exam": version.exam,
            "year": version.year,
            "paper_code": version.paper_code,
            "title": version.title,
            "source_url": version.source_url,
            "source_sha256": version.source_sha256,
            "retrieved_at": version.retrieved_at.isoformat() if version.retrieved_at else None,
            "is_active": version.is_active,
        },
        "sections": [
            {
                "id": s.id,
                "code": s.code,
                "title": s.title,
                "category": s.category,
                "official_text": s.official_text,
            }
            for s in sections
        ],
        "subjects": taxonomy_tree(db),
        "note": "Official section wording is preserved verbatim; topic/subtopic/concept expansion is a study aid.",
    }


@router.get("/taxonomy")
def taxonomy(db: Session = Depends(get_db)) -> dict:
    return {"subjects": taxonomy_tree(db)}


@router.get("/taxonomy/validate")
def taxonomy_validate(db: Session = Depends(get_db)) -> dict:
    return validate_taxonomy(db)


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)) -> dict:
    subjects = db.scalars(select(Subject).order_by(Subject.display_order)).all()
    progress = {p["id"]: p for p in subject_progress(db)}
    counts = dict(
        db.execute(
            select(Question.subject_id, func.count(Question.id))
            .where(Question.import_status == "approved")
            .group_by(Question.subject_id)
        ).all()
    )
    return {
        "subjects": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "description": s.description,
                "color": s.color,
                "section_code": s.section_code,
                "questions_available": counts.get(s.id, 0),
                "progress": progress.get(s.id),
            }
            for s in subjects
        ]
    }


@router.get("/subjects/{subject_id}")
def subject_detail(subject_id: int, db: Session = Depends(get_db)) -> dict:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    topics = db.scalars(
        select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.display_order)
    ).all()
    progress = {p["id"]: p for p in topic_progress(db, subject_id)}
    counts = dict(
        db.execute(
            select(Question.topic_id, func.count(Question.id))
            .where(
                Question.subject_id == subject_id, Question.import_status == "approved"
            )
            .group_by(Question.topic_id)
        ).all()
    )
    return {
        "subject": {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "description": subject.description,
            "color": subject.color,
        },
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "section_id": t.section_id,
                "description": t.description,
                "questions_available": counts.get(t.id, 0),
                "progress": progress.get(t.id),
            }
            for t in topics
        ],
    }


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: int, db: Session = Depends(get_db)) -> dict:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    subtopics = db.scalars(
        select(Subtopic).where(Subtopic.topic_id == topic_id).order_by(Subtopic.display_order)
    ).all()
    progress = {
        p["id"]: p
        for p in (progress_payload(db, "subtopic", {"id": s.id, "name": s.name}) for s in subtopics)
    }
    counts = dict(
        db.execute(
            select(Question.subtopic_id, func.count(Question.id))
            .where(Question.topic_id == topic_id, Question.import_status == "approved")
            .group_by(Question.subtopic_id)
        ).all()
    )
    return {
        "topic": {
            "id": topic.id,
            "name": topic.name,
            "subject_id": topic.subject_id,
            "description": topic.description,
        },
        "subtopics": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "questions_available": counts.get(s.id, 0),
                "progress": progress.get(s.id),
                "concepts": [
                    {"id": c.id, "name": c.name, "description": c.description}
                    for c in s.concepts
                ],
            }
            for s in subtopics
        ],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    stats = overall_stats(db)
    subjects = subject_progress(db)
    weak_strong = weak_strong_topics(db, limit=6)
    revisions = due_revisions(db, limit=8)
    activity = recent_activity(db, limit=8)
    try:
        analytics = weightage(db)
        priority = [
            {
                "subject_id": s["subject_id"],
                "subject": s["subject"],
                "average_marks": s["average_marks"],
                "priority_score": s["priority_score"],
                "priority_band": s["priority_band"],
            }
            for s in analytics["subjects"][:5]
        ]
    except Exception:  # noqa: BLE001
        priority = []
    recommended = []
    for topic in sorted(
        [t for t in topic_progress(db) if t["questions_available"] > 0],
        key=lambda t: (t["accuracy"] if t["accuracy"] is not None else -1, t["attempted"]),
    )[:6]:
        recommended.append(
            {
                "topic_id": topic["id"],
                "topic": topic["name"],
                "questions_available": topic["questions_available"],
                "accuracy": topic["accuracy"],
                "reason": (
                    "No attempts yet; start with available PYQs."
                    if topic["attempted"] == 0
                    else f"Accuracy {round((topic['accuracy'] or 0) * 100)}% over {topic['distinct_questions']} questions."
                ),
            }
        )
    return {
        "stats": stats,
        "subjects": subjects,
        "weak_topics": weak_strong["weak"],
        "strong_topics": weak_strong["strong"],
        "recent_activity": activity,
        "revision_due": revisions,
        "priority_subjects": priority,
        "recommended_topics": recommended,
        "empty_state": stats["questions_available"] == 0,
    }
