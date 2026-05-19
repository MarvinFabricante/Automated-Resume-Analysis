from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json

from app.utils.database import get_db
from app.schemas.notification_schema import NotificationResponse
from app.services import notification_service
from app.utils.websocket_manager import manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(role: str = None, email: str = None, db: AsyncSession = Depends(get_db)):
    """
    Get recent notifications, filtered by role and email if provided.
    """
    return await notification_service.get_all_notifications(db, role, email)

@router.put("/mark-read", status_code=status.HTTP_200_OK)
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    """
    Mark all unread notifications as read.
    """
    await notification_service.mark_all_as_read(db)
    return {"message": "All notifications marked as read"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications, partitioned by role and email.
    """
    role = websocket.query_params.get("role", "Guest")
    email = websocket.query_params.get("email")
    await manager.connect(websocket, role, email)
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, role, email)
