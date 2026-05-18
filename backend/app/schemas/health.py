"""Health check response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    db_ok: bool
