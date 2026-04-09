"""Tests for app/services/razorpay_service.py"""

import pytest

# ── razorpay_service ──────────────────────────────────────────────────────────


def test_verify_webhook_signature_correct():
    import hashlib
    import hmac

    from app.core.config import settings
    from app.services.razorpay_service import verify_webhook_signature

    # Override webhook secret temporarily
    original_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "test-secret"  # noqa: S105

    body = b'{"event": "payment.captured"}'
    expected = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    result = verify_webhook_signature(body, expected)
    settings.RAZORPAY_WEBHOOK_SECRET = original_secret
    assert result is True


def test_verify_webhook_signature_wrong():
    from app.core.config import settings
    from app.services.razorpay_service import verify_webhook_signature

    original_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "test-secret"  # noqa: S105

    body = b'{"event": "payment.captured"}'
    result = verify_webhook_signature(body, "wrong-signature")
    settings.RAZORPAY_WEBHOOK_SECRET = original_secret
    assert result is False


def test_verify_webhook_signature_no_secret():
    from app.core.config import settings
    from app.services.razorpay_service import verify_webhook_signature

    original_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = ""

    result = verify_webhook_signature(b"body", "sig")
    settings.RAZORPAY_WEBHOOK_SECRET = original_secret
    assert result is False


def test_verify_payment_signature_invalid():
    from app.services.razorpay_service import verify_payment_signature

    # Without a real client, this will raise RuntimeError
    with pytest.raises((RuntimeError, Exception)):
        verify_payment_signature("order_id", "pay_id", "bad_sig")


def test_get_client_raises_when_not_initialized():
    from app.services import razorpay_service

    original_client = razorpay_service._client
    razorpay_service._client = None
    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            razorpay_service.get_client()
    finally:
        razorpay_service._client = original_client
