from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import IngestionFile, IngestionJob
from app.services.ingestion import IngestionError, create_job, process_job
from app.utils import utcnow

router = APIRouter(tags=["ingestion"])


@router.post("/ingestion/upload")
async def upload_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip archive.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    digest = hashlib.sha256()
    temp_path = settings.uploads_dir / f"upload_{utcnow().strftime('%Y%m%d%H%M%S%f')}.zip"
    size = 0
    try:
        with open(temp_path, "wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"ZIP exceeds the {settings.max_upload_mb} MB upload limit.",
                    )
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty ZIP file.")
        try:
            job = create_job(db, temp_path, file.filename)
        except IngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if job.status in {"queued", "running", "failed"}:
            job.status = "queued"
            job.stage = "queued"
            db.commit()
            background_tasks.add_task(process_job, job.id)
        return {
            "job_id": job.id,
            "status": job.status,
            "stats": job.stats,
            "duplicate_upload": job.created_at.isoformat() if job.status != "queued" else None,
        }
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/ingestion")
def list_jobs(db: Session = Depends(get_db)) -> dict:
    jobs = db.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc())).all()
    return {
        "items": [
            {
                "id": job.id,
                "filename": job.filename,
                "status": job.status,
                "stage": job.stage,
                "stats": job.stats or {},
                "error": job.error,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ]
    }


@router.get("/ingestion/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    files = db.scalars(
        select(IngestionFile)
        .where(IngestionFile.job_id == job.id)
        .order_by(IngestionFile.relative_path)
    ).all()
    return {
        "job": {
            "id": job.id,
            "filename": job.filename,
            "status": job.status,
            "stage": job.stage,
            "stats": job.stats or {},
            "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "files": [
            {
                "id": f.id,
                "relative_path": f.relative_path,
                "kind": f.file_kind,
                "status": f.status,
                "year": f.year,
                "session": f.session,
                "page_count": f.page_count,
                "questions_found": f.questions_found,
                "answers_found": f.answers_found,
                "duplicates": f.duplicates,
                "warnings": f.warnings or [],
                "error": f.error,
                "paper_id": f.paper_id,
            }
            for f in files
        ],
    }


@router.post("/ingestion/{job_id}/resume")
def resume_job(
    job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> dict:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    files = db.scalars(select(IngestionFile).where(IngestionFile.job_id == job.id)).all()
    reset = 0
    for file in files:
        if file.status in {"failed", "needs_review"}:
            file.status = "pending"
            file.error = None
            reset += 1
    job.status = "queued"
    job.stage = "resuming"
    job.error = None
    job.completed_at = None
    db.commit()
    background_tasks.add_task(process_job, job.id)
    return {"job_id": job.id, "reset_files": reset, "status": job.status}
