from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./data/intervue.db"

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_scheme(cls, value: str) -> str:
        # Some hosts (Render/Heroku-style) hand out connection strings
        # prefixed "postgres://", a scheme SQLAlchemy 2.x's psycopg2
        # dialect no longer accepts - normalize to "postgresql://".
        if value.startswith("postgres://"):
            return "postgresql://" + value.removeprefix("postgres://")
        return value
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_request_timeout_seconds: float = 15.0
    gemini_max_retries: int = 1
    allowed_origins: list[str] = ["http://localhost:3000"]

    max_session_duration_minutes: int = 60
    max_questions_per_session: int = 40
    rate_limit_per_minute: int = 20

    # Auth (docs/BLUEPRINT.md §21 follow-up). jwt_secret_key has no safe
    # default - app.main refuses to start with an empty one in production.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    password_reset_token_expire_minutes: int = 30
    auth_rate_limit_per_minute: int = 10

    resend_api_key: str = ""
    email_from: str = "InterVue AI <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
