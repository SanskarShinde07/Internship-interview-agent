from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./data/intervue.db"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_request_timeout_seconds: float = 15.0
    gemini_max_retries: int = 1
    allowed_origins: list[str] = ["http://localhost:3000"]

    max_session_duration_minutes: int = 60
    max_questions_per_session: int = 40
    rate_limit_per_minute: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
