"""Persistence service — saves and retrieves documents with their relations.

Keeps all ORM interactions in one place so routes stay thin and the persistence
logic is independently testable via the service layer.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.feedback import Feedback
from app.models.grammar_check import GrammarCheck
from app.models.paraphrase import Paraphrase
from app.models.rewrite import Rewrite


async def save_feedback(
    session: AsyncSession,
    *,
    original_text: str,
    result: dict[str, Any],
    user_id: uuid.UUID,
) -> uuid.UUID:
    """Persist a Document and its Feedback in one transaction, return the document id.

    The ID is generated in Python (not DB-generated) so the caller can
    return it in the response before the session commits.
    """
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_text=original_text, user_id=user_id)
    fb = Feedback(id=uuid.uuid4(), document_id=doc_id, result=result)
    session.add(doc)
    session.add(fb)
    await session.flush()
    return doc_id


async def save_rewrite(
    session: AsyncSession,
    *,
    original_text: str,
    style: str,
    output: str,
    user_id: uuid.UUID,
) -> uuid.UUID:
    """Persist a Document and its Rewrite in one transaction, return the document id."""
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_text=original_text, user_id=user_id)
    rw = Rewrite(id=uuid.uuid4(), document_id=doc_id, style=style, output=output)
    session.add(doc)
    session.add(rw)
    await session.flush()
    return doc_id


async def save_grammar_check(
    session: AsyncSession,
    *,
    original_text: str,
    result: dict[str, Any],
    corrected_text: str,
    user_id: uuid.UUID,
) -> uuid.UUID:
    """Persist a Document and its GrammarCheck in one transaction, return the document id."""
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_text=original_text, user_id=user_id)
    gc = GrammarCheck(
        id=uuid.uuid4(),
        document_id=doc_id,
        result=result,
        corrected_text=corrected_text,
    )
    session.add(doc)
    session.add(gc)
    await session.flush()
    return doc_id


async def save_paraphrase(
    session: AsyncSession,
    *,
    original_text: str,
    mode: str,
    output: str,
    user_id: uuid.UUID,
) -> uuid.UUID:
    """Persist a Document and its Paraphrase in one transaction, return the document id."""
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_text=original_text, user_id=user_id)
    ph = Paraphrase(id=uuid.uuid4(), document_id=doc_id, mode=mode, output=output)
    session.add(doc)
    session.add(ph)
    await session.flush()
    return doc_id


async def get_documents_by_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[Document]:
    """Fetch the most recent ``limit`` documents for a user, newest first.

    ``limit`` is server-enforced; callers should not pass values above 100.
    """
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .options(
            selectinload(Document.feedbacks),
            selectinload(Document.rewrites),
            selectinload(Document.grammar_checks),
            selectinload(Document.paraphrases),
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_document(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> Document | None:
    """Fetch a document with all relations eager-loaded.

    Uses selectinload to avoid N+1 queries. Returns None if not found.
    Explicit eager loading is required because the relationships default to lazy="raise".
    """
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .options(
            selectinload(Document.feedbacks),
            selectinload(Document.rewrites),
            selectinload(Document.grammar_checks),
            selectinload(Document.paraphrases),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
