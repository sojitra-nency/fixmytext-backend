"""
Integration tests for the /api/v1/text/* endpoints using FastAPI's TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_uppercase_endpoint():
    response = client.post("/api/v1/text/uppercase", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "HELLO"


def test_lowercase_endpoint():
    response = client.post("/api/v1/text/lowercase", json={"text": "HELLO"})
    assert response.status_code == 200
    assert response.json()["result"] == "hello"


def test_reverse_endpoint():
    response = client.post("/api/v1/text/reverse", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "olleh"


def test_base64_encode_endpoint():
    response = client.post("/api/v1/text/base64-encode", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json()["result"] == "aGVsbG8="


def test_empty_text_returns_422():
    """Backend should reject empty strings (min_length=1 on TextRequest)."""
    response = client.post("/api/v1/text/uppercase", json={"text": ""})
    assert response.status_code == 422


def test_invalid_tone_returns_422():
    """Invalid tone value should be rejected by Literal validation."""
    response = client.post("/api/v1/text/change-tone", json={"text": "hello", "tone": "invalid"})
    assert response.status_code == 422


def test_invalid_format_returns_422():
    """Invalid format value should be rejected by Literal validation."""
    response = client.post("/api/v1/text/change-format", json={"text": "hello", "format": "invalid"})
    assert response.status_code == 422
