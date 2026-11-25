from __future__ import annotations

import io
import zipfile

import pymupdf
import pytest

from app.services.ingestion import create_job, process_job


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


def build_zip():
    q = make_pdf(
        [
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
        ]
    )
    a = make_pdf(["GATE 2025 — Session 1 — Answer Key", "1 B", "2 C"])
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("2025/CS_GATE2025_Question_Paper_Session_1.pdf", q)
        bundle.writestr("2025/CS_GATE2025_Answer_Key_Session_1.pdf", a)
    return archive.getvalue()


def test_duplicate_zip_import_is_idempotent(client, tmp_path):
    archive = build_zip()
    r1 = client.post("/api/ingestion/upload", files={"file": ("g.zip", archive, "application/zip")})
    assert r1.status_code == 200
    job1 = r1.json()["job_id"]
    r2 = client.post("/api/ingestion/upload", files={"file": ("g.zip", archive, "application/zip")})
    assert r2.status_code == 200
    assert r2.json()["job_id"] == job1
    # question count unchanged
    listing = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    assert listing["total"] == 2


def test_reimport_after_manual_classification_preserves_it(client, tmp_path):
    archive = build_zip()
    r = client.post("/api/ingestion/upload", files={"file": ("g2.zip", archive, "application/zip")})
    job_id = r.json()["job_id"]
    job = client.get(f"/api/ingestion/{job_id}").json()
    assert job["job"]["status"] in {"completed", "completed_with_errors"}
    listing = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    qid = listing["items"][0]["id"]
    client.post(
        f"/api/questions/{qid}/classification",
        json={
            "subject_id": listing["items"][0]["subject_id"],
            "topic_id": listing["items"][0]["topic_id"],
            "subtopic_id": listing["items"][0]["subtopic_id"],
            "concept_ids": [],
            "reason": "manual",
            "accept": True,
        },
    )
    before = client.get(f"/api/questions/{qid}").json()
    assert before["classification_method"] == "manual"

    # Re-upload duplicate zip
    client.post("/api/ingestion/upload", files={"file": ("g2.zip", archive, "application/zip")})
    after = client.get(f"/api/questions/{qid}").json()
    assert after["classification_method"] == "manual"
    assert after["subject_id"] == before["subject_id"]


def test_backup_restore_preserves_data(client, tmp_path):
    # create a question via ingestion
    archive = build_zip()
    r = client.post("/api/ingestion/upload", files={"file": ("g3.zip", archive, "application/zip")})
    assert r.status_code == 200
    listing = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    count_before = listing["total"]
    assert count_before == 2

    # backup
    b = client.post("/api/data/backups", json={"label": "integrity-test"})
    assert b.status_code == 200
    filename = b.json()["file"]

    # integrity before
    integrity = client.get("/api/data/integrity").json()
    assert integrity["sqlite_integrity"] == "ok"

    # restore
    restore = client.post("/api/data/restore", json={"filename": filename})
    assert restore.status_code == 200

    listing_after = client.get("/api/questions", params={"year": 2025, "include_staged": True}).json()
    assert listing_after["total"] == count_before