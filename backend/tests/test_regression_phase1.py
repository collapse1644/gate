from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pymupdf
import pytest

from app.services.pdf_extract import (
    TextLine,
    _strip_headers,
    detect_year_session,
    inspect_pdf,
)
from app.services.classifier import classify_question


def write_pdf(path: Path, lines: list[str]) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    for line in lines:
        page.insert_text((50, y), line, fontsize=10)
        y += 18
    doc.save(path)
    doc.close()
    return path


def test_filename_year_parsing():
    year, session = detect_year_session("2024_CS1.pdf", "")
    assert year == 2024
    year2, session2 = detect_year_session("2024_CS2.pdf", "")
    assert year2 == 2024
    assert session2 == "Set 2"


def test_option_markers_preserved_in_strip_headers():
    lines = [TextLine(page=i % 3, text="(A)", x0=0, y0=0, x1=10, y1=10) for i in range(12)]
    kept = _strip_headers(lines, 3)
    assert len(kept) == 12


def test_word_based_marks_parsing(tmp_path):
    pdf = write_pdf(
        tmp_path / "CS_GATE2024_Question_Paper.pdf",
        [
            "GATE 2024",
            "Q.1 to Q.2 Carry ONE mark Each.",
            "Q.1 What is a stack?",
            "(A) LIFO",
            "(B) FIFO",
            "(C) Random",
            "(D) None",
            "Q.2 Which sort is stable?",
            "(A) Quick",
            "(B) Merge",
            "(C) Heap",
            "(D) Selection",
        ],
    )
    info = inspect_pdf(pdf)
    assert info.kind == "question_paper"
    assert info.year == 2024
    assert len(info.questions) == 2
    assert all(q.marks == 1.0 for q in info.questions)


def test_set_session_detection():
    year, session = detect_year_session("2024_CS2.pdf", "GATE 2024 Computer Science Set 2")
    assert year == 2024
    assert session == "Set 2"
    _, session1 = detect_year_session("2023_CS.pdf", "GATE 2023 Set 1")
    assert session1 == "Set 1"


def test_multiline_question_detection(tmp_path):
    pdf = write_pdf(
        tmp_path / "CS_GATE2024_Question_Paper_multiline.pdf",
        [
            "GATE 2024",
            "Q.1 to Q.1 carry 1 mark.",
            "Q.1",
            "Consider the following",
            "multi-line question text.",
            "(A) Option A",
            "(B) Option B",
            "(C) Option C",
            "(D) Option D",
        ],
    )
    info = inspect_pdf(pdf)
    assert len(info.questions) == 1
    assert "multi-line" in info.questions[0].text


def test_classifier_concept_ids_are_unique(db):
    result = classify_question(
        db,
        text="Explain deadlock prevention in operating systems.",
        options=[],
    )
    assert len(result.concept_ids) == len(set(result.concept_ids))


def test_raw_text_preserved_distinct_from_normalized(client, tmp_path):
    # Reuse build_zip from test_ingestion by constructing minimal
    import io, zipfile, pymupdf

    def make_pdf(lines):
        doc = pymupdf.open()
        page = doc.new_page()
        y = 60
        for line in lines:
            page.insert_text((50, y), line, fontsize=10)
            y += 18
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        return buf.getvalue()

    question_pdf = make_pdf(
        [
            "GATE 2025 — Session 1",
            "Q.1 to Q.2 carry 1 mark each.",
            "Q.1 Which data structure uses the master theorem?",
            "(A) Stack",
            "(B) Divide and conquer recursion",
            "(C) Queue",
            "(D) Hash table",
        ]
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("2025/CS_GATE2025_Question_Paper_Session_1.pdf", question_pdf)
    archive_bytes = archive.getvalue()

    response = client.post(
        "/api/ingestion/upload",
        files={"file": ("raw.zip", archive_bytes, "application/zip")},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    job = client.get(f"/api/ingestion/{job_id}").json()
    assert job["job"]["status"] in {"completed", "completed_with_errors"}

    listing = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    assert listing["total"] >= 1
    q = client.get(f"/api/questions/{listing['items'][0]['id']}").json()
    assert q.get("raw_text") is not None
    assert q["question_text"] is not None


def test_reimport_does_not_overwrite_manual_classification(client, tmp_path):
    # Build a minimal zip
    question_pdf = None
    import pymupdf, io
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    for line in [
        "GATE 2025 — Session 1",
        "Q.1 to Q.2 carry 1 mark each.",
        "Q.1 Which data structure uses the master theorem?",
        "(A) Stack",
        "(B) Divide and conquer recursion",
        "(C) Queue",
        "(D) Hash table",
        "Q.2 Which normal form removes transitive dependencies?",
        "(A) 1NF",
        "(B) 2NF",
        "(C) 3NF",
        "(D) BCNF",
    ]:
        page.insert_text((50, y), line, fontsize=10)
        y += 18
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    question_pdf = buf.getvalue()

    answer_pdf = None
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    for line in ["GATE 2025 — Session 1 — Answer Key", "1 B", "2 C"]:
        page.insert_text((50, y), line, fontsize=10)
        y += 18
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    answer_pdf = buf.getvalue()

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("2025/CS_GATE2025_Question_Paper_Session_1.pdf", question_pdf)
        bundle.writestr("2025/CS_GATE2025_Answer_Key_Session_1.pdf", answer_pdf)
    archive_bytes = archive.getvalue()

    response = client.post(
        "/api/ingestion/upload",
        files={"file": ("gate2025.zip", archive_bytes, "application/zip")},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    job = client.get(f"/api/ingestion/{job_id}").json()
    assert job["job"]["status"] in {"completed", "completed_with_errors"}

    listing = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    assert listing["total"] == 2
    qid = listing["items"][0]["id"]

    # Manual classification correction
    manual = client.post(
        f"/api/questions/{qid}/classification",
        json={
            "subject_id": listing["items"][0]["subject_id"],
            "topic_id": listing["items"][0]["topic_id"],
            "subtopic_id": listing["items"][0]["subtopic_id"],
            "concept_ids": [],
            "reason": "manual test",
            "accept": True,
        },
    )
    assert manual.status_code == 200
    before = client.get(f"/api/questions/{qid}").json()
    assert before["classification_method"] == "manual"

    # Re-import same zip (duplicate content) should not overwrite
    response2 = client.post(
        "/api/ingestion/upload",
        files={"file": ("gate2025.zip", archive_bytes, "application/zip")},
    )
    assert response2.status_code == 200
    after = client.get(f"/api/questions/{qid}").json()
    assert after["classification_method"] == "manual"
    assert after["subject_id"] == before["subject_id"]