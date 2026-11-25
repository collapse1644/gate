from __future__ import annotations

import asyncio
import hashlib
import time

from sqlalchemy.orm import Session

from app.ai.base import (
    AIError,
    AIResult,
    ImageInput,
    ProviderUnavailable,
    RateLimited,
)
from app.ai.gemini import GeminiProvider
from app.ai.local import LocalProvider
from app.ai import local_server
from app.models import AIRun
from app.settings_service import get_ai_config, get_setting


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_error_message(message: str, limit: int = 500) -> str:
    """Return an ASCII-safe error message.

    Non-ASCII characters (including U+2026 ellipsis) are replaced with their
    closest ASCII equivalent or removed, to prevent 'ascii' codec errors when
    the message is logged or serialized in contexts that expect ASCII.
    """
    replacements = {
        "\u2026": "...",  # ellipsis
        "\u2014": "-",    # em dash
        "\u2013": "-",    # en dash
        "\u201c": '"',    # left double quotation mark
        "\u201d": '"',    # right double quotation mark
        "\u2018": "'",    # left single quotation mark
        "\u2019": "'",    # right single quotation mark
        "\u00d7": "x",    # multiplication sign
        "\u00f7": "/",    # division sign
    }
    for orig, repl in replacements.items():
        message = message.replace(orig, repl)
    message = "".join(ch if ord(ch) < 128 else "?" for ch in message)
    return message[:limit]


def _redact(value: str, limit: int = 400) -> str:
    import re

    value = _safe_error_message(value, limit=limit)
    value = re.sub(r"(?i)(api[_-]?key|token|authorization)\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
    value = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", value)
    return value[:limit]


def _log_run(
    db: Session,
    *,
    provider: str,
    model: str,
    task: str,
    question_id: int | None,
    mode: str | None,
    status: str,
    latency_ms: int,
    prompt: str,
    response_text: str,
    error: str | None = None,
    fallback_from: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> AIRun:
    logging_mode = get_setting(db, "ai_logging", "metadata")
    run = AIRun(
        provider=provider,
        model=model,
        task=task,
        question_id=question_id,
        mode=mode,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        request_sha256=_sha(prompt),
        response_sha256=_sha(response_text) if response_text else "",
        request_excerpt=_redact(prompt) if logging_mode == "redacted_excerpt" else None,
        response_excerpt=(
            _redact(response_text) if logging_mode == "redacted_excerpt" and response_text else None
        ),
        error=_redact(error, 1000) if error else None,
        fallback_from=fallback_from,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _providers(db: Session) -> tuple[list[str], list[dict]]:
    cfg = get_ai_config(db)
    mode = cfg.get("ai_mode", "auto")
    preferred = cfg.get("preferred_provider", "gemini")
    allow_fallback = bool(cfg.get("allow_auto_fallback", True))
    notes: list[dict] = []

    if mode == "local_only":
        return ["local"], notes
    if mode == "local":
        return ["local"], notes
    if mode == "gemini":
        return ["gemini"], notes
    # automatic
    if preferred == "local":
        order = ["local", "gemini"]
    else:
        order = ["gemini", "local"]
    if not allow_fallback:
        order = order[:1]
    return order, notes


async def _ensure_local(db: Session, *, vision: bool = False) -> None:
    cfg = get_ai_config(db)
    provider = LocalProvider(
        base_url=cfg.get("local_base_url", "http://127.0.0.1:8080/v1"),
        model_label=cfg.get("local_model_label", "Qwen"),
        timeout_seconds=cfg.get("local_timeout_seconds", 300),
    )
    health = await provider.health()
    if health.get("ok"):
        return
    # In local_only mode, never silently start or fall back to cloud.
    if cfg.get("ai_mode") == "local_only":
        raise ProviderUnavailable(
            "Local model is offline and local_only mode is enabled. Start llama-server in Settings.",
            provider="local",
        )
    if not cfg.get("local_auto_start", True):
        raise ProviderUnavailable(
            "Local model is offline. Start llama-server manually or enable auto-start.", provider="local"
        )
    try:
        await asyncio.to_thread(local_server.start, db, vision=vision)
    except (ProviderUnavailable, AIError):
        raise


def _gemini_provider(db: Session) -> GeminiProvider:
    cfg = get_ai_config(db)
    if not cfg.get("cloud_consent", False):
        raise ProviderUnavailable(
            "Cloud AI consent is off. Enable it in Settings before sending any question content to Google.",
            provider="gemini",
        )
    if not cfg.get("gemini_api_key"):
        raise ProviderUnavailable("Gemini API key is not configured.", provider="gemini")
    return GeminiProvider(
        api_key=cfg["gemini_api_key"],
        model=cfg.get("gemini_model", "gemini-3.8-flash"),
        temperature=cfg.get("gemini_temperature", 0.2),
        max_output_tokens=cfg.get("gemini_max_output_tokens", 8192),
        timeout_seconds=cfg.get("gemini_timeout_seconds", 120),
        max_retries=cfg.get("gemini_max_retries", 2),
    )


def _local_provider(db: Session) -> LocalProvider:
    cfg = get_ai_config(db)
    return LocalProvider(
        base_url=cfg.get("local_base_url", "http://127.0.0.1:8080/v1"),
        model_label=cfg.get("local_model_label", "Qwen"),
        temperature=cfg.get("local_temperature", 0.2),
        max_tokens=cfg.get("local_max_tokens", 3072),
        timeout_seconds=cfg.get("local_timeout_seconds", 300),
    )


async def generate(
    db: Session,
    *,
    task: str,
    system: str,
    prompt: str,
    images: list[ImageInput] | None = None,
    json_mode: bool = False,
    question_id: int | None = None,
    mode: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> AIResult:
    order, _ = _providers(db)
    cfg = get_ai_config(db)
    attempts: list[dict] = []
    last_error: Exception | None = None
    fallback_from: str | None = None
    started = time.perf_counter()

    for provider_name in order:
        try:
            if provider_name == "gemini":
                provider = _gemini_provider(db)
            else:
                await _ensure_local(db, vision=bool(images))
                provider = _local_provider(db)
            result = await provider.generate(
                system=system,
                prompt=prompt,
                images=images,
                json_mode=json_mode,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result.attempts = attempts + [{"provider": provider_name, "status": "success"}]
            if fallback_from:
                result.fallback_from = fallback_from
            attempts.append({"provider": provider_name, "status": "success"})
            run = _log_run(
                db,
                provider=result.provider,
                model=result.model,
                task=task,
                question_id=question_id,
                mode=mode,
                status="success",
                latency_ms=result.latency_ms,
                prompt=prompt,
                response_text=result.text,
                fallback_from=fallback_from,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            setattr(result, "ai_run_id", run.id)
            return result
        except (ProviderUnavailable, RateLimited, AIError) as exc:
            last_error = exc
            attempts.append(
                {
                    "provider": provider_name,
                    "status": "error",
                    "error": str(exc)[:300],
                    "retry_after": getattr(exc, "retry_after", None),
                }
            )
            if not fallback_from:
                fallback_from = f"{provider_name}:unavailable"
            # Explicit single-provider modes do not silently fall back.
            if cfg.get("ai_mode") in {"gemini", "local", "local_only"}:
                break
            if not cfg.get("allow_auto_fallback", True):
                break
            continue

    latency = int((time.perf_counter() - started) * 1000)
    message = _safe_error_message(str(last_error), limit=700) if last_error else "No AI provider was available."
    _log_run(
        db,
        provider=order[0] if order else "none",
        model="",
        task=task,
        question_id=question_id,
        mode=mode,
        status="error",
        latency_ms=latency,
        prompt=prompt,
        response_text="",
        error=message,
        fallback_from=fallback_from,
    )
    detail = "; ".join(
        f"{a['provider']}: {_safe_error_message(a.get('error', a['status']), limit=200)}" for a in attempts
    ) or message
    if isinstance(last_error, RateLimited):
        raise RateLimited(detail, retry_after=last_error.retry_after) from last_error
    raise AIError(detail) from last_error


async def provider_status(db: Session) -> dict:
    cfg = get_ai_config(db)
    local = _local_provider(db)
    local_health = await local.health()
    gemini_ready = bool(cfg.get("gemini_api_key")) and bool(cfg.get("cloud_consent"))
    return {
        "mode": cfg.get("ai_mode", "auto"),
        "preferred_provider": cfg.get("preferred_provider", "gemini"),
        "allow_auto_fallback": cfg.get("allow_auto_fallback", True),
        "cloud_consent": cfg.get("cloud_consent", False),
        "gemini": {
            "configured": bool(cfg.get("gemini_api_key")),
            "ready": gemini_ready,
            "model": cfg.get("gemini_model", "gemini-3.8-flash"),
            "note": "Free-tier eligibility depends on your Google project and can change. Check official pricing.",
        },
        "local": {
            "ready": bool(local_health.get("ok")),
            "health": local_health,
            "endpoint": cfg.get("local_base_url"),
            "model": cfg.get("local_model_label"),
            "vision_model": cfg.get("local_vision_model_label"),
            "server": local_server.status(db),
        },
        "privacy": {
            "cloud_optional": True,
            "local_only_mode": cfg.get("ai_mode") == "local_only",
            "note": "Only the current question and the minimum retrieved context are sent when cloud consent is enabled.",
        },
    }
