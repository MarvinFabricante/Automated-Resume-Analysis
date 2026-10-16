import os
import json
import pickle
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.utils.cache import (
    is_in_test_environment,
    get_cache,
    set_cache,
    delete_cache,
    clear_cache_pattern,
    cache_entity,
    get_cached_entity,
    delete_cached_entity,
    invalidate_entity_type,
    cache_response,
    db_cache,
)


def test_is_in_test_environment():
    assert is_in_test_environment() is True


@pytest.mark.asyncio
async def test_get_cache_bypassed_in_test_env():
    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "true"}):
        res = await get_cache("test:bypassed_key")
        assert res is None


@pytest.mark.asyncio
async def test_get_cache_pickle_deserialization():
    mock_redis = AsyncMock()
    data = {"user": "Alice", "score": 100}
    mock_redis.get.return_value = pickle.dumps(data)

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
            res = await get_cache("test:pickle_key")
            assert res == data


@pytest.mark.asyncio
async def test_get_cache_json_deserialization():
    mock_redis = AsyncMock()
    data = {"status": "ok", "items": [1, 2, 3]}
    mock_redis.get.return_value = json.dumps(data).encode("utf-8")

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
            res = await get_cache("test:json_key")
            assert res == data


@pytest.mark.asyncio
async def test_get_cache_raw_string_and_bytes():
    mock_redis = AsyncMock()
    # Malformed json / not pickle
    mock_redis.get.return_value = b"Plain unformatted string"

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
            res = await get_cache("test:raw_key")
            assert res == "Plain unformatted string"


@pytest.mark.asyncio
async def test_get_cache_key_not_found():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
            res = await get_cache("test:non_existent")
            assert res is None


@pytest.mark.asyncio
async def test_get_cache_redis_exception():
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection timeout")

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
            res = await get_cache("test:error_key")
            assert res is None


@pytest.mark.asyncio
async def test_set_cache_with_ttl():
    mock_redis = AsyncMock()
    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await set_cache("my_key", {"data": 123}, ttl=600)
        mock_redis.setex.assert_awaited_once()
        args = mock_redis.setex.await_args[0]
        assert args[0] == "my_key"
        assert args[1] == 600
        assert pickle.loads(args[2]) == {"data": 123}


@pytest.mark.asyncio
async def test_set_cache_without_ttl():
    mock_redis = AsyncMock()
    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await set_cache("my_key", "simple_val", ttl=0)
        mock_redis.set.assert_awaited_once()
        args = mock_redis.set.await_args[0]
        assert args[0] == "my_key"
        assert pickle.loads(args[1]) == "simple_val"


@pytest.mark.asyncio
async def test_set_cache_exception_handling():
    mock_redis = AsyncMock()
    mock_redis.setex.side_effect = Exception("Write failed")
    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        # Should not raise exception
        await set_cache("error_key", "val", ttl=300)


@pytest.mark.asyncio
async def test_delete_cache_exact_key():
    mock_redis = AsyncMock()
    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await delete_cache("exact_key")
        mock_redis.delete.assert_awaited_once_with("exact_key")


@pytest.mark.asyncio
async def test_delete_cache_pattern_delegation():
    with patch("app.utils.cache.clear_cache_pattern", new_callable=AsyncMock) as mock_clear:
        await delete_cache("user:*")
        mock_clear.assert_awaited_once_with("user:")


@pytest.mark.asyncio
async def test_delete_cache_exception_handling():
    mock_redis = AsyncMock()
    mock_redis.delete.side_effect = Exception("Delete failed")
    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await delete_cache("key")


@pytest.mark.asyncio
async def test_clear_cache_pattern():
    mock_redis = AsyncMock()

    async def mock_scan(match):
        for k in ["entity:job:1", "entity:job:2"]:
            yield k

    mock_redis.scan_iter = mock_scan

    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await clear_cache_pattern("job")
        mock_redis.delete.assert_awaited_once_with("entity:job:1", "entity:job:2")


@pytest.mark.asyncio
async def test_clear_cache_pattern_empty():
    mock_redis = AsyncMock()

    async def mock_scan(match):
        if False:
            yield None

    mock_redis.scan_iter = mock_scan

    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await clear_cache_pattern("nonexistent")
        mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_clear_cache_pattern_exception():
    mock_redis = AsyncMock()

    async def mock_scan_err(match):
        raise Exception("Scan error")
        yield None

    mock_redis.scan_iter = mock_scan_err

    with patch("app.utils.cache.get_async_redis", return_value=mock_redis):
        await clear_cache_pattern("error")



@pytest.mark.asyncio
async def test_entity_cache_helpers():
    with patch("app.utils.cache.set_cache", new_callable=AsyncMock) as mock_set, \
         patch("app.utils.cache.get_cache", new_callable=AsyncMock) as mock_get, \
         patch("app.utils.cache.delete_cache", new_callable=AsyncMock) as mock_del, \
         patch("app.utils.cache.clear_cache_pattern", new_callable=AsyncMock) as mock_clear:

        mock_get.return_value = {"id": 42, "name": "Resume"}

        # cache_entity
        await cache_entity("resume", 42, {"id": 42, "name": "Resume"}, ttl=120)
        mock_set.assert_awaited_once_with("entity:resume:42", {"id": 42, "name": "Resume"}, 120)

        # get_cached_entity
        res = await get_cached_entity("resume", 42)
        assert res == {"id": 42, "name": "Resume"}
        mock_get.assert_awaited_once_with("entity:resume:42")

        # delete_cached_entity
        await delete_cached_entity("resume", 42)
        mock_del.assert_awaited_once_with("entity:resume:42")

        # invalidate_entity_type
        await invalidate_entity_type("resume")
        mock_clear.assert_awaited_once_with("entity:resume:")


@pytest.mark.asyncio
async def test_cache_response_decorator_bypassed():
    call_count = 0

    @cache_response("test_prefix", ttl=60)
    async def sample_endpoint(param: str):
        nonlocal call_count
        call_count += 1
        return {"param": param, "count": call_count}

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "true"}):
        res1 = await sample_endpoint("hello")
        res2 = await sample_endpoint("hello")
        assert res1["count"] == 1
        assert res2["count"] == 2


@pytest.mark.asyncio
async def test_cache_response_decorator_active():
    call_count = 0

    @cache_response("test_active", ttl=60)
    async def sample_endpoint(item_id: int):
        nonlocal call_count
        call_count += 1
        return {"item_id": item_id, "count": call_count}

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_cache", new_callable=AsyncMock) as mock_get, \
             patch("app.utils.cache.set_cache", new_callable=AsyncMock) as mock_set:

            # First invocation: cache miss
            mock_get.return_value = None
            res1 = await sample_endpoint(10)
            assert res1["count"] == 1
            mock_set.assert_awaited_once()

            # Second invocation: cache hit
            mock_get.return_value = {"item_id": 10, "count": 1}
            res2 = await sample_endpoint(10)
            assert res2["count"] == 1
            # original function should not have been called again
            assert call_count == 1


@pytest.mark.asyncio
async def test_db_cache_decorator():
    class FakeSession:
        pass

    call_count = 0

    @db_cache("repo_prefix", ttl=100)
    async def get_items(db, filter_name: str, limit: int = 10):
        nonlocal call_count
        call_count += 1
        return [{"name": filter_name, "count": call_count}]

    with patch.dict(os.environ, {"TEST_BYPASS_CACHE": "false"}):
        with patch("app.utils.cache.get_cache", new_callable=AsyncMock) as mock_get, \
             patch("app.utils.cache.set_cache", new_callable=AsyncMock) as mock_set:

            mock_get.return_value = None
            session = FakeSession()
            res1 = await get_items(session, "tech", limit=5)
            assert res1[0]["count"] == 1
            mock_set.assert_awaited_once()
            cache_key = mock_set.await_args[0][0]
            assert "db:repo_prefix:get_items" in cache_key
            assert "FakeSession" not in cache_key

            # Cache hit
            mock_get.return_value = [{"name": "tech", "count": 1}]
            res2 = await get_items(session, "tech", limit=5)
            assert res2[0]["count"] == 1
            assert call_count == 1
