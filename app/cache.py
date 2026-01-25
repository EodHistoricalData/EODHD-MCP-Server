# app/cache.py
"""
In-memory LRU cache with TTL support for EODHD MCP Server.
"""

import time
import hashlib
import json
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional
import threading


class TTLCache:
    """Thread-safe LRU cache with TTL (time-to-live) support."""

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of items in cache
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl

        with self._lock:
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = (value, expiry)

            # Evict oldest if over capacity
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed items."""
        now = time.time()
        removed = 0
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if now > exp]
            for key in expired:
                del self._cache[key]
                removed += 1
        return removed

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0
            }


# Global cache instance
_cache = TTLCache(maxsize=1000, default_ttl=300)


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds (None = use default)
        key_prefix: Optional prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = key_prefix + _cache._make_key(func.__name__, *args, **kwargs)
            result = _cache.get(cache_key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            if result is not None:
                _cache.set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = key_prefix + _cache._make_key(func.__name__, *args, **kwargs)
            result = _cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            if result is not None:
                _cache.set(cache_key, result, ttl)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_cache() -> TTLCache:
    """Get the global cache instance."""
    return _cache


def clear_cache() -> None:
    """Clear the global cache."""
    _cache.clear()


def cache_stats() -> dict:
    """Get cache statistics."""
    return _cache.stats


# TTL presets for different data types
TTL_REALTIME = 10       # Real-time data: 10 seconds
TTL_INTRADAY = 60       # Intraday data: 1 minute
TTL_EOD = 3600          # EOD data: 1 hour
TTL_FUNDAMENTALS = 86400  # Fundamentals: 24 hours
TTL_STATIC = 86400 * 7  # Static data (exchanges, etc.): 7 days
