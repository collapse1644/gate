"""llama.cpp adapter (OpenAI-compatible llama-server endpoint).

Only the local HTTP endpoint is used. The app never falls back to cloud from
this adapter.
"""

from __future__ import annotations

import base64
import json
import time

import httpx

from app.ai.base import AIError, AIResult, ImageInput, InvalidResponse, ProviderUnavailable


class LocalProvider:
    name = "local"

    def __init__(
        self,
        *,
        base_url: str,
        model_label: str,
        temperature: float = 0.2,
        max_tokens: int = 3072,
        timeout_seconds: int = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_label = model_label or "local-qwen"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    @property
    def health_url(self) -> str:
        root = self.base_url
        if root.endswith("/v1"):
            root = root[:-3]
        return f"{root}/health"

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(self.health_url)
                return {"ok": response.status_code == 200, "detail": response.text[:200]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": str(exc)[:200]}

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
        started = time.perf_counter()
        if images:
            content: list[dict] | str = [
                {"type": "text", "text": prompt},
                *[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img.mime_type};base64,"
                            + base64.b64encode(img.data).decode("ascii")
                        },
                    }
                    for img in images
                ],
            ]
        else:
            content = prompt
        payload = {
            "model": self.model_label,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(
                "Local llama.cpp server is not reachable. Start it in Settings or run llama-server manually.",
                provider=self.name,
            ) from exc
        except httpx.TimeoutException as exc:
            raise AIError(
                f"Local model timed out after {self.timeout_seconds}s.", provider=self.name
            ) from exc
        if response.status_code >= 400:
            message = response.text[:500]
            if response.status_code == 429:
                from app.ai.base import RateLimited

                raise RateLimited("Local server is busy (429).", provider=self.name)
            raise AIError(f"Local model request failed ({response.status_code}): {message}", provider=self.name)
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise InvalidResponse("Local model returned an unexpected response.", provider=self.name) from exc
        text = text or ""
        if json_mode:
            stripped = text.strip()
            if stripped.startswith("```"):
                stripped = stripped.strip("`")
                if stripped.lower().startswith("json"):
                    stripped = stripped[4:]
            start, end = stripped.find("{"), stripped.rfind("}")
            if start < 0 or end <= start:
                raise InvalidResponse("Local model returned invalid JSON.", provider=self.name)
            try:
                json.loads(stripped[start : end + 1])
            except json.JSONDecodeError as exc:
                raise InvalidResponse("Local model returned invalid JSON.", provider=self.name) from exc
            text = stripped[start : end + 1]
        usage = data.get("usage", {})
        return AIResult(
            text=text,
            provider=self.name,
            model=self.model_label,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
