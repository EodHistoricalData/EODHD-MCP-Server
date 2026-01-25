# app/redis_cache.py
"""
Redis cache implementation for EODHD MCP Server.
Provides distributed caching with Redis backend.
"""

import json
import logging
import hashlib
from typing import Any, Optional, Union
from functools import wraps

logger = logging.getLogger("eodhd-mcp.redis_cache")

# Try to import redis, but allow graceful degradation
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory cache fallback.")


class RedisCache:
    """
    Async Redis cache client with connection pooling.
    Falls back to in-memory cache if Redis is unavailable.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "eodhd:",
        default_ttl: int = 300,
        max_connections: int = 10
    ):
        """
        Initialize Redis cache.

        Args:
            url: Redis connection URL
            prefix: Key prefix for all cache entries
            default_ttl: Default TTL in seconds
            max_connections: Maximum connections in pool
        """
        self.url = url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self._client: Optional[Any] = None
        self._connected = False
        self._fallback_cache: dict[str, tuple[Any, float]] = {}

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connected successfully, False otherwise
        """
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using in-memory fallback")
            return False

        try:
            self._client = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using fallback cache.")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client and self._connected:
            await self._client.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}{key}"

    def _hash_key(self, key: str) -> str:
        """Create a hash for long keys."""
        if len(key) > 200:
            return hashlib.sha256(key.encode()).hexdigest()
        return key

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        full_key = self._make_key(self._hash_key(key))

        if self._connected and self._client:
            try:
                value = await self._client.get(full_key)
                if value:
                    logger.debug(f"Cache hit: {key[:50]}")
                    return json.loads(value)
                logger.debug(f"Cache miss: {key[:50]}")
                return None
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                return self._fallback_get(full_key)
        else:
            return self._fallback_get(full_key)

    def _fallback_get(self, key: str) -> Optional[Any]:
        """Get from fallback in-memory cache."""
        import time
        if key in self._fallback_cache:
            value, expires = self._fallback_cache[key]
            if time.time() < expires:
                return value
            else:
                del self._fallback_cache[key]
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (uses default if not specified)

        Returns:
            True if set successfully
        """
        full_key = self._make_key(self._hash_key(key))
        ttl = ttl or self.default_ttl

        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize cache value: {e}")
            return False

        if self._connected and self._client:
            try:
                await self._client.setex(full_key, ttl, serialized)
                logger.debug(f"Cache set: {key[:50]} (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                return self._fallback_set(full_key, value, ttl)
        else:
            return self._fallback_set(full_key, value, ttl)

    def _fallback_set(self, key: str, value: Any, ttl: int) -> bool:
        """Set in fallback in-memory cache."""
        import time
        self._fallback_cache[key] = (value, time.time() + ttl)
        return True

    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted successfully
        """
        full_key = self._make_key(self._hash_key(key))

        if self._connected and self._client:
            try:
                await self._client.delete(full_key)
                logger.debug(f"Cache delete: {key[:50]}")
                return True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                return False
        else:
            self._fallback_cache.pop(full_key, None)
            return True

    async def clear_prefix(self, prefix: str) -> int:
        """
        Clear all keys matching a prefix.

        Args:
            prefix: Key prefix to clear

        Returns:
            Number of keys deleted
        """
        full_prefix = self._make_key(prefix)

        if self._connected and self._client:
            try:
                keys = []
                async for key in self._client.scan_iter(f"{full_prefix}*"):
                    keys.append(key)
                if keys:
                    await self._client.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys with prefix: {prefix}")
                return len(keys)
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
                return 0
        else:
            # Clear from fallback cache
            count = 0
            keys_to_delete = [k for k in self._fallback_cache if k.startswith(full_prefix)]
            for k in keys_to_delete:
                del self._fallback_cache[k]
                count += 1
            return count

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        full_key = self._make_key(self._hash_key(key))

        if self._connected and self._client:
            try:
                return await self._client.exists(full_key) > 0
            except Exception as e:
                logger.warning(f"Redis exists error: {e}")
                return full_key in self._fallback_cache
        else:
            import time
            if full_key in self._fallback_cache:
                _, expires = self._fallback_cache[full_key]
                return time.time() < expires
            return False

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            "connected": self._connected,
            "fallback_size": len(self._fallback_cache)
        }

        if self._connected and self._client:
            try:
                info = await self._client.info("memory")
                stats["used_memory"] = info.get("used_memory_human", "unknown")
                stats["keys"] = await self._client.dbsize()
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")

        return stats

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


async def init_cache(url: str = "redis://localhost:6379") -> RedisCache:
    """
    Initialize and connect the global cache.

    Args:
        url: Redis connection URL

    Returns:
        Connected cache instance
    """
    global _cache
    _cache = RedisCache(url=url)
    await _cache.connect()
    return _cache


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[callable] = None
):
    """
    Decorator for caching function results.

    Args:
        key_prefix: Prefix for cache keys
        ttl: Cache TTL in seconds
        key_builder: Optional function to build cache key from args

    Usage:
        @cached("stock_price", ttl=60)
        async def get_stock_price(symbol: str) -> dict:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Default key from args
                key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
