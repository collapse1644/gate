from __future__ import annotations

import json
import re
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import (
    AnswerKeyEntry,
    ClassificationHistory,
    IngestionFile,
    IngestionJob,
    Paper,
    Question,
    QuestionAsset,
    QuestionConcept,
    QuestionSecondaryTopic,
)
from app.services.classifier import classify_question
from app.services.pdf_extract import inspect_pdf, negative_for
from app.settings_service import get_setting
from app.utils import content_hash, file_sha256, normalize_text, slugify

MAX_FILES = 800
MAX_UNCOMPRESSED = 3 * 1024 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}


class IngestionError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Safe extraction
# ---------------------------------------------------------------------------
def safe_extract(zip_path: Path, destination: Path) -> list[tuple[str, Path]]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[tuple[str, Path]] = []
    total_size = 0
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise IngestionError(f"ZIP contains too many entries ({len(infos)} > {MAX_FILES}).")
        for info in infos:
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise IngestionError(f"Unsafe ZIP entry path: {name}")
            if info.file_size > MAX_UNCOMPRESSED:
                raise IngestionError(f"ZIP entry too large: {name}")
            total_size += info.file_size
            if total_size > MAX_UNCOMPRESSED:
                raise IngestionError("ZIP expands beyond the configured safety limit.")
            suffix = pure.suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                continue
            target = destination / Path(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append((str(pure), target))
    return extracted


# ---------------------------------------------------------------------------
# Upload / job creation
# ---------------------------------------------------------------------------
def create_job(db: Session, zip_path: Path, original_name: str) -> IngestionJob:
    sha = file_sha256(zip_path)
    existing = db.scalar(select(IngestionJob).where(IngestionJob.sha256 == sha))
    if existing:
        return existing
    stored = settings.uploads_dir / f"{sha}.zip"
    if zip_path.resolve() != stored.resolve():
        shutil.copy2(zip_path, stored)
    job = IngestionJob(
        filename=original_name,
        stored_path=str(stored),
        sha256=sha,
        status="queued",
        stage="extracting",
        stats={},
    )
    db.add(job)
    db.flush()
    extraction_dir = settings.uploads_dir / f"job_{job.id}"
    extracted = safe_extract(stored, extraction_dir)
    for relative, path in extracted:
        suffix = path.suffix.lower()
        kind = "pdf" if suffix == ".pdf" else "other"
        db.add(
            IngestionFile(
                job_id=job.id,
                relative_path=relative,
                stored_path=str(path),
                sha256=file_sha256(path),
                file_kind=kind,
                status="pending" if kind == "pdf" else "skipped",
                warnings=[] if kind == "pdf" else ["Unsupported file type; preserved but not imported."],
            )
        )
    job.stats = {
        "files_discovered": len(extracted),
        "files_processed": 0,
        "files_failed": 0,
        "questions_extracted": 0,
        "duplicates": 0,
        "missing_answers": 0,
        "classification_reviews": 0,
        "extraction_reviews": 0,
        "assets_extracted": 0,
    }
    db.commit()
    db.refresh(job)
    return job


def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(IngestionJob, job_id)
        if job is None:
            return
        if job.status in {"completed"}:
            return
        job.status = "running"
        job.started_at = job.started_at or utcnow()
        job.stage = "processing"
        db.commit()

        files = db.scalars(
            select(IngestionFile).where(IngestionFile.job_id == job.id)
        ).all()
        # Process question papers before answer keys so keys can be associated.
        pdf_files = [f for f in files if f.file_kind == "pdf" and f.status in {"pending", "failed"}]
        pdf_files.sort(key=lambda f: (0 if _looks_like_question(f) else 1, f.relative_path))

        for file in pdf_files:
            try:
                _process_pdf(db, job, file)
                file.status = "done"
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                file = db.get(IngestionFile, file.id)
                if file:
                    file.status = "failed"
                    file.error = str(exc)[:2000]
                    file.processed_at = utcnow()
                    db.commit()
            _refresh_stats(db, job)

        # Second pass: try to associate answers for every question paper in the job.
        for file in files:
            if file.status == "done" and file.paper_id:
                _associate_answers(db, file.paper_id)
        db.commit()

        remaining = db.scalars(
            select(IngestionFile).where(
                IngestionFile.job_id == job.id,
                IngestionFile.status.in_(["pending", "failed"]),
            )
        ).all()
        job.status = "completed" if not remaining else "completed_with_errors"
        job.stage = "finished"
        job.completed_at = utcnow()
        _refresh_stats(db, job)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(IngestionJob, job_id)
        if job:
            job.status = "failed"
            job.stage = "error"
            job.error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def _looks_like_question(file: IngestionFile) -> bool:
    name = file.relative_path.lower()
    return not any(token in name for token in ("answer", "key", "solution"))


# ---------------------------------------------------------------------------
# PDF processing
# ---------------------------------------------------------------------------
def _process_pdf(db: Session, job: IngestionJob, file: IngestionFile) -> None:
    path = Path(file.stored_path)
    if not path.exists():
        raise IngestionError("Stored PDF is missing.")

    # Existing identical PDF: do not import twice.
    existing_file = db.scalar(
        select(IngestionFile).where(
            IngestionFile.sha256 == file.sha256,
            IngestionFile.id != file.id,
            IngestionFile.status == "done",
        )
    )
    if existing_file:
        file.status = "done"
        file.warnings = (file.warnings or []) + ["Duplicate PDF content already processed in another ingestion."]
        file.processed_at = utcnow()
        db.commit()
        return

    year_hint = _year_from_name(path.name)
    temp_assets = settings.uploads_dir / f"job_{job.id}" / "assets" / slugify(path.stem)
    info = inspect_pdf(path, output_assets_dir=temp_assets, asset_key=slugify(path.stem))
    file.year = info.year or year_hint
    file.session = info.session
    file.page_count = info.page_count
    file.warnings = list(file.warnings or []) + info.warnings

    if info.kind == "unknown":
        file.status = "needs_review"
        file.error = "Could not determine whether this PDF is a question paper or answer key."
        file.processed_at = utcnow()
        db.commit()
        return
    if info.kind == "question_paper":
        if not info.questions:
            file.status = "needs_review"
            file.processed_at = utcnow()
            db.commit()
            return
        if not file.year:
            file.status = "needs_review"
            file.error = "Year could not be detected from filename or PDF text."
            file.processed_at = utcnow()
            db.commit()
            return
        _import_question_paper(db, job, file, info, path, temp_assets)
    else:
        _import_answer_key(db, job, file, info, path)
    file.processed_at = utcnow()
    db.commit()


def _year_from_name(name: str) -> int | None:
    years = [int(y) for y in re.findall(r"(?<!\d)(20[12]\d)(?!\d)", name)]
    return max(years) if years else None


def _paper_label(year: int, session: str | None) -> str:
    return f"GATE {year} CS" + (f" — {session}" if session else "")


def _copy_original(path: Path, year: int, session: str | None) -> Path:
    destination = settings.originals_dir / str(year)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{slugify(session or 'session-unspecified')}_{path.name}"
    if not target.exists() or file_sha256(target) != file_sha256(path):
        shutil.copy2(path, target)
    return target


def _import_question_paper(
    db: Session,
    job: IngestionJob,
    file: IngestionFile,
    info,
    path: Path,
    temp_assets: Path,
) -> None:
    source_sha = file.sha256
    paper = db.scalar(select(Paper).where(Paper.source_sha256 == source_sha))
    if paper is None:
        paper = db.scalar(
            select(Paper).where(
                Paper.year == file.year,
                Paper.session == file.session,
                Paper.paper_code == "CS",
                Paper.is_duplicate.is_(False),
            )
        )
    if paper is None:
        paper = Paper(
            year=file.year,
            session=file.session,
            paper_code="CS",
            label=_paper_label(file.year, file.session),
            source_pdf=path.name,
            source_sha256=source_sha,
        )
        db.add(paper)
        db.flush()
    file.paper_id = paper.id
    original = _copy_original(path, file.year, file.session)
    paper.source_pdf = str(original)
    paper.source_sha256 = source_sha
    db.flush()

    paper_dir = settings.assets_dir / str(file.year) / slugify(f"{file.session or 'unknown'}-{path.stem}")
    paper_dir.mkdir(parents=True, exist_ok=True)

    # Answer key entries may already exist (answer key processed first in a resumed job).
    answers = {
        entry.question_no: entry.answer
        for entry in db.scalars(
            select(AnswerKeyEntry).where(AnswerKeyEntry.paper_id == paper.id)
        ).all()
    }

    imported = 0
    duplicates = 0
    for draft in info.questions:
        text = normalize_text(draft.text)
        raw_text = draft.text
        question_hash = content_hash(
            str(file.year), file.session or "", str(draft.question_no), text
        )
        existing = db.scalar(
            select(Question).where(Question.source_question_hash == question_hash)
        )
        if existing:
            duplicates += 1
            continue
        # Same paper/slot but different content: likely a re-extraction conflict.
        slot = db.scalar(
            select(Question).where(
                Question.paper_id == paper.id, Question.question_no == draft.question_no
            )
        )
        notes = list(draft.notes)
        needs_review = bool(draft.confidence < 0.72)
        if slot:
            notes.append("Another question already occupies this paper/question slot.")
            needs_review = True

        answer = answers.get(draft.question_no)
        qtype = draft.question_type
        if answer:
            letters = sorted(set(re.findall(r"[A-D]", answer.upper())))
            if len(letters) > 1:
                qtype = "MSQ"
            elif letters and not draft.options:
                notes.append("Answer key indicates options, but no options were extracted.")
                needs_review = True
            elif not letters and not draft.options:
                qtype = "NAT"
        negative = negative_for(qtype, draft.marks)
        question = Question(
            paper_id=paper.id,
            year=file.year,
            paper_code="CS",
            session=file.session,
            paper_label=paper.label,
            question_no=draft.question_no,
            question_type=qtype,
            marks=draft.marks,
            negative_marks=negative,
            marks_source=draft.marks_source,
            question_text=text,
            raw_text=raw_text,
            options=draft.options or None,
            official_answer=answer,
            extraction_confidence=draft.confidence,
            extraction_notes=notes,
            source_pdf=str(original),
            source_page=draft.page_start,
            source_bbox=[draft.y_start, draft.y_end],
            source_question_hash=question_hash,
            import_status="staged",
            needs_review=needs_review,
            review_status="pending",
        )
        db.add(question)
        db.flush()

        # Move rendered figures to their permanent paper folder.
        asset_paths = []
        for asset in draft.assets:
            src = Path(asset["path"])
            target = paper_dir / src.name
            if src.exists() and src.resolve() != target.resolve():
                shutil.copy2(src, target)
            if target.exists():
                rel = target.relative_to(settings.data_dir).as_posix()
                record = QuestionAsset(
                    question_id=question.id,
                    path=rel,
                    kind=asset.get("kind", "figure"),
                    page=asset.get("page", draft.page_start),
                    bbox=asset.get("bbox"),
                    width=asset.get("width"),
                    height=asset.get("height"),
                    sha256=asset.get("sha256", ""),
                )
                db.add(record)
                asset_paths.append(rel)

        result = classify_question(
            db,
            text=text,
            options=draft.options,
            review_threshold=get_setting(db, "classification_review_threshold", 0.55),
            accept_threshold=get_setting(db, "classification_accept_threshold", 0.72),
        )
        question.subject_id = result.subject_id
        question.section_id = result.section_id
        question.topic_id = result.topic_id
        question.subtopic_id = result.subtopic_id
        question.classification_confidence = result.confidence
        question.classification_method = result.method
        question.review_status = result.review_status
        question.concept_text = ", ".join(
            _concept_names(db, result.concept_ids)
        )
        for cid in list(dict.fromkeys(result.concept_ids)):
            db.add(QuestionConcept(question_id=question.id, concept_id=cid))
        for tid in result.secondary_topic_ids:
            db.add(QuestionSecondaryTopic(question_id=question.id, topic_id=tid))
        if result.review_status in {"pending", "out_of_syllabus"}:
            question.needs_review = True
            question.review_notes = (
                f"Classifier: {result.explanation}\nCandidates: "
                + json.dumps(result.candidates[:5], ensure_ascii=True)
            )
        db.flush()
        imported += 1
        if not answer:
            notes.append("No official answer key matched this question.")

    # Downloading/staging figures before approval would leave orphan files if rejected;
    # that is acceptable because originals are preserved and assets are small.
    # Associate any orphaned answer-key entries (from an answer-key PDF
    # uploaded before this question paper) with questions in this paper.
    matched = _associate_orphaned_answers(db, paper)
    if matched:
        file.warnings = list(file.warnings or []) + [
            f"Matched {matched} previously orphaned answer-key entries to this paper."
        ]

    paper.question_count = db.scalar(
        select(func.count(Question.id)).where(Question.paper_id == paper.id)
    ) or 0
    paper.total_marks = db.scalar(
        select(func.sum(Question.marks)).where(Question.paper_id == paper.id)
    )
    file.questions_found = imported
    file.duplicates = duplicates
    file.status = "done"
    jst = dict(job.stats or {})
    jst["assets_extracted"] = jst.get("assets_extracted", 0) + sum(len(q.assets) for q in info.questions)
    job.stats = jst
    db.commit()


def _concept_names(db: Session, concept_ids: list[int]) -> list[str]:
    from app.models import Concept

    if not concept_ids:
        return []
    rows = db.scalars(select(Concept).where(Concept.id.in_(concept_ids))).all()
    return [row.name for row in rows]


def _import_answer_key(db: Session, job: IngestionJob, file: IngestionFile, info, path: Path) -> None:
    if not file.year:
        file.status = "needs_review"
        file.error = "Year could not be detected for answer key."
        return
    if not info.answers:
        file.status = "needs_review"
        file.error = "No answers parsed."
        return
    original = _copy_original(path, file.year, file.session)
    paper = _match_paper(db, file.year, file.session)
    if paper is None:
        # Store answers as orphaned entries (paper_id = NULL) so they can be
        # associated when the matching question paper is uploaded later.
        for draft in info.answers:
            existing = db.scalar(
                select(AnswerKeyEntry).where(
                    AnswerKeyEntry.paper_id.is_(None),
                    AnswerKeyEntry.question_no == draft.question_no,
                )
            )
            if existing is None:
                entry = AnswerKeyEntry(
                    paper_id=None,
                    question_no=draft.question_no,
                    answer=draft.answer,
                    source_pdf=str(original),
                    source_page=draft.page + 1,
                )
                db.add(entry)
        file.answers_found = len(info.answers)
        file.status = "needs_review"
        file.error = (
            "No matching question paper found for this answer key. "
            "Upload/process the question paper first, then resume."
        )
        db.commit()
        return
    for draft in info.answers:
        entry = db.scalar(
            select(AnswerKeyEntry).where(
                AnswerKeyEntry.paper_id == paper.id, AnswerKeyEntry.question_no == draft.question_no
            )
        )
        if entry is None:
            entry = AnswerKeyEntry(
                paper_id=paper.id,
                question_no=draft.question_no,
                answer=draft.answer,
                source_pdf=str(original),
                source_page=draft.page + 1,
            )
            db.add(entry)
        elif entry.answer != draft.answer:
            file.warnings = list(file.warnings or []) + [
                f"Conflicting answer for Q{draft.question_no}: kept {entry.answer}, ignored {draft.answer}."
            ]
        question = db.scalar(
            select(Question).where(
                Question.paper_id == paper.id, Question.question_no == draft.question_no
            )
        )
        if question:
            question.official_answer = draft.answer
            letters = sorted(set(re.findall(r"[A-D]", draft.answer.upper())))
            if len(letters) > 1:
                question.question_type = "MSQ"
            elif letters and question.options:
                question.question_type = "MCQ"
            elif not letters and not question.options:
                question.question_type = "NAT"
            question.negative_marks = negative_for(question.question_type, question.marks)
    paper.question_count = db.scalar(
        select(func.count(Question.id)).where(Question.paper_id == paper.id)
    ) or paper.question_count
    file.answers_found = len(info.answers)
    file.paper_id = paper.id
    file.status = "done"
    db.commit()


def _associate_orphaned_answers(db: Session, paper: Paper) -> int:
    """Associate orphaned answer-key entries (paper_id IS NULL) with questions
    in the given paper by matching question numbers."""
    orphaned = db.scalars(
        select(AnswerKeyEntry).where(
            AnswerKeyEntry.paper_id.is_(None),
        )
    ).all()
    matched = 0
    for entry in orphaned:
        question = db.scalar(
            select(Question).where(
                Question.paper_id == paper.id,
                Question.question_no == entry.question_no,
            )
        )
        if question:
            entry.paper_id = paper.id
            question.official_answer = entry.answer
            letters = sorted(set(re.findall(r"[A-D]", entry.answer.upper())))
            if len(letters) > 1:
                question.question_type = "MSQ"
            elif letters and question.options:
                question.question_type = "MCQ"
            elif not letters and not question.options:
                question.question_type = "NAT"
            question.negative_marks = negative_for(question.question_type, question.marks)
            matched += 1
    return matched


def _match_paper(db: Session, year: int, session: str | None) -> Paper | None:
    query = select(Paper).where(Paper.year == year, Paper.paper_code == "CS")
    if session:
        match = db.scalar(query.where(Paper.session == session))
        if match:
            return match
    candidates = db.scalars(query).all()
    if len(candidates) == 1:
        return candidates[0]
    # If session is missing, only match when there is exactly one paper that year.
    return None


def _associate_answers(db: Session, paper_id: int) -> None:
    entries = db.scalars(select(AnswerKeyEntry).where(AnswerKeyEntry.paper_id == paper_id)).all()
    if not entries:
        return
    by_no = {entry.question_no: entry.answer for entry in entries}
    questions = db.scalars(select(Question).where(Question.paper_id == paper_id)).all()
    for question in questions:
        answer = by_no.get(question.question_no)
        if not answer:
            continue
        question.official_answer = answer
        letters = sorted(set(re.findall(r"[A-D]", answer.upper())))
        if len(letters) > 1:
            question.question_type = "MSQ"
        elif letters and (question.options or []):
            question.question_type = "MCQ"
        elif not letters and not (question.options or []):
            question.question_type = "NAT"
        question.negative_marks = negative_for(question.question_type, question.marks)
    db.commit()


# ---------------------------------------------------------------------------
# Stats / lifecycle
# ---------------------------------------------------------------------------
def _refresh_stats(db: Session, job: IngestionJob) -> None:
    files = db.scalars(select(IngestionFile).where(IngestionFile.job_id == job.id)).all()
    processed = sum(1 for f in files if f.status in {"done", "skipped"})
    failed = sum(1 for f in files if f.status in {"failed", "needs_review"})
    questions = sum(f.questions_found for f in files)
    duplicates = sum(f.duplicates for f in files)
    paper_ids = {f.paper_id for f in files if f.paper_id}
    question_rows = []
    for paper_id in paper_ids:
        question_rows.extend(
            db.scalars(select(Question).where(Question.paper_id == paper_id)).all()
        )
    missing_answers = sum(1 for q in question_rows if not q.official_answer)
    classification_reviews = sum(
        1
        for q in question_rows
        if q.review_status in {"pending", "out_of_syllabus"} or q.needs_review
    )
    extraction_reviews = sum(1 for q in question_rows if q.extraction_confidence < 0.72)
    stats = dict(job.stats or {})
    stats.update(
        {
            "files_discovered": len(files),
            "files_processed": processed,
            "files_failed": failed,
            "questions_extracted": questions,
            "duplicates": duplicates,
            "missing_answers": missing_answers,
            "classification_reviews": classification_reviews,
            "extraction_reviews": extraction_reviews,
            "staged_questions": sum(1 for q in question_rows if q.import_status == "staged"),
            "approved_questions": sum(1 for q in question_rows if q.import_status == "approved"),
        }
    )
    job.stats = stats


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------
def approve_question(db: Session, question: Question, reviewer: str = "user") -> None:
    question.import_status = "approved"
    if question.review_status == "pending" and question.classification_confidence >= 0.55:
        question.review_status = "manually_accepted"
    question.needs_review = False
    question.reviewed_by = reviewer
    question.reviewed_at = utcnow()
    db.commit()


def reject_question(db: Session, question: Question, reviewer: str = "user", reason: str = "") -> None:
    question.import_status = "rejected"
    question.review_notes = (question.review_notes + "\n" + reason).strip()
    question.reviewed_by = reviewer
    question.reviewed_at = utcnow()
    db.commit()


def update_classification(
    db: Session,
    question: Question,
    *,
    subject_id: int | None,
    topic_id: int | None,
    subtopic_id: int | None,
    concept_ids: list[int],
    actor: str = "user",
    reason: str = "",
    accept: bool = True,
) -> None:
    from app.models import Concept, Subject, Subtopic, Topic

    db.add(
        ClassificationHistory(
            question_id=question.id,
            old_subject_id=question.subject_id,
            old_topic_id=question.topic_id,
            old_subtopic_id=question.subtopic_id,
            old_confidence=question.classification_confidence,
            old_method=question.classification_method,
            new_subject_id=subject_id,
            new_topic_id=topic_id,
            new_subtopic_id=subtopic_id,
            new_confidence=1.0,
            new_method="manual",
            actor=actor,
            reason=reason,
        )
    )
    if subject_id and not db.get(Subject, subject_id):
        raise IngestionError("Unknown subject id")
    if topic_id:
        topic = db.get(Topic, topic_id)
        if not topic:
            raise IngestionError("Unknown topic id")
        subject_id = subject_id or topic.subject_id
    if subtopic_id:
        sub = db.get(Subtopic, subtopic_id)
        if not sub:
            raise IngestionError("Unknown subtopic id")
        topic_id = topic_id or sub.topic_id
        subject_id = subject_id or sub.topic.subject_id
    question.subject_id = subject_id
    question.topic_id = topic_id
    question.subtopic_id = subtopic_id
    question.classification_confidence = 1.0
    question.classification_method = "manual"
    question.review_status = "manually_accepted" if accept else "pending"
    question.needs_review = not accept
    question.review_notes = (question.review_notes + "\n" + reason).strip()
    question.reviewed_by = actor
    question.reviewed_at = utcnow()
    if topic_id:
        topic = db.get(Topic, topic_id)
        question.section_id = topic.section_id if topic else question.section_id
    db.query(QuestionConcept).filter(QuestionConcept.question_id == question.id).delete()
    names = []
    for cid in list(dict.fromkeys(concept_ids)):
        concept = db.get(Concept, cid)
        if concept:
            db.add(QuestionConcept(question_id=question.id, concept_id=cid))
            names.append(concept.name)
    question.concept_text = ", ".join(names)
    db.commit()
