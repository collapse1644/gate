"""HTTP smoke tests for the assembled application."""

from __future__ import annotations

import base64

from app.config import settings
from app.models import QuestionAsset


PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_health_and_seeded_syllabus(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["startup"]["seeded"] is True

    syllabus = client.get("/api/syllabus").json()
    assert syllabus["version"]["year"] == 2027
    assert len(syllabus["sections"]) == 14
    assert len(syllabus["subjects"]) == 11

    subjects = client.get("/api/subjects").json()["subjects"]
    assert len(subjects) == 11


def test_settings_secrets_are_masked(client):
    response = client.put(
        "/api/settings",
        json={"values": {"gemini_api_key": "super-secret-key", "ai_mode": "local_only"}},
    )
    assert response.status_code == 200
    values = response.json()["settings"]
    assert values["gemini_api_key_set"] is True
    assert values["ai_mode"] == "local_only"
    assert "super-secret-key" not in str(values)
    assert values["gemini_api_key"] != "super-secret-key"
    assert values["gemini_api_key"]


def test_question_library_search_and_detail(client, make_question):
    question = make_question(text="Binary search runs in logarithmic time on sorted arrays.")
    listing = client.get("/api/questions", params={"q": "binary"}).json()
    assert listing["total"] >= 1
    ids = [item["id"] for item in listing["items"]]
    assert question.id in ids

    detail = client.get(f"/api/questions/{question.id}").json()
    assert detail["id"] == question.id
    assert "Binary search" in detail["question_text"]


def test_practice_session_hides_answer_until_submission(client, make_question):
    question = make_question(official_answer="B")
    created = client.post(
        "/api/practice/sessions",
        json={"mode": "random", "limit": 5, "shuffle": False},
    )
    assert created.status_code == 200
    session = created.json()
    assert session["total_questions"] == 1
    assert session["questions"][0]["official_answer"] is None

    answered = client.post(
        f"/api/practice/sessions/{session['id']}/answer",
        json={"question_id": question.id, "selected_answer": "B", "time_spent_seconds": 30},
    )
    assert answered.status_code == 200
    body = answered.json()
    assert body["is_correct"] is True
    assert body["official_answer"] == "B"
    assert body["session"]["completed"] is True


def test_full_paper_session_preserves_order(client, make_paper, make_question):
    paper = make_paper(2024, "Session 2")
    first = make_question(text="First question in the paper.", paper=paper, year=2024)
    second = make_question(text="Second question in the paper.", paper=paper, year=2024)

    from app.db import SessionLocal

    with SessionLocal() as session:
        session.query(type(first)).filter_by(id=first.id).update({"question_no": 7})
        session.query(type(second)).filter_by(id=second.id).update({"question_no": 1})
        session.commit()

    created = client.post(
        "/api/practice/sessions",
        json={"mode": "full_paper", "paper_id": paper.id},
    ).json()
    numbers = [item["question_no"] for item in created["questions"]]
    assert numbers == [1, 7]


def test_assets_cannot_escape_data_directory(client, db, make_question):
    question = make_question()
    outside = QuestionAsset(question_id=question.id, path="../outside.png", page=1)
    db.add(outside)
    db.commit()
    db.refresh(outside)
    assert client.get(f"/api/assets/{outside.id}").status_code == 400

    settings.assets_dir.mkdir(parents=True, exist_ok=True)
    image = settings.assets_dir / "figure.png"
    image.write_bytes(PNG_1PX)
    inside = QuestionAsset(question_id=question.id, path="assets/figure.png", page=1)
    db.add(inside)
    db.commit()
    db.refresh(inside)
    response = client.get(f"/api/assets/{inside.id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_settings_update_preserves_encrypted_key(client):
    """Updating unrelated settings must not overwrite the encrypted API key."""
    # First set a real key
    client.put(
        "/api/settings",
        json={"values": {"gemini_api_key": "real-secret-key-12345", "ai_mode": "auto"}},
    )
    # Read back: key should be masked but set
    values = client.get("/api/settings").json()["settings"]
    assert values["gemini_api_key_set"] is True
    assert values["gemini_api_key"] != "real-secret-key-12345"
    assert "real-secret-key-12345" not in str(values)

    # Update an unrelated setting WITHOUT sending the key
    response = client.put(
        "/api/settings",
        json={"values": {"ai_mode": "local_only"}},
    )
    assert response.status_code == 200
    values2 = response.json()["settings"]
    assert values2["ai_mode"] == "local_only"
    assert values2["gemini_api_key_set"] is True
    # The key must still be the same (masked), not overwritten with placeholder
    assert values2["gemini_api_key"] == values["gemini_api_key"]
    assert "***" in values2["gemini_api_key"] or values2["gemini_api_key"] == ""


def test_pdf_page_rendering(client, db, make_question, make_paper):
    """PDF page endpoint renders the source page as a PNG."""
    import pymupdf

    from app.config import settings

    paper = make_paper(2024, "Set 1")
    # Create a minimal PDF file under data_dir so it passes the path check
    pdf_path = settings.data_dir / "test_page_render.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test PDF content", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    question = make_question(
        text="Test question for PDF rendering.",
        paper=paper,
        year=2024,
        source_pdf=str(pdf_path),
        source_page=1,
    )
    response = client.get(f"/api/questions/{question.id}/pdf-page?dpi=100")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_pdf_page_rendering_missing_pdf(client, db, make_question):
    """PDF page endpoint returns 404 when source PDF is missing."""
    question = make_question(
        text="Test question without source PDF.",
        source_pdf="",
        source_page=1,
    )
    response = client.get(f"/api/questions/{question.id}/pdf-page")
    assert response.status_code == 404


def test_staged_question_preview_attempt(client, make_question):
    """Staged questions can be attempted in preview mode."""
    question = make_question(
        official_answer="B",
        import_status="staged",
    )
    response = client.post(
        f"/api/questions/{question.id}/attempts",
        json={
            "selected_answer": "B",
            "mode": "preview",
            "time_spent_seconds": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["preview"] is True
    assert body["is_correct"] is True
    assert body["official_answer"] == "B"


def test_staged_question_without_answer_preview(client, make_question):
    """Staged question without official answer returns is_correct=None in preview."""
    question = make_question(
        official_answer=None,
        import_status="staged",
    )
    response = client.post(
        f"/api/questions/{question.id}/attempts",
        json={
            "selected_answer": "42",
            "mode": "preview",
            "time_spent_seconds": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["preview"] is True
    assert body["is_correct"] is None  # Cannot grade without official answer
    assert body["official_answer"] is None


def test_settings_masked_key_is_not_overwritten(client):
    """A masked placeholder from get_all_settings must not replace the real key."""
    client.put(
        "/api/settings",
        json={"values": {"gemini_api_key": "real-secret-key-12345"}},
    )
    # Simulate frontend sending back the masked value along with unrelated changes
    masked = client.get("/api/settings").json()["settings"]["gemini_api_key"]
    assert masked  # should be a non-empty mask
    response = client.put(
        "/api/settings",
        json={"values": {"gemini_api_key": masked, "backup_retention": 20}},
    )
    assert response.status_code == 200
    values2 = response.json()["settings"]
    # Key set flag must remain True (real key preserved)
    assert values2["gemini_api_key_set"] is True
    assert values2["backup_retention"] == 20


def test_review_queue_and_dashboard_empty_states(client):
    queue = client.get("/api/review/queue").json()
    assert queue["total"] == 0
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["empty_state"] is True
    assert dashboard["stats"]["questions_available"] == 0
