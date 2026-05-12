"""POST /api/v1/feedback — submit a draft, receive structured AI feedback."""

from __future__ import annotations

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.api.deps import get_llm_client
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import generate_feedback
from app.services.llm.base import LLMClient

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    req: FeedbackRequest,
    llm: LLMClient = Depends(get_llm_client),  # noqa: B008
) -> FeedbackResponse:
    """Submit a writing draft and receive structured feedback across focus dimensions."""
    try:
        return await generate_feedback(req, llm)
    except anthropic.APITimeoutError as exc:
        raise HTTPException(status_code=504, detail="LLM request timed out") from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded") from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=502, detail="AI response could not be validated"
        ) from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail="LLM service error") from exc
