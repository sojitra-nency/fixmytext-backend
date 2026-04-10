"""
Rate limiting middleware for AI endpoints.

Uses in-memory sliding window. For distributed deployments,
replace with Redis-backed implementation.
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Sliding-window rate limiter backed by an in-memory dict.

    Keys are either ``user:<user_id>`` (for authenticated requests) or the
    client IP address.  Expired timestamps are purged on every check.
    """

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def check(self, request: Request, user_id: str | None = None) -> None:
        """Check rate limit. Raises HTTPException(429) if exceeded."""
        # Use user-based key when available; fall back to client IP
        if user_id:
            key = f"user:{user_id}"
        else:
            key = request.client.host if request.client else "unknown"

        now = time.time()
        # Purge expired entries outside the current window
        self._hits[key] = [t for t in self._hits[key] if now - t < self.window_seconds]

        # Remove the key entirely if no timestamps remain to prevent memory leak
        if not self._hits[key]:
            del self._hits[key]

        if self._hits.get(key) and len(self._hits[key]) >= self.max_requests:
            logger.warning(
                "RATE LIMIT hit for %s (%d/%d in %ds)",
                key,
                len(self._hits[key]),
                self.max_requests,
                self.window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again shortly.",
            )
        self._hits[key].append(now)


# Default limiter instance used by AI endpoints
ai_limiter = InMemoryRateLimiter()
