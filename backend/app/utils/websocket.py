import json
import asyncio
import logging
from fastapi import WebSocket
from typing import Dict, Set
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # user_id -> set of active WebSockets (local to this instance)
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.pubsub_task = None

    async def _listen_to_redis(self):
        """
        Background task to listen for messages from Redis Pub/Sub
        and deliver them to local connections.
        """
        pubsub = None
        try:
            redis = await redis_client.get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe("chat_channel")
        except Exception as e:
            logger.warning(f"Redis PubSub unavailable; chat will use local delivery only: {e}")
            return
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    target_user_id = data.get("target_user_id")
                    payload = data.get("payload")
                    
                    if target_user_id:
                        # Direct message to a specific user
                        await self._send_local_message(payload, target_user_id)
                    else:
                        # Global broadcast
                        for uid in list(self.active_connections.keys()):
                            await self._send_local_message(payload, uid)
        except Exception as e:
            logger.error(f"Redis PubSub error: {e}")
        finally:
            if pubsub:
                await pubsub.unsubscribe("chat_channel")

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        try:
            # Start pubsub listener if not started
            if self.pubsub_task is None:
                self.pubsub_task = asyncio.create_task(self._listen_to_redis())

            # Update global presence in Redis
            redis = await redis_client.get_redis()
            await redis.sadd("online_users", str(user_id))
        except Exception as e:
            logger.warning(f"Redis presence unavailable; continuing WebSocket locally: {e}")

        await self.broadcast_status(user_id, True)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                try:
                    # Only remove from global online set if no more local connections
                    redis = await redis_client.get_redis()
                    await redis.srem("online_users", str(user_id))
                except Exception as e:
                    logger.warning(f"Redis presence cleanup unavailable: {e}")
                await self.broadcast_status(user_id, False)

    async def _send_local_message(self, message: dict, user_id: int):
        """Send message only to WebSockets connected to THIS instance."""
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    if connection in self.active_connections[user_id]:
                        self.active_connections[user_id].remove(connection)

    async def send_personal_message(self, message: dict, user_id: int):
        """Publish a message to Redis to be delivered to the target user (globally)."""
        try:
            redis = await redis_client.get_redis()
            await redis.publish("chat_channel", json.dumps({
                "target_user_id": user_id,
                "payload": message
            }))
        except Exception as e:
            logger.warning(f"Redis publish unavailable; delivering chat message locally: {e}")
            await self._send_local_message(message, user_id)

    async def broadcast_status(self, user_id: int, is_online: bool):
        """Broadcast status change to ALL users via Redis Pub/Sub."""
        message = {"type": "status", "user_id": user_id, "is_online": is_online}
        try:
            redis = await redis_client.get_redis()
            await redis.publish("chat_channel", json.dumps({
                "target_user_id": None, # Global
                "payload": message
            }))
        except Exception as e:
            logger.warning(f"Redis status broadcast unavailable; delivering status locally: {e}")
            for uid in list(self.active_connections.keys()):
                await self._send_local_message(message, uid)

    async def is_user_online(self, user_id: int) -> bool:
        """Check global presence in Redis."""
        try:
            redis = await redis_client.get_redis()
            return await redis.sismember("online_users", str(user_id))
        except Exception:
            return user_id in self.active_connections

manager = ConnectionManager()
