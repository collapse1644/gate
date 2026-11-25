"""Gemini adapter using the official google-genai SDK.

The API key never leaves the backend. Model names are configuration values; the
default is a model currently listed by Google as free-tier eligible. Free-tier
eligibility and quotas can change, so the UI links to the official pricing page
instead of asserting permanent free access.
"""

from __future__ import annotations

import asyncio
import json
import re
import time

from app.ai.base import (
    AIError,
    AIResult,
    ImageInput,
    InvalidResponse,
    ProviderUnavailable,
    RateLimited,
)


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
        timeout_seconds: int = 120,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, min(max_retries, 3))

    def _client(self):
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable("google-genai is not installed.", provider=self.name) from exc
        return genai.Client(api_key=self.api_key)

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        images: list[ImageInput] | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AIResult:
        if not self.api_key:
            raise ProviderUnavailable("Gemini API key is not configured.", provider=self.name)

        started = time.perf_counter()
        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable("google-genai is not installed.", provider=self.name) from exc

        parts: list = [types.Part.from_text(text=prompt)]
        for image in images or []:
            parts.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature if temperature is None else temperature,
            max_output_tokens=self.max_output_tokens if max_tokens is None else max_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client().models.generate_content,
                        model=self.model,
                        contents=parts,
                        config=config,
                    ),
                    timeout=self.timeout_seconds,
                )
                text = getattr(response, "text", None) or ""
                if json_mode:
                    text = _ensure_json(text)
                usage = getattr(response, "usage_metadata", None)
                return AIResult(
                    text=text,
                    provider=self.name,
                    model=self.model,
                    input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
                    output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                message = str(exc)
                if _is_rate_limit(message):
                    retry_after = _retry_after(message)
                    # Do not hammer the free tier. One deferred retry at most,
                    # and only when the server explicitly recommends a short wait.
                    if attempt == 0 and retry_after is not None and retry_after <= 20:
                        await asyncio.sleep(retry_after)
                        continue
                    raise RateLimited(
                        f"Gemini rate limit reached. {message[:300]}",
                        provider=self.name,
                        retry_after=retry_after,
                    ) from exc
                if _is_auth_error(message):
                    raise ProviderUnavailable(
                        "Gemini authentication failed. Check the API key.", provider=self.name
                    ) from exc
                if attempt < self.max_retries and _is_transient(message):
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                break
        raise AIError(
            f"Gemini request failed: {_safe_error_message(str(last_error), limit=500)}",
            provider=self.name,
        )


def _safe_error_message(message: str, limit: int = 500) -> str:
    """Return an ASCII-safe error message.

    Non-ASCII characters (including U+2026 ellipsis) are replaced with their
    closest ASCII equivalent or removed, to prevent 'ascii' codec errors when
    the message is logged or serialized in contexts that expect ASCII.
    """
    # Replace common non-ASCII characters with ASCII equivalents
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
    # Remove any remaining non-ASCII characters
    message = "".join(ch if ord(ch) < 128 else "?" for ch in message)
    return message[:limit]


def _is_rate_limit(message: str) -> bool:
    lowered = message.lower()
    return "429" in lowered or "resource_exhausted" in lowered or "rate limit" in lowered


def _is_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ("401", "403", "api key", "permission denied", "unauthenticated"))


def _is_transient(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ("500", "502", "503", "504", "timeout", "deadline", "unavailable"))


def _retry_after(message: str) -> float | None:
    import re

    match = re.search(r"retry(?:_delay| after)?[\"':=\s]+(\d+(?:\.\d+)?)\s*s?", message, re.I)
    if match:
        return float(match.group(1))
    return None


def _ensure_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidate = stripped[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    raise InvalidResponse("Gemini returned invalid JSON.", provider="gemini")
