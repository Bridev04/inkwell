"""Server-Sent Events formatting utilities."""

from __future__ import annotations

from pydantic import BaseModel


def format_sse(event_name: str, payload: BaseModel) -> str:
    """Serialize a Pydantic model as a standard SSE frame.

    The frame ends with two newlines so clients can detect event boundaries
    without buffering. ``event_name`` maps to the ``event:`` field; clients
    use it to dispatch to typed handlers.
    """
    return f"event: {event_name}\ndata: {payload.model_dump_json()}\n\n"
