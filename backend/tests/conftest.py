"""Shared pytest fixtures.

The test database lives in a temporary directory and is rebuilt before every
test so tests never touch ``backend/data/gate.db``.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="gate-tests-"))
os.environ.setdefault("GATE_DATABASE_URL", f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}")
os.environ.setdefault("GATE_DATA_DIR", str(TEST_ROOT / "data"))

from app.db import Base, SessionLocal, engine, init_fts  # noqa: E402
from app.models import Paper, Question, Subject  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS question_fts")
    Base.metadata.create_all(engine)
    init_fts()
    with SessionLocal() as session:
        seed(session)
        yield session
        session.rollback()


@pytest.fixture()
def make_paper(db):
    def _make(year: int = 2025, session: str = "Session 1") -> Paper:
        paper = Paper(
            year=year,
            session=session,
            label=f"GATE {year} CS {session}",
            question_count=0,
        )
        db.add(paper)
        db.commit()
        db.refresh(paper)
        return paper

    return _make


@pytest.fixture()
def make_question(db):
    counter = {"n": 0}

    def _make(
        *,
        text: str = "What is the time complexity of binary search?",
        paper: Paper | None = None,
        subject: Subject | None = None,
        question_type: str = "MCQ",
        official_answer: str | None = "B",
        marks: float | None = 1,
        year: int = 2025,
        import_status: str = "approved",
        **kwargs,
    ) -> Question:
        counter["n"] += 1
        if subject is None:
            subject = db.query(Subject).filter(Subject.code == "ALGO").one()
        topic = subject.topics[0]
        subtopic = topic.subtopics[0]
        question = Question(
            year=year,
            question_no=counter["n"],
            question_text=text,
            options=[
                {"key": "A", "text": "O(1)"},
                {"key": "B", "text": "O(log n)"},
                {"key": "C", "text": "O(n)"},
                {"key": "D", "text": "O(n log n)"},
            ],
            question_type=question_type,
            official_answer=official_answer,
            marks=marks,
            subject_id=subject.id,
            section_id=topic.section_id,
            topic_id=topic.id,
            subtopic_id=subtopic.id,
            paper_id=paper.id if paper else None,
            import_status=import_status,
            source_question_hash=hashlib.sha256(
                f"{text}-{counter['n']}-{year}".encode()
            ).hexdigest(),
            **kwargs,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    return _make


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
