from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Application settings, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TrustAI API"
    environment: str = "development"
    api_prefix: str = "/api"

    # PostgreSQL connection, built from separate variables (no credentials in code).
    postgres_user: str = "trustai"
    postgres_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "trustai"

    # Comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:5173"

    # CV storage (US03)
    upload_dir: Path = Path("uploads")
    max_upload_size_mb: int = 5

    # LLM (US05, US09, US14): Groq's OpenAI-compatible API.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    # Must support strict json_schema output (see app/services/llm/groq.py).
    llm_model: str = "openai/gpt-oss-120b"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    # Room for the model's reasoning + a full profile (Groq's default, 3072, cuts it off).
    llm_max_completion_tokens: int = 8192
    # "low" / "medium" / "high" for gpt-oss models; empty for models without reasoning.
    llm_reasoning_effort: str = "low"

    # JWT (US01)
    jwt_secret: str = "change-me"
    jwt_expires_minutes: int = 60
    # Short-lived on purpose: a reset token grants a password change with no other check.
    password_reset_expires_minutes: int = 15

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
