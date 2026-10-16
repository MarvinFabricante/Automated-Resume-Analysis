import uuid
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.utils.redis_client import (
    get_async_pool,
    get_sync_pool,
    get_async_redis,
    get_sync_redis,
    close_redis_pools,
    is_redis_available,
    is_sync_redis_available,
    _safe_decode,
    _json_serial,
    sanitize_payload,
    RedisTransactionManager,
    redis_tx_manager,
    TransactionContext,
    redis_transaction_context,
    redis_sync_transaction_context,
    publish_event,
    publish_event_sync,
    push_to_queue,
    pop_from_queue,
    push_to_queue_sync,
    pop_from_queue_sync,
)


@pytest.mark.asyncio
async def test_pools_lifecycle():
    pool_async = get_async_pool()
    assert pool_async is not None
    assert get_async_pool() is pool_async

    pool_sync = get_sync_pool()
    assert pool_sync is not None
    assert get_sync_pool() is pool_sync

    async_client = get_async_redis()
    sync_client = get_sync_redis()
    assert async_client is not None
    assert sync_client is not None

    await close_redis_pools()


@pytest.mark.asyncio
async def test_is_redis_available():
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with patch("app.utils.redis_client.get_async_redis", return_value=mock_client):
        assert await is_redis_available() is True

    mock_client.ping.side_effect = Exception("Connection lost")
    with patch("app.utils.redis_client.get_async_redis", return_value=mock_client):
        assert await is_redis_available() is False


def test_is_sync_redis_available():
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("app.utils.redis_client.get_sync_redis", return_value=mock_client):
        assert is_sync_redis_available() is True

    mock_client.ping.side_effect = Exception("Down")
    with patch("app.utils.redis_client.get_sync_redis", return_value=mock_client):
        assert is_sync_redis_available() is False


def test_safe_decode_and_json_serial():
    assert _safe_decode(None) == ""
    assert _safe_decode(b"hello bytes") == "hello bytes"
    assert _safe_decode("plain string") == "plain string"
    assert _safe_decode(123) == "123"

    class SampleEnum(Enum):
        TEST = "test_val"

    class DummyModel:
        def model_dump(self):
            return {"a": 1}

    class DummyOldModel:
        def dict(self):
            return {"b": 2}

    class CustomObj:
        def __init__(self):
            self.x = 10
            self._secret = "hide"

    class FallbackObj:
        pass

    now = datetime(2026, 1, 1, 12, 0, 0)
    d = date(2026, 1, 1)
    t = time(12, 0, 0)
    u = uuid.uuid4()
    dec = Decimal("15.75")

    assert _json_serial(now) == now.isoformat()
    assert _json_serial(d) == d.isoformat()
    assert _json_serial(t) == t.isoformat()
    assert _json_serial(SampleEnum.TEST) == "test_val"
    assert _json_serial(u) == str(u)
    assert _json_serial(dec) == 15.75
    assert _json_serial(b"data") == "data"
    assert _json_serial({1, 2}) == [1, 2]
    assert _json_serial(frozenset([3])) == [3]
    assert _json_serial(DummyModel()) == {"a": 1}
    assert _json_serial(DummyOldModel()) == {"b": 2}
    assert _json_serial(CustomObj()) == {"x": 10}

    # sanitize_payload
    assert sanitize_payload(None) == {}
    sanitized = sanitize_payload({"uuid": u, "enum": SampleEnum.TEST, "dec": dec})
    assert sanitized["uuid"] == str(u)
    assert sanitized["enum"] == "test_val"
    assert sanitized["dec"] == 15.75


@pytest.mark.asyncio
async def test_redis_transaction_manager_async_flow():
    manager = RedisTransactionManager()
    payload = {"candidate_id": 99, "action": "applied"}
    metadata = {"ip": "127.0.0.1"}

    # Stage
    tx_id = await manager.stage_transaction(
        target="application",
        action="CREATE",
        payload=payload,
        metadata=metadata,
    )
    assert tx_id.startswith("tx_")

    # Get transaction
    tx = await manager.get_transaction(tx_id)
    assert tx is not None
    assert tx["status"] == "PENDING"
    assert tx["target"] == "application"
    assert tx["action"] == "CREATE"
    assert tx["payload"] == payload
    assert tx["metadata"] == metadata

    # Commit
    res = await manager.commit_transaction(tx_id, {"new_id": 501})
    assert res is True

    tx_committed = await manager.get_transaction(tx_id)
    assert tx_committed["status"] == "COMMITTED"
    assert tx_committed["result"] == {"new_id": 501}

    # Fail flow
    tx_id_fail = await manager.stage_transaction(
        target="application",
        action="UPDATE",
        payload={"id": 501},
    )
    fail_res = await manager.fail_transaction(tx_id_fail, "DB error occurred")
    assert fail_res is True

    tx_failed = await manager.get_transaction(tx_id_fail)
    assert tx_failed["status"] == "FAILED"
    assert tx_failed["error"] == "DB error occurred"


@pytest.mark.asyncio
async def test_redis_transaction_manager_recent_pending_stats():
    manager = RedisTransactionManager()
    tx_id = await manager.stage_transaction("test_stats", "PING", {"ok": True})

    pending = await manager.get_pending_transactions()
    assert isinstance(pending, list)
    assert any(t["tx_id"] == tx_id for t in pending)

    recent = await manager.get_recent_transactions(limit=10)
    assert isinstance(recent, list)
    assert any(t["tx_id"] == tx_id for t in recent)

    stats = await manager.get_transaction_stats()
    assert isinstance(stats, dict)
    assert "total" in stats
    assert "pending" in stats

    # Clean up by committing
    await manager.commit_transaction(tx_id)


def test_redis_transaction_manager_sync_flow():
    manager = RedisTransactionManager()
    payload = {"file": "test.pdf"}

    tx_id = manager.stage_transaction_sync("storage", "UPLOAD", payload)
    assert tx_id.startswith("tx_")

    tx = manager.get_transaction_sync(tx_id)
    assert tx is not None
    assert tx["status"] == "PENDING"

    committed = manager.commit_transaction_sync(tx_id, {"url": "https://s3/test.pdf"})
    assert committed is True

    tx_done = manager.get_transaction_sync(tx_id)
    assert tx_done["status"] == "COMMITTED"

    # Fail sync
    tx_id_f = manager.stage_transaction_sync("storage", "DELETE", payload)
    failed = manager.fail_transaction_sync(tx_id_f, "File not found")
    assert failed is True

    tx_f = manager.get_transaction_sync(tx_id_f)
    assert tx_f["status"] == "FAILED"
    assert tx_f["error"] == "File not found"


@pytest.mark.asyncio
async def test_redis_transaction_context_manager():
    # Success branch
    async with redis_transaction_context("interview", "SCHEDULE", {"time": "10:00"}) as ctx:
        assert isinstance(ctx, TransactionContext)
        ctx.set_result({"meet_url": "https://meet.google.com/xyz"})

    tx = await redis_tx_manager.get_transaction(ctx.tx_id)
    assert tx["status"] == "COMMITTED"
    assert tx["result"]["meet_url"] == "https://meet.google.com/xyz"

    # Failure branch
    err_tx_id = None
    with pytest.raises(ValueError):
        async with redis_transaction_context("interview", "CANCEL", {"id": 1}) as ctx_err:
            err_tx_id = ctx_err.tx_id
            raise ValueError("Invalid cancellation time")

    tx_err = await redis_tx_manager.get_transaction(err_tx_id)
    assert tx_err["status"] == "FAILED"
    assert "Invalid cancellation time" in tx_err["error"]


def test_redis_sync_transaction_context():
    # Success branch
    with redis_sync_transaction_context("celery", "RUN", {"job": 1}) as ctx:
        ctx.set_result({"status": "SUCCESS"})

    tx = redis_tx_manager.get_transaction_sync(ctx.tx_id)
    assert tx["status"] == "COMMITTED"

    # Failure branch
    err_id = None
    with pytest.raises(RuntimeError):
        with redis_sync_transaction_context("celery", "FAIL_JOB", {"job": 2}) as ctx:
            err_id = ctx.tx_id
            raise RuntimeError("Worker crashed")

    tx_err = redis_tx_manager.get_transaction_sync(err_id)
    assert tx_err["status"] == "FAILED"
    assert "Worker crashed" in tx_err["error"]


@pytest.mark.asyncio
async def test_pubsub_and_queue_async():
    channel = f"test:chan:{uuid.uuid4().hex}"
    queue = f"test:q:{uuid.uuid4().hex}"

    # Publish
    pub_res = await publish_event(channel, {"type": "ping"})
    assert isinstance(pub_res, int)

    # Queue push and pop (immediate)
    item = {"task": "process_doc", "id": 101}
    push_res = await push_to_queue(queue, item)
    assert push_res > 0

    popped = await pop_from_queue(queue, timeout=0)
    assert popped == item

    empty_pop = await pop_from_queue(queue, timeout=0)
    assert empty_pop is None

    # Queue pop with timeout
    await push_to_queue(queue, {"delayed": True})
    popped_timeout = await pop_from_queue(queue, timeout=1)
    assert popped_timeout == {"delayed": True}


def test_pubsub_and_queue_sync():
    channel = f"test:sync_chan:{uuid.uuid4().hex}"
    queue = f"test:sync_q:{uuid.uuid4().hex}"

    pub_res = publish_event_sync(channel, {"type": "sync_ping"})
    assert isinstance(pub_res, int)

    item = {"task": "sync_task", "val": 42}
    push_res = push_to_queue_sync(queue, item)
    assert push_res > 0

    popped = pop_from_queue_sync(queue, timeout=0)
    assert popped == item

    empty_pop = pop_from_queue_sync(queue, timeout=0)
    assert empty_pop is None

    push_to_queue_sync(queue, {"sync_delayed": True})
    popped_timeout = pop_from_queue_sync(queue, timeout=1)
    assert popped_timeout == {"sync_delayed": True}


@pytest.mark.asyncio
async def test_redis_tx_manager_error_handling():
    mock_redis = AsyncMock()
    mock_redis.hset.side_effect = Exception("Redis write failed")
    mock_redis.hgetall.side_effect = Exception("Redis read failed")
    mock_redis.lrange.side_effect = Exception("Redis lrange failed")
    mock_redis.smembers.side_effect = Exception("Redis smembers failed")

    with patch("app.utils.redis_client.get_async_redis", return_value=mock_redis):
        mgr = RedisTransactionManager()
        # Stage exception -> catches and still returns tx_id
        tx_id = await mgr.stage_transaction("t", "A", {})
        assert tx_id.startswith("tx_")

        # Commit exception -> returns False
        assert await mgr.commit_transaction("tx_1", {}) is False

        # Fail exception -> returns False
        assert await mgr.fail_transaction("tx_1", "err") is False

        # Get transaction exception -> returns None
        assert await mgr.get_transaction("tx_1") is None

        # Get recent / pending exception -> returns []
        assert await mgr.get_recent_transactions() == []
        assert await mgr.get_pending_transactions() == []
        assert (await mgr.get_transaction_stats())["total"] == 0
