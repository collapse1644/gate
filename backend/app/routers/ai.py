from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import local_server, prompts
from app.ai.base import AIError, ImageInput, RateLimited
from app.ai.gemini import GeminiProvider
from app.ai.router import generate, provider_status
from app.config import settings
from app.settings_service import get_setting
from app.db import get_db
from app.models import (
    AIRun,
    Formula,
    Question,
    QuestionAsset,
    Solution,
    Subject,
    Subtopic,
    SyllabusSection,
    Topic,
    TutorMessage,
    TutorSession,
)
from app.schemas import (
    ConceptLessonRequest,
    FormulaExtractRequest,
    SolutionRequest,
    TutorMessageCreate,
    TutorSessionCreate,
    VisionRequest,
)
from app.serializers import formula_payload, question_detail, solution_payload
from app.services.rag import build_question_context, related_questions
from app.services.verification import extract_final_answer, verify_solution

router = APIRouter(tags=["ai"])


def _image_inputs(question: Question, limit: int = 4) -> list[ImageInput]:
    images: list[ImageInput] = []
    total = 0
    for asset in question.assets[:limit]:
        path = settings.data_dir / asset.path
        if not path.exists():
            continue
        data = path.read_bytes()
        total += len(data)
        if total > 12 * 1024 * 1024:
            break
        mime = "image/png"
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        images.append(ImageInput(data=data, mime_type=mime, label=f"page {asset.page}"))
    return images


def _ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RateLimited):
        return HTTPException(
            status_code=429,
            detail={
                "error": str(exc),
                "retry_after": exc.retry_after,
                "note": "Rate limits are not bypassed. Wait before retrying or switch to local mode.",
            },
        )
    if isinstance(exc, AIError):
        return HTTPException(status_code=503, detail={"error": str(exc)})
    return HTTPException(status_code=500, detail={"error": str(exc)})


@router.get("/ai/status")
async def ai_status(db: Session = Depends(get_db)) -> dict:
    return await provider_status(db)


@router.post("/ai/local/start")
def start_local(vision: bool = False, db: Session = Depends(get_db)) -> dict:
    try:
        return local_server.start(db, vision=vision)
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc


@router.post("/ai/local/stop")
def stop_local(db: Session = Depends(get_db)) -> dict:
    return local_server.stop(db)


@router.get("/ai/runs")
def ai_runs(
    question_id: int | None = None,
    limit: int = 30,
    db: Session = Depends(get_db),
) -> dict:
    query = select(AIRun).order_by(AIRun.created_at.desc()).limit(min(limit, 100))
    if question_id:
        query = query.where(AIRun.question_id == question_id)
    runs = db.scalars(query).all()
    return {
        "items": [
            {
                "id": run.id,
                "provider": run.provider,
                "model": run.model,
                "task": run.task,
                "mode": run.mode,
                "status": run.status,
                "latency_ms": run.latency_ms,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "fallback_from": run.fallback_from,
                "error": run.error,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in runs
        ]
    }


@router.post("/ai/solution/{question_id}")
async def generate_solution(
    question_id: int, payload: SolutionRequest, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    context = build_question_context(db, question, working_text=payload.working_text)
    system, prompt = prompts.solution_prompt(context, payload.mode)
    images = []
    mmproj = get_setting(db, "local_mmproj_path", "")
    cloud_consent = bool(get_setting(db, "cloud_consent", False))
    if mmproj or cloud_consent:
        images = _image_inputs(question)
    try:
        result = await generate(
            db,
            task="solution",
            system=system,
            prompt=prompt,
            images=images,
            question_id=question.id,
            mode=payload.mode,
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc

    version = max((s.version for s in question.solutions), default=0) + 1
    for old in question.solutions:
        old.is_current = False
    final_answer = extract_final_answer(result.text)
    solution = Solution(
        question_id=question.id,
        version=version,
        provider=result.provider,
        model=result.model,
        learning_mode=payload.mode,
        content=result.text,
        final_answer=final_answer,
        verification_status="UNVERIFIED",
        is_current=True,
        ai_run_id=getattr(result, "ai_run_id", None),
    )
    db.add(solution)
    question.solution_text = result.text
    db.commit()
    db.refresh(solution)
    # Structural checks are recorded immediately; this does not make the
    # solution VERIFIED without independent evidence.
    verify_solution(db, solution, question, plan=None)
    return {
        "solution": solution_payload(solution),
        "question": question_detail(question, db),
        "ai": {
            "provider": result.provider,
            "model": result.model,
            "fallback_from": result.fallback_from,
            "latency_ms": result.latency_ms,
            "attempts": result.attempts,
        },
        "notice": (
            "This explanation was generated by the stated provider/model. "
            "It is not automatically verified; inspect the verification checks."
        ),
    }


@router.post("/ai/tutor/sessions")
def create_tutor_session(payload: TutorSessionCreate, db: Session = Depends(get_db)) -> dict:
    question = None
    if payload.question_id:
        question = db.get(Question, payload.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
    if payload.mode == "concept" and not (payload.topic_id or payload.subtopic_id):
        raise HTTPException(status_code=400, detail="Concept mode requires a topic or subtopic.")
    title = payload.title
    if not title:
        if question:
            title = f"{question.year} Q{question.question_no} — {payload.mode}"
        elif payload.subtopic_id:
            sub = db.get(Subtopic, payload.subtopic_id)
            title = sub.name if sub else "Concept lesson"
        elif payload.topic_id:
            topic = db.get(Topic, payload.topic_id)
            title = topic.name if topic else "Concept lesson"
        else:
            title = "Tutor session"
    session = TutorSession(
        question_id=payload.question_id,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        mode=payload.mode,
        title=title[:255],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_payload(session, db)


def _session_payload(session: TutorSession, db: Session) -> dict:
    question = db.get(Question, session.question_id) if session.question_id else None
    return {
        "id": session.id,
        "title": session.title,
        "mode": session.mode,
        "question_id": session.question_id,
        "question": question_detail(question, db) if question else None,
        "subject_id": session.subject_id,
        "topic_id": session.topic_id,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "provider": m.provider,
                "model": m.model,
                "verification_status": m.verification_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in session.messages
        ],
    }


@router.get("/ai/tutor/sessions")
def list_sessions(db: Session = Depends(get_db)) -> dict:
    sessions = db.scalars(
        select(TutorSession).order_by(TutorSession.updated_at.desc()).limit(50)
    ).all()
    return {
        "items": [
            {
                "id": s.id,
                "title": s.title,
                "mode": s.mode,
                "question_id": s.question_id,
                "message_count": len(s.messages),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]
    }


@router.get("/ai/tutor/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = db.get(TutorSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tutor session not found")
    return _session_payload(session, db)


@router.post("/ai/tutor/sessions/{session_id}/messages")
async def tutor_message(
    session_id: int, payload: TutorMessageCreate, db: Session = Depends(get_db)
) -> dict:
    session = db.get(TutorSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tutor session not found")
    if session.question_id:
        question = db.get(Question, session.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="Question for this session no longer exists")
        context = build_question_context(db, question)
        history = [
            {"role": m.role, "content": m.content} for m in session.messages
        ]
        follow_up = bool(history)
        mode = "doubt" if follow_up else session.mode
        system, prompt = prompts.tutor_prompt(context, mode, history, payload.message)
        mmproj = get_setting(db, "local_mmproj_path", "")
        cloud_consent = bool(get_setting(db, "cloud_consent", False))
        images = _image_inputs(question) if (payload.include_figures and (mmproj or cloud_consent)) else []
    else:
        if not (session.topic_id or session.subject_id):
            raise HTTPException(status_code=400, detail="Session has no question or concept context.")
        context = _concept_context(db, session.subject_id, session.topic_id, None)
        history = [{"role": m.role, "content": m.content} for m in session.messages]
        system, prompt = prompts.concept_prompt(context)
        prompt += "\n\nStudent message: " + payload.message
        images = []

    user_message = TutorMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_message)
    db.commit()

    try:
        result = await generate(
            db,
            task="tutor_concept" if not session.question_id else "tutor",
            system=system,
            prompt=prompt,
            images=images,
            question_id=session.question_id,
            mode=session.mode,
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc

    assistant = TutorMessage(
        session_id=session.id,
        role="assistant",
        content=result.text,
        provider=result.provider,
        model=result.model,
        verification_status="EXPLANATION — NOT VERIFIED",
        ai_run_id=getattr(result, "ai_run_id", None),
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return {
        "message": {
            "id": assistant.id,
            "role": "assistant",
            "content": assistant.content,
            "provider": result.provider,
            "model": result.model,
            "fallback_from": result.fallback_from,
            "verification_status": assistant.verification_status,
            "latency_ms": result.latency_ms,
        },
        "session": _session_payload(session, db),
    }


def _concept_context(
    db: Session, subject_id: int | None, topic_id: int | None, subtopic_id: int | None
) -> dict:
    subject = db.get(Subject, subject_id) if subject_id else None
    topic = db.get(Topic, topic_id) if topic_id else None
    sub = db.get(Subtopic, subtopic_id) if subtopic_id else None
    if topic and not subject:
        subject = db.get(Subject, topic.subject_id)
    if sub and not topic:
        topic = db.get(Topic, sub.topic_id)
        subject = db.get(Subject, topic.subject_id) if topic else subject
    section = db.get(SyllabusSection, topic.section_id) if topic and topic.section_id else None
    related_query = select(Question).where(Question.import_status == "approved")
    if sub:
        related_query = related_query.where(Question.subtopic_id == sub.id)
    elif topic:
        related_query = related_query.where(Question.topic_id == topic.id)
    elif subject:
        related_query = related_query.where(Question.subject_id == subject.id)
    related = db.scalars(related_query.limit(5)).all()
    return {
        "subject": subject.name if subject else "Unspecified",
        "topic": topic.name if topic else "Unspecified",
        "subtopic": sub.name if sub else "Unspecified",
        "official_text": section.official_text if section else "",
        "related_questions": [
            {
                "year": q.year,
                "question_no": q.question_no,
                "excerpt": q.question_text[:260],
            }
            for q in related
        ],
    }


@router.post("/ai/gemini/test")
async def gemini_test(payload: dict, db: Session = Depends(get_db)) -> dict:
    from app.ai.base import ProviderUnavailable

    if not bool(get_setting(db, "cloud_consent", False)):
        raise HTTPException(status_code=403, detail="Cloud consent is disabled. Enable it in Settings before testing Gemini.")
    api_key = get_setting(db, "gemini_api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured.")
    model = get_setting(db, "gemini_model", "gemini-3.8-flash")
    prompt = str(payload.get("prompt") or "Reply with the single word: OK").strip()[:2000]
    provider = GeminiProvider(api_key=api_key, model=model)
    try:
        result = await provider.generate(
            system="You are a concise test endpoint. Reply briefly.",
            prompt=prompt,
            json_mode=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc
    return {
        "provider": result.provider,
        "model": result.model,
        "response": result.text,
        "latency_ms": result.latency_ms,
        "notice": "Gemini response from a real API call. Cloud consent was explicitly enabled.",
    }


@router.post("/ai/concept-lesson")
async def concept_lesson(payload: ConceptLessonRequest, db: Session = Depends(get_db)) -> dict:
    if not (payload.topic_id or payload.subtopic_id):
        raise HTTPException(status_code=400, detail="Select a topic or subtopic.")
    context = _concept_context(
        db, payload.subject_id, payload.topic_id, payload.subtopic_id
    )
    system, prompt = prompts.concept_prompt(context)
    try:
        result = await generate(
            db, task="concept_lesson", system=system, prompt=prompt, mode="concept"
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc
    session = TutorSession(
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        mode="concept",
        title=f"{context['topic']} — {context['subtopic']}",
    )
    db.add(session)
    db.flush()
    db.add(
        TutorMessage(
            session_id=session.id,
            role="user",
            content=f"Teach me {context['topic']} / {context['subtopic']} from fundamentals.",
        )
    )
    db.add(
        TutorMessage(
            session_id=session.id,
            role="assistant",
            content=result.text,
            provider=result.provider,
            model=result.model,
            verification_status="EXPLANATION — NOT VERIFIED",
            ai_run_id=getattr(result, "ai_run_id", None),
        )
    )
    db.commit()
    db.refresh(session)
    return {"session": _session_payload(session, db), "context": context}


@router.post("/ai/vision/{question_id}")
async def interpret_figure(
    question_id: int, payload: VisionRequest, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if not question.assets:
        raise HTTPException(status_code=400, detail="This question has no extracted figure.")
    asset = None
    if payload.asset_id:
        asset = db.get(QuestionAsset, payload.asset_id)
        if asset is None or asset.question_id != question.id:
            raise HTTPException(status_code=404, detail="Asset not found for this question")
    else:
        asset = question.assets[0]
    path = settings.data_dir / asset.path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset file is missing.")
    import base64

    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    system, prompt = prompts.vision_prompt(
        question.question_text, f"page {asset.page}, asset {asset.id}"
    )
    try:
        result = await generate(
            db,
            task="vision",
            system=system,
            prompt=prompt,
            images=[ImageInput(data=path.read_bytes(), mime_type=mime, label=str(asset.id))],
            json_mode=True,
            question_id=question.id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc
    try:
        parsed = json.loads(result.text)
    except json.JSONDecodeError:
        parsed = {"description": result.text, "uncertainties": ["Model returned unstructured text."]}
    asset.interpretation = json.dumps(parsed, indent=2)
    asset.interpretation_status = "ai_interpreted_unverified"
    asset.interpretation_model = f"{result.provider}:{result.model}"
    db.commit()
    return {
        "asset": {
            "id": asset.id,
            "interpretation": parsed,
            "status": asset.interpretation_status,
            "provider": result.provider,
            "model": result.model,
        },
        "notice": "AI figure interpretation is unverified and must not be treated as the original figure.",
    }


@router.post("/ai/formulas/extract/{question_id}")
async def extract_formulas(
    question_id: int, payload: FormulaExtractRequest, db: Session = Depends(get_db)
) -> dict:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    solution = None
    if payload.solution_id:
        solution = db.get(Solution, payload.solution_id)
        if solution is None or solution.question_id != question.id:
            raise HTTPException(status_code=404, detail="Solution not found for this question")
    else:
        solution = next((s for s in question.solutions if s.is_current), None)
    if solution is None:
        raise HTTPException(status_code=400, detail="Generate or select a solution first.")
    context = build_question_context(db, question)
    context["solution_text"] = solution.content
    system, prompt = prompts.formula_extraction_prompt(context)
    try:
        result = await generate(
            db,
            task="formula_extraction",
            system=system,
            prompt=prompt,
            json_mode=True,
            question_id=question.id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _ai_error(exc) from exc
    try:
        parsed = json.loads(result.text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Model returned invalid formula JSON.") from exc
    created = []
    for item in (parsed.get("formulas") or [])[:3]:
        if not item.get("name") or not item.get("latex"):
            continue
        formula = Formula(
            name=str(item["name"])[:255],
            latex=str(item["latex"]),
            subject_id=question.subject_id,
            topic_id=question.topic_id,
            subtopic_id=question.subtopic_id,
            variable_definitions=item.get("variables") or [],
            units=str(item.get("units", "")),
            applicability=str(item.get("applicability", "")),
            derivation=str(item.get("derivation", "")),
            common_mistakes=str(item.get("common_mistakes", "")),
            related_concepts=str(item.get("related_concepts", "")),
            pyq_references=[question.id],
            verification_status="proposed",
            source_solution_id=solution.id,
        )
        db.add(formula)
        db.flush()
        created.append(formula_payload(formula))
    db.commit()
    return {
        "created": created,
        "notice": "Proposed formulas require manual validation before entering the verified formula bank.",
    }
