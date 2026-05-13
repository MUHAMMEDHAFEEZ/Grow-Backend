"""
core/rate_limit.py — Shared rate-limiting utilities with Redis failure resilience.

Every cache call is wrapped in a try/except that catches connection errors.
If the cache backend (Redis) is unreachable, rate limiting degrades gracefully:
- `check_rate_limit` logs a warning and returns without blocking the request.
- `is_blocked` returns ``False`` so authentication/login can proceed.

This ensures the login endpoint (and every other endpoint) never crashes
when Redis is down — only rate-limit protection is temporarily weakened.
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

from core.exceptions import RateLimitExceeded

logger = logging.getLogger(__name__)


def check_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
    block_seconds: int | None = None,
    namespace: str = "rl",
) -> None:
    now = timezone.now()
    cache_key = f"{namespace}:{key}"
    try:
        data = cache.get(cache_key)
    except Exception:
        logger.warning("Rate-limit check skipped — cache unavailable for key '%s'", cache_key)
        return

    if data is None:
        try:
            cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        except Exception:
            logger.exception("Rate-limit cache set failed for key '%s'", cache_key)
        return

    window_start = timezone.datetime.fromtimestamp(data["window_start"], tz=now.tzinfo)
    if (now - window_start).total_seconds() > window_seconds:
        try:
            cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        except Exception:
            logger.exception("Rate-limit cache set failed for key '%s'", cache_key)
        return

    data["count"] += 1
    if data["count"] > max_attempts:
        if block_seconds:
            try:
                cache.set(cache_key + ":blocked", True, block_seconds)
            except Exception:
                logger.exception("Rate-limit block set failed for key '%s'", cache_key)
        raise RateLimitExceeded("Too many attempts. Try again later.")

    try:
        cache.set(cache_key, data, window_seconds)
    except Exception:
        logger.exception("Rate-limit cache set failed for key '%s'", cache_key)


def is_blocked(key: str, namespace: str = "rl") -> bool:
    try:
        return cache.get(f"{namespace}:{key}:blocked") is not None
    except Exception:
        logger.warning("Rate-limit block check skipped — cache unavailable for key '%s'", key)
        return False
