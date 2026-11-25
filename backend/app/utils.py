from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "item"


def normalize_text(value: str) -> str:
    value = value.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-")
    value = value.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def content_hash(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def file_sha256(path) -> str:  # noqa: ANN001
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None
