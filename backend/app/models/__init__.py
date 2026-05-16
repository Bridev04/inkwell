"""ORM models package.

Importing here registers all models on Base.metadata so that Alembic
autogenerate can discover them via `target_metadata = Base.metadata`.
"""

from app.models.document import Document
from app.models.feedback import Feedback
from app.models.grammar_check import GrammarCheck
from app.models.paraphrase import Paraphrase
from app.models.rewrite import Rewrite
from app.models.user import User

__all__ = ["Document", "Feedback", "GrammarCheck", "Paraphrase", "Rewrite", "User"]
