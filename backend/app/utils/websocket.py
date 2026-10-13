import json
import uuid
import asyncio
import logging
from fastapi import WebSocket
from typing import Dict, Set, Optional, Any

from app.utils.redis_client import get_async_redis, publish_event

logger = logging.getLogger(__name__)

# Unique ID per backend process instance to prevent self-echoing in Redis Pub/Sub
INSTANCE_ID = uuid.uuid4().hex


def _normalize_uid(user_id: Any) -> int:
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return user_id


class ConnectionManager:
    def __init__(self):
        # user_id -> set of active WebSockets (local to this instance)
        self.active_connections: Dict[Any, Set[WebSocket]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._pubsub = None

    async def start_redis_listener(self):
        """Start background task listening to Redis for chat and status events."""
        if self._listener_task and not self._listener_task.done():
            return
        self._listener_task = asyncio.create_task(self._listen_redis_pubsub())

    async def stop_redis_listener(self):
        """Gracefully stop background Redis pubsub listener."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error stopping Redis listener: {e}")
            self._listener_task = None

    async def _listen_redis_pubsub(self):
        try:
            client = get_async_redis()
            self._pubsub = client.pubsub()
            await self._pubsub.subscribe("pubsub:ws_chat", "pubsub:ws_status")
            logger.info("[Chat WS Manager] Subscribed to Redis channels: pubsub:ws_chat, pubsub:ws_status")

            async for message in self._pubsub.listen():
                if message and message.get("type") == "message":
                    try:
                        channel = message.get("channel")
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8", errors="replace")

                        raw_data = message.get("data")
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8", errors="replace")

                        data = json.loads(raw_data)

                        # Self-echo deduplication: skip messages published by this worker instance
                        if data.get("origin_id") == INSTANCE_ID:
                            continue

                        if channel == "pubsub:ws_chat":
                            target_uid = data.get("user_id")
                            msg = data.get("message")
                            if target_uid is not None and msg:
                                await self._send_local_message(msg, target_uid)
                        elif channel == "pubsub:ws_status":
                            uid = data.get("user_id")
                            is_online = data.get("is_online", False)
                            if uid is not None:
                                status_msg = {"type": "status", "user_id": uid, "is_online": is_online}
                                for local_uid in list(self.active_connections.keys()):
                                    await self._send_local_message(status_msg, local_uid)
                    except Exception as e:
                        logger.debug(f"Error handling Redis WS message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Redis WS listener stopped: {e}")
        finally:
            if self._pubsub:
                try:
                    await self._pubsub.unsubscribe("pubsub:ws_chat", "pubsub:ws_status")
                    await self._pubsub.close()
                except Exception:
                    pass
                self._pubsub = None

    async def connect(self, websocket: WebSocket, user_id: Any):
        await websocket.accept()
        uid = _normalize_uid(user_id)
        if uid not in self.active_connections:
            self.active_connections[uid] = set()
        self.active_connections[uid].add(websocket)

        # Mark user online in Redis set
        try:
            client = get_async_redis()
            await client.sadd("users:online", str(uid))
        except Exception:
            pass

        await self.start_redis_listener()
        await self.broadcast_status(uid, True)

    async def disconnect(self, websocket: WebSocket, user_id: Any):
        uid = _normalize_uid(user_id)
        if uid in self.active_connections:
            self.active_connections[uid].discard(websocket)
            if not self.active_connections[uid]:
                del self.active_connections[uid]
                try:
                    client = get_async_redis()
                    await client.srem("users:online", str(uid))
                    if isinstance(uid, int):
                        await client.srem("users:online", uid)
                except Exception:
                    pass
                await self.broadcast_status(uid, False)

    async def _send_local_message(self, message: dict, user_id: Any):
        """Send message only to WebSockets connected to THIS instance."""
        uid = _normalize_uid(user_id)
        if uid in self.active_connections:
            dead_connections = []
            for connection in list(self.active_connections[uid]):
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)

            if dead_connections:
                for dead in dead_connections:
                    if uid in self.active_connections:
                        self.active_connections[uid].discard(dead)
                if uid in self.active_connections and not self.active_connections[uid]:
                    del self.active_connections[uid]

    async def send_personal_message(self, message: dict, user_id: Any):
        """Deliver a chat message locally and publish to Redis for other workers."""
        uid = _normalize_uid(user_id)
        # 1. Deliver to local WebSockets
        await self._send_local_message(message, uid)

        # 2. Publish to Redis so all other backend workers deliver to their clients
        await publish_event("pubsub:ws_chat", {
            "origin_id": INSTANCE_ID,
            "user_id": uid,
            "message": message,
        })

    async def broadcast_status(self, user_id: Any, is_online: bool):
        """Broadcast status change to ALL users locally and via Redis."""
        uid = _normalize_uid(user_id)
        message = {"type": "status", "user_id": uid, "is_online": is_online}
        for local_uid in list(self.active_connections.keys()):
            await self._send_local_message(message, local_uid)

        await publish_event("pubsub:ws_status", {
            "origin_id": INSTANCE_ID,
            "user_id": uid,
            "is_online": is_online,
        })

    async def is_user_online(self, user_id: Any) -> bool:
        """Check presence via Redis set, falling back to local connections."""
        uid = _normalize_uid(user_id)
        try:
            client = get_async_redis()
            is_member = await client.sismember("users:online", str(uid))
            if not is_member and isinstance(uid, int):
                is_member = await client.sismember("users:online", uid)
            if is_member:
                return True
        except Exception:
            pass
        return uid in self.active_connections

    def get_online_count(self) -> int:
        """Return the number of unique online users from Redis or local count."""
        try:
            from app.utils.redis_client import get_sync_redis, is_sync_redis_available
            if is_sync_redis_available():
                client = get_sync_redis()
                count = client.scard("users:online")
                if count is not None and count > 0:
                    return int(count)
        except Exception:
            pass
        return len(self.active_connections)

    async def get_online_count_async(self) -> int:
        """Return the number of unique online users asynchronously."""
        try:
            client = get_async_redis()
            count = await client.scard("users:online")
            if count is not None and count > 0:
                return int(count)
        except Exception:
            pass
        return len(self.active_connections)


manager = ConnectionManager()
