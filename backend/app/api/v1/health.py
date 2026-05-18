"""Health check route."""

from fastapi import APIRouter, Request

from app.config import settings
from app.core.limiter import limiter
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health(request: Request) -> HealthResponse:
    """Liveness probe. Returns service status for deploy targets."""
    return HealthResponse(status="ok", app=settings.app_name)
