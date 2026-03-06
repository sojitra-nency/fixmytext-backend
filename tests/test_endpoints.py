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


def test_analyze_endpoint():
    response = client.post("/api/v1/text/analyze", json={"text": "Hello world"})
    assert response.status_code == 200
    data = response.json()
    assert data["word_count"] == 2


def test_empty_text_returns_422():
    """Backend should reject empty strings (min_length=1 on TextRequest)."""
    response = client.post("/api/v1/text/uppercase", json={"text": ""})
    assert response.status_code == 422
