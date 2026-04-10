"""Tests for app/core/rate_limit.py — in-memory sliding window rate limiter."""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter


def _make_request(host: str = "127.0.0.1") -> MagicMock:
    """Build a minimal Request-like mock."""
    request = MagicMock()
    request.client.host = host
    return request


class TestInMemoryRateLimiter:
    """Tests for the sliding-window in-memory rate limiter."""

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        """Requests within the limit are allowed without raising."""
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        request = _make_request()
        for _ in range(5):
            await limiter.check(request)

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Sixth request exceeds limit of 5 and raises HTTP 429."""
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        request = _make_request()
        for _ in range(5):
            await limiter.check(request)
        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_uses_user_key_when_provided(self):
        """When user_id is passed, uses user-based key instead of IP."""
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        request = _make_request("10.0.0.1")
        # Fill the limit for user-123
        await limiter.check(request, user_id="user-123")
        await limiter.check(request, user_id="user-123")
        # user-123 is now blocked
        with pytest.raises(HTTPException):
            await limiter.check(request, user_id="user-123")
        # But user-456 on the same IP is allowed
        await limiter.check(request, user_id="user-456")

    @pytest.mark.asyncio
    async def test_different_ips_tracked_separately(self):
        """Different IP addresses have independent rate limits."""
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        req1 = _make_request("10.0.0.1")
        req2 = _make_request("10.0.0.2")
        await limiter.check(req1)
        await limiter.check(req2)
        # Each IP used its 1 allowed request
        with pytest.raises(HTTPException):
            await limiter.check(req1)
        with pytest.raises(HTTPException):
            await limiter.check(req2)

    @pytest.mark.asyncio
    async def test_expired_entries_are_purged(self):
        """Entries outside the window are purged, freeing up the limit."""
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=1)
        request = _make_request()
        await limiter.check(request)
        await limiter.check(request)
        # Now at limit; inject old timestamps
        key = request.client.host
        limiter._hits[key] = [time.time() - 10, time.time() - 10]
        # Should succeed because old entries get purged
        await limiter.check(request)

    @pytest.mark.asyncio
    async def test_unknown_client_host_fallback(self):
        """Request with no client falls back to 'unknown' key."""
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        request = MagicMock()
        request.client = None
        await limiter.check(request)
        with pytest.raises(HTTPException):
            await limiter.check(request)

    @pytest.mark.asyncio
    async def test_default_settings_from_config(self):
        """Limiter without explicit params uses settings defaults."""
        limiter = InMemoryRateLimiter()
        from app.core.config import settings

        assert limiter.max_requests == settings.RATE_LIMIT_MAX_REQUESTS
        assert limiter.window_seconds == settings.RATE_LIMIT_WINDOW_SECONDS
