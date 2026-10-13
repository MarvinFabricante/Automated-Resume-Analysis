import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Dict, List
from contextlib import asynccontextmanager, contextmanager

import redis.asyncio as aioredis
import redis as syncredis
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Connection configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_async_pools: Dict[Any, aioredis.ConnectionPool] = {}
_sync_pool: Optional[syncredis.ConnectionPool] = None


def get_async_pool() -> aioredis.ConnectionPool:
    try:
        loop = asyncio.get_running_loop()
        loop_key = id(loop)
        if loop.is_closed():
            loop_key = "default"
    except RuntimeError:
        loop_key = "default"

    if loop_key not in _async_pools:
        _async_pools[loop_key] = aioredis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=False,
        )
    return _async_pools[loop_key]


def get_sync_pool() -> syncredis.ConnectionPool:
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = syncredis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=False,
        )
    return _sync_pool


def get_async_redis() -> Any:
    """Get an asynchronous Redis client instance from connection pool."""
    return aioredis.Redis(connection_pool=get_async_pool())


def get_sync_redis() -> Any:
    """Get a synchronous Redis client instance from connection pool."""
    return syncredis.Redis(connection_pool=get_sync_pool())


async def close_redis_pools():
    """Disconnect and clean up all Redis connection pools."""
    global _sync_pool, _async_pools
    for loop_key, pool in list(_async_pools.items()):
        try:
            await pool.disconnect()
        except Exception as e:
            logger.debug(f"Error disconnecting async pool {loop_key}: {e}")
    _async_pools.clear()

    if _sync_pool is not None:
        try:
            _sync_pool.disconnect()
        except Exception as e:
            logger.debug(f"Error disconnecting sync pool: {e}")
        _sync_pool = None


async def is_redis_available() -> bool:
    """Check if Redis server is reachable."""
    try:
        client = get_async_redis()
        return bool(await client.ping())
    except Exception as e:
        logger.warning(f"Redis is not available: {e}")
        return False


def is_sync_redis_available() -> bool:
    """Check if synchronous Redis is reachable."""
    try:
        client = get_sync_redis()
        return bool(client.ping())
    except Exception as e:
        logger.warning(f"Sync Redis is not available: {e}")
        return False


def _safe_decode(val: Any) -> str:
    """Safely decode bytes or string to str without raising AttributeError."""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


def _json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


def sanitize_payload(payload: Any) -> Any:
    """Ensure payload is safely serializable to JSON."""
    if payload is None:
        return {}
    try:
        return json.loads(json.dumps(payload, default=_json_serial))
    except Exception:
        return str(payload)


class RedisTransactionManager:
    """
    Manages Redis-first transactions.
    Every operation (database write, storage upload, email send, calendar mutation)
    is recorded in Redis first before executing against the source of truth.
    """

    async def stage_transaction(
        self,
        target: str,
        action: str,
        payload: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tx_id: Optional[str] = None,
    ) -> str:
        """
        Record and stage a transaction in Redis before calling the source of truth.
        Status is set to 'PENDING'.
        """
        if not tx_id:
            tx_id = f"tx_{uuid.uuid4().hex}"

        sanitized = sanitize_payload(payload)
        sanitized_meta = sanitize_payload(metadata or {})
        now_str = datetime.utcnow().isoformat()

        record = {
            "tx_id": tx_id,
            "target": str(target),
            "action": str(action).upper(),
            "payload": json.dumps(sanitized),
            "status": "PENDING",
            "created_at": now_str,
            "metadata": json.dumps(sanitized_meta),
        }

        try:
            client = get_async_redis()
            key = f"tx:{tx_id}"

            # Map strings for Redis hash
            hash_data = {k.encode("utf-8"): str(v).encode("utf-8") for k, v in record.items()}
            await client.hset(key, mapping=hash_data)
            await client.expire(key, 86400)  # 24-hour retention

            # Add to pending set & recent list
            await client.sadd("transactions:pending", tx_id)
            await client.lpush("transactions:recent", tx_id)
            await client.ltrim("transactions:recent", 0, 999)  # Keep latest 1000

            # Update stats counters
            await client.hincrby("transactions:stats", "total", 1)
            await client.hincrby("transactions:stats", f"target:{target}", 1)
            await client.hincrby("transactions:stats", f"action:{action.upper()}", 1)

            logger.debug(f"[Redis-First] Staged transaction {tx_id} ({target}.{action}) in Redis.")
        except Exception as e:
            logger.warning(f"[Redis-First] Failed to stage transaction {tx_id} in Redis: {e}")

        return tx_id

    async def commit_transaction(
        self,
        tx_id: str,
        result_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a staged transaction as COMMITTED after successful source of truth write.
        """
        now_str = datetime.utcnow().isoformat()
        res_str = json.dumps(sanitize_payload(result_metadata or {}))

        try:
            client = get_async_redis()
            key = f"tx:{tx_id}"
            updates = {
                b"status": b"COMMITTED",
                b"committed_at": now_str.encode("utf-8"),
                b"result": res_str.encode("utf-8"),
            }
            await client.hset(key, mapping=updates)
            await client.srem("transactions:pending", tx_id)
            await client.hincrby("transactions:stats", "committed", 1)

            logger.debug(f"[Redis-First] Committed transaction {tx_id} in Redis.")
            return True
        except Exception as e:
            logger.warning(f"[Redis-First] Failed to mark transaction {tx_id} committed: {e}")
            return False

    async def fail_transaction(
        self,
        tx_id: str,
        error: str,
    ) -> bool:
        """
        Mark a staged transaction as FAILED if source of truth write failed.
        """
        now_str = datetime.utcnow().isoformat()

        try:
            client = get_async_redis()
            key = f"tx:{tx_id}"
            updates = {
                b"status": b"FAILED",
                b"failed_at": now_str.encode("utf-8"),
                b"error": str(error).encode("utf-8"),
            }
            await client.hset(key, mapping=updates)
            await client.srem("transactions:pending", tx_id)
            await client.hincrby("transactions:stats", "failed", 1)

            logger.warning(f"[Redis-First] Marked transaction {tx_id} FAILED in Redis: {error}")
            return True
        except Exception as e:
            logger.warning(f"[Redis-First] Failed to mark transaction {tx_id} failed: {e}")
            return False

    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a transaction record from Redis."""
        try:
            client = get_async_redis()
            data = await client.hgetall(f"tx:{tx_id}")
            if not data:
                return None
            decoded = {_safe_decode(k): _safe_decode(v) for k, v in data.items()}
            for json_field in ("payload", "metadata", "result"):
                if json_field in decoded and decoded[json_field]:
                    try:
                        decoded[json_field] = json.loads(decoded[json_field])
                    except Exception:
                        pass
            return decoded
        except Exception as e:
            logger.warning(f"Error fetching transaction {tx_id}: {e}")
            return None

    async def get_recent_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the most recent transactions stored in Redis."""
        try:
            client = get_async_redis()
            tx_ids = await client.lrange("transactions:recent", 0, limit - 1)
            results = []
            for tx_id_b in tx_ids:
                tx_id = _safe_decode(tx_id_b)
                tx = await self.get_transaction(tx_id)
                if tx:
                    results.append(tx)
            return results
        except Exception as e:
            logger.warning(f"Error fetching recent transactions: {e}")
            return []

    async def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Retrieve all currently pending transactions in Redis."""
        try:
            client = get_async_redis()
            tx_ids = await client.smembers("transactions:pending")
            results = []
            for tx_id_b in tx_ids:
                tx_id = _safe_decode(tx_id_b)
                tx = await self.get_transaction(tx_id)
                if tx:
                    results.append(tx)
            return results
        except Exception as e:
            logger.warning(f"Error fetching pending transactions: {e}")
            return []

    async def get_transaction_stats(self) -> Dict[str, Any]:
        """Get summary stats of transactions recorded in Redis."""
        try:
            client = get_async_redis()
            raw_stats = await client.hgetall("transactions:stats")
            stats = {}
            for k_b, v_b in raw_stats.items():
                k = _safe_decode(k_b)
                v_str = _safe_decode(v_b)
                try:
                    stats[k] = int(v_str)
                except ValueError:
                    stats[k] = v_str
            pending_count = await client.scard("transactions:pending")
            stats["pending"] = pending_count
            return stats
        except Exception as e:
            logger.warning(f"Error fetching transaction stats: {e}")
            return {"total": 0, "committed": 0, "failed": 0, "pending": 0}

    # Synchronous methods for Celery workers & sync operations
    def stage_transaction_sync(
        self,
        target: str,
        action: str,
        payload: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tx_id: Optional[str] = None,
    ) -> str:
        if not tx_id:
            tx_id = f"tx_{uuid.uuid4().hex}"

        sanitized = sanitize_payload(payload)
        sanitized_meta = sanitize_payload(metadata or {})
        now_str = datetime.utcnow().isoformat()

        record = {
            "tx_id": tx_id,
            "target": str(target),
            "action": str(action).upper(),
            "payload": json.dumps(sanitized),
            "status": "PENDING",
            "created_at": now_str,
            "metadata": json.dumps(sanitized_meta),
        }

        try:
            client = get_sync_redis()
            key = f"tx:{tx_id}"
            hash_data = {k.encode("utf-8"): str(v).encode("utf-8") for k, v in record.items()}
            client.hset(key, mapping=hash_data)
            client.expire(key, 86400)
            client.sadd("transactions:pending", tx_id)
            client.lpush("transactions:recent", tx_id)
            client.ltrim("transactions:recent", 0, 999)
            client.hincrby("transactions:stats", "total", 1)
            client.hincrby("transactions:stats", f"target:{target}", 1)
            client.hincrby("transactions:stats", f"action:{action.upper()}", 1)
        except Exception as e:
            logger.warning(f"[Redis-First Sync] Failed to stage transaction {tx_id}: {e}")

        return tx_id

    def commit_transaction_sync(
        self,
        tx_id: str,
        result_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        now_str = datetime.utcnow().isoformat()
        res_str = json.dumps(sanitize_payload(result_metadata or {}))
        try:
            client = get_sync_redis()
            key = f"tx:{tx_id}"
            updates = {
                b"status": b"COMMITTED",
                b"committed_at": now_str.encode("utf-8"),
                b"result": res_str.encode("utf-8"),
            }
            client.hset(key, mapping=updates)
            client.srem("transactions:pending", tx_id)
            client.hincrby("transactions:stats", "committed", 1)
            return True
        except Exception as e:
            logger.warning(f"[Redis-First Sync] Failed to mark transaction {tx_id} committed: {e}")
            return False

    def fail_transaction_sync(
        self,
        tx_id: str,
        error: str,
    ) -> bool:
        now_str = datetime.utcnow().isoformat()
        try:
            client = get_sync_redis()
            key = f"tx:{tx_id}"
            updates = {
                b"status": b"FAILED",
                b"failed_at": now_str.encode("utf-8"),
                b"error": str(error).encode("utf-8"),
            }
            client.hset(key, mapping=updates)
            client.srem("transactions:pending", tx_id)
            client.hincrby("transactions:stats", "failed", 1)
            return True
        except Exception as e:
            logger.warning(f"[Redis-First Sync] Failed to mark transaction {tx_id} failed: {e}")
            return False

    def get_transaction_sync(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Synchronously retrieve a transaction record from Redis."""
        try:
            client = get_sync_redis()
            data = client.hgetall(f"tx:{tx_id}")
            if not data:
                return None
            decoded = {_safe_decode(k): _safe_decode(v) for k, v in data.items()}
            for json_field in ("payload", "metadata", "result"):
                if json_field in decoded and decoded[json_field]:
                    try:
                        decoded[json_field] = json.loads(decoded[json_field])
                    except Exception:
                        pass
            return decoded
        except Exception as e:
            logger.warning(f"Error fetching transaction sync {tx_id}: {e}")
            return None


# Global singleton instance
redis_tx_manager = RedisTransactionManager()


class TransactionContext:
    def __init__(self, tx_id: str):
        self.tx_id = tx_id
        self.committed = False
        self.result_metadata: Optional[Dict[str, Any]] = None

    def set_result(self, result_metadata: Dict[str, Any]):
        self.result_metadata = result_metadata


@asynccontextmanager
async def redis_transaction_context(
    target: str,
    action: str,
    payload: Any,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager that stores a transaction in Redis FIRST.
    If the block succeeds, transaction is committed in Redis.
    If an exception is raised, transaction is marked FAILED in Redis.
    """
    tx_id = await redis_tx_manager.stage_transaction(target, action, payload, metadata)
    ctx = TransactionContext(tx_id)
    try:
        yield ctx
        await redis_tx_manager.commit_transaction(tx_id, ctx.result_metadata)
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


@contextmanager
def redis_sync_transaction_context(
    target: str,
    action: str,
    payload: Any,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Synchronous version of redis_transaction_context."""
    tx_id = redis_tx_manager.stage_transaction_sync(target, action, payload, metadata)
    ctx = TransactionContext(tx_id)
    try:
        yield ctx
        redis_tx_manager.commit_transaction_sync(tx_id, ctx.result_metadata)
    except Exception as e:
        redis_tx_manager.fail_transaction_sync(tx_id, str(e))
        raise


# ─── Pub/Sub & Queue Helpers ──────────────────────────────────────────

async def publish_event(channel: str, message: Dict[str, Any]) -> int:
    """Publish a real-time event to a Redis channel."""
    try:
        client = get_async_redis()
        msg_str = json.dumps(sanitize_payload(message))
        return await client.publish(channel, msg_str)
    except Exception as e:
        logger.warning(f"Failed to publish event to channel {channel}: {e}")
        return 0


def publish_event_sync(channel: str, message: Dict[str, Any]) -> int:
    """Synchronously publish a real-time event to a Redis channel."""
    try:
        client = get_sync_redis()
        msg_str = json.dumps(sanitize_payload(message))
        return client.publish(channel, msg_str)
    except Exception as e:
        logger.warning(f"Failed to publish sync event to channel {channel}: {e}")
        return 0


async def push_to_queue(queue_name: str, item: Dict[str, Any]) -> int:
    """Push an item to a Redis queue."""
    try:
        client = get_async_redis()
        payload_str = json.dumps(sanitize_payload(item))
        return await client.rpush(queue_name, payload_str)
    except Exception as e:
        logger.warning(f"Failed to push to queue {queue_name}: {e}")
        return 0


async def pop_from_queue(queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
    """Pop an item from a Redis queue."""
    try:
        client = get_async_redis()
        if timeout > 0:
            res = await client.blpop(queue_name, timeout=timeout)
            if res:
                _, val = res
                return json.loads(_safe_decode(val))
        else:
            val = await client.lpop(queue_name)
            if val:
                return json.loads(_safe_decode(val))
        return None
    except Exception as e:
        logger.warning(f"Failed to pop from queue {queue_name}: {e}")
        return None


def push_to_queue_sync(queue_name: str, item: Dict[str, Any]) -> int:
    """Push an item to a Redis queue synchronously."""
    try:
        client = get_sync_redis()
        payload_str = json.dumps(sanitize_payload(item))
        return client.rpush(queue_name, payload_str)
    except Exception as e:
        logger.warning(f"Failed to push to queue sync {queue_name}: {e}")
        return 0


def pop_from_queue_sync(queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
    """Pop an item from a Redis queue synchronously."""
    try:
        client = get_sync_redis()
        if timeout > 0:
            res = client.blpop(queue_name, timeout=timeout)
            if res:
                _, val = res
                return json.loads(_safe_decode(val))
        else:
            val = client.lpop(queue_name)
            if val:
                return json.loads(_safe_decode(val))
        return None
    except Exception as e:
        logger.warning(f"Failed to pop from queue sync {queue_name}: {e}")
        return None
