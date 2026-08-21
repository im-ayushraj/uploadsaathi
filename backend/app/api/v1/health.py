from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str
    database: str
    prototype_notice: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "up"
    except Exception:
        database = "down"

    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.VERSION,
        env=settings.APP_ENV,
        database=database,
        prototype_notice="Prototype — not an official UIDAI product.",
    )
