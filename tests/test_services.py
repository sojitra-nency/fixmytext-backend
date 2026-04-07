"""Unit tests for service-layer functions (pass_service, region_service, razorpay_service)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_mock_db, make_user

# ── pass_service.get_subscription_tier ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_subscription_tier_free():
    from app.services.pass_service import get_subscription_tier

    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = None  # no active pro subscription
    db.execute.return_value = result

    tier = await get_subscription_tier(uuid.uuid4(), db)
    assert tier == "free"


@pytest.mark.asyncio
async def test_get_subscription_tier_pro():
    from app.services.pass_service import get_subscription_tier

    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = "pro"
    db.execute.return_value = result

    tier = await get_subscription_tier(uuid.uuid4(), db)
    assert tier == "pro"


# ── pass_service.get_credit_balance ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_credit_balance_zero():
    from app.services.pass_service import get_credit_balance

    user = make_user()
    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = 0
    db.execute.return_value = result

    balance = await get_credit_balance(user, db)
    assert balance == 0


@pytest.mark.asyncio
async def test_get_credit_balance_positive():
    from app.services.pass_service import get_credit_balance

    user = make_user()
    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = 15
    db.execute.return_value = result

    balance = await get_credit_balance(user, db)
    assert balance == 15


# ── pass_service.check_tool_access ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_tool_access_always_free():
    from app.services.pass_service import check_tool_access

    user = make_user()
    db = make_mock_db()

    # "find_replace" is in ALWAYS_FREE_TOOL_IDS
    result = await check_tool_access(user, "find_replace", "api", db)
    assert result["allowed"] is True
    assert result["reason"] == "free"


@pytest.mark.asyncio
async def test_check_tool_access_drawer_type():
    from app.services.pass_service import check_tool_access

    user = make_user()
    db = make_mock_db()

    result = await check_tool_access(user, "any_tool", "drawer", db)
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_check_tool_access_within_daily_limit():
    from app.services.pass_service import check_tool_access

    user = make_user()
    db = make_mock_db()

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # subscription check
        if call_count == 1:
            result.scalar.return_value = None  # not pro
        # active passes
        elif call_count == 2:
            result.scalars.return_value.all.return_value = []  # no passes
        # credit balance
        elif call_count == 3:
            result.scalar.return_value = 0  # no credits
        # daily login bonus
        elif call_count == 4:
            result.scalars.return_value.first.return_value = None  # no login bonus
        # tool usage count today
        elif call_count == 5:
            result.scalar.return_value = 0  # 0 uses today
        return result

    db.execute.side_effect = execute_side_effect

    result = await check_tool_access(user, "uppercase", "api", db)
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_check_tool_access_daily_limit_exceeded():
    from app.services.pass_service import check_tool_access

    user = make_user()
    db = make_mock_db()

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar.return_value = None  # not pro
        elif call_count == 2:
            result.scalars.return_value.all.return_value = []  # no passes
        elif call_count == 3:
            result.scalars.return_value.first.return_value = None  # no credits
        elif call_count == 4:
            # get_tool_use_count_today → 5 uses today (over limit)
            result.scalar.return_value = 5
        elif call_count == 5:
            # has_logged_in_today → not logged in today
            result.scalars.return_value.first.return_value = None
        return result

    db.execute.side_effect = execute_side_effect

    result = await check_tool_access(user, "uppercase", "api", db)
    assert result["allowed"] is False


# ── pass_service.grant_credits ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grant_credits():
    from app.services.pass_service import grant_credits

    user = make_user()
    db = make_mock_db()

    await grant_credits(user, 10, "test", db)
    db.add.assert_called_once()
    db.commit.assert_awaited()


# ── pass_service.get_tool_use_count_today ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_tool_use_count_today_zero():
    from app.services.pass_service import get_tool_use_count_today

    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = None
    db.execute.return_value = result

    count = await get_tool_use_count_today(uuid.uuid4(), "uppercase", db)
    assert count == 0


@pytest.mark.asyncio
async def test_get_tool_use_count_today_nonzero():
    from app.services.pass_service import get_tool_use_count_today

    db = make_mock_db()
    result = MagicMock()
    result.scalar.return_value = 3
    db.execute.return_value = result

    count = await get_tool_use_count_today(uuid.uuid4(), "uppercase", db)
    assert count == 3


# ── region_service ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detect_region_india():
    from app.services.region_service import detect_region

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"countryCode": "IN"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        region = await detect_region("203.0.113.5")  # non-local IP
    assert region == "IN"


@pytest.mark.asyncio
async def test_detect_region_us():
    from app.services.region_service import detect_region

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"countryCode": "US"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        region = await detect_region("8.8.8.8")
    assert region == "US"


@pytest.mark.asyncio
async def test_detect_region_eu():
    from app.services.region_service import detect_region

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"countryCode": "DE"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        region = await detect_region("1.2.3.4")
    assert region == "EU"


@pytest.mark.asyncio
async def test_detect_region_unknown_country_defaults_us():
    from app.services.region_service import detect_region

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"countryCode": "ZZ"}  # not mapped

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        region = await detect_region("1.2.3.4")
    assert region == "US"


@pytest.mark.asyncio
async def test_detect_region_api_error_defaults_us():
    from app.services.region_service import detect_region

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get.side_effect = Exception("network error")
        mock_client_cls.return_value = mock_client

        region = await detect_region("1.2.3.4")
    assert region == "US"


def test_is_local_ip_localhost():
    from app.services.region_service import _is_local_ip

    assert _is_local_ip("127.0.0.1") is True
    assert _is_local_ip("localhost") is True
    assert _is_local_ip("0.0.0.0") is True  # noqa: S104


def test_is_local_ip_private():
    from app.services.region_service import _is_local_ip

    assert _is_local_ip("192.168.1.1") is True
    assert _is_local_ip("10.0.0.1") is True


def test_is_local_ip_public():
    from app.services.region_service import _is_local_ip

    assert _is_local_ip("8.8.8.8") is False
    assert _is_local_ip("1.1.1.1") is False


def test_is_local_ip_empty():
    from app.services.region_service import _is_local_ip

    assert _is_local_ip("") is True


@pytest.mark.asyncio
async def test_resolve_user_region_uses_existing():
    from app.services.region_service import resolve_user_region

    user = make_user(region="IN")
    region = await resolve_user_region(user, None, None)
    assert region == "IN"
    assert user.region == "IN"


@pytest.mark.asyncio
async def test_resolve_user_region_explicit_override():
    from app.services.region_service import resolve_user_region

    user = make_user(region="IN")
    region = await resolve_user_region(user, None, None, explicit_region="US")
    assert region == "US"


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


# ── pass_service.record_tool_discovery ───────────────────────────────────────


@pytest.mark.asyncio
async def test_record_tool_discovery():
    from app.services.pass_service import record_tool_discovery

    db = make_mock_db()
    await record_tool_discovery(uuid.uuid4(), "uppercase", db)
    db.execute.assert_awaited()
    db.commit.assert_awaited()
