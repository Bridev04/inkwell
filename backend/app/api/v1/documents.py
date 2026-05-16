"""Document endpoints — list and fetch saved documents with their relations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.documents import DocumentRead
from app.services.persistence import get_document, get_documents_by_user

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentRead])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[DocumentRead]:
    """Return all documents owned by the current user, newest first."""
    docs = await get_documents_by_user(session, user.id)
    return [DocumentRead.model_validate(doc) for doc in docs]


@router.get(
    "/documents/{document_id}",
    response_model=DocumentRead,
    summary="Fetch a saved document",
    description=(
        "Returns the document record with embedded feedback and rewrite arrays. "
        "Feedbacks and rewrites are eager-loaded in a single round-trip. "
        "Returns 404 if the document id is not found or belongs to another user. "
        "IDs that are not valid UUIDs are rejected with 422."
    ),
)
async def get_document_by_id(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DocumentRead:
    """Retrieve a document and its embedded records by id. Returns 404 if not found or not owned."""
    doc = await get_document(session, document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(doc)
