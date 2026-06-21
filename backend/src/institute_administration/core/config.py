"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
and validated by Pydantic. Access them through :func:`get_settings`, which
returns a cached singleton.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Application --------------------------------------------------------
    app_name: str = "Institute Administration API"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # -- Server -------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # -- CORS ---------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # -- Logging ------------------------------------------------------------
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = False

    # -- Database -----------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "institute_administration"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Name of the ICU collation used to sort Arabic text linguistically
    # (created by the initial migration). See infrastructure/database/collation.
    arabic_collation: str = "arabic"

    # -- Authentication / JWT ----------------------------------------------
    # SECURITY: override jwt_secret_key in every non-local environment.
    jwt_secret_key: str = "insecure-development-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # -- Bootstrap super-admin (seed) --------------------------------------
    superadmin_email: str = "SuperAdmin@gmail.com"
    superadmin_password: str = "admin"
    superadmin_full_name: str = "مدير النظام"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (asyncpg driver), used by the application."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
