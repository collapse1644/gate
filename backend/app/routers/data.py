from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services import data_mgmt
from sqlalchemy import func, select
from app.models import Question

router = APIRouter(tags=["data"])


class BackupRequest(BaseModel):
    label: str = "manual"


class RestoreRequest(BaseModel):
    filename: str


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


@router.get("/data/overview")
def data_overview(db: Session = Depends(get_db)) -> dict:
    db_path = settings.database_url.replace("sqlite:///", "")
    total_questions = int(db.scalar(select(func.count(Question.id))) or 0)
    raw_populated = int(db.scalar(select(func.count(Question.id)).where(Question.raw_text.is_not(None))) or 0)
    return {
        "database": {
            "path": db_path,
            "size_bytes": Path(db_path).stat().st_size if Path(db_path).exists() else 0,
        },
        "raw_text_coverage": {
            "total_questions": total_questions,
            "raw_text_populated": raw_populated,
            "raw_text_missing": total_questions - raw_populated,
            "note": "Historical questions ingested before raw_text persistence may have NULL raw_text; no backfill is performed.",
        },
        "storage": {
            "originals_bytes": _dir_size(settings.originals_dir),
            "assets_bytes": _dir_size(settings.assets_dir),
            "uploads_bytes": _dir_size(settings.uploads_dir),
            "backups_bytes": _dir_size(settings.backups_dir),
            "total_bytes": _dir_size(settings.data_dir),
        },
        "backups": data_mgmt.list_backups(),
        "ingestion_history": data_mgmt.ingestion_history(db),
        "notes": [
            "Original PDFs are copied to data/originals and never modified.",
            "A backup copies the database only; originals and figure assets live in data/.",
        ],
    }


@router.post("/data/backups")
def create_backup(payload: BackupRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return data_mgmt.create_backup(db, payload.label[:40] or "manual")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/data/backups")
def list_backups() -> dict:
    return {"items": data_mgmt.list_backups()}


@router.post("/data/restore")
def restore_backup(payload: RestoreRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return data_mgmt.restore_backup(db, payload.filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/data/integrity")
def integrity(db: Session = Depends(get_db)) -> dict:
    return data_mgmt.integrity_check(db)


@router.get("/data/export")
def export_json(db: Session = Depends(get_db)) -> dict:
    return data_mgmt.export_data(db)


@router.get("/data/export/file")
def export_file(db: Session = Depends(get_db)):
    path = data_mgmt.write_export(db)
    return FileResponse(path, media_type="application/json", filename=path.name)
