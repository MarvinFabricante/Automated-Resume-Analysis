import os
import json
import functools
import pickle
import logging
from typing import Any, Optional, List
from fastapi.encoders import jsonable_encoder

from app.utils.redis_client import (
    get_async_redis,
    get_sync_redis,
    is_redis_available,
    REDIS_URL,
    redis_tx_manager,
    redis_transaction_context,
)

logger = logging.getLogger(__name__)

# Re-export redis_client for backward compatibility
redis_client = get_async_redis()


def is_in_test_environment() -> bool:
    """Check if code is running inside pytest."""
    return "PYTEST_CURRENT_TEST" in os.environ


async def get_cache(key: str) -> Optional[Any]:
    """Get data from Redis cache with error handling and fallback."""
    if is_in_test_environment() and os.getenv("TEST_BYPASS_CACHE", "true").lower() == "true":
        # In pytest, SQLite in-memory sessions rollback per test.
        # Bypass returning rolled-back database entities to prevent cross-test contamination.
        return None

    try:
        client = get_async_redis()
        item = await client.get(key)
        if item:
            try:
                return pickle.loads(item)
            except Exception:
                try:
                    return json.loads(item.decode("utf-8"))
                except Exception:
                    return item.decode("utf-8") if isinstance(item, bytes) else item
    except Exception as e:
        logger.debug(f"[Redis Cache] get_cache error for key '{key}': {e}")
    return None


async def set_cache(key: str, value: Any, ttl: int = 3600):
    """Set data in Redis cache with an optional TTL (default 1 hour)."""
    try:
        client = get_async_redis()
        try:
            serializable_value = pickle.dumps(value)
        except Exception:
            try:
                serializable_value = json.dumps(jsonable_encoder(value)).encode("utf-8")
            except Exception:
                serializable_value = str(value).encode("utf-8")

        if ttl:
            await client.setex(key, ttl, serializable_value)
        else:
            await client.set(key, serializable_value)
    except Exception as e:
        logger.debug(f"[Redis Cache] set_cache error for key '{key}': {e}")


async def delete_cache(key: str):
    """Delete a key or pattern from Redis cache."""
    try:
        client = get_async_redis()
        if "*" in key:
            await clear_cache_pattern(key.replace("*", ""))
        else:
            await client.delete(key)
    except Exception as e:
        logger.debug(f"[Redis Cache] delete_cache error for key '{key}': {e}")


async def clear_cache_pattern(pattern: str):
    """Clear all keys matching a pattern."""
    try:
        client = get_async_redis()
        clean_pat = pattern.strip("*")
        keys_to_delete = []
        async for key in client.scan_iter(match=f"*{clean_pat}*"):
            keys_to_delete.append(key)
        if keys_to_delete:
            await client.delete(*keys_to_delete)
            logger.debug(f"[Redis Cache] Cleared {len(keys_to_delete)} keys matching pattern '*{clean_pat}*'")
    except Exception as e:
        logger.debug(f"[Redis Cache] clear_cache_pattern error for pattern '{pattern}': {e}")


# ─── Entity Cache Helpers ─────────────────────────────────────────────

async def cache_entity(entity_type: str, entity_id: Any, data: Any, ttl: int = 3600):
    """Cache an individual entity by type and ID."""
    key = f"entity:{entity_type}:{entity_id}"
    await set_cache(key, data, ttl)


async def get_cached_entity(entity_type: str, entity_id: Any) -> Optional[Any]:
    """Retrieve an individual entity by type and ID."""
    key = f"entity:{entity_type}:{entity_id}"
    return await get_cache(key)


async def delete_cached_entity(entity_type: str, entity_id: Any):
    """Delete an individual entity from cache."""
    key = f"entity:{entity_type}:{entity_id}"
    await delete_cache(key)


async def invalidate_entity_type(entity_type: str):
    """Invalidate all cached entities of a given type."""
    await clear_cache_pattern(f"entity:{entity_type}:")


# ─── Decorators ────────────────────────────────────────────────────────

def cache_response(key_prefix: str, ttl: int = 3600):
    """
    Decorator to cache the response of a FastAPI endpoint.
    Usage: @cache_response("jobs_list", ttl=600)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if is_in_test_environment() and os.getenv("TEST_BYPASS_CACHE", "true").lower() == "true":
                return await func(*args, **kwargs)

            # Build cache key based on args and kwargs
            serializable_args = []
            for arg in args:
                if isinstance(arg, (str, int, float, bool, type(None))):
                    serializable_args.append(arg)

            serializable_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    serializable_kwargs[k] = v

            cache_key_parts = [
                key_prefix,
                json.dumps(serializable_args, sort_keys=True),
                json.dumps(serializable_kwargs, sort_keys=True),
            ]
            cache_key = ":".join(cache_key_parts)

            cached_data = await get_cache(cache_key)
            if cached_data is not None:
                return cached_data

            result = await func(*args, **kwargs)

            if result is not None:
                await set_cache(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


def db_cache(key_prefix: str, ttl: int = 600):
    """
    Decorator to cache database repository calls.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if is_in_test_environment() and os.getenv("TEST_BYPASS_CACHE", "true").lower() == "true":
                return await func(*args, **kwargs)

            serializable_args = []
            for arg in args:
                if type(arg).__name__ in ("AsyncSession", "Session"):
                    continue
                if isinstance(arg, (str, int, float, bool, type(None))):
                    serializable_args.append(arg)

            serializable_kwargs = {}
            for k, v in kwargs.items():
                if type(v).__name__ in ("AsyncSession", "Session"):
                    continue
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    serializable_kwargs[k] = v

            cache_key_parts = [
                "db",
                key_prefix,
                func.__name__,
                json.dumps(serializable_args, sort_keys=True),
                json.dumps(serializable_kwargs, sort_keys=True),
            ]
            cache_key = ":".join(cache_key_parts)

            cached_data = await get_cache(cache_key)
            if cached_data is not None:
                return cached_data

            result = await func(*args, **kwargs)

            if result is not None:
                await set_cache(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
