import json
import uuid
import asyncio
import logging
from fastapi import WebSocket
from typing import List, Dict, Optional

from app.utils.redis_client import get_async_redis, publish_event

logger = logging.getLogger(__name__)

# Unique ID per backend process instance to prevent self-echoing in Redis Pub/Sub
INSTANCE_ID = uuid.uuid4().hex


class ConnectionManager:
    def __init__(self):
        # Store connections grouped by role
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connections grouped by email
        self.email_connections: Dict[str, List[WebSocket]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._pubsub = None

    async def start_redis_listener(self):
        """Start background task listening to Redis Pub/Sub for cross-worker messages."""
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
                logger.debug(f"Error stopping notifications listener: {e}")
            self._listener_task = None

    async def _listen_redis_pubsub(self):
        """Listen to Redis channel for broadcasts from other workers."""
        try:
            client = get_async_redis()
            self._pubsub = client.pubsub()
            await self._pubsub.subscribe("pubsub:ws_notifications")
            logger.info("[WebSocket Manager] Subscribed to Redis channel 'pubsub:ws_notifications'.")
            async for message in self._pubsub.listen():
                if message and message.get("type") == "message":
                    try:
                        raw_data = message.get("data")
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8", errors="replace")

                        data = json.loads(raw_data)

                        # Skip messages originated by this process to prevent duplicate local delivery
                        if data.get("origin_id") == INSTANCE_ID:
                            continue

                        await self._send_local(
                            data.get("message", ""),
                            data.get("target_role"),
                            data.get("target_email"),
                        )
                    except Exception as e:
                        logger.debug(f"Error handling Redis WS notification: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Redis WS notifications listener stopped: {e}")
        finally:
            if self._pubsub:
                try:
                    await self._pubsub.unsubscribe("pubsub:ws_notifications")
                    await self._pubsub.close()
                except Exception:
                    pass
                self._pubsub = None

    async def connect(self, websocket: WebSocket, role: str, email: str = None):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = []
        self.active_connections[role].append(websocket)

        if email:
            if email not in self.email_connections:
                self.email_connections[email] = []
            self.email_connections[email].append(websocket)

        # Ensure Redis listener is running
        await self.start_redis_listener()

    def disconnect(self, websocket: WebSocket, role: str, email: str = None):
        if role in self.active_connections:
            if websocket in self.active_connections[role]:
                self.active_connections[role].remove(websocket)
            if not self.active_connections[role]:
                del self.active_connections[role]

        if email and email in self.email_connections:
            if websocket in self.email_connections[email]:
                self.email_connections[email].remove(websocket)
            if not self.email_connections[email]:
                del self.email_connections[email]

    async def _send_local(self, message: str, target_role: str = None, target_email: str = None):
        """Send message only to connections locally attached to this worker process."""
        if target_email:
            if target_email in self.email_connections:
                dead_conns = []
                for connection in list(self.email_connections[target_email]):
                    try:
                        await connection.send_text(message)
                    except Exception:
                        dead_conns.append(connection)
                for dead in dead_conns:
                    if target_email in self.email_connections and dead in self.email_connections[target_email]:
                        self.email_connections[target_email].remove(dead)
        elif target_role:
            if target_role in self.active_connections:
                dead_conns = []
                for connection in list(self.active_connections[target_role]):
                    try:
                        await connection.send_text(message)
                    except Exception:
                        dead_conns.append(connection)
                for dead in dead_conns:
                    if target_role in self.active_connections and dead in self.active_connections[target_role]:
                        self.active_connections[target_role].remove(dead)
        else:
            for role, role_conns in list(self.active_connections.items()):
                dead_conns = []
                for connection in list(role_conns):
                    try:
                        await connection.send_text(message)
                    except Exception:
                        dead_conns.append(connection)
                for dead in dead_conns:
                    if role in self.active_connections and dead in self.active_connections[role]:
                        self.active_connections[role].remove(dead)

    async def broadcast(self, message: str, target_role: str = None, target_email: str = None):
        """
        Broadcasts a message locally and across all worker processes via Redis Pub/Sub.
        """
        # 1. Deliver to local WebSockets
        await self._send_local(message, target_role, target_email)

        # 2. Publish to Redis so all other backend workers deliver to their clients
        await publish_event("pubsub:ws_notifications", {
            "origin_id": INSTANCE_ID,
            "message": message,
            "target_role": target_role,
            "target_email": target_email,
        })


manager = ConnectionManager()
