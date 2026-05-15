"""add grammar_checks and paraphrases tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grammar_checks",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("corrected_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_grammar_checks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grammar_checks"),
    )
    op.create_index(
        "ix_grammar_checks_document_id", "grammar_checks", ["document_id"], unique=False
    )

    op.create_table(
        "paraphrases",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mode IN ('standard', 'simpler', 'shorter', 'academic', 'creative')",
            name="ck_paraphrases_valid_mode",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_paraphrases_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_paraphrases"),
    )
    op.create_index(
        "ix_paraphrases_document_id", "paraphrases", ["document_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_paraphrases_document_id", table_name="paraphrases")
    op.drop_table("paraphrases")
    op.drop_index("ix_grammar_checks_document_id", table_name="grammar_checks")
    op.drop_table("grammar_checks")
