"""
Unified WebSocket & Real-Time Connection Manager
------------------------------------------------
Provides function-based WebSocket connection management, channel partitioning,
role-based and user-based messaging, and Redis Pub/Sub synchronization
across multiple backend worker processes.

Unified features:
- Chat messaging & direct personal message delivery
- Online presence tracking & status broadcast via Redis sets
- Real-time notifications by role (ADMIN, HR, CANDIDATE) and email
- Cross-worker real-time synchronization via Redis Pub/Sub channels:
  - pubsub:ws_notifications
  - pubsub:ws_chat
  - pubsub:ws_status
"""

import sys
import json
import uuid
import asyncio
import logging
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket

from app.utils.redis_client import get_async_redis, publish_event

logger = logging.getLogger(__name__)

# Unique ID per backend process instance to prevent self-echoing in Redis Pub/Sub
INSTANCE_ID: str = uuid.uuid4().hex

# --- State (in-memory for local process) ---
# Chat/presence: user_id -> Set[WebSocket]
chat_connections: Dict[Any, Set[WebSocket]] = {}
active_connections: Dict[Any, Set[WebSocket]] = chat_connections  # Alias for backward compatibility

# Notifications: role -> List[WebSocket], email -> List[WebSocket]
role_connections: Dict[str, List[WebSocket]] = {}
email_connections: Dict[str, List[WebSocket]] = {}

# Background listener task and pubsub client
_listener_task: Optional[asyncio.Task] = None
_pubsub = None


# --- Helper ---
def _normalize_uid(user_id: Any) -> Any:
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return user_id


class _SyncOrAsyncNone:
    """Helper enabling disconnect to be used synchronously or awaited cleanly."""
    def __await__(self):
        async def _noop():
            return None
        return _noop().__await__()


# --- Chat & Presence Functions ---

async def send_local_chat_message(message: dict, user_id: Any) -> None:
    """Send message only to WebSockets connected to THIS instance for the given user."""
    uid = _normalize_uid(user_id)
    if uid in chat_connections:
        dead_connections = []
        for connection in list(chat_connections[uid]):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        if dead_connections:
            for dead in dead_connections:
                if uid in chat_connections:
                    chat_connections[uid].discard(dead)
            if uid in chat_connections and not chat_connections[uid]:
                del chat_connections[uid]


async def send_personal_message(message: dict, user_id: Any) -> None:
    """Deliver a chat message locally and publish to Redis for other workers."""
    uid = _normalize_uid(user_id)
    # 1. Deliver to local WebSockets
    await send_local_chat_message(message, uid)

    # 2. Publish to Redis so all other backend workers deliver to their clients
    await publish_event("pubsub:ws_chat", {
        "origin_id": INSTANCE_ID,
        "user_id": uid,
        "message": message,
    })


async def broadcast_status(user_id: Any, is_online: bool) -> None:
    """Broadcast user presence status change to ALL users locally and via Redis."""
    uid = _normalize_uid(user_id)
    message = {"type": "status", "user_id": uid, "is_online": is_online}
    for local_uid in list(chat_connections.keys()):
        await send_local_chat_message(message, local_uid)

    await publish_event("pubsub:ws_status", {
        "origin_id": INSTANCE_ID,
        "user_id": uid,
        "is_online": is_online,
    })


async def connect_chat(websocket: WebSocket, user_id: Any) -> None:
    """Accept and register a user's chat WebSocket connection."""
    await websocket.accept()
    uid = _normalize_uid(user_id)
    if uid not in chat_connections:
        chat_connections[uid] = set()
    chat_connections[uid].add(websocket)

    # Mark user online in Redis set
    try:
        client = get_async_redis()
        await client.sadd("users:online", str(uid))
    except Exception:
        pass

    await start_redis_listener()
    await broadcast_status(uid, True)


async def disconnect_chat(websocket: WebSocket, user_id: Any) -> None:
    """Unregister a user's chat WebSocket connection and update online status."""
    uid = _normalize_uid(user_id)
    if uid in chat_connections:
        chat_connections[uid].discard(websocket)
        if not chat_connections[uid]:
            del chat_connections[uid]
            try:
                client = get_async_redis()
                await client.srem("users:online", str(uid))
                if isinstance(uid, int):
                    await client.srem("users:online", uid)
            except Exception:
                pass
            await broadcast_status(uid, False)


async def is_user_online(user_id: Any) -> bool:
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
    return uid in chat_connections


def get_online_count() -> int:
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
    return len(chat_connections)


async def get_online_count_async() -> int:
    """Return the number of unique online users asynchronously."""
    try:
        client = get_async_redis()
        count = await client.scard("users:online")
        if count is not None and count > 0:
            return int(count)
    except Exception:
        pass
    return len(chat_connections)


# --- Notification Functions ---

async def connect_notification(websocket: WebSocket, role: str, email: Optional[str] = None) -> None:
    """Accept and register a WebSocket for notification broadcasts by role and optional email."""
    await websocket.accept()
    norm_role = (role or "").upper()
    norm_email = (email or "").lower() if email else None

    if norm_role not in role_connections:
        role_connections[norm_role] = []
    role_connections[norm_role].append(websocket)

    if norm_email:
        if norm_email not in email_connections:
            email_connections[norm_email] = []
        email_connections[norm_email].append(websocket)

    await start_redis_listener()


def disconnect_notification(websocket: WebSocket, role: str, email: Optional[str] = None) -> None:
    """Unregister a notification WebSocket by role and optional email."""
    norm_role = (role or "").upper()
    norm_email = (email or "").lower() if email else None

    if norm_role in role_connections:
        if websocket in role_connections[norm_role]:
            role_connections[norm_role].remove(websocket)
        if not role_connections[norm_role]:
            del role_connections[norm_role]

    if norm_email and norm_email in email_connections:
        if websocket in email_connections[norm_email]:
            email_connections[norm_email].remove(websocket)
        if not email_connections[norm_email]:
            del email_connections[norm_email]


async def send_local_notification(message: str, target_role: Optional[str] = None, target_email: Optional[str] = None) -> None:
    """Send notification message only to connections locally attached to this worker process."""
    if target_email:
        norm_email = target_email.lower()
        if norm_email in email_connections:
            dead_conns = []
            for connection in list(email_connections[norm_email]):
                try:
                    await connection.send_text(message)
                except Exception:
                    dead_conns.append(connection)
            for dead in dead_conns:
                if norm_email in email_connections and dead in email_connections[norm_email]:
                    email_connections[norm_email].remove(dead)
    elif target_role:
        norm_role = target_role.upper()
        roles_to_notify = [norm_role]
        if norm_role == "HR":
            # Admin can also monitor HR operational notifications
            roles_to_notify.append("ADMIN")

        for r in roles_to_notify:
            if r in role_connections:
                dead_conns = []
                for connection in list(role_connections[r]):
                    try:
                        await connection.send_text(message)
                    except Exception:
                        dead_conns.append(connection)
                for dead in dead_conns:
                    if r in role_connections and dead in role_connections[r]:
                        role_connections[r].remove(dead)
    else:
        # Default: only broadcast internal events to ADMIN and HR (NEVER to CANDIDATES or Guests)
        for r in ["ADMIN", "HR"]:
            if r in role_connections:
                dead_conns = []
                for connection in list(role_connections[r]):
                    try:
                        await connection.send_text(message)
                    except Exception:
                        dead_conns.append(connection)
                for dead in dead_conns:
                    if r in role_connections and dead in role_connections[r]:
                        role_connections[r].remove(dead)


async def broadcast_notification(message: str, target_role: Optional[str] = None, target_email: Optional[str] = None) -> None:
    """Broadcasts a notification message locally and across all worker processes via Redis Pub/Sub."""
    # 1. Deliver to local WebSockets
    await send_local_notification(message, target_role, target_email)

    # 2. Publish to Redis so all other backend workers deliver to their clients
    await publish_event("pubsub:ws_notifications", {
        "origin_id": INSTANCE_ID,
        "message": message,
        "target_role": target_role,
        "target_email": target_email,
    })


# --- Unified High-Level Dispatchers ---

async def connect(websocket: WebSocket, identifier_or_role: Any, email: Optional[str] = None) -> None:
    """
    Unified connect handler.
    Automatically routes to connect_notification when role/email is provided,
    or connect_chat when user_id is provided.
    """
    if email is not None:
        await connect_notification(websocket, role=str(identifier_or_role), email=email)
    elif isinstance(identifier_or_role, int):
        await connect_chat(websocket, user_id=identifier_or_role)
    elif isinstance(identifier_or_role, str) and identifier_or_role.isdigit():
        await connect_chat(websocket, user_id=int(identifier_or_role))
    else:
        await connect_notification(websocket, role=str(identifier_or_role), email=email)


def disconnect(websocket: WebSocket, identifier_or_role: Any, email: Optional[str] = None):
    """
    Unified disconnect handler.
    Routes to disconnect_notification (sync) or returns coroutine for disconnect_chat.
    """
    if email is not None or (isinstance(identifier_or_role, str) and not identifier_or_role.isdigit()):
        disconnect_notification(websocket, role=str(identifier_or_role), email=email)
        return _SyncOrAsyncNone()
    else:
        return disconnect_chat(websocket, user_id=identifier_or_role)


async def broadcast(message: str, target_role: Optional[str] = None, target_email: Optional[str] = None) -> None:
    """Broadcast notification message (alias for broadcast_notification)."""
    await broadcast_notification(message, target_role=target_role, target_email=target_email)


# Aliases for backward-compatibility with internal methods
_send_local = send_local_notification
_send_local_message = send_local_chat_message


# --- Redis Pub/Sub Background Listener ---

async def start_redis_listener() -> None:
    """Start unified background task listening to Redis Pub/Sub for cross-worker messages."""
    global _listener_task
    if _listener_task and not _listener_task.done():
        return
    _listener_task = asyncio.create_task(_listen_redis_pubsub())


async def stop_redis_listener() -> None:
    """Gracefully stop background Redis pubsub listener."""
    global _listener_task, _pubsub
    if _listener_task and not _listener_task.done():
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error stopping Redis listener: {e}")
        _listener_task = None


async def _listen_redis_pubsub() -> None:
    """Listen to Redis channels for cross-worker notifications, chat, and status broadcasts."""
    global _pubsub
    try:
        client = get_async_redis()
        _pubsub = client.pubsub()
        await _pubsub.subscribe("pubsub:ws_notifications", "pubsub:ws_chat", "pubsub:ws_status")
        logger.info("[WebSocket Manager] Subscribed to Redis channels: pubsub:ws_notifications, pubsub:ws_chat, pubsub:ws_status")

        async for message in _pubsub.listen():
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

                    if channel == "pubsub:ws_notifications":
                        await send_local_notification(
                            data.get("message", ""),
                            data.get("target_role"),
                            data.get("target_email"),
                        )
                    elif channel == "pubsub:ws_chat":
                        target_uid = data.get("user_id")
                        msg = data.get("message")
                        if target_uid is not None and msg:
                            await send_local_chat_message(msg, target_uid)
                    elif channel == "pubsub:ws_status":
                        uid = data.get("user_id")
                        is_online = data.get("is_online", False)
                        if uid is not None:
                            status_msg = {"type": "status", "user_id": uid, "is_online": is_online}
                            for local_uid in list(chat_connections.keys()):
                                await send_local_chat_message(status_msg, local_uid)
                except Exception as e:
                    logger.debug(f"Error handling Redis WS message: {e}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"Redis WS listener stopped: {e}")
    finally:
        if _pubsub:
            try:
                await _pubsub.unsubscribe("pubsub:ws_notifications", "pubsub:ws_chat", "pubsub:ws_status")
                await _pubsub.close()
            except Exception:
                pass
            _pubsub = None


# --- Backward Compatibility Class Proxy ---

class ConnectionManager:
    """Proxy providing backward-compatibility for class-based references or tests."""
    def __init__(self):
        self.active_connections = chat_connections
        self.email_connections = email_connections
        self.role_connections = role_connections

    @property
    def _listener_task(self):
        return _listener_task

    @_listener_task.setter
    def _listener_task(self, val):
        global _listener_task
        _listener_task = val

    start_redis_listener = staticmethod(start_redis_listener)
    stop_redis_listener = staticmethod(stop_redis_listener)
    connect = staticmethod(connect)
    disconnect = staticmethod(disconnect)
    send_personal_message = staticmethod(send_personal_message)
    broadcast_status = staticmethod(broadcast_status)
    broadcast = staticmethod(broadcast)
    is_user_online = staticmethod(is_user_online)
    get_online_count = staticmethod(get_online_count)
    get_online_count_async = staticmethod(get_online_count_async)
    _send_local = staticmethod(send_local_notification)
    _send_local_message = staticmethod(send_local_chat_message)


manager = ConnectionManager()
websocket_manager = sys.modules[__name__]
