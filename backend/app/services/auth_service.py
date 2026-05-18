"""Authentication service — password hashing, user creation, credential verification."""

from __future__ import annotations

import logging
import uuid

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)

# Pre-computed dummy hash used in authenticate_user when the email is not found.
# Always running bcrypt (even for unknown emails) prevents a timing oracle that
# would let an attacker distinguish "email not registered" from "wrong password".
_DUMMY_HASH: str = bcrypt.hashpw(b"__dummy__", bcrypt.gensalt()).decode()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    """Create a new user. Raises 409 if the email is already registered."""
    user = User(
        id=uuid.uuid4(),
        email=email.lower(),
        hashed_password=hash_password(password),
        is_active=True,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        logger.warning("registration_duplicate", extra={"event": "registration_duplicate"})
        raise HTTPException(status_code=409, detail="Registration unsuccessful") from exc
    logger.info("user_registered", extra={"event": "user_registered", "user_id": str(user.id)})
    return user


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Return the User if credentials are valid, else None.

    Always calls bcrypt regardless of whether the email exists or is Google-only,
    so the response time is indistinguishable between "unknown email", "wrong
    password", and "Google-only account".
    """
    result = await session.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    # Use the real hash when available; otherwise verify against a dummy so
    # timing is constant even for unknown emails or Google-only accounts.
    target_hash = (
        user.hashed_password
        if user is not None and user.hashed_password is not None
        else _DUMMY_HASH
    )
    if not verify_password(password, target_hash) or user is None or user.hashed_password is None:
        logger.warning("login_failed", extra={"event": "login_failed"})
        return None
    logger.info("login_success", extra={"event": "login_success", "user_id": str(user.id)})
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address. Returns None if not found."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    """Fetch a user by primary key. Returns None if not found."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
