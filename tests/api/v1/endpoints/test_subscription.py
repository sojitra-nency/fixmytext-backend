"""Tests for /api/v1/subscription/* endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

# ── GET /subscription/status ─────────────────────────────────────────────────


def test_subscription_status_success(client, mock_db, fake_user):
    """Authenticated user gets subscription status with usage info."""
    with (
        patch("app.api.v1.endpoints.subscription.resolve_user_region", AsyncMock()),
        patch(
            "app.api.v1.endpoints.subscription.get_all_tool_uses_today",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.api.v1.endpoints.subscription.has_logged_in_today",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.api.v1.endpoints.subscription.record_daily_login",
            AsyncMock(),
        ),
        patch(
            "app.api.v1.endpoints.subscription.get_credit_balance",
            AsyncMock(return_value=0),
        ),
        patch(
            "app.api.v1.endpoints.subscription.get_active_passes",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.api.v1.endpoints.subscription.get_subscription_tier",
            AsyncMock(return_value="free"),
        ),
    ):
        resp = client.get("/api/v1/subscription/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data
    assert "tool_uses_today" in data
    assert data["tier"] == "free"


def test_subscription_status_requires_auth(unauth_client):
    """Unauthenticated subscription status returns 401."""
    resp = unauth_client.get("/api/v1/subscription/status")
    assert resp.status_code == 401


# ── POST /subscription/checkout ──────────────────────────────────────────────


def test_checkout_payments_not_configured(client, mock_db):
    """When RAZORPAY_KEY_ID is empty, checkout returns 503."""
    from app.core.config import settings

    original = settings.RAZORPAY_KEY_ID
    settings.RAZORPAY_KEY_ID = ""

    # subscription tier check
    result = MagicMock()
    result.scalar.return_value = None
    mock_db.execute.return_value = result

    resp = client.post("/api/v1/subscription/checkout")
    settings.RAZORPAY_KEY_ID = original
    assert resp.status_code == 503


def test_checkout_already_pro(client, mock_db):
    """User already subscribed to Pro gets 400."""
    from app.core.config import settings

    original = settings.RAZORPAY_KEY_ID
    settings.RAZORPAY_KEY_ID = "rzp_test_xxx"

    result = MagicMock()
    result.scalar.return_value = "pro"  # already pro
    mock_db.execute.return_value = result

    resp = client.post("/api/v1/subscription/checkout")
    settings.RAZORPAY_KEY_ID = original
    assert resp.status_code == 400


def test_checkout_requires_auth(unauth_client):
    """Checkout requires authentication."""
    resp = unauth_client.post("/api/v1/subscription/checkout")
    assert resp.status_code == 401


# ── POST /subscription/cancel ────────────────────────────────────────────────


def test_cancel_no_active_sub(client, mock_db):
    """Cancelling with no active Pro subscription returns 400."""
    result = MagicMock()
    result.scalar.return_value = None  # not pro
    mock_db.execute.return_value = result

    resp = client.post("/api/v1/subscription/cancel")
    assert resp.status_code == 400


def test_cancel_requires_auth(unauth_client):
    """Cancel requires authentication."""
    resp = unauth_client.post("/api/v1/subscription/cancel")
    assert resp.status_code == 401


# ── POST /subscription/verify ────────────────────────────────────────────────


def test_verify_requires_auth(unauth_client):
    """Verify requires authentication."""
    resp = unauth_client.post(
        "/api/v1/subscription/verify",
        json={
            "razorpay_order_id": "order_xxx",
            "razorpay_payment_id": "pay_xxx",
            "razorpay_signature": "sig_xxx",
        },
    )
    assert resp.status_code == 401


# ── POST /subscription/webhook ───────────────────────────────────────────────


def test_webhook_no_secret_configured(anon_client, mock_db):
    """When webhook secret is not configured, returns 503."""
    from app.core.config import settings

    original = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = ""

    resp = anon_client.post(
        "/api/v1/subscription/webhook",
        data=b'{"event":"test"}',
        headers={"x-razorpay-signature": "sig", "content-type": "application/json"},
    )
    settings.RAZORPAY_WEBHOOK_SECRET = original
    assert resp.status_code == 503


def test_webhook_invalid_signature(anon_client, mock_db):
    """Invalid webhook signature returns 400."""
    from app.core.config import settings

    original = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "test-secret"  # noqa: S105

    resp = anon_client.post(
        "/api/v1/subscription/webhook",
        data=b'{"event":"test"}',
        headers={
            "x-razorpay-signature": "bad-signature",
            "content-type": "application/json",
        },
    )
    settings.RAZORPAY_WEBHOOK_SECRET = original
    assert resp.status_code == 400
