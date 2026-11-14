from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TrustAI API"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://trustai:trustai@localhost:5432/trustai"

    # Comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:5173"

    # CV storage (US03)
    upload_dir: Path = Path("uploads")
    max_upload_size_mb: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
