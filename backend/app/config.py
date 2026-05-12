"""Application settings, loaded once from environment.

Per CLAUDE.md: this is the ONLY place env vars are read.
Import `settings` everywhere else.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Inkwell"
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


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. FastAPI uses this as a dependency."""
    return Settings()


settings = get_settings()
