"""FastAPI application factory and startup wiring.

Run from the ``backend`` directory:

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.db import SessionLocal, init_fts
from app.models import QuestionAsset
from app.routers import (
    ai,
    analytics,
    data,
    formulas,
    ingestion,
    practice,
    questions,
    revision,
    system,
    verification,
)
from app.seed import seed

logger = logging.getLogger("gate")

MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the FTS index and idempotently seed the syllabus.

    Failures are recorded instead of crashing the process so ``/api/health``
    can explain what still needs to be done (usually ``alembic upgrade head``).
    """

    state: dict[str, str | bool | None] = {
        "fts": False,
        "seeded": False,
        "error": None,
    }
    try:
        init_fts()
        state["fts"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("FTS initialisation failed: %s", exc)
        state["error"] = f"fts: {exc}"

    try:
        with SessionLocal() as db:
            stats = seed(db)
        state["seeded"] = True
        state["taxonomy"] = ", ".join(
            f"{key}={stats[key]}"
            for key in ("subjects", "topics", "subtopics", "concepts")
            if key in stats
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seeding failed: %s", exc)
        prefix = f"{state['error']}; " if state["error"] else ""
        state["error"] = f"{prefix}seed: {exc}"

    app.state.startup = state
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Local-first GATE CS 2027 PYQ tutor. Content comes only from PDFs you "
            "upload; AI output is always labelled with its verification status."
        ),
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        system,
        analytics,
        questions,
        ingestion,
        ai,
        verification,
        formulas,
        practice,
        revision,
        data,
    ):
        app.include_router(module.router, prefix=settings.api_prefix)

    @app.get("/api/assets/{asset_id}", tags=["assets"], include_in_schema=False)
    def asset_file(asset_id: int):
        """Serve a figure clipped from an uploaded PDF.

        Asset paths are stored relative to the data directory. Resolution is
        checked so a database row can never escape that directory.
        """

        with SessionLocal() as db:
            asset = db.get(QuestionAsset, asset_id)
            if asset is None:
                raise HTTPException(status_code=404, detail="Asset not found")
            stored = asset.path

        data_root = settings.data_dir.resolve()
        candidate = (data_root / Path(stored)).resolve()
        if data_root not in candidate.parents and candidate != data_root:
            raise HTTPException(status_code=400, detail="Invalid asset path")
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="Asset file is missing on disk")

        return FileResponse(
            candidate,
            media_type=MEDIA_TYPES.get(candidate.suffix.lower(), "application/octet-stream"),
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "app": settings.app_name,
            "docs": "/docs",
            "api": settings.api_prefix,
            "local_first": True,
        }

    return app


app = create_app()
