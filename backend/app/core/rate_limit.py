"""In-memory rate limiting (docs/BLUEPRINT.md §17).

A sliding window keyed by (client IP, session_id), held in process memory.
That's adequate for this project's deployment plan (§21: a single backend
instance) - a multi-instance deployment would need a shared store like
Redis instead of this, which is a deployment change to make later, not
something to build speculatively now.
"""

import time
from collections import defaultdict

from fastapi import Request

from app.config import get_settings

WINDOW_SECONDS = 60


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit_per_window: int) -> None:
        now = time.monotonic()
        window_start = now - WINDOW_SECONDS
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.pop(0)
        if len(hits) >= limit_per_window:
            raise RateLimitExceeded(
                "Too many requests - please slow down and try again shortly."
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _limiter


def enforce_rate_limit(request: Request, session_id: str) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{session_id}"
    _limiter.check(key, settings.rate_limit_per_minute)


def enforce_auth_rate_limit(request: Request) -> None:
    """Tighter, IP-only limit for register/login/forgot/reset - these have
    no session_id to key on, and are exactly the endpoints worth throttling
    against credential-stuffing/brute-force attempts."""
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"auth:{client_ip}"
    _limiter.check(key, settings.auth_rate_limit_per_minute)
