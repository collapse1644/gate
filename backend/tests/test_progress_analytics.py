"""Progress, revision scheduling and analytics from uploaded papers only."""

from __future__ import annotations

from app.models import Attempt, Subject
from app.services.analytics import weightage
from app.services.progress import (
    due_revisions,
    is_correct_answer,
    overall_stats,
    record_attempt,
    subject_progress,
)


def test_mcq_and_nat_answer_matching(db, make_question):
    mcq = make_question(official_answer="B", question_type="MCQ")
    assert is_correct_answer(mcq, "B") is True
    assert is_correct_answer(mcq, "A") is False
    assert is_correct_answer(mcq, None) is None

    msq = make_question(official_answer="A,C", question_type="MSQ")
    assert is_correct_answer(msq, "C,A") is True
    assert is_correct_answer(msq, "A") is False

    nat = make_question(official_answer="10 to 12", question_type="NAT")
    assert is_correct_answer(nat, "11") is True
    assert is_correct_answer(nat, "9") is False


def test_record_attempt_updates_progress_and_revision(db, make_question):
    question = make_question(official_answer="B")
    attempt = record_attempt(
        db,
        question=question,
        selected_answer="B",
        mode="test",
        time_spent_seconds=42,
    )
    assert attempt.is_correct is True

    algo = db.query(Subject).filter(Subject.code == "ALGO").one()
    subject = next(row for row in subject_progress(db) if row["id"] == algo.id)
    assert subject["attempted"] == 1
    assert subject["correct"] == 1
    assert subject["accuracy"] == 1.0
    assert subject["mastery"] == "learning"
    assert subject["time_spent_seconds"] == 42

    stats = overall_stats(db)
    assert stats["questions_attempted"] == 1
    assert stats["correct_attempts"] == 1

    # A correct answer schedules the next revision in the future, not immediately.
    assert due_revisions(db) == []


def test_incorrect_answer_needs_revision(db, make_question):
    question = make_question(official_answer="B")
    record_attempt(db, question=question, selected_answer="D", mode="test", time_spent_seconds=10)
    record_attempt(db, question=question, selected_answer="A", mode="test", time_spent_seconds=10)
    algo = db.query(Subject).filter(Subject.code == "ALGO").one()
    subject = next(row for row in subject_progress(db) if row["id"] == algo.id)
    assert subject["incorrect"] == 2
    assert subject["mastery"] == "needs_revision"


def test_analytics_uses_only_uploaded_papers(db, make_paper, make_question):
    paper = make_paper(2025, "Session 1")
    algo = db.query(Subject).filter(Subject.code == "ALGO").one()
    os_subject = db.query(Subject).filter(Subject.code == "OS").one()
    make_question(text="Algorithm question about sorting.", paper=paper, subject=algo, marks=2)
    make_question(text="Operating system question about paging.", paper=paper, subject=os_subject, marks=1)
    # Approved but not part of an uploaded paper: must not be counted.
    make_question(text="Orphan question outside any paper.", paper=None, marks=5)

    report = weightage(db)
    assert report["papers_analyzed"] == 1
    assert report["questions_analyzed"] == 2
    by_code = {row["code"]: row for row in report["subjects"]}
    assert set(by_code) == {"ALGO", "OS"}
    assert by_code["ALGO"]["average_marks"] == 2.0
    assert by_code["OS"]["average_marks"] == 1.0
    assert abs(
        by_code["ALGO"]["average_percentage"] + by_code["OS"]["average_percentage"] - 100.0
    ) < 0.05
    assert report["papers"][0]["year"] == 2025


def test_analytics_empty_state_is_honest(db):
    report = weightage(db)
    assert report["papers_analyzed"] == 0
    assert report["questions_analyzed"] == 0
    assert report["subjects"] == []
    assert report["topics"] == []
    assert report["yearly"] == []
