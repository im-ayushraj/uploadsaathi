from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "UploadSaathi API"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "0.1.0"

    # Local dev falls back to SQLite; Docker Compose supplies a PostgreSQL URL.
    DATABASE_URL: str = "sqlite+pysqlite:///./uploadsaathi.db"

    # Auth. JWT_SECRET must be overridden via env in any deployed environment.
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Comma-separated list of allowed browser origins.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Where optimised documents are kept. Originals are never written to disk.
    STORAGE_DIR: str = "./var/documents"
    # Refuse an upload larger than this before any processing starts.
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg3(cls, value: str) -> str:
        """Managed hosts (Render, Neon, Railway, Heroku) hand out `postgres://` URLs, which
        SQLAlchemy resolves to psycopg2 — a driver this project does not install. Point them at
        psycopg 3 so a copy-pasted connection string just works."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return f"postgresql+psycopg://{value[len(prefix) :]}"
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
