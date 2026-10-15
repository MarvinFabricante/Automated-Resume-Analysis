from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging
from jose import JWTError, jwt

from app.utils.database import get_db
from app.utils.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.schemas.notification_schema import NotificationResponse
from app.services import notification_service
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    role: Optional[str] = None,
    email: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent notifications, strictly role-based and partitioned by authenticated user.
    Only Candidates, HR, or Admins can access their own notifications.
    """
    user_role = (current_user.get("role") or "").upper()
    user_email = (current_user.get("sub") or "").lower()

    if user_role not in ["ADMIN", "HR", "CANDIDATE"]:
        raise HTTPException(status_code=403, detail="Access denied: unauthorized role")

    if user_role == "CANDIDATE":
        effective_role = "CANDIDATE"
        effective_email = user_email
    elif user_role == "HR":
        effective_role = "HR"
        effective_email = user_email
    else:  # ADMIN
        effective_role = role.upper() if role and role.upper() in ["ADMIN", "HR"] else "ADMIN"
        effective_email = email.lower() if email else user_email

    return await notification_service.get_all_notifications(db, effective_role, effective_email)

@router.put("/mark-read", status_code=status.HTTP_200_OK)
async def mark_all_read(
    role: Optional[str] = None,
    email: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark unread notifications as read for the authenticated role and user.
    """
    user_role = (current_user.get("role") or "").upper()
    user_email = (current_user.get("sub") or "").lower()

    if user_role not in ["ADMIN", "HR", "CANDIDATE"]:
        raise HTTPException(status_code=403, detail="Access denied: unauthorized role")

    if user_role == "CANDIDATE":
        effective_role = "CANDIDATE"
        effective_email = user_email
    elif user_role == "HR":
        effective_role = "HR"
        effective_email = user_email
    else:  # ADMIN
        effective_role = role.upper() if role and role.upper() in ["ADMIN", "HR"] else "ADMIN"
        effective_email = email.lower() if email else user_email

    await notification_service.mark_all_as_read(db, effective_role, effective_email)
    return {"message": "All notifications marked as read"}

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    email: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time notifications.
    Strictly authenticates the token to ensure only CANDIDATE, HR, or ADMIN
    can connect to their own notification stream.
    """
    auth_role = None
    auth_email = None

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            auth_role = (payload.get("role") or "").upper()
            auth_email = (payload.get("sub") or "").lower()
        except JWTError as e:
            logger.warning(f"Notification WebSocket rejected: invalid token ({e})")
            await websocket.close(code=1008)
            return

    # Fallback to query params only if token not provided, but strictly validate allowed roles
    if not auth_role and role:
        norm_r = role.upper()
        if norm_r in ["ADMIN", "HR", "CANDIDATE"]:
            auth_role = norm_r
            auth_email = email.lower() if email else None

    if not auth_role or auth_role not in ["ADMIN", "HR", "CANDIDATE"]:
        logger.warning("Notification WebSocket rejected: unauthorized role or unauthenticated attempt")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, auth_role, auth_email)
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, auth_role, auth_email)
    except Exception as e:
        logger.debug(f"Notification WebSocket disconnected with exception: {e}")
        manager.disconnect(websocket, auth_role, auth_email)
