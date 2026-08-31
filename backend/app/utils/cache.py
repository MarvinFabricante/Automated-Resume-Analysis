import json
import functools
import time
import pickle
import redis.asyncio as redis
from typing import Any, Optional
from fastapi.encoders import jsonable_encoder

# Initialize Redis client
redis_client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=False)

async def get_cache(key: str) -> Optional[Any]:
    """Get data from Redis cache."""
    item = await redis_client.get(key)
    if item:
        try:
            return pickle.loads(item)
        except Exception:
            try:
                return json.loads(item)
            except Exception:
                return item
    return None

async def set_cache(key: str, value: Any, ttl: int = 3600):
    """Set data in Redis cache with an optional TTL (default 1 hour)."""
    try:
        serializable_value = pickle.dumps(value)
    except Exception:
        serializable_value = json.dumps(jsonable_encoder(value)).encode('utf-8')
    
    if ttl:
        await redis_client.setex(key, ttl, serializable_value)
    else:
        await redis_client.set(key, serializable_value)

async def delete_cache(key: str):
    """Delete a key from Redis cache."""
    await redis_client.delete(key)

async def clear_cache_pattern(pattern: str):
    """Clear all keys matching a pattern."""
    keys_to_delete = []
    async for key in redis_client.scan_iter(match=f"*{pattern}*"):
        keys_to_delete.append(key)
    if keys_to_delete:
        await redis_client.delete(*keys_to_delete)

def cache_response(key_prefix: str, ttl: int = 3600):
    """
    Decorator to cache the response of a FastAPI endpoint.
    Usage: @cache_response("jobs_list", ttl=600)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key based on args and kwargs (ignoring unhashable like Request/AsyncSession)
            serializable_args = []
            for arg in args:
                if isinstance(arg, (str, int, float, bool, type(None))):
                    serializable_args.append(arg)
            
            serializable_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    serializable_kwargs[k] = v
            
            cache_key_parts = [key_prefix, json.dumps(serializable_args, sort_keys=True), json.dumps(serializable_kwargs, sort_keys=True)]
            cache_key = ":".join(cache_key_parts)
            
            cached_data = await get_cache(cache_key)
            if cached_data:
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
            serializable_args = []
            for arg in args:
                # skip AsyncSession
                if type(arg).__name__ == "AsyncSession":
                    continue
                if isinstance(arg, (str, int, float, bool, type(None))):
                    serializable_args.append(arg)
            
            serializable_kwargs = {}
            for k, v in kwargs.items():
                if type(v).__name__ == "AsyncSession":
                    continue
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    serializable_kwargs[k] = v
            
            cache_key_parts = ["db", key_prefix, func.__name__, json.dumps(serializable_args, sort_keys=True), json.dumps(serializable_kwargs, sort_keys=True)]
            cache_key = ":".join(cache_key_parts)
            
            cached_data = await get_cache(cache_key)
            if cached_data:
                # Because we used pickle, the SQLAlchemy objects will be unpickled.
                # Note: They are detached from the session. This is fine for read-only if we don't lazy load.
                # Some objects like Row might be unpickled correctly.
                return cached_data
            
            result = await func(*args, **kwargs)
            
            if result is not None:
                await set_cache(cache_key, result, ttl)
                
            return result
        return wrapper
    return decorator
