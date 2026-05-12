from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from core.exceptions import RateLimitExceeded


def check_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
    block_seconds: int | None = None,
    namespace: str = "rl",
) -> None:
    now = timezone.now()
    cache_key = f"{namespace}:{key}"
    data = cache.get(cache_key)

    if data is None:
        cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        return

    window_start = timezone.datetime.fromtimestamp(data["window_start"], tz=now.tzinfo)
    if (now - window_start).total_seconds() > window_seconds:
        cache.set(cache_key, {"count": 1, "window_start": now.timestamp()}, window_seconds)
        return

    data["count"] += 1
    if data["count"] > max_attempts:
        if block_seconds:
            cache.set(cache_key + ":blocked", True, block_seconds)
        raise RateLimitExceeded("Too many attempts. Try again later.")

    cache.set(cache_key, data, window_seconds)


def is_blocked(key: str, namespace: str = "rl") -> bool:
    return cache.get(f"{namespace}:{key}:blocked") is not None
