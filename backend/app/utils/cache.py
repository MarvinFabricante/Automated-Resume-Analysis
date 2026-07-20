import json
import functools
import time
from typing import Any, Optional
from fastapi.encoders import jsonable_encoder

_cache = {}

async def get_cache(key: str) -> Optional[Any]:
    """Get data from in-memory cache."""
    item = _cache.get(key)
    if item:
        if item.get("expires_at") and time.time() > item["expires_at"]:
            del _cache[key]
            return None
        return json.loads(item["value"])
    return None

async def set_cache(key: str, value: Any, ttl: int = 3600):
    """Set data in in-memory cache with an optional TTL (default 1 hour)."""
    serializable_value = jsonable_encoder(value)
    _cache[key] = {
        "value": json.dumps(serializable_value),
        "expires_at": time.time() + ttl if ttl else None
    }

async def delete_cache(key: str):
    """Delete a key from in-memory cache."""
    if key in _cache:
        del _cache[key]

async def clear_cache_pattern(pattern: str):
    """Clear all keys matching a pattern. (Simple wildcard matching)"""
    keys_to_delete = []
    prefix = pattern.replace("*", "")
    for k in _cache.keys():
        if prefix in k:
            keys_to_delete.append(k)
    for k in keys_to_delete:
        del _cache[k]

def cache_response(key_prefix: str, ttl: int = 3600):
    """
    Decorator to cache the response of a FastAPI endpoint.
    Usage: @cache_response("jobs_list", ttl=600)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            serializable_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    serializable_kwargs[k] = v
            
            cache_key = f"{key_prefix}:{json.dumps(serializable_kwargs, sort_keys=True)}"
            
            cached_data = await get_cache(cache_key)
            if cached_data:
                return cached_data
            
            result = await func(*args, **kwargs)
            
            if result:
                await set_cache(cache_key, result, ttl)
                
            return result
        return wrapper
    return decorator
