"""Database package: base class, session factory, and FastAPI dependency."""

from app.db.base import Base
from app.db.session import get_session

__all__ = ["Base", "get_session"]
