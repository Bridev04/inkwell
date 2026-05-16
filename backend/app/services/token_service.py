"""JWT token creation and verification."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import Settings


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    """Encode a signed JWT with the user id as subject."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload: dict[str, object] = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Decode and validate a JWT. Raises HTTP 401 on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return uuid.UUID(str(payload["sub"]))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
