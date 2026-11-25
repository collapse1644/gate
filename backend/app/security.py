from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _key_path() -> Path:
    return settings.data_dir / ".secret.key"


def _get_fernet() -> Fernet:
    path = _key_path()
    if path.exists():
        key = path.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return Fernet(key)


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}***{value[-4:]}"
