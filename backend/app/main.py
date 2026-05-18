"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging


class _BodySizeLimitMiddleware:
    """Reject requests whose Content-Length header exceeds MAX_BYTES.

    Pure-ASGI, so it does not buffer bodies or interfere with SSE streaming.
    Chunked-encoded requests without Content-Length are not covered here —
    Railway's edge proxy provides an additional cap for those.
    """

    MAX_BYTES = 256 * 1024  # 256 KB — well above any valid JSON API payload

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        cl = headers.get(b"content-length")
        if cl is not None:
            try:
                if int(cl) > self.MAX_BYTES:
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": b'{"detail":"Request body too large"}',
                            "more_body": False,
                        }
                    )
                    return
            except ValueError:
                pass

        await self.app(scope, receive, send)


class _SecurityHeadersMiddleware:
    """Pure-ASGI middleware that injects security headers without buffering the body.

    Using a raw ASGI callable (rather than BaseHTTPMiddleware) is necessary to
    preserve streaming responses (SSE) without introducing latency.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def _send_with_headers(message: Any) -> None:
            if message.get("type") == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing = {h[0].lower() for h in headers}
                to_add = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"deny"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                if settings.environment == "production":
                    to_add.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                for name, value in to_add:
                    if name not in existing:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, _send_with_headers)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    configure_logging(level=level)
    yield


def create_app() -> FastAPI:
    """Application factory. Keeps top-level state explicit and testable."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(_BodySizeLimitMiddleware)
    app.add_middleware(_SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Type"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
