"""Health check route."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.limiter import limiter
from app.db.session import get_session
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health(
    request: Request,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> HealthResponse:
    """Liveness + DB readiness probe. Returns service and database status."""
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return HealthResponse(status="ok", app=settings.app_name, db_ok=db_ok)
