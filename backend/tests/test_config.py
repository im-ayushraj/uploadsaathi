"""Settings behaviour that only bites in a deployed environment."""

from app.core.config import Settings


def _settings(url: str) -> Settings:
    # _env_file=None so a developer's local .env cannot influence the assertion.
    return Settings(DATABASE_URL=url, _env_file=None)


def test_managed_postgres_url_is_pointed_at_psycopg3():
    url = _settings("postgres://user:pw@host.neon.tech:5432/db?sslmode=require").DATABASE_URL
    assert url == "postgresql+psycopg://user:pw@host.neon.tech:5432/db?sslmode=require"


def test_postgresql_scheme_without_driver_is_also_rewritten():
    assert _settings("postgresql://u:p@db:5432/x").DATABASE_URL == "postgresql+psycopg://u:p@db:5432/x"


def test_explicit_driver_and_sqlite_urls_are_left_alone():
    assert _settings("postgresql+psycopg://u:p@db/x").DATABASE_URL == "postgresql+psycopg://u:p@db/x"
    assert _settings("sqlite+pysqlite:///./x.db").DATABASE_URL == "sqlite+pysqlite:///./x.db"


def test_cors_origins_are_split_and_trimmed():
    parsed = _settings("sqlite+pysqlite:///./x.db").model_copy(
        update={"CORS_ORIGINS": "https://app.vercel.app , http://localhost:5173"}
    )
    assert parsed.cors_origins == ["https://app.vercel.app", "http://localhost:5173"]
