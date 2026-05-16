"""Application settings, loaded once from environment.

Per CLAUDE.md: this is the ONLY place env vars are read.
Import `settings` everywhere else.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Draftwell"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # LLM
    anthropic_api_key: SecretStr
    llm_default_model: str = Field(default="claude-haiku-4-5-20251001")
    llm_max_tokens: int = Field(default=1024)

    # Feedback endpoint
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001")
    feedback_max_text_chars: int = Field(default=10_000)

    # Rewrites endpoint
    rewrite_max_text_chars: int = Field(default=10_000)

    # Grammar checker endpoint
    grammar_max_text_chars: int = Field(default=10_000)

    # Paraphrase endpoint
    paraphrase_max_text_chars: int = Field(default=10_000)

    # CORS
    # Allowlist of origins permitted to make cross-origin requests (browser clients).
    # Set CORS_ALLOWED_ORIGINS as a comma-separated string to add additional origins
    # without a code change — e.g. the deployed Vercel URL in production.
    cors_allowed_origins: list[str] = Field(default=["http://localhost:3000"])

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Auth / JWT
    jwt_secret_key: SecretStr = Field(default=SecretStr("changeme-for-dev-only"))
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_minutes: int = Field(default=1440)  # 24 hours

    # Database
    # Two URLs for the same Postgres instance: the app uses the async asyncpg driver;
    # Alembic uses the sync psycopg v3 driver. Both point at the same database.
    database_url: str | None = Field(default=None)
    database_url_sync: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. FastAPI uses this as a dependency."""
    return Settings()


settings = get_settings()
