"""POST /api/v1/paraphrase — submit a draft, receive a streamed paraphrase via SSE."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_llm_client
from app.db.session import get_session
from app.models.user import User
from app.schemas.paraphrase import ParaphraseRequest
from app.services.llm.base import LLMClient
from app.services.paraphrase_service import stream_paraphrase

router = APIRouter(tags=["paraphrase"])

_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@router.post("/paraphrase")
async def create_paraphrase(
    req: ParaphraseRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    llm: LLMClient = Depends(get_llm_client),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> StreamingResponse:
    """Submit a writing draft and receive a paraphrase streamed as SSE.

    Events: ``token`` (zero or more text chunks), ``done`` (final metadata),
    or ``error`` (if generation fails mid-stream after the response has started).
    When ``save=true``, a ``document`` event follows ``done`` with the saved document id.
    Pre-flight provider failures are returned as standard HTTP error codes.
    """
    gen = stream_paraphrase(req, llm, session=session, user_id=user.id)

    try:
        first_frame = await gen.__anext__()
    except anthropic.APITimeoutError as exc:
        raise HTTPException(status_code=504, detail="LLM request timed out") from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded") from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail="LLM service error") from exc

    async def _combined() -> AsyncGenerator[str, None]:
        yield first_frame
        async for frame in gen:
            yield frame

    return StreamingResponse(
        _combined(),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )
