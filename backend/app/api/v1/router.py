"""Aggregates all v1 routers into one."""

from fastapi import APIRouter

from app.api.v1 import feedback, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(feedback.router)
