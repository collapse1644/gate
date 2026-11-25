from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    Concept,
    Progress,
    Question,
    QuestionConcept,
    RevisionItem,
    Subject,
    Subtopic,
    Topic,
    VerifiedAnswer,
)
from app.settings_service import get_setting


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_numeric(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def _get_official_answer(question: Question, db: Session) -> str | None:
    """Return the official answer, checking VerifiedAnswer first, then AnswerKeyEntry."""
    if question.verified_answer:
        return question.verified_answer.answer
    return question.official_answer


def is_correct_answer(
    question: Question, selected: str | None, db: Session | None = None
) -> bool | None:
    official = _get_official_answer(question, db)
    if not official or selected is None or selected == "":
        return None
    if official.strip().upper() == "MTA":
        return True
    if question.question_type in {"MCQ", "MSQ"}:
        expected = set(re.findall(r"[A-D]", official.upper()))
        actual = set(re.findall(r"[A-D]", selected.upper()))
        if not expected:
            return None
        return expected == actual
    if question.question_type == "NAT":
        expected_nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", official.replace(",", ""))]
        actual_num = parse_numeric(selected)
        if actual_num is None or not expected_nums:
            return None
        if len(expected_nums) >= 2 and re.search(r"(?:to|–|-|,)", official):
            low, high = min(expected_nums[:2]), max(expected_nums[:2])
            return low - 1e-9 <= actual_num <= high + 1e-9
        return abs(actual_num - expected_nums[0]) <= 1e-6 * max(1.0, abs(expected_nums[0]))
    return None


def _level_filter(level: str, ref_id: int):
    column = {
        "subject": Question.subject_id,
        "topic": Question.topic_id,
        "subtopic": Question.subtopic_id,
        "concept": None,
    }.get(level)
    if level == "concept":
        from app.models import QuestionConcept

        return Question.id.in_(
            select(QuestionConcept.question_id).where(QuestionConcept.concept_id == ref_id)
        )
    if column is None:
        raise ValueError(f"Unsupported level {level}")
    return column == ref_id


def update_progress_for_question(db: Session, question: Question) -> None:
    refs: list[tuple[str, int]] = []
    if question.subject_id:
        refs.append(("subject", question.subject_id))
    if question.topic_id:
        refs.append(("topic", question.topic_id))
    if question.subtopic_id:
        refs.append(("subtopic", question.subtopic_id))
    for concept in question.concepts:
        refs.append(("concept", concept.id))
    for level, ref_id in refs:
        _recompute(db, level, ref_id)


def _recompute(db: Session, level: str, ref_id: int) -> None:
    condition = _level_filter(level, ref_id)
    row = db.execute(
        select(
            func.count(Attempt.id),
            func.count(distinct(Attempt.question_id)),
            func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)),
            func.sum(case((Attempt.is_correct.is_(False), 1), else_=0)),
            func.sum(Attempt.time_spent_seconds),
            func.max(Attempt.completed_at),
        )
        .join(Question, Question.id == Attempt.question_id)
        .where(condition)
    ).one()
    attempted, distinct_questions, correct, incorrect, seconds, last_at = row
    correct = int(correct or 0)
    incorrect = int(incorrect or 0)
    progress = db.scalar(
        select(Progress).where(Progress.level == level, Progress.ref_id == ref_id)
    )
    if progress is None:
        progress = Progress(level=level, ref_id=ref_id)
        db.add(progress)
    progress.attempted = int(attempted or 0)
    progress.distinct_questions = int(distinct_questions or 0)
    progress.correct = correct
    progress.incorrect = incorrect
    progress.time_spent_seconds = int(seconds or 0)
    progress.last_attempted_at = last_at
    progress.updated_at = utcnow()
    db.flush()


def mastery_for(progress: Progress | None, db: Session) -> str:
    if progress is None or progress.distinct_questions == 0:
        return "not_started"
    if progress.manual_status:
        return progress.manual_status
    strong_acc = float(get_setting(db, "mastery_strong_accuracy", 0.75))
    strong_min = int(get_setting(db, "mastery_strong_min_attempts", 5))
    strong_q = int(get_setting(db, "mastery_strong_min_questions", 3))
    revision_acc = float(get_setting(db, "mastery_revision_accuracy", 0.55))
    graded = progress.correct + progress.incorrect
    if graded == 0:
        return "learning"
    accuracy = progress.correct / graded
    if accuracy < revision_acc and graded >= 2:
        return "needs_revision"
    if (
        accuracy >= strong_acc
        and graded >= strong_min
        and progress.distinct_questions >= strong_q
    ):
        return "strong"
    if graded >= 2:
        return "practising"
    return "learning"


def record_attempt(
    db: Session,
    *,
    question: Question,
    selected_answer: str | None,
    mode: str,
    time_spent_seconds: int,
    working_text: str = "",
    confidence: str | None = None,
) -> Attempt:
    correct = is_correct_answer(question, selected_answer, db)
    marks_awarded = _calculate_marks_awarded(question, correct, selected_answer)
    attempt = Attempt(
        question_id=question.id,
        selected_answer=selected_answer,
        is_correct=correct,
        marks_awarded=marks_awarded,
        mode=mode,
        confidence=confidence,
        working_text=working_text,
        time_spent_seconds=max(0, int(time_spent_seconds)),
        completed_at=utcnow(),
    )
    db.add(attempt)
    db.flush()
    update_progress_for_question(db, question)
    _schedule_revision(db, question, correct)
    db.commit()
    db.refresh(attempt)
    return attempt


def _calculate_marks_awarded(
    question: Question, correct: bool | None, selected_answer: str | None
) -> float | None:
    """Calculate marks awarded for an attempt.

    MCQ: +marks for correct, negative_marks for incorrect (if negative marking applies).
    MSQ: +marks for correct, 0 for incorrect (no negative marking unless specified).
    NAT: +marks for correct, 0 for incorrect (no negative marking unless specified).
    No official answer: None (ungraded).
    """
    if correct is None or question.marks is None:
        return None
    if correct:
        return question.marks
    if question.question_type == "MCQ" and question.negative_marks is not None:
        return question.negative_marks
    # MSQ and NAT: no negative marking by default
    return 0.0


def _schedule_revision(db: Session, question: Question, correct: bool | None) -> None:
    item = db.scalar(select(RevisionItem).where(RevisionItem.question_id == question.id))
    if item is None:
        item = RevisionItem(
            question_id=question.id,
            repetitions=0,
            interval_days=1,
            ease=2.5,
            lapses=0,
        )
        db.add(item)
    now = utcnow()
    if correct is True:
        item.repetitions += 1
        if item.repetitions == 1:
            item.interval_days = 1
        elif item.repetitions == 2:
            item.interval_days = 6
        else:
            item.interval_days = max(1, round(item.interval_days * item.ease))
        item.ease = min(2.8, item.ease + 0.05)
    else:
        item.repetitions = 0
        item.interval_days = 1
        item.lapses += 1
        item.ease = max(1.3, item.ease - 0.2)
    item.last_reviewed_at = now
    item.due_at = now + timedelta(days=item.interval_days)
    db.flush()


def due_revisions(db: Session, limit: int = 50) -> list[dict]:
    rows = db.execute(
        select(RevisionItem, Question)
        .join(Question, Question.id == RevisionItem.question_id)
        .where(RevisionItem.due_at <= utcnow(), Question.import_status == "approved")
        .order_by(RevisionItem.due_at)
        .limit(limit)
    ).all()
    return [
        {
            "question_id": q.id,
            "year": q.year,
            "question_no": q.question_no,
            "session": q.session,
            "question_type": q.question_type,
            "question_text": q.question_text[:300],
            "due_at": item.due_at.isoformat(),
            "interval_days": item.interval_days,
            "lapses": item.lapses,
        }
        for item, q in rows
    ]


def progress_payload(db: Session, level: str, ref: dict) -> dict:
    progress = db.scalar(
        select(Progress).where(Progress.level == level, Progress.ref_id == ref["id"])
    )
    attempted = progress.attempted if progress else 0
    correct = progress.correct if progress else 0
    graded = correct + (progress.incorrect if progress else 0)
    return {
        **ref,
        "level": level,
        "questions_available": _available_count(db, level, ref["id"]),
        "attempted": progress.attempted if progress else 0,
        "distinct_questions": progress.distinct_questions if progress else 0,
        "correct": correct,
        "incorrect": progress.incorrect if progress else 0,
        "accuracy": round(correct / graded, 4) if graded else None,
        "time_spent_seconds": progress.time_spent_seconds if progress else 0,
        "last_attempted_at": progress.last_attempted_at.isoformat() if progress and progress.last_attempted_at else None,
        "mastery": mastery_for(progress, db),
        "manual_status": progress.manual_status if progress else None,
    }


def _available_count(db: Session, level: str, ref_id: int) -> int:
    condition = _level_filter(level, ref_id)
    return int(
        db.scalar(
            select(func.count(Question.id)).where(
                condition, Question.import_status == "approved"
            )
        )
        or 0
    )


def subject_progress(db: Session) -> list[dict]:
    subjects = db.scalars(select(Subject).order_by(Subject.display_order)).all()
    result = []
    for subject in subjects:
        result.append(
            progress_payload(db, "subject", {"id": subject.id, "name": subject.name, "code": subject.code})
        )
    return result


def topic_progress(db: Session, subject_id: int | None = None) -> list[dict]:
    query = select(Topic).order_by(Topic.display_order)
    if subject_id:
        query = query.where(Topic.subject_id == subject_id)
    topics = db.scalars(query).all()
    result = []
    for topic in topics:
        payload = progress_payload(db, "topic", {"id": topic.id, "name": topic.name, "subject_id": topic.subject_id})
        if payload["questions_available"] or payload["attempted"]:
            result.append(payload)
    return result


def weak_strong_topics(db: Session, limit: int = 8) -> dict:
    topics = topic_progress(db)
    scored = [t for t in topics if t["accuracy"] is not None]
    weak = sorted(scored, key=lambda t: (t["accuracy"], -t["attempted"]))[:limit]
    strong = sorted(scored, key=lambda t: (-t["accuracy"], -t["attempted"]))[:limit]
    return {"weak": weak, "strong": strong}


def overall_stats(db: Session) -> dict:
    approved = int(
        db.scalar(select(func.count(Question.id)).where(Question.import_status == "approved")) or 0
    )
    attempted_distinct = int(
        db.scalar(
            select(func.count(distinct(Attempt.question_id))).join(
                Question, Question.id == Attempt.question_id
            ).where(Question.import_status == "approved")
        )
        or 0
    )
    correct = int(
        db.scalar(
            select(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0))).where(
                Attempt.is_correct.isnot(None)
            )
        )
        or 0
    )
    graded = int(
        db.scalar(select(func.count(Attempt.id)).where(Attempt.is_correct.isnot(None))) or 0
    )
    seconds = int(db.scalar(select(func.sum(Attempt.time_spent_seconds))) or 0)
    due = int(
        db.scalar(select(func.count(RevisionItem.id)).where(RevisionItem.due_at <= utcnow())) or 0
    )
    return {
        "questions_available": approved,
        "questions_attempted": attempted_distinct,
        "questions_remaining": max(0, approved - attempted_distinct),
        "graded_attempts": graded,
        "correct_attempts": correct,
        "accuracy": round(correct / graded, 4) if graded else None,
        "time_spent_seconds": seconds,
        "due_revisions": due,
        "completion": round(attempted_distinct / approved, 4) if approved else 0,
    }


def recent_activity(db: Session, limit: int = 10) -> list[dict]:
    rows = db.execute(
        select(Attempt, Question)
        .join(Question, Question.id == Attempt.question_id)
        .order_by(Attempt.started_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "attempt_id": attempt.id,
            "question_id": question.id,
            "year": question.year,
            "question_no": question.question_no,
            "is_correct": attempt.is_correct,
            "mode": attempt.mode,
            "at": (attempt.completed_at or attempt.started_at).isoformat(),
            "excerpt": question.question_text[:160],
        }
        for attempt, question in rows
    ]
