from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.analytics import weightage
from app.services.progress import (
    due_revisions,
    overall_stats,
    subject_progress,
    weak_strong_topics,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics(
    from_year: int | None = Query(default=None, ge=2000, le=2100),
    to_year: int | None = Query(default=None, ge=2000, le=2100),
    session: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Weightage computed strictly from approved questions in uploaded papers."""

    if from_year and to_year and from_year > to_year:
        from_year, to_year = to_year, from_year
    return weightage(db, from_year=from_year, to_year=to_year, session=session)


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)) -> dict:
    weak_strong = weak_strong_topics(db, limit=10)
    revisions = due_revisions(db, limit=30)
    return {
        "stats": overall_stats(db),
        "subjects": subject_progress(db),
        "weak_topics": weak_strong["weak"],
        "strong_topics": weak_strong["strong"],
        "revision_due": revisions,
        "revision_due_count": len(revisions),
    }
