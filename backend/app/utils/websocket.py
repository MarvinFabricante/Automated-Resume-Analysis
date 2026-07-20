import json
import logging
from fastapi import WebSocket
from typing import Dict, Set

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # user_id -> set of active WebSockets (local to this instance)
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        await self.broadcast_status(user_id, True)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
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
        """Deliver a chat message locally."""
        await self._send_local_message(message, user_id)

    async def broadcast_status(self, user_id: int, is_online: bool):
        """Broadcast status change to ALL users locally."""
        message = {"type": "status", "user_id": user_id, "is_online": is_online}
        for uid in list(self.active_connections.keys()):
            await self._send_local_message(message, uid)

    async def is_user_online(self, user_id: int) -> bool:
        """Check local presence."""
        return user_id in self.active_connections

manager = ConnectionManager()

