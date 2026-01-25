# tests/test_cache.py
"""Tests for app/cache.py module."""

import time
import pytest
from app.cache import (
    TTLCache,
    cached,
    get_cache,
    clear_cache,
    cache_stats,
    TTL_REALTIME,
    TTL_EOD
)


class TestTTLCache:
    """Tests for TTLCache class."""

    def test_set_and_get(self):
        cache = TTLCache(maxsize=10, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = TTLCache(maxsize=10, default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = TTLCache(maxsize=10, default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_maxsize_eviction(self):
        cache = TTLCache(maxsize=2, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_delete(self):
        cache = TTLCache(maxsize=10, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False

    def test_clear(self):
        cache = TTLCache(maxsize=10, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        cache = TTLCache(maxsize=10, default_ttl=60)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cleanup(self):
        cache = TTLCache(maxsize=10, default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=60)
        time.sleep(1.1)
        removed = cache.cleanup()
        assert removed == 1
        assert cache.get("key2") == "value2"


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_sync_function_cached(self):
        call_count = 0

        @cached(ttl=60)
        def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        clear_cache()
        result1 = my_func(5)
        result2 = my_func(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Second call should use cache

    @pytest.mark.asyncio
    async def test_async_function_cached(self):
        call_count = 0

        @cached(ttl=60)
        async def my_async_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        clear_cache()
        result1 = await my_async_func(5)
        result2 = await my_async_func(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1


class TestGlobalCache:
    """Tests for global cache functions."""

    def test_get_cache_returns_instance(self):
        cache = get_cache()
        assert isinstance(cache, TTLCache)

    def test_cache_stats(self):
        clear_cache()
        stats = cache_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats

    def test_ttl_constants(self):
        assert TTL_REALTIME == 10
        assert TTL_EOD == 3600
