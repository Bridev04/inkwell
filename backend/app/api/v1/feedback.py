"""POST /api/v1/feedback — submit a draft, receive structured AI feedback."""

from __future__ import annotations

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_llm_client
from app.db.session import get_session
from app.models.user import User
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import generate_feedback
from app.services.llm.base import LLMClient
from app.services.persistence import save_feedback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    llm: LLMClient = Depends(get_llm_client),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> FeedbackResponse:
    """Submit a writing draft and receive structured feedback across focus dimensions."""
    try:
        response = await generate_feedback(req, llm)
    except anthropic.APITimeoutError as exc:
        raise HTTPException(status_code=504, detail="LLM request timed out") from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="AI response could not be validated") from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail="LLM service error") from exc

    if req.save:
        try:
            doc_id = await save_feedback(
                session,
                original_text=req.text,
                # Exclude document_id from the stored payload to avoid circular redundancy.
                result=response.model_dump(mode="json", exclude={"document_id"}),
                user_id=user.id,
            )
            response = response.model_copy(update={"document_id": doc_id})
        except Exception:
            # Saving is best-effort: the user already has their feedback.
            # A persistence failure must not invalidate a successful LLM response.
            logger.exception("Failed to persist feedback result")

    return response
