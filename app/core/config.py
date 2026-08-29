"""Application configuration — everything comes from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings. Secrets are read from the environment / .env only."""

    app_name: str = "Imtihan"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "sqlite:///./imtihan.db"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    allowed_origins: str = "*"

    # Rate limiting
    rate_limit_register: str = "5/minute"
    rate_limit_login: str = "10/minute"
    rate_limit_submit: str = "10/minute"

    # Exam codes live for this many days
    exam_code_ttl_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
