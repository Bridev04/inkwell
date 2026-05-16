"""Fixtures for tests/api/ — wires a stub user into get_current_user for all api tests."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def _stub_auth() -> Generator[None, None, None]:
    """Override get_current_user with an in-memory stub for all tests in tests/api/."""
    stub = User(
        id=uuid.uuid4(),
        email="stub@example.com",
        hashed_password="irrelevant",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: stub
    yield
    app.dependency_overrides.pop(get_current_user, None)
