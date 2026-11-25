"""End-to-end ZIP ingestion: two PDFs, answer association, approval, practice."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pymupdf

QUESTION_LINES = [
    "GATE 2025 — Session 1",
    "Q.1 to Q.2 carry 1 mark each.",
    "Q.1 Which data structure uses the master theorem for recurrence analysis?",
    "(A) Stack",
    "(B) Divide and conquer recursion",
    "(C) Queue",
    "(D) Hash table",
    "Q.2 Which normal form removes transitive dependencies?",
    "(A) 1NF",
    "(B) 2NF",
    "(C) 3NF",
    "(D) BCNF",
]

ANSWER_LINES = ["GATE 2025 — Session 1 — Answer Key", "1 B", "2 C"]


def make_pdf(path: Path, lines: list[str]) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    for line in lines:
        page.insert_text((50, y), line, fontsize=10)
        y += 18
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def build_zip(tmp_path: Path) -> bytes:
    question_pdf = make_pdf(tmp_path / "q.pdf", QUESTION_LINES)
    answer_pdf = make_pdf(tmp_path / "a.pdf", ANSWER_LINES)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "2025/CS_GATE2025_Question_Paper_Session_1.pdf", question_pdf
        )
        bundle.writestr("2025/CS_GATE2025_Answer_Key_Session_1.pdf", answer_pdf)
        bundle.writestr("notes/readme.txt", "hello")
    return archive.getvalue()


def test_zip_ingestion_to_practice(client, tmp_path):
    archive = build_zip(tmp_path)
    response = client.post(
        "/api/ingestion/upload",
        files={"file": ("gate2025.zip", archive, "application/zip")},
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]

    job = client.get(f"/api/ingestion/{job_id}").json()
    assert job["job"]["status"] in {"completed", "completed_with_errors"}
    kinds = {file["kind"] for file in job["files"]}
    assert "pdf" in kinds

    listing = client.get(
        "/api/questions", params={"year": 2025, "include_staged": True}
    ).json()
    assert listing["total"] == 2
    by_no = {item["question_no"]: item for item in listing["items"]}
    assert by_no[1]["official_answer"] == "B"
    assert by_no[2]["official_answer"] == "C"
    assert by_no[1]["import_status"] == "staged"
    assert by_no[1]["source_page"] == 1
    assert by_no[2]["subject"]  # classifier assigned a subject or flagged review

    approved = client.post(
        f"/api/questions/{by_no[1]['id']}/approve", json={"reviewer": "pytest"}
    )
    assert approved.status_code == 200
    assert approved.json()["import_status"] == "approved"

    practice = client.post(
        "/api/practice/sessions", json={"mode": "random", "limit": 10, "shuffle": False}
    )
    assert practice.status_code == 200
    body = practice.json()
    assert body["total_questions"] == 1
    assert body["questions"][0]["question_no"] == 1
    assert body["questions"][0]["official_answer"] is None

    answered = client.post(
        f"/api/practice/sessions/{body['id']}/answer",
        json={"question_id": by_no[1]["id"], "selected_answer": "B", "time_spent_seconds": 15},
    )
    assert answered.status_code == 200
    assert answered.json()["is_correct"] is True


def test_unsafe_zip_is_rejected(client, tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.pdf", b"%PDF-1.4")
    response = client.post(
        "/api/ingestion/upload",
        files={"file": ("evil.zip", archive.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "Unsafe" in response.json()["detail"]


def test_non_zip_upload_is_rejected(client):
    response = client.post(
        "/api/ingestion/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
