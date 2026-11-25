from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """Process-level configuration. User-facing configuration lives in app_settings.

    Only bootstrap values belong here. The Gemini key is stored encrypted in the
    local database and can alternatively be supplied via GEMINI_API_KEY.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GATE_", extra="ignore")

    app_name: str = "GATE CS 2027 Tutor"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{(DATA_DIR / 'gate.db').as_posix()}"
    data_dir: Path = DATA_DIR
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_upload_mb: int = 512
    gemini_api_key: str | None = None  # bootstrap fallback only

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def originals_dir(self) -> Path:
        return self.data_dir / "originals"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def official_dir(self) -> Path:
        return self.data_dir / "official"

    def ensure_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.originals_dir,
            self.assets_dir,
            self.backups_dir,
            self.official_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
