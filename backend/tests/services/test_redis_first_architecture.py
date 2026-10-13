import pytest
import asyncio
from datetime import datetime

from app.utils.redis_client import (
    redis_tx_manager,
    is_redis_available,
    redis_transaction_context,
    get_async_redis,
    push_to_queue,
    pop_from_queue,
)
from app.utils.cache import (
    get_cache,
    set_cache,
    delete_cache,
    clear_cache_pattern,
    cache_entity,
    get_cached_entity,
    delete_cached_entity,
)


@pytest.mark.asyncio
async def test_redis_connection_available():
    """Verify that Redis connection check works and returns a boolean."""
    available = await is_redis_available()
    assert isinstance(available, bool)


@pytest.mark.asyncio
async def test_redis_transaction_lifecycle():
    """
    Test the full lifecycle of a Redis-first transaction:
    STAGE (PENDING) -> COMMIT (COMMITTED)
    """
    payload = {"entity": "test_app", "score": 95, "name": "Candidate One"}
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_application",
        action="CREATE",
        payload=payload,
        metadata={"client_ip": "127.0.0.1"},
    )
    assert tx_id.startswith("tx_")

    # Verify transaction in Redis
    tx = await redis_tx_manager.get_transaction(tx_id)
    assert tx is not None
    assert tx["status"] == "PENDING"
    assert tx["target"] == "job_application"
    assert tx["action"] == "CREATE"
    assert tx["payload"]["score"] == 95

    # Commit transaction
    committed = await redis_tx_manager.commit_transaction(tx_id, {"saved_id": 1001})
    assert committed is True

    # Verify status changed to COMMITTED
    tx_after = await redis_tx_manager.get_transaction(tx_id)
    assert tx_after["status"] == "COMMITTED"
    assert "committed_at" in tx_after
    assert tx_after["result"]["saved_id"] == 1001


@pytest.mark.asyncio
async def test_redis_transaction_failure():
    """Test that failed transactions are properly marked as FAILED in Redis."""
    payload = {"operation": "delete_all"}
    tx_id = await redis_tx_manager.stage_transaction(
        target="security",
        action="DELETE",
        payload=payload,
    )

    failed = await redis_tx_manager.fail_transaction(tx_id, "Permission denied")
    assert failed is True

    tx = await redis_tx_manager.get_transaction(tx_id)
    assert tx["status"] == "FAILED"
    assert tx["error"] == "Permission denied"


@pytest.mark.asyncio
async def test_redis_transaction_context_manager():
    """Test context manager auto-commits on clean exit and auto-fails on error."""
    # Success case
    async with redis_transaction_context("resume", "UPLOAD", {"file": "cv.pdf"}) as ctx:
        ctx.set_result({"url": "https://example.com/cv.pdf"})

    tx = await redis_tx_manager.get_transaction(ctx.tx_id)
    assert tx["status"] == "COMMITTED"
    assert tx["result"]["url"] == "https://example.com/cv.pdf"

    # Failure case
    caught = False
    try:
        async with redis_transaction_context("resume", "DELETE", {"id": 999}):
            raise ValueError("File in use")
    except ValueError:
        caught = True

    assert caught is True


@pytest.mark.asyncio
async def test_redis_queue_helpers():
    """Test Redis queue push and pop helpers."""
    q_name = "test:queue:operations"
    item = {"task": "send_email", "to": "test@example.com", "id": 123}

    push_res = await push_to_queue(q_name, item)
    assert push_res > 0

    popped = await pop_from_queue(q_name)
    assert popped is not None
    assert popped["task"] == "send_email"
    assert popped["to"] == "test@example.com"


@pytest.mark.asyncio
async def test_redis_cache_operations():
    """Test raw Redis cache set, get, and delete operations."""
    client = get_async_redis()
    test_key = "test:cache:sample_key"

    await client.setex(test_key, 60, b"Hello Redis!")
    raw_val = await client.get(test_key)
    assert raw_val == b"Hello Redis!"

    await client.delete(test_key)
    deleted_val = await client.get(test_key)
    assert deleted_val is None


@pytest.mark.asyncio
async def test_transaction_stats():
    """Verify transaction stats reporting from Redis."""
    stats = await redis_tx_manager.get_transaction_stats()
    assert isinstance(stats, dict)
    assert "total" in stats
    assert "committed" in stats
    assert stats["total"] >= 0


def test_serialization_and_safe_decode():
    """Verify _safe_decode and _json_serial handle complex types."""
    from enum import Enum
    from decimal import Decimal
    import uuid
    from app.utils.redis_client import _json_serial, _safe_decode, sanitize_payload

    class SampleRole(Enum):
        ADMIN = "ADMIN"

    uid = uuid.uuid4()
    dec = Decimal("19.99")

    assert _safe_decode(b"hello") == "hello"
    assert _safe_decode("world") == "world"
    assert _safe_decode(None) == ""

    assert _json_serial(SampleRole.ADMIN) == "ADMIN"
    assert _json_serial(uid) == str(uid)
    assert _json_serial(dec) == 19.99
    assert _json_serial(b"bytes_val") == "bytes_val"
    assert _json_serial({1, 2}) == [1, 2]

    sanitized = sanitize_payload({"role": SampleRole.ADMIN, "uuid": uid, "price": dec})
    assert sanitized["role"] == "ADMIN"
    assert sanitized["price"] == 19.99


def test_sync_transactions_and_queue():
    """Verify synchronous variants of transaction and queue operations."""
    from app.utils.redis_client import (
        push_to_queue_sync,
        pop_from_queue_sync,
        publish_event_sync,
    )

    q_name = "test:sync:queue"
    push_to_queue_sync(q_name, {"msg": "sync_test"})
    popped = pop_from_queue_sync(q_name)
    assert popped is not None
    assert popped["msg"] == "sync_test"

    pub_count = publish_event_sync("test:sync:channel", {"event": "ping"})
    assert isinstance(pub_count, int)

    # Sync transaction lifecycle
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="sync_test",
        action="UPDATE",
        payload={"v": 1},
    )
    assert tx_id.startswith("tx_")

    committed = redis_tx_manager.commit_transaction_sync(tx_id, {"done": True})
    assert committed is True

    tx = redis_tx_manager.get_transaction_sync(tx_id)
    assert tx is not None
    assert tx["status"] == "COMMITTED"
    assert tx["result"]["done"] is True


@pytest.mark.asyncio
async def test_websocket_connection_manager_edge_cases():
    """Verify WebSocket connection manager handles connects, disconnects without KeyError, and online presence."""
    from unittest.mock import AsyncMock
    from app.utils.websocket import ConnectionManager, INSTANCE_ID

    manager = ConnectionManager()
    mock_ws = AsyncMock()

    # Connect
    await manager.connect(mock_ws, 9999)
    assert 9999 in manager.active_connections
    assert mock_ws in manager.active_connections[9999]
    assert manager.get_online_count() >= 1

    is_online = await manager.is_user_online(9999)
    assert is_online is True

    # Send personal message
    await manager.send_personal_message({"type": "greeting", "text": "hi"}, 9999)
    assert mock_ws.send_json.call_count == 2
    assert mock_ws.send_json.call_args_list[0][0][0] == {"type": "status", "user_id": 9999, "is_online": True}
    assert mock_ws.send_json.call_args_list[1][0][0] == {"type": "greeting", "text": "hi"}

    # Disconnect
    await manager.disconnect(mock_ws, 9999)
    assert 9999 not in manager.active_connections

    # Second disconnect should NOT raise KeyError (safe discard)
    await manager.disconnect(mock_ws, 9999)
    assert 9999 not in manager.active_connections

    # Graceful stop of Redis listener
    await manager.stop_redis_listener()
    assert manager._listener_task is None


@pytest.mark.asyncio
async def test_close_redis_pools():
    """Verify close_redis_pools cleans up connections cleanly."""
    from app.utils.redis_client import close_redis_pools, get_async_pool, get_sync_pool
    # Touch pools
    get_async_pool()
    get_sync_pool()

    # Close pools
    await close_redis_pools()
    # Verify idempotent re-call
    await close_redis_pools()

