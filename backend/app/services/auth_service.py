"""Authentication service — password hashing, user creation, credential verification."""

from __future__ import annotations

import uuid

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


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
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    return user


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Return the User if credentials are valid, else None."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    """Fetch a user by primary key. Returns None if not found."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
