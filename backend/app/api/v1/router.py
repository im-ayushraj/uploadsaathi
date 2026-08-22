from fastapi import APIRouter

from app.api.v1 import auth, documents, enrolments, health, portals

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(portals.router)
api_router.include_router(enrolments.router)
api_router.include_router(documents.router)
