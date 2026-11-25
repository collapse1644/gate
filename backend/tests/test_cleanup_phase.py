from __future__ import annotations

from fastapi.testclient import TestClient


def test_taxonomy_validation_endpoint(client):
    r = client.get("/api/taxonomy/validate")
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body
    assert "counts" in body
    assert body["counts"]["subjects"] >= 1


def test_raw_text_coverage_in_data_overview(client):
    r = client.get("/api/data/overview")
    assert r.status_code == 200
    body = r.json()
    assert "raw_text_coverage" in body
    cov = body["raw_text_coverage"]
    assert "total_questions" in cov
    assert "raw_text_populated" in cov
    assert "raw_text_missing" in cov


def test_benchmark_provenance_defaults_ai_assisted(client):
    # create a question first
    from app.db import SessionLocal
    from app.models import Question, Subject, Topic, Subtopic
    import hashlib
    db = SessionLocal()
    subject = db.query(Subject).filter(Subject.code == "ALGO").one()
    topic = subject.topics[0]
    subtopic = topic.subtopics[0]
    q = Question(
        year=2025,
        question_no=999,
        question_text="What is a graph?",
        question_type="MCQ",
        marks=1,
        subject_id=subject.id,
        section_id=topic.section_id,
        topic_id=topic.id,
        subtopic_id=subtopic.id,
        source_question_hash=hashlib.sha256(b"graph-999").hexdigest(),
        import_status="staged",
    )
    db.add(q)
    db.commit()
    qid = q.id
    db.close()

    r = client.post(f"/api/questions/{qid}/benchmark", json={
        "expected_subject_id": subject.id,
        "expected_topic_id": topic.id,
        "expected_subtopic_id": subtopic.id,
        "notes": "test",
    })
    assert r.status_code == 200

    bench = client.get("/api/review/benchmark").json()
    row = next((d for d in bench["report"]["details"] if d["question_id"] == qid), None)
    assert row is not None
    assert row["label_source"] == "ai_assisted"
    assert bench["report"]["human_verified_count"] == 0


def test_human_verified_accuracy_excludes_ai_assisted(client):
    # same as above but label_source human_verified
    from app.db import SessionLocal
    from app.models import Question, Subject, Topic, Subtopic
    import hashlib
    db = SessionLocal()
    subject = db.query(Subject).filter(Subject.code == "ALGO").one()
    topic = subject.topics[0]
    subtopic = topic.subtopics[0]
    q = Question(
        year=2025,
        question_no=1000,
        question_text="What is a tree?",
        question_type="MCQ",
        marks=1,
        subject_id=subject.id,
        section_id=topic.section_id,
        topic_id=topic.id,
        subtopic_id=subtopic.id,
        source_question_hash=hashlib.sha256(b"tree-1000").hexdigest(),
        import_status="staged",
    )
    db.add(q)
    db.commit()
    qid = q.id
    db.close()

    r = client.post(f"/api/questions/{qid}/benchmark", json={
        "expected_subject_id": subject.id,
        "expected_topic_id": topic.id,
        "expected_subtopic_id": subtopic.id,
        "label_source": "human_verified",
        "reviewer": "tester",
        "notes": "human",
    })
    assert r.status_code == 200

    bench = client.get("/api/review/benchmark").json()
    assert bench["report"]["human_verified_count"] >= 1