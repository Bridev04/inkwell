"""ORM models package.

Importing here registers all models on Base.metadata so that Alembic
autogenerate can discover them via `target_metadata = Base.metadata`.
"""

from app.models.document import Document
from app.models.feedback import Feedback
from app.models.rewrite import Rewrite

__all__ = ["Document", "Feedback", "Rewrite"]
