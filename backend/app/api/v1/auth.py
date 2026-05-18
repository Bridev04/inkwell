"""POST /api/v1/auth/* — registration, login, logout, and whoami."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import Settings, get_settings
from app.core.limiter import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.users import UserCreate, UserLogin, UserRead
from app.services.auth_service import authenticate_user, create_user
from app.services.token_service import create_access_token

router = APIRouter(tags=["auth"])


def _set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="strict",  # all API traffic goes through the Next.js same-origin proxy
        max_age=settings.jwt_expiry_minutes * 60,
    )


@router.post("/auth/register", response_model=UserRead, status_code=201)
@limiter.limit("3/hour")
async def register(
    request: Request,
    body: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserRead:
    """Create a new user account and issue a session cookie."""
    user = await create_user(session, email=body.email, password=body.password)
    token = create_access_token(user.id, settings)
    _set_auth_cookie(response, token, settings)
    return UserRead.model_validate(user)


@router.post("/auth/login", response_model=UserRead)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: UserLogin,
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserRead:
    """Validate credentials and issue a session cookie."""
    user = await authenticate_user(session, email=body.email, password=body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id, settings)
    _set_auth_cookie(response, token, settings)
    return UserRead.model_validate(user)


@router.post("/auth/logout", status_code=204)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.environment == "production",
        samesite="strict",
        path="/",
    )


@router.get("/auth/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:  # noqa: B008
    """Return the currently authenticated user."""
    return UserRead.model_validate(user)
