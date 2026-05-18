"""GET /api/v1/auth/google — start OAuth flow
GET /api/v1/auth/google/callback — complete OAuth flow
"""

from __future__ import annotations

import logging
import re
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.limiter import limiter
from app.db.session import get_session
from app.services import google_oauth
from app.services.token_service import create_access_token

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

_NEXT_PATH_RE = re.compile(r"^/[a-zA-Z0-9/_-]{0,128}$")
_STATE_COOKIE = "oauth_state"
_STATE_SALT = "google-oauth-state"
_STATE_MAX_AGE = 600  # 10 minutes


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.jwt_secret_key.get_secret_value(), salt=_STATE_SALT)


def _safe_next(raw: str | None) -> str:
    """Return the path if it looks safe, else /desk."""
    if raw and _NEXT_PATH_RE.match(raw):
        return raw
    return "/desk"


@router.get("/auth/google")
@limiter.limit("10/minute")
async def google_start(
    request: Request,
    next: str | None = None,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RedirectResponse:
    """Redirect the browser to Google's consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier, code_challenge = google_oauth.generate_pkce_pair()
    next_path = _safe_next(next)

    signed = _serializer(settings).dumps(
        {"state": state, "nonce": nonce, "code_verifier": code_verifier, "next": next_path}
    )

    auth_url = google_oauth.build_authorization_url(
        settings, state=state, nonce=nonce, code_challenge=code_challenge
    )
    response = RedirectResponse(url=auth_url, status_code=307)
    response.set_cookie(
        key=_STATE_COOKIE,
        value=signed,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=_STATE_MAX_AGE,
        path="/",
    )
    return response


@router.get("/auth/google/callback")
@limiter.limit("20/minute")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    """Validate state, exchange code, upsert user, set JWT cookie, redirect to app."""
    if error:
        logger.warning("google_oauth_error", extra={"event": "google_oauth_error", "error": error})
        raise HTTPException(status_code=400, detail="Google login was cancelled or failed")

    if not code or not state:
        raise HTTPException(status_code=422, detail="Missing code or state parameter")

    raw_cookie = request.cookies.get(_STATE_COOKIE)
    if not raw_cookie:
        raise HTTPException(status_code=400, detail="OAuth state cookie missing or expired")

    try:
        cookie_data: dict[str, str] = _serializer(settings).loads(
            raw_cookie, max_age=_STATE_MAX_AGE
        )
    except SignatureExpired as exc:
        raise HTTPException(
            status_code=400, detail="OAuth session expired, please try again"
        ) from exc
    except BadSignature as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    if cookie_data["state"] != state:
        logger.warning("google_state_mismatch", extra={"event": "google_state_mismatch"})
        raise HTTPException(status_code=400, detail="OAuth state mismatch")

    try:
        tokens = await google_oauth.exchange_code(
            settings, code=code, code_verifier=cookie_data["code_verifier"]
        )
    except httpx.HTTPStatusError as exc:
        # Log only the status code — the request body contains client_secret
        logger.warning(
            "google_token_exchange_failed",
            extra={"event": "google_token_exchange_failed", "status": exc.response.status_code},
        )
        raise HTTPException(
            status_code=502, detail="Failed to exchange authorization code"
        ) from exc
    except Exception as exc:
        logger.warning(
            "google_token_exchange_error", extra={"event": "google_token_exchange_error"}
        )
        raise HTTPException(
            status_code=502, detail="Failed to exchange authorization code"
        ) from exc

    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="No ID token in Google response")

    try:
        jwks = await google_oauth.fetch_google_jwks()
        claims = google_oauth.validate_id_token(
            str(id_token),
            client_id=settings.google_client_id or "",
            nonce=cookie_data["nonce"],
            jwks_data=jwks,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Do not use logger.exception here — the traceback may embed token material
        logger.warning("google_id_token_invalid", extra={"event": "google_id_token_invalid"})
        raise HTTPException(status_code=502, detail="Invalid ID token from Google") from exc

    user = await google_oauth.get_or_link_user(session, claims=claims)

    token = create_access_token(user.id, settings)
    next_path = _safe_next(cookie_data.get("next"))
    destination = settings.frontend_base_url.rstrip("/") + next_path

    response = RedirectResponse(url=destination, status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_expiry_minutes * 60,
    )
    response.delete_cookie(key=_STATE_COOKIE, path="/")
    return response
