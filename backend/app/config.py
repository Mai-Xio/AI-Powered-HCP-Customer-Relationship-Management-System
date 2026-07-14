from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AIVOA AI-first HCP CRM"
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm"
    groq_api_key: str | None = None
    aivoa_use_live_llm: bool = False
    aivoa_groq_calls_per_minute: int = 6
    aivoa_voice_calls_per_minute: int = 4
    aivoa_compose_with_llm: bool = False
    groq_transcription_model: str = "whisper-large-v3-turbo"
    voice_max_upload_bytes: int = 20 * 1024 * 1024
    # The assignment named gemma2-9b-it (now decommissioned on Groq) and
    # llama-3.3-70b-versatile (deprecating 2026-08-16). Default to Groq's
    # recommended, still-supported replacements; both are switchable at runtime
    # via the Developer settings panel and the model catalog.
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def database_must_be_mysql_or_postgres(cls, value: str) -> str:
        allowed_prefixes = (
            "mysql://",
            "mysql+pymysql://",
            "postgresql://",
            "postgresql+psycopg://",
        )
        if not value.startswith(allowed_prefixes):
            raise ValueError("DATABASE_URL must use MySQL or PostgreSQL for this assignment.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
