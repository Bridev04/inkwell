"""Document ORM model — root of the persistence hierarchy."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.feedback import Feedback
    from app.models.rewrite import Rewrite


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # lazy="raise" forces callers to use explicit selectinload — prevents N+1 accidents.
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback", back_populates="document", lazy="raise"
    )
    rewrites: Mapped[list[Rewrite]] = relationship(
        "Rewrite", back_populates="document", lazy="raise"
    )
