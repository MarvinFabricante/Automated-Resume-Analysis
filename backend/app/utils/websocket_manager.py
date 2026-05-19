from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Store connections grouped by role
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connections grouped by email
        self.email_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, role: str, email: str = None):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = []
        self.active_connections[role].append(websocket)
        
        if email:
            if email not in self.email_connections:
                self.email_connections[email] = []
            self.email_connections[email].append(websocket)

    def disconnect(self, websocket: WebSocket, role: str, email: str = None):
        if role in self.active_connections and websocket in self.active_connections[role]:
            self.active_connections[role].remove(websocket)
        if email and email in self.email_connections and websocket in self.email_connections[email]:
            self.email_connections[email].remove(websocket)

    async def broadcast(self, message: str, target_role: str = None, target_email: str = None):
        """
        Broadcasts a message. If target_email is specified, only connections for that email receive it.
        If target_role is specified, only connections with that role receive it.
        Otherwise, everyone receives it.
        """
        if target_email:
            if target_email in self.email_connections:
                for connection in self.email_connections[target_email]:
                    try:
                        await connection.send_text(message)
                    except Exception:
                        pass
        elif target_role:
            if target_role in self.active_connections:
                for connection in self.active_connections[target_role]:
                    try:
                        await connection.send_text(message)
                    except Exception:
                        pass
        else:
            for role_conns in self.active_connections.values():
                for connection in role_conns:
                    try:
                        await connection.send_text(message)
                    except Exception:
                        pass

manager = ConnectionManager()
