"""Unit tests for app/core/security.py — JWT creation, verification, password hashing."""

import time
import uuid

import jwt
import pytest
from jwt.exceptions import PyJWTError as JWTError

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

# ── Password hashing ──────────────────────────────────────────────────────────


def test_hash_password_returns_string():
    result = hash_password("secret123")
    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_password_is_bcrypt():
    result = hash_password("secret123")
    assert result.startswith("$2b$") or result.startswith("$2a$")


def test_verify_password_correct():
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_hash_is_not_plain():
    pw = "mypassword"
    assert hash_password(pw) != pw


def test_two_hashes_of_same_password_differ():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


# ── Access token ──────────────────────────────────────────────────────────────


def test_create_access_token_returns_string():
    token = create_access_token(uuid.uuid4())
    assert isinstance(token, str)
    assert len(token) > 0


def test_access_token_has_correct_type():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["type"] == "access"


def test_access_token_has_correct_sub():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)


def test_access_token_has_exp():
    token = create_access_token(uuid.uuid4())
    payload = decode_token(token)
    assert "exp" in payload


def test_access_token_exp_in_future():
    token = create_access_token(uuid.uuid4())
    payload = decode_token(token)
    assert payload["exp"] > time.time()


# ── Refresh token ─────────────────────────────────────────────────────────────


def test_create_refresh_token_returns_string():
    token = create_refresh_token(uuid.uuid4())
    assert isinstance(token, str)


def test_refresh_token_has_correct_type():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_refresh_token_has_correct_sub():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)


def test_refresh_token_exp_later_than_access():
    uid = uuid.uuid4()
    access = create_access_token(uid)
    refresh = create_refresh_token(uid)
    access_exp = decode_token(access)["exp"]
    refresh_exp = decode_token(refresh)["exp"]
    assert refresh_exp > access_exp


# ── Decode token ──────────────────────────────────────────────────────────────


def test_decode_valid_token():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)


def test_decode_tampered_token_raises():
    token = create_access_token(uuid.uuid4())
    # Corrupt the signature
    tampered = token[:-4] + "xxxx"
    with pytest.raises(JWTError):
        decode_token(tampered)


def test_decode_wrong_secret_raises():
    user_id = uuid.uuid4()
    bad_token = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        "wrong-secret-key",
        algorithm=ALGORITHM,
    )
    with pytest.raises(JWTError):
        decode_token(bad_token)


def test_decode_expired_token_raises():
    from datetime import UTC, datetime, timedelta

    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=10),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with pytest.raises(JWTError):
        decode_token(expired_token)
