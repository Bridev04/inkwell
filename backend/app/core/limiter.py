"""Rate-limiter singleton shared across all routers.

Default key: real client IP, X-Forwarded-For-aware (required behind Railway's proxy).
LLM endpoints use ``get_user_or_ip`` so the budget is per-account, not per-IP.
In-memory storage is sufficient for a single-process Railway deployment; swap to
a Redis backend (SLOWAPI_STORAGE_URI) if horizontal scaling is added.
"""

from __future__ import annotations

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    """Return the real client IP, honouring X-Forwarded-For from Railway's proxy.

    We take the RIGHTMOST value: Railway (and any well-behaved reverse proxy)
    appends the real client IP at the end, so an attacker who injects a fake IP
    in the header will have their real IP appended after it by the proxy.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return get_remote_address(request)


def get_user_or_ip(request: Request) -> str:
    """Rate-limit key for authenticated endpoints: user-id when valid JWT is present,
    real IP otherwise. Prevents one account from abusing multiple IPs and avoids
    penalising shared-NAT users for each other's quota.
    """
    token = request.cookies.get("access_token")
    if token:
        try:
            from app.config import settings  # local import to avoid circular deps

            payload = jwt.decode(
                token,
                settings.jwt_secret_key.get_secret_value(),
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return get_real_ip(request)


limiter = Limiter(key_func=get_real_ip)
