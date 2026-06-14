from fastapi import APIRouter

from app.api.v1.endpoints import ai, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ai.router)
