from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Progress, Question, RevisionItem
from app.schemas import ProgressStatusUpdate
from app.services.progress import due_revisions, overall_stats, subject_progress

router = APIRouter(tags=["revision"])


class ReviewRequest(BaseModel):
    outcome: str = "good"  # good | again
    note: str = ""


@router.get("/revision")
def revision_overview(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    upcoming = db.execute(
        select(RevisionItem, Question)
        .join(Question, Question.id == RevisionItem.question_id)
        .where(RevisionItem.due_at > now, Question.import_status == "approved")
        .order_by(RevisionItem.due_at)
        .limit(30)
    ).all()
    total_tracked = int(db.scalar(select(func.count(RevisionItem.id))) or 0)
    return {
        "stats": overall_stats(db),
        "due": due_revisions(db, limit=50),
        "upcoming": [
            {
                "question_id": question.id,
                "year": question.year,
                "question_no": question.question_no,
                "question_text": question.question_text[:240],
                "due_at": item.due_at.isoformat(),
                "interval_days": item.interval_days,
                "repetitions": item.repetitions,
            }
            for item, question in upcoming
        ],
        "tracked": total_tracked,
        "subjects": subject_progress(db),
    }


@router.post("/revision/{question_id}/review")
def review_revision(
    question_id: int, payload: ReviewRequest, db: Session = Depends(get_db)
) -> dict:
    """Record a self-reported review outcome without creating a graded attempt."""

    item = db.scalar(select(RevisionItem).where(RevisionItem.question_id == question_id))
    if item is None:
        raise HTTPException(status_code=404, detail="No revision item for this question")
    if payload.outcome not in {"good", "again"}:
        raise HTTPException(status_code=400, detail="outcome must be 'good' or 'again'.")
    now = datetime.now(timezone.utc)
    if payload.outcome == "good":
        item.repetitions += 1
        item.interval_days = 1 if item.repetitions == 1 else (6 if item.repetitions == 2 else max(1, round(item.interval_days * item.ease)))
        item.ease = min(2.8, item.ease + 0.05)
    else:
        item.repetitions = 0
        item.interval_days = 1
        item.lapses += 1
        item.ease = max(1.3, item.ease - 0.2)
    item.last_reviewed_at = now
    item.due_at = now + timedelta(days=item.interval_days)
    db.commit()
    return {
        "question_id": question_id,
        "due_at": item.due_at.isoformat(),
        "interval_days": item.interval_days,
        "repetitions": item.repetitions,
    }


@router.patch("/progress/{level}/{ref_id}")
def set_manual_status(
    level: str,
    ref_id: int,
    payload: ProgressStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    if level not in {"subject", "topic", "subtopic", "concept"}:
        raise HTTPException(status_code=400, detail="Unsupported progress level.")
    progress = db.scalar(
        select(Progress).where(Progress.level == level, Progress.ref_id == ref_id)
    )
    if progress is None:
        progress = Progress(level=level, ref_id=ref_id)
        db.add(progress)
    progress.manual_status = payload.manual_status
    db.commit()
    return {
        "level": level,
        "ref_id": ref_id,
        "manual_status": progress.manual_status,
    }
