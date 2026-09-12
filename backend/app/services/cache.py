"""Thin Redis wrapper — callers never touch redis.asyncio directly.

Caching here is strictly an optimization, never a correctness requirement:
if Redis is unreachable (not started, wrong URL, test suite), every function
in this module degrades to a no-op and the app keeps working uncached. That
is why `cache_get`/`cache_set` swallow connection errors instead of raising —
call sites are meant to call them unconditionally, with no availability
check of their own.

Keys are content-addressed (see `build_cache_key`): the inputs that actually
determine a result are hashed into the key, so an edited profile, a changed
posting, or a bumped `cache_prompt_version` lands on a different key instead
of serving a stale hit. There is deliberately no explicit invalidation path.
"""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Flipped the first time a call fails to reach Redis, so the warning is
# logged once rather than on every cache lookup for the rest of the process.
_unavailable = False


@lru_cache
def get_redis() -> aioredis.Redis | None:
    """Cached client, or None if one can't even be constructed.

    Constructing a redis.asyncio client doesn't connect — the connection is
    made lazily on first command — so an unreachable server surfaces in
    `cache_get`/`cache_set`, not here.
    """
    global _unavailable
    try:
        return aioredis.from_url(settings.redis_url, decode_responses=True)
    except (RedisError, ValueError, OSError) as exc:
        if not _unavailable:
            logger.warning("Redis unavailable (%s) — running without cache", exc)
            _unavailable = True
        return None


def _mark_unavailable(exc: Exception) -> None:
    global _unavailable
    if not _unavailable:
        logger.warning("Redis unavailable (%s) — running without cache", exc)
        _unavailable = True


async def cache_get(key: str) -> str | None:
    """Read a cached value. Returns None on a miss *or* any Redis problem."""
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except (RedisError, OSError) as exc:
        _mark_unavailable(exc)
        return None


async def cache_set(key: str, value: str, ttl_seconds: int) -> None:
    """Write a value with a TTL. Silently does nothing if Redis is down."""
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(key, value, ex=ttl_seconds)
    except (RedisError, OSError) as exc:
        _mark_unavailable(exc)


def build_cache_key(*parts: str) -> str:
    """Content-addressed key: SHA-256 over the joined parts.

    Hashing keeps keys bounded regardless of how much content goes in (a full
    job description and profile summary both feed the match key), and makes
    any change to any part produce a different key.
    """
    joined = "|".join(parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return f"jobless:{digest}"
