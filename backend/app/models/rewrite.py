"""Rewrite ORM model — stores the rewritten text for a document."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document

_VALID_STYLES = "('formal', 'casual', 'persuasive', 'concise', 'vivid')"


class Rewrite(Base):
    __tablename__ = "rewrites"
    __table_args__ = (
        # String column + CHECK is intentional — avoids the ALTER TABLE cost of a Postgres enum.
        CheckConstraint(f"style IN {_VALID_STYLES}", name="valid_style"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    style: Mapped[str] = mapped_column(String(16), nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    document: Mapped[Document] = relationship("Document", back_populates="rewrites", lazy="raise")
