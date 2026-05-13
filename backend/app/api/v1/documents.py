"""GET /api/v1/documents/{document_id} — fetch a saved document with its relations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.documents import DocumentRead
from app.services.persistence import get_document

router = APIRouter(tags=["documents"])


@router.get(
    "/documents/{document_id}",
    response_model=DocumentRead,
    summary="Fetch a saved document",
    description=(
        "Returns the document record with embedded feedback and rewrite arrays. "
        "Feedbacks and rewrites are eager-loaded in a single round-trip. "
        "Returns 404 if the document id is not found. "
        "IDs that are not valid UUIDs are rejected with 422."
    ),
)
async def get_document_by_id(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DocumentRead:
    """Retrieve a document and its embedded feedback and rewrite records by id."""
    doc = await get_document(session, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(doc)
