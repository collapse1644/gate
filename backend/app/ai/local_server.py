"""Optional llama-server process manager for the local Qwen models.

The RTX 5050 has 8 GB VRAM. The manager loads exactly one model at a time. When
switching between the reasoning model and the vision model it stops the current
process first, so both models are never resident together.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.ai.base import AIError, ProviderUnavailable
from app.settings_service import get_setting
from sqlalchemy.orm import Session

_process: subprocess.Popen | None = None
_loaded_model: str | None = None


def _health_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    return f"{root}/health"


def _port(base_url: str) -> int:
    parsed = urlparse(base_url)
    return parsed.port or 8080


def status(db: Session) -> dict:
    global _process
    base_url = get_setting(db, "local_base_url", "http://127.0.0.1:8080/v1")
    alive = _process is not None and _process.poll() is None
    health = False
    detail = "not started"
    try:
        response = httpx.get(_health_url(base_url), timeout=2.0)
        health = response.status_code == 200
        detail = "llama-server healthy" if health else f"HTTP {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)[:180]
    model_path = get_setting(db, "local_model_path", "")
    return {
        "managed_process": alive,
        "pid": _process.pid if alive and _process else None,
        "loaded_model": _loaded_model,
        "model_path_configured": bool(model_path),
        "server_path_configured": bool(get_setting(db, "local_server_path", "")),
        "endpoint_healthy": health,
        "detail": detail,
        "base_url": base_url,
    }


def start(db: Session, *, vision: bool = False) -> dict:
    global _process, _loaded_model
    base_url = get_setting(db, "local_base_url", "http://127.0.0.1:8080/v1")
    server_path = get_setting(db, "local_server_path", "")
    model_path = get_setting(db, "local_model_path", "")
    if vision:
        model_path = get_setting(db, "local_vision_model_path", "") or model_path
    mmproj_path = get_setting(db, "local_mmproj_path", "")
    if not server_path:
        raise ProviderUnavailable(
            "llama-server executable path is not configured. Download a CUDA llama.cpp build and set it in Settings."
        )
    if not Path(server_path).exists():
        raise ProviderUnavailable(f"llama-server not found at {server_path}")
    if not model_path or not Path(model_path).exists():
        raise ProviderUnavailable("Local GGUF model path is not configured or does not exist.")
    if vision and (not mmproj_path or not Path(mmproj_path).exists()):
        raise ProviderUnavailable(
            "Vision projector (mmproj) is not configured. Set the Qwen3-VL mmproj path first."
        )

    desired = ("vision:" if vision else "text:") + str(Path(model_path).resolve())
    if _process is not None and _process.poll() is None:
        if _loaded_model == desired:
            return status(db)
        stop(db)

    args = [
        str(server_path),
        "-m",
        str(model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(_port(base_url)),
        "-ngl",
        str(get_setting(db, "local_gpu_layers", 28)),
        "-c",
        str(get_setting(db, "local_context", 8192)),
        "-t",
        str(get_setting(db, "local_threads", 8)),
    ]
    if vision and mmproj_path:
        args.extend(["--mmproj", str(mmproj_path)])
    extra = get_setting(db, "local_extra_args", "") or ""
    if extra:
        import shlex

        args.extend(shlex.split(extra))

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    try:
        _process = subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        _loaded_model = desired
    except OSError as exc:
        raise ProviderUnavailable(f"Could not start llama-server: {exc}") from exc

    deadline = time.time() + 120
    while time.time() < deadline:
        if _process.poll() is not None:
            _process = None
            _loaded_model = None
            raise ProviderUnavailable(
                "llama-server exited during startup. Check the model path, VRAM, and CUDA build."
            )
        try:
            response = httpx.get(_health_url(base_url), timeout=2.0)
            if response.status_code == 200:
                return status(db)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.0)
    stop(db)
    raise AIError("llama-server did not become healthy within 120 seconds.")


def stop(db: Session) -> dict:
    global _process, _loaded_model
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()
    _process = None
    _loaded_model = None
    return status(db)
