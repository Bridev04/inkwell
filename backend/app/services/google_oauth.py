"""Google OAuth2 + OIDC helpers — authorization URL, token exchange, user upsert."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from base64 import urlsafe_b64encode
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from joserfc import jwt as joserfc_jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.user import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

# Google rotates keys roughly every 6 hours; cache for 1 hour so we stay fresh
# without hammering their endpoint on every OAuth callback.
_JWKS_TTL: float = 3600.0
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge_S256) for PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorization_url(
    settings: Settings,
    *,
    state: str,
    nonce: str,
    code_challenge: str,
) -> str:
    """Return the Google OAuth2 authorization URL with all required parameters."""
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise RuntimeError(
            "Google OAuth is not configured (GOOGLE_CLIENT_ID or GOOGLE_REDIRECT_URI missing)"
        )
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    """POST the authorization code to Google's token endpoint and return the response."""
    if (
        not settings.google_client_id
        or not settings.google_client_secret
        or not settings.google_redirect_uri
    ):
        raise RuntimeError("Google OAuth is not configured")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret.get_secret_value(),
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


async def fetch_google_jwks() -> dict[str, Any]:
    """Fetch Google's current public key set, cached for 1 hour.

    Single-process safe (Procfile pins --workers 1).  If worker count is ever
    raised, move the cache to Redis.
    """
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if _jwks_cache and now - _jwks_fetched_at < _JWKS_TTL:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        r = await client.get(GOOGLE_JWKS_URL)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
    _jwks_cache = data
    _jwks_fetched_at = now
    return _jwks_cache


def validate_id_token(
    id_token: str,
    *,
    client_id: str,
    nonce: str,
    jwks_data: dict[str, Any],
) -> dict[str, Any]:
    """Validate a Google OIDC ID token (RS256). Returns the verified claims dict."""
    key_set = KeySet.import_key_set(jwks_data)  # type: ignore[arg-type]
    token = joserfc_jwt.decode(id_token, key_set, algorithms=["RS256"])

    registry = JWTClaimsRegistry(
        leeway=60,  # tolerate up to 60s of clock skew between server and Google
        iss={"essential": True, "values": list(GOOGLE_ISSUERS)},
        aud={"essential": True, "value": client_id},
    )
    registry.validate(token.claims)

    if token.claims.get("nonce") != nonce:
        raise ValueError("nonce mismatch in ID token")

    return dict(token.claims)


async def get_or_link_user(
    session: AsyncSession,
    *,
    claims: dict[str, Any],
) -> User:
    """Return (or create/link) a User row from validated OIDC claims.

    Linking rules:
    - Match by google_sub first (returning Google user — no DB change needed).
    - Match by email when email_verified=True AND the existing row has a local
      password: link google_sub to that row and return it.
    - Match by email but email_verified=False: raise 409 — cannot auto-link.
    - No match: create a new Google-only user (hashed_password=None).
    """
    sub: str = claims["sub"]
    email: str = claims["email"].lower()
    email_verified: bool = bool(claims.get("email_verified", False))

    # 1. Returning Google user
    result = await session.execute(select(User).where(User.google_sub == sub))
    user = result.scalar_one_or_none()
    if user is not None:
        logger.info(
            "google_login_existing",
            extra={"event": "google_login_existing", "user_id": str(user.id)},
        )
        return user

    # 2. Email collision
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        if not email_verified:
            logger.warning(
                "google_link_blocked_unverified",
                extra={"event": "google_link_blocked_unverified"},
            )
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in with your password.",
            )
        existing.google_sub = sub
        await session.flush()
        logger.info(
            "google_account_linked",
            extra={"event": "google_account_linked", "user_id": str(existing.id)},
        )
        return existing

    # 3. New Google-only user
    new_user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=None,
        google_sub=sub,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()
    logger.info(
        "google_user_created",
        extra={"event": "google_user_created", "user_id": str(new_user.id)},
    )
    return new_user
