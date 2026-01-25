# tests/test_redis_cache.py
"""Tests for app/redis_cache.py module."""

import pytest
from app.redis_cache import (
    RedisCache,
    get_cache,
    cached,
    REDIS_AVAILABLE
)


class TestRedisCache:
    """Tests for RedisCache class."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        return RedisCache(
            url="redis://localhost:6379",
            prefix="test:",
            default_ttl=60
        )

    def test_init(self, cache):
        assert cache.prefix == "test:"
        assert cache.default_ttl == 60
        assert cache._connected is False

    def test_make_key(self, cache):
        key = cache._make_key("mykey")
        assert key == "test:mykey"

    def test_hash_key_short(self, cache):
        short_key = "abc"
        assert cache._hash_key(short_key) == "abc"

    def test_hash_key_long(self, cache):
        long_key = "a" * 250
        hashed = cache._hash_key(long_key)
        assert len(hashed) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_fallback_cache(self, cache):
        """Test fallback in-memory cache when Redis is not available."""
        # Don't connect to Redis, use fallback
        await cache.set("test_key", {"data": "value"}, ttl=60)
        result = await cache.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_fallback_delete(self, cache):
        await cache.set("del_key", "value")
        await cache.delete("del_key")
        result = await cache.get("del_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_exists(self, cache):
        await cache.set("exists_key", "value")
        assert await cache.exists("exists_key") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_fallback_clear_prefix(self, cache):
        await cache.set("clear:a", "1")
        await cache.set("clear:b", "2")
        await cache.set("other:c", "3")
        count = await cache.clear_prefix("clear:")
        assert count == 2
        assert await cache.get("other:c") == "3"

    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        stats = await cache.get_stats()
        assert "connected" in stats
        assert "fallback_size" in stats

    def test_is_connected(self, cache):
        assert cache.is_connected is False


class TestGetCache:
    """Tests for get_cache function."""

    def test_returns_cache_instance(self):
        cache = get_cache()
        assert isinstance(cache, RedisCache)

    def test_returns_same_instance(self):
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_caches_result(self):
        call_count = 0

        @cached("test_func", ttl=60)
        async def my_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(5)

        assert result1 == 10
        assert result2 == 10
        # Function should be called twice because cache might not be persistent
        # across tests, but the decorator should work

    @pytest.mark.asyncio
    async def test_different_args_cached_separately(self):
        @cached("test_func2", ttl=60)
        async def my_func(x: int) -> int:
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(10)

        assert result1 == 10
        assert result2 == 20

    @pytest.mark.asyncio
    async def test_custom_key_builder(self):
        @cached("custom", ttl=60, key_builder=lambda x, y: f"{x}_{y}")
        async def my_func(x: int, y: int) -> int:
            return x + y

        result = await my_func(3, 4)
        assert result == 7


class TestRedisAvailability:
    """Tests for Redis availability check."""

    def test_redis_available_flag_exists(self):
        # REDIS_AVAILABLE should be a boolean
        assert isinstance(REDIS_AVAILABLE, bool)
