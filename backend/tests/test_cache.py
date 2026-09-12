"""Cache-layer tests.

No Redis runs in the test suite, and that's the point: the whole contract of
services/cache.py is that callers can use it unconditionally and get a
silent no-op when Redis isn't there. get_redis is patched to None here so
that path is exercised deterministically rather than depending on whether
the developer happens to have a local Redis up.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache import build_cache_key, cache_get, cache_set


def test_build_cache_key_is_deterministic():
    first = build_cache_key("match", "v1", "offer-123", "description text")
    second = build_cache_key("match", "v1", "offer-123", "description text")

    assert first == second
    assert first.startswith("jobless:")
    assert len(first) == len("jobless:") + 64  # sha256 hexdigest


@pytest.mark.parametrize(
    "parts",
    [
        ("match", "v2", "offer-123", "description text"),  # prompt version bumped
        ("match", "v1", "offer-999", "description text"),  # different offer
        ("match", "v1", "offer-123", "edited description"),  # content changed
        ("score", "v1", "offer-123", "description text"),  # different namespace
        ("match", "v1", "offer-123"),  # part dropped
    ],
)
def test_build_cache_key_changes_when_any_part_changes(parts):
    baseline = build_cache_key("match", "v1", "offer-123", "description text")
    assert build_cache_key(*parts) != baseline


def test_build_cache_key_is_not_confusable_across_part_boundaries():
    """Joining on "|" must not let two different part lists collide."""
    assert build_cache_key("a", "b") != build_cache_key("ab")


@pytest.mark.asyncio
async def test_cache_get_returns_none_without_redis():
    with patch("app.services.cache.get_redis", return_value=None):
        assert await cache_get("jobless:anything") is None


@pytest.mark.asyncio
async def test_cache_set_is_a_noop_without_redis():
    with patch("app.services.cache.get_redis", return_value=None):
        # must not raise
        assert await cache_set("jobless:anything", "value", 60) is None


@pytest.mark.asyncio
async def test_cache_get_swallows_redis_errors():
    """A Redis that's up but failing must degrade to a miss, not propagate."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    client = MagicMock()
    client.get = AsyncMock(side_effect=RedisConnectionError("connection refused"))

    with patch("app.services.cache.get_redis", return_value=client):
        assert await cache_get("jobless:anything") is None


@pytest.mark.asyncio
async def test_cache_set_swallows_redis_errors():
    from redis.exceptions import ConnectionError as RedisConnectionError

    client = MagicMock()
    client.set = AsyncMock(side_effect=RedisConnectionError("connection refused"))

    with patch("app.services.cache.get_redis", return_value=client):
        assert await cache_set("jobless:anything", "value", 60) is None


@pytest.mark.asyncio
async def test_cache_round_trip_uses_ttl():
    """When Redis *is* available, the value and TTL are passed through."""
    client = MagicMock()
    client.get = AsyncMock(return_value='{"score": 82}')
    client.set = AsyncMock(return_value=True)

    with patch("app.services.cache.get_redis", return_value=client):
        assert await cache_get("jobless:k") == '{"score": 82}'
        await cache_set("jobless:k", '{"score": 82}', 1234)

    client.set.assert_awaited_once_with("jobless:k", '{"score": 82}', ex=1234)
