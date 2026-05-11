"""Health check route."""

from fastapi import APIRouter

from app.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Returns app metadata so deploy targets can verify config."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )
