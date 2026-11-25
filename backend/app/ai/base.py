from __future__ import annotations

import time
from dataclasses import dataclass, field


class AIError(Exception):
    def __init__(self, message: str, *, provider: str | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.provider = provider
        self.retry_after = retry_after


class ProviderUnavailable(AIError):
    pass


class RateLimited(AIError):
    pass


class InvalidResponse(AIError):
    pass


@dataclass
class ImageInput:
    data: bytes
    mime_type: str = "image/png"
    label: str = ""


@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    fallback_from: str | None = None
    attempts: list[dict] = field(default_factory=list)


def timed(fn):  # noqa: ANN001, ANN201
    async def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003
        started = time.perf_counter()
        result = await fn(*args, **kwargs)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        return result

    return wrapper
