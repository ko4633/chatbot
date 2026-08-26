"""Single place secrets and configuration are read from the environment.

Swapping .env for a real secret manager later means replacing this module
only (see docs/SECURITY.md §2) — nothing else in the codebase reads os.environ
directly for a secret.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "omnis"
    postgres_user: str = "omnis"
    postgres_password: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379

    raw_store_backend: str = "local"  # "local" | "minio"
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "omnis"
    minio_root_password: str = ""
    minio_bucket: str = "omnis-raw"
    minio_secure: bool = False
    local_raw_store_path: str = str(REPO_ROOT / "data" / "raw")

    ai_enabled: bool = False
    anthropic_api_key: str = ""

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def ai_effectively_enabled(self) -> bool:
        """AI is only "on" if both enabled AND a key is present.

        A missing key must never crash startup (see docs/AI_POLICY.md §6) —
        it silently falls back to NullAIProvider instead.
        """
        return self.ai_enabled and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
