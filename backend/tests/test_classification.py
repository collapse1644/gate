"""Hybrid classification: taxonomy routing, confidence and no forced mapping."""

from __future__ import annotations

from app.models import Subject
from app.services.classifier import classify_question, taxonomy_tree


def test_recurrence_question_routes_to_algorithms(db):
    result = classify_question(
        db,
        text=(
            "Solve the recurrence relation T(n) = 2T(n/2) + n using the master theorem "
            "and state the asymptotic complexity."
        ),
        options=[
            {"key": "A", "text": "O(n)"},
            {"key": "B", "text": "O(n log n)"},
        ],
    )
    algo = db.query(Subject).filter(Subject.code == "ALGO").one()
    assert result.out_of_syllabus is False
    assert result.subject_id == algo.id
    assert result.subtopic_id is not None
    assert "recurrence" in result.explanation.lower()
    assert 0.0 < result.confidence <= 1.0
    assert result.review_status in {"auto_accepted", "pending"}


def test_deadlock_question_routes_to_operating_systems(db):
    result = classify_question(
        db,
        text=(
            "Use Banker's algorithm to determine whether the system is in a safe state "
            "and explain deadlock avoidance."
        ),
    )
    os_subject = db.query(Subject).filter(Subject.code == "OS").one()
    assert result.subject_id == os_subject.id
    assert result.topic_id is not None


def test_unrelated_text_is_not_forced_into_syllabus(db):
    result = classify_question(
        db,
        text="Zzzqqq wxyzzy blorptastic frobnicate glimmering nonsense tokens only.",
    )
    assert result.out_of_syllabus is True
    assert result.subject_id is None
    assert result.subtopic_id is None
    assert result.confidence == 0.0


def test_llm_opinion_alone_never_auto_accepts(db):
    text = (
        "Solve the recurrence relation T(n) = 2T(n/2) + n using the master theorem "
        "and state the asymptotic complexity."
    )
    plain = classify_question(db, text=text)
    if plain.subtopic_id is None:
        return  # nothing to recommend; covered by the out-of-syllabus test
    with_llm = classify_question(
        db,
        text=text,
        llm_recommendation={"subtopic_id": plain.subtopic_id},
    )
    assert with_llm.method == "hybrid"
    assert with_llm.review_status != "auto_accepted"


def test_taxonomy_tree_is_complete(db):
    tree = taxonomy_tree(db)
    assert len(tree) == 11
    assert {node["code"] for node in tree} >= {"GA", "EM", "ALGO", "OS", "DB", "CN"}
    algo = next(node for node in tree if node["code"] == "ALGO")
    assert algo["topics"]
    assert all(topic["subtopics"] for topic in algo["topics"])
