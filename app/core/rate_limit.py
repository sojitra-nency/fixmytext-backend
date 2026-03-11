"""
Simple in-memory rate limiter for AI endpoints.

Limits requests per IP within a sliding time window.
Keeps Groq API usage under the free-tier limit (30 req/min).
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException


class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 25, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request):
        """Raise 429 if the client has exceeded the rate limit."""
        key = request.client.host if request.client else "unknown"
        now = time.time()
        # Purge expired entries
        self._hits[key] = [t for t in self._hits[key] if now - t < self.window]
        if not self._hits[key]:
            del self._hits[key]
            return
        if len(self._hits[key]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again shortly.",
            )
        self._hits[key].append(now)


ai_limiter = InMemoryRateLimiter(max_requests=25, window_seconds=60)
