"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.config import settings
from app.api.v1.router import api_router


def create_app() -> FastAPI:
    """Application factory. Keeps top-level state explicit and testable."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()