"""Application settings, loaded once from environment.

Per CLAUDE.md: this is the ONLY place env vars are read.
Import `settings` everywhere else.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_KNOWN_WEAK_SECRETS = frozenset(
    {
        "changeme-for-dev-only",
        "changeme-dev-only-not-for-production",
        "changeme",
        "secret",
    }
)


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
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # LLM
    anthropic_api_key: SecretStr
    llm_default_model: str = Field(default="claude-haiku-4-5-20251001")
    llm_max_tokens: int = Field(default=1024)

    # Feedback endpoint
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
    # Comma-separated string; pydantic-settings v2 JSON-parses list fields at the
    # source level before field validators run, so we keep this as str and split at use sites.
    cors_allowed_origins: str = Field(default="http://localhost:3000")

    # Auth / JWT
    jwt_secret_key: SecretStr = Field(default=SecretStr("changeme-for-dev-only"))
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_minutes: int = Field(default=1440)  # 24 hours

    @model_validator(mode="after")
    def _reject_weak_secrets_in_production(self) -> "Settings":
        if self.environment == "production":
            secret = self.jwt_secret_key.get_secret_value()
            if len(secret) < 32 or secret in _KNOWN_WEAK_SECRETS:
                raise ValueError(
                    "JWT_SECRET_KEY must be ≥ 32 characters and not a known placeholder "
                    "when ENVIRONMENT=production. "
                    'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
                )
            origins = [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
            localhost_only = all("localhost" in o or "127.0.0.1" in o for o in origins)
            if localhost_only:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS still contains only localhost origins in production. "
                    "Set it to your Vercel deployment URL, e.g. https://draftwell.vercel.app"
                )
        return self

    # Google OAuth
    google_client_id: str | None = Field(default=None)
    google_client_secret: SecretStr | None = Field(default=None)
    # Redirect URI must match exactly what is registered in Google Cloud Console.
    # Local dev: http://localhost:3000/api/v1/auth/google/callback (via Next.js proxy)
    google_redirect_uri: str = Field(default="http://localhost:3000/api/v1/auth/google/callback")
    # Where to send the browser after a successful OAuth callback.
    frontend_base_url: str = Field(default="http://localhost:3000")

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
