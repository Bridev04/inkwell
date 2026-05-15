"""POST /api/v1/grammar — submit a draft, receive structured grammar analysis."""

from __future__ import annotations

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_llm_client
from app.db.session import get_session
from app.schemas.grammar import GrammarRequest, GrammarResponse
from app.services.grammar_service import check_grammar
from app.services.llm.base import LLMClient
from app.services.persistence import save_grammar_check

logger = logging.getLogger(__name__)

router = APIRouter(tags=["grammar"])


@router.post("/grammar", response_model=GrammarResponse)
async def create_grammar_check(
    req: GrammarRequest,
    llm: LLMClient = Depends(get_llm_client),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GrammarResponse:
    """Submit a writing draft and receive a list of grammar, spelling, punctuation, and style issues."""
    try:
        response = await check_grammar(req, llm)
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
            doc_id = await save_grammar_check(
                session,
                original_text=req.text,
                result=response.model_dump(mode="json", exclude={"document_id"}),
                corrected_text="",
            )
            response = response.model_copy(update={"document_id": doc_id})
        except Exception:
            logger.exception("Failed to persist grammar check result")

    return response
