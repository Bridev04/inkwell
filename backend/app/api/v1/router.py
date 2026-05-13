"""Aggregates all v1 routers into one."""

from fastapi import APIRouter

from app.api.v1 import documents, feedback, health, rewrites

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(feedback.router)
api_router.include_router(rewrites.router)
api_router.include_router(documents.router)
