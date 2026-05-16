"""Aggregates all v1 routers into one."""

from fastapi import APIRouter

from app.api.v1 import auth, documents, feedback, grammar, health, paraphrase, rewrites

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(feedback.router)
api_router.include_router(rewrites.router)
api_router.include_router(grammar.router)
api_router.include_router(paraphrase.router)
api_router.include_router(documents.router)
