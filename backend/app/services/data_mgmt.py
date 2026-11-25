from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, init_fts
from app.models import (
    AppSetting,
    Attempt,
    Formula,
    IngestionJob,
    Paper,
    Progress,
    Question,
    QuestionAsset,
    RevisionItem,
    Solution,
)


def _db_path() -> Path:
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        raise ValueError("Backup/restore currently supports SQLite only.")
    return Path(url.replace("sqlite:///", ""))


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def create_backup(db: Session, label: str = "manual") -> dict:
    source = _db_path()
    if not source.exists():
        raise FileNotFoundError("Database file does not exist.")
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    target = settings.backups_dir / f"gate_{_timestamp()}_{label}.db"
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    counts = {
        "questions": int(db.scalar(select(func.count(Question.id))) or 0),
        "papers": int(db.scalar(select(func.count(Paper.id))) or 0),
        "attempts": int(db.scalar(select(func.count(Attempt.id))) or 0),
        "formulas": int(db.scalar(select(func.count(Formula.id))) or 0),
        "solutions": int(db.scalar(select(func.count(Solution.id))) or 0),
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "file": target.name,
        "sha256": _sha256(target),
        "counts": counts,
        "schema_note": "SQLite online backup; original PDFs and assets are stored separately.",
    }
    manifest_path = target.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _prune_backups(db)
    return manifest


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prune_backups(db: Session) -> None:
    retention = 10
    try:
        from app.settings_service import get_setting

        retention = int(get_setting(db, "backup_retention", 10))
    except Exception:  # noqa: BLE001
        pass
    backups = sorted(settings.backups_dir.glob("gate_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[retention:]:
        old.unlink(missing_ok=True)
        old.with_suffix(".json").unlink(missing_ok=True)


def list_backups() -> list[dict]:
    result = []
    for path in sorted(settings.backups_dir.glob("gate_*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        manifest_path = path.with_suffix(".json")
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
        result.append(
            {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "manifest": manifest,
            }
        )
    return result


def restore_backup(db: Session, filename: str) -> dict:
    safe_name = Path(filename).name
    if safe_name != filename:
        raise ValueError("Invalid backup filename.")
    source = (settings.backups_dir / safe_name).resolve()
    if not source.exists() or source.parent != settings.backups_dir.resolve():
        raise FileNotFoundError("Backup not found.")
    # Always make a safety copy of the current database before replacing it.
    safety = create_backup(db, label="pre_restore")
    db.close()
    engine.dispose()
    target = _db_path()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(target) + suffix)
        try:
            sidecar.unlink(missing_ok=True)
        except PermissionError:
            # On Windows the WAL sidecar may still be locked by a pooled
            # connection; overwriting the main database file is still safe.
            pass
    shutil.copy2(source, target)
    init_fts()
    return {"restored_from": source.name, "safety_backup": safety["file"], "restart_recommended": True}


def export_data(db: Session) -> dict:
    questions = db.scalars(select(Question)).all()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "schema": "gate-cs-2027-v1",
        "questions": [
            {
                "id": q.id,
                "public_id": q.public_id,
                "year": q.year,
                "paper_code": q.paper_code,
                "session": q.session,
                "question_no": q.question_no,
                "question_type": q.question_type,
                "marks": q.marks,
                "negative_marks": q.negative_marks,
                "question_text": q.question_text,
                "options": q.options,
                "official_answer": q.official_answer,
                "subject_id": q.subject_id,
                "topic_id": q.topic_id,
                "subtopic_id": q.subtopic_id,
                "concept_text": q.concept_text,
                "verification_status": q.verification_status,
                "import_status": q.import_status,
                "source_pdf": q.source_pdf,
                "source_page": q.source_page,
                "source_question_hash": q.source_question_hash,
            }
            for q in questions
        ],
        "attempts": [
            {
                "question_id": a.question_id,
                "selected_answer": a.selected_answer,
                "is_correct": a.is_correct,
                "mode": a.mode,
                "time_spent_seconds": a.time_spent_seconds,
                "working_text": a.working_text,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in db.scalars(select(Attempt)).all()
        ],
        "progress": [
            {
                "level": p.level,
                "ref_id": p.ref_id,
                "attempted": p.attempted,
                "correct": p.correct,
                "incorrect": p.incorrect,
                "distinct_questions": p.distinct_questions,
                "time_spent_seconds": p.time_spent_seconds,
                "manual_status": p.manual_status,
            }
            for p in db.scalars(select(Progress)).all()
        ],
        "formulas": [
            {
                "name": f.name,
                "latex": f.latex,
                "units": f.units,
                "applicability": f.applicability,
                "verification_status": f.verification_status,
                "subject_id": f.subject_id,
                "topic_id": f.topic_id,
                "subtopic_id": f.subtopic_id,
            }
            for f in db.scalars(select(Formula)).all()
        ],
        "revision_items": [
            {
                "question_id": r.question_id,
                "due_at": r.due_at.isoformat() if r.due_at else None,
                "interval_days": r.interval_days,
                "repetitions": r.repetitions,
                "lapses": r.lapses,
            }
            for r in db.scalars(select(RevisionItem)).all()
        ],
        "settings": {
            row.key: "[secret]"
            for row in db.scalars(select(AppSetting)).all()
            if row.is_secret
        },
    }
    return payload


def write_export(db: Session) -> Path:
    payload = export_data(db)
    target = settings.backups_dir / f"export_{_timestamp()}.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def integrity_check(db: Session) -> dict:
    issues: list[dict] = []
    with engine.connect() as connection:
        pragma = connection.exec_driver_sql("PRAGMA integrity_check").scalar()
        fk = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if pragma != "ok":
        issues.append({"type": "sqlite_integrity", "detail": pragma})
    for row in fk:
        issues.append({"type": "foreign_key", "detail": str(row)})
    duplicate_hashes = db.execute(
        select(Question.source_question_hash, func.count(Question.id))
        .group_by(Question.source_question_hash)
        .having(func.count(Question.id) > 1)
    ).all()
    if duplicate_hashes:
        issues.append({"type": "duplicate_hashes", "detail": duplicate_hashes})
    approved_no_answer = int(
        db.scalar(
            select(func.count(Question.id)).where(
                Question.import_status == "approved", Question.official_answer.is_(None)
            )
        )
        or 0
    )
    if approved_no_answer:
        issues.append(
            {
                "type": "approved_without_answer",
                "detail": f"{approved_no_answer} approved questions have no official answer.",
            }
        )
    missing_assets = []
    for asset in db.scalars(select(QuestionAsset)).all():
        if not (settings.data_dir / asset.path).exists():
            missing_assets.append(asset.id)
    if missing_assets:
        issues.append({"type": "missing_assets", "detail": missing_assets[:50]})
    return {
        "ok": not issues,
        "sqlite_integrity": pragma,
        "issues": issues,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def ingestion_history(db: Session) -> list[dict]:
    jobs = db.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc())).all()
    return [
        {
            "id": job.id,
            "filename": job.filename,
            "status": job.status,
            "stage": job.stage,
            "stats": job.stats or {},
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }
        for job in jobs
    ]
