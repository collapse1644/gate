from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppSetting
from app.security import decrypt, encrypt, mask_secret

DEFAULTS: dict[str, Any] = {
    # AI routing
    "ai_mode": "auto",  # gemini | local | auto | local_only
    "preferred_provider": "gemini",
    "allow_auto_fallback": True,
    "cloud_consent": False,
    "gemini_model": "gemini-3.8-flash",
    "gemini_temperature": 0.2,
    "gemini_max_output_tokens": 8192,
    "gemini_timeout_seconds": 120,
    "gemini_max_retries": 2,
    "ai_logging": "metadata",  # metadata | redacted_excerpt
    # Local llama.cpp
    "local_base_url": "http://127.0.0.1:8080/v1",
    "local_server_path": "",
    "local_model_path": "",
    "local_mmproj_path": "",
    "local_vision_model_path": "",
    "local_model_label": "Qwen3-8B Q4_K_M",
    "local_vision_model_label": "Qwen3-VL-4B",
    "local_context": 8192,
    "local_gpu_layers": 28,
    "local_threads": 8,
    "local_temperature": 0.2,
    "local_max_tokens": 3072,
    "local_timeout_seconds": 300,
    "local_auto_start": True,
    "local_extra_args": "",
    # Classification
    "classification_review_threshold": 0.55,
    "classification_accept_threshold": 0.72,
    "attribution_policy": "primary",  # primary | split
    # Mastery
    "mastery_strong_accuracy": 0.75,
    "mastery_strong_min_attempts": 5,
    "mastery_strong_min_questions": 3,
    "mastery_revision_accuracy": 0.55,
    # Data
    "backup_retention": 10,
}

SECRET_KEYS = {"gemini_api_key"}


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _decode(raw: str, default: Any) -> Any:
    if isinstance(default, bool):
        return raw.lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        try:
            return int(float(raw))
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except ValueError:
            return default
    if isinstance(default, (dict, list)):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return raw


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(AppSetting, key)
    if row is None:
        return DEFAULTS.get(key, default)
    if row.is_secret:
        return decrypt(row.value)
    fallback = DEFAULTS.get(key, default)
    return _decode(row.value, fallback if fallback is not None else "")


def get_all_settings(db: Session) -> dict[str, Any]:
    rows = {row.key: row for row in db.scalars(select(AppSetting)).all()}
    result: dict[str, Any] = {}
    for key, default in DEFAULTS.items():
        row = rows.get(key)
        if row is None:
            result[key] = default
        elif row.is_secret:
            result[key] = mask_secret(decrypt(row.value))
        else:
            result[key] = _decode(row.value, default)
    for key in SECRET_KEYS:
        if key in result:
            continue
        row = rows.get(key)
        result[key] = mask_secret(decrypt(row.value)) if row else ""
    result["gemini_api_key_set"] = bool(get_gemini_key(db))
    return result


def set_setting(db: Session, key: str, value: Any) -> None:
    is_secret = key in SECRET_KEYS
    raw = encrypt(str(value)) if is_secret else _encode(value)
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=raw, is_secret=is_secret)
        db.add(row)
    else:
        row.value = raw
        row.is_secret = is_secret
    db.commit()


def update_settings(db: Session, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if key.startswith("_"):
            continue
        if key == "gemini_api_key":
            # Never overwrite the real encrypted key with a masked placeholder
            # returned by get_all_settings. Only store a non-empty, non-masked value.
            if not value or _is_masked(value):
                continue
        if key not in DEFAULTS and key not in SECRET_KEYS:
            continue
        set_setting(db, key, value)


def _is_masked(value: str) -> bool:
    """Return True if the value looks like a masked secret placeholder.

    Only the placeholder format produced by ``mask_secret`` is treated as
    masked. Real API keys (even short ones) pass through unchanged.
    """
    if not isinstance(value, str):
        return False
    return "•" in value or "*" in value


def get_gemini_key(db: Session) -> str:
    stored = get_setting(db, "gemini_api_key", "")
    return stored or (settings.gemini_api_key or "")


def get_ai_config(db: Session) -> dict[str, Any]:
    keys = {
        key
        for key in DEFAULTS
        if key.startswith(("ai_", "gemini_", "local_"))
        or key in {"preferred_provider", "allow_auto_fallback", "cloud_consent"}
    }
    cfg = {key: get_setting(db, key) for key in keys}
    cfg["gemini_api_key"] = get_gemini_key(db)
    return cfg
