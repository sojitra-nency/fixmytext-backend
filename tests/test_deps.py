"""Tests for app/core/deps.py — the actual auth dependency implementation."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, create_refresh_token
from app.db.models import User
from app.db.session import get_db
from main import app
from tests.conftest import make_mock_db, make_user


# ── get_current_user (real implementation) ────────────────────────────────────


def _make_client_with_db(mock_db):
    """Return TestClient with only get_db overridden (not get_current_user)."""
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    from app.core.deps import get_optional_user
    app.dependency_overrides[get_optional_user] = lambda: None

    client = TestClient(app, raise_server_exceptions=False)
    return client


def test_get_current_user_no_credentials():
    """No Authorization header → 401."""
    mock_db = make_mock_db()
    client = _make_client_with_db(mock_db)
    resp = client.get("/api/v1/auth/me")
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_get_current_user_valid_token():
    """Valid token + user in DB → returns user."""
    user = make_user()
    mock_db = make_mock_db()
    mock_db.get.return_value = user

    # Also mock subscription check for /auth/me
    result = MagicMock()
    result.scalar.return_value = None  # not pro
    mock_db.execute.return_value = result

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    token = create_access_token(user.id)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user.email


def test_get_current_user_expired_token():
    """Expired/invalid token → 401."""
    mock_db = make_mock_db()
    client = _make_client_with_db(mock_db)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_get_current_user_refresh_token_type():
    """Refresh token used for auth → 401 (wrong type)."""
    user = make_user()
    mock_db = make_mock_db()
    mock_db.get.return_value = user

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    refresh_token = create_refresh_token(user.id)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_get_current_user_inactive_user():
    """Valid token but user is inactive → 401."""
    user = make_user(is_active=False)
    mock_db = make_mock_db()
    mock_db.get.return_value = user

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    token = create_access_token(user.id)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_get_current_user_not_in_db():
    """Valid token but user doesn't exist in DB → 401."""
    mock_db = make_mock_db()
    mock_db.get.return_value = None  # user not found

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    token = create_access_token(uuid.uuid4())
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


# ── get_optional_user (real implementation) ───────────────────────────────────


def test_get_optional_user_no_credentials():
    """No credentials → no user (None), public endpoint still works."""
    from unittest.mock import AsyncMock, patch

    mock_db = make_mock_db()

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    _ALLOW = {"allowed": True, "reason": "free"}
    with (
        patch("app.api.v1.endpoints.text.check_visitor_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.check_tool_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.record_tool_discovery", AsyncMock()),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/text/uppercase", json={"text": "hello"})
    app.dependency_overrides.clear()
    assert resp.status_code == 200


def test_get_optional_user_invalid_token_returns_none():
    """Invalid token for optional auth → treated as anonymous (None)."""
    from unittest.mock import AsyncMock, patch

    mock_db = make_mock_db()

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    _ALLOW = {"allowed": True, "reason": "free"}
    with (
        patch("app.api.v1.endpoints.text.check_visitor_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.check_tool_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.record_tool_discovery", AsyncMock()),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/v1/text/uppercase",
            json={"text": "hello"},
            headers={"Authorization": "Bearer bad.token"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 200  # anonymous access allowed


def test_get_optional_user_valid_token_wrong_type():
    """Refresh token for optional auth → treated as anonymous."""
    from unittest.mock import AsyncMock, patch

    user = make_user()
    mock_db = make_mock_db()
    mock_db.get.return_value = user

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    refresh_token = create_refresh_token(user.id)
    _ALLOW = {"allowed": True, "reason": "free"}
    with (
        patch("app.api.v1.endpoints.text.check_visitor_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.check_tool_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.record_tool_discovery", AsyncMock()),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/v1/text/uppercase",
            json={"text": "hello"},
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 200
