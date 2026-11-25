from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Paper, Question, Subject, Topic


def _question_attribution(question: Question, policy: str) -> list[tuple[int, float]]:
    if not question.subject_id:
        return []
    secondary_subjects = []
    for topic in question.secondary_topics:
        if topic.subject_id and topic.subject_id != question.subject_id:
            secondary_subjects.append(topic.subject_id)
    secondary_subjects = list(dict.fromkeys(secondary_subjects))
    if policy == "split" and secondary_subjects:
        share = 1.0 / (1 + len(secondary_subjects))
        return [(question.subject_id, share)] + [(sid, share) for sid in secondary_subjects]
    return [(question.subject_id, 1.0)]


def weightage(
    db: Session,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    session: str | None = None,
) -> dict:
    query = select(Question).where(Question.import_status == "approved")
    if from_year:
        query = query.where(Question.year >= from_year)
    if to_year:
        query = query.where(Question.year <= to_year)
    if session:
        query = query.where(Question.session == session)
    questions = db.scalars(query).all()
    paper_ids = {q.paper_id for q in questions if q.paper_id}
    papers = db.scalars(
        select(Paper).where(Paper.id.in_(paper_ids)).order_by(Paper.year, Paper.session)
    ).all() if paper_ids else []
    # Exclude papers with zero approved questions (already implicit).
    paper_ids = {p.id for p in papers}
    questions = [q for q in questions if q.paper_id in paper_ids]
    policy = "primary"
    try:
        from app.settings_service import get_setting

        policy = get_setting(db, "attribution_policy", "primary")
    except Exception:  # noqa: BLE001
        pass

    subjects = {s.id: s for s in db.scalars(select(Subject)).all()}
    per_paper_subject: dict[tuple[int, int], float] = defaultdict(float)
    per_paper_subject_questions: dict[tuple[int, int], float] = defaultdict(float)
    missing_marks = 0
    for question in questions:
        if question.marks is None:
            missing_marks += 1
            continue
        for subject_id, share in _question_attribution(question, policy):
            per_paper_subject[(question.paper_id, subject_id)] += question.marks * share
            per_paper_subject_questions[(question.paper_id, subject_id)] += share

    paper_count = len(papers)
    paper_total_marks: dict[int, float] = defaultdict(float)
    for (paper_id, _subject_id), marks in per_paper_subject.items():
        paper_total_marks[paper_id] += marks

    subject_stats = []
    for subject_id, subject in subjects.items():
        marks_by_paper = {
            pid: per_paper_subject.get((pid, subject_id), 0.0) for pid in paper_ids
        }
        if not any(marks_by_paper.values()):
            continue
        total_marks = sum(marks_by_paper.values())
        total_pct = 0.0
        pct_papers = 0
        for pid, marks in marks_by_paper.items():
            total = paper_total_marks.get(pid, 0.0)
            if total > 0:
                total_pct += marks / total
                pct_papers += 1
        subject_stats.append(
            {
                "subject_id": subject_id,
                "subject": subject.name,
                "code": subject.code,
                "color": subject.color,
                "average_marks": round(total_marks / paper_count, 3) if paper_count else 0,
                "average_percentage": round(100 * total_pct / pct_papers, 2) if pct_papers else 0,
                "average_question_count": round(
                    sum(
                        per_paper_subject_questions.get((pid, subject_id), 0.0)
                        for pid in paper_ids
                    )
                    / paper_count,
                    2,
                )
                if paper_count
                else 0,
                "min_marks": round(min(marks_by_paper.values()), 3) if paper_count else 0,
                "max_marks": round(max(marks_by_paper.values()), 3) if paper_count else 0,
                "papers_present": sum(1 for m in marks_by_paper.values() if m > 0),
                "frequency": round(
                    sum(1 for m in marks_by_paper.values() if m > 0) / paper_count, 4
                )
                if paper_count
                else 0,
                "year_wise": [
                    {
                        "year": year,
                        "average_marks": round(
                            sum(
                                marks_by_paper.get(p.id, 0.0)
                                for p in papers
                                if p.year == year
                            )
                            / max(1, sum(1 for p in papers if p.year == year)),
                            3,
                        ),
                        "papers": sum(1 for p in papers if p.year == year),
                    }
                    for year in sorted({p.year for p in papers})
                ],
                "trend": _trend(marks_by_paper, papers),
            }
        )
    subject_stats.sort(key=lambda s: s["average_marks"], reverse=True)
    for stat in subject_stats:
        stat["raw_priority_score"] = round(
            0.45 * (stat["average_percentage"] / 100)
            + 0.25 * stat["frequency"]
            + 0.15 * max(0.0, min(1.0, (stat["trend"]["change"] + 0.25) * 2))
            + 0.15 * 1.0,
            4,
        )
    max_priority = max((s["raw_priority_score"] for s in subject_stats), default=1.0)
    for stat in subject_stats:
        stat["priority_score"] = round(100 * stat["raw_priority_score"] / max_priority, 1)
        stat["priority_band"] = (
            "High" if stat["priority_score"] >= 70 else "Medium" if stat["priority_score"] >= 40 else "Lower"
        )

    topic_stats = _topic_stats(db, questions, papers, policy, paper_count)
    yearly = _yearly(questions, papers, paper_count)
    return {
        "filters": {"from_year": from_year, "to_year": to_year, "session": session},
        "papers_analyzed": paper_count,
        "papers": [
            {
                "id": p.id,
                "year": p.year,
                "session": p.session,
                "label": p.label,
                "question_count": p.question_count,
                "total_marks": p.total_marks,
            }
            for p in papers
        ],
        "questions_analyzed": len(questions),
        "questions_missing_marks": missing_marks,
        "attribution_policy": policy,
        "attribution_note": (
            "Primary topic receives all marks."
            if policy != "split"
            else "Marks are split equally between the primary subject and distinct secondary subjects."
        ),
        "subjects": subject_stats,
        "topics": topic_stats,
        "yearly": yearly,
        "priority_formula": (
            "0.45 × normalized average marks percentage + 0.25 × paper frequency + "
            "0.15 × recent trend + 0.15 × syllabus relevance. Priority is a study-ordering heuristic, "
            "not a prediction of future questions."
        ),
    }


def _trend(marks_by_paper: dict[int, float], papers: list[Paper]) -> dict:
    if not papers:
        return {"change": 0.0, "recent_average": 0.0, "earlier_average": 0.0, "direction": "stable"}
    by_year: dict[int, list[float]] = defaultdict(list)
    for paper in papers:
        by_year[paper.year].append(marks_by_paper.get(paper.id, 0.0))
    years = sorted(by_year)
    recent_years = years[-3:]
    earlier_years = years[: max(0, len(years) - 3)] or years[:1]
    recent = [sum(by_year[y]) / len(by_year[y]) for y in recent_years]
    earlier = [sum(by_year[y]) / len(by_year[y]) for y in earlier_years]
    recent_avg = sum(recent) / len(recent) if recent else 0
    earlier_avg = sum(earlier) / len(earlier) if earlier else 0
    change = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0.0
    direction = "rising" if change > 0.12 else "falling" if change < -0.12 else "stable"
    return {
        "change": round(change, 4),
        "recent_average": round(recent_avg, 3),
        "earlier_average": round(earlier_avg, 3),
        "direction": direction,
        "recent_years": recent_years,
    }


def _topic_stats(
    db: Session,
    questions: list[Question],
    papers: list[Paper],
    policy: str,
    paper_count: int,
) -> list[dict]:
    topics = {t.id: t for t in db.scalars(select(Topic)).all()}
    per_topic: dict[int, float] = defaultdict(float)
    per_topic_questions: dict[int, int] = defaultdict(int)
    for question in questions:
        if not question.topic_id or question.marks is None:
            continue
        per_topic[question.topic_id] += question.marks
        per_topic_questions[question.topic_id] += 1
    total = sum(per_topic.values())
    result = []
    for topic_id, marks in per_topic.items():
        topic = topics.get(topic_id)
        if not topic:
            continue
        result.append(
            {
                "topic_id": topic_id,
                "topic": topic.name,
                "subject_id": topic.subject_id,
                "marks": round(marks, 3),
                "average_marks": round(marks / paper_count, 3) if paper_count else 0,
                "share": round(100 * marks / total, 2) if total else 0,
                "questions": per_topic_questions[topic_id],
            }
        )
    result.sort(key=lambda x: x["marks"], reverse=True)
    return result


def _yearly(questions: list[Question], papers: list[Paper], paper_count: int) -> list[dict]:
    years = sorted({p.year for p in papers})
    result = []
    for year in years:
        year_papers = [p for p in papers if p.year == year]
        year_questions = [q for q in questions if q.year == year]
        marks = sum(q.marks or 0 for q in year_questions)
        result.append(
            {
                "year": year,
                "papers": len(year_papers),
                "questions": len(year_questions),
                "average_marks_per_paper": round(marks / len(year_papers), 3)
                if year_papers
                else 0,
            }
        )
    return result
