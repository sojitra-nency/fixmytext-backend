"""
Legacy integration tests for text endpoints — now uses mock DB like the rest of the suite.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import create_access_token

_ALLOW = {"allowed": True, "reason": "free"}


@pytest.fixture(autouse=True)
def patch_access_checks():
    with (
        patch("app.api.v1.endpoints.text.check_tool_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.check_visitor_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.record_tool_discovery", AsyncMock()),
    ):
        yield


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_uppercase_endpoint(client):
    response = client.post("/api/v1/text/uppercase", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "HELLO"


def test_lowercase_endpoint(client):
    response = client.post("/api/v1/text/lowercase", json={"text": "HELLO"})
    assert response.status_code == 200
    assert response.json()["result"] == "hello"


def test_reverse_endpoint(client):
    response = client.post("/api/v1/text/reverse", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "olleh"


def test_base64_encode_endpoint(client):
    response = client.post("/api/v1/text/base64-encode", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "aGVsbG8="


def test_empty_text_returns_422(client):
    response = client.post("/api/v1/text/uppercase", json={"text": ""})
    assert response.status_code == 422


def test_ai_endpoint_requires_auth(unauth_client):
    response = unauth_client.post("/api/v1/text/change-tone", json={"text": "hello", "tone": "formal"})
    assert response.status_code == 401


def test_invalid_tone_returns_422(client):
    response = client.post(
        "/api/v1/text/change-tone",
        json={"text": "hello", "tone": "invalid"},
    )
    assert response.status_code == 422


def test_invalid_format_returns_422(client):
    response = client.post(
        "/api/v1/text/change-format",
        json={"text": "hello", "format": "invalid"},
    )
    assert response.status_code == 422
