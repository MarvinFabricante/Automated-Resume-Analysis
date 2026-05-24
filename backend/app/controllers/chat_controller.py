from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.schemas.message_schema import MessageCreate, MessageResponse, ChatContactResponse
from app.utils.websocket import manager
from app.services import chat_service
from app.repositories.auth_repository import AuthRepository
from app.controllers.base_controller import BaseController, Get, Post, WebSocketRoute


async def get_current_user_obj(payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    email = payload.get("sub")
    user = await AuthRepository.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class ChatController(BaseController):
    prefix = "/chat"
    tags = ["Chat"]

    @Get("/active-count")
    async def get_active_count(self):
        from app.utils.redis_client import redis_client
        try:
            redis = await redis_client.get_redis()
            count = await redis.scard("online_users")
            if count < 1:
                count = 1
        except Exception:
            count = 1
        return {"count": count}

    @Get("/contacts", response_model=ChatContactResponse)
    async def get_contacts(
        self,
        search: Optional[str] = None,
        current_user: User = Depends(get_current_user_obj),
        db: AsyncSession = Depends(get_db)
    ):
        chat_users = await chat_service.get_contacts(db, current_user, search)
        return ChatContactResponse(users=chat_users)

    @Get("/messages/{other_user_id}", response_model=List[MessageResponse])
    async def get_messages(
        self,
        other_user_id: int,
        current_user: User = Depends(get_current_user_obj),
        db: AsyncSession = Depends(get_db)
    ):
        return await chat_service.get_messages(db, current_user, other_user_id)

    @Post("/messages/{other_user_id}", response_model=MessageResponse)
    async def send_message(
        self,
        other_user_id: int,
        msg_in: MessageCreate,
        current_user: User = Depends(get_current_user_obj),
        db: AsyncSession = Depends(get_db)
    ):
        new_msg = await chat_service.send_message(db, current_user, other_user_id, msg_in.content)
        if not new_msg:
            raise HTTPException(status_code=403, detail="You cannot message this user.")
        return new_msg

    @WebSocketRoute("/ws")
    async def websocket_endpoint(self, websocket: WebSocket, token: str = Query(...)):
        from app.utils.database import AsyncSessionLocal
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Use a short-lived session for verification to avoid holding a connection from the pool
            async with AsyncSessionLocal() as db:
                user = await chat_service.verify_token(token, db)
                if not user:
                    logger.warning(f"WebSocket connection rejected: Invalid token")
                    await websocket.close(code=1008)
                    return
                user_id = user.id

            await manager.connect(websocket, user_id)
            logger.info(f"WebSocket connected: User {user_id}")
            
            try:
                while True:
                    data_str = await websocket.receive_text()
                    try:
                        import json
                        data = json.loads(data_str)
                        if data.get("type") == "send_message":
                            await chat_service.handle_websocket_message(AsyncSessionLocal, user_id, data)
                    except json.JSONDecodeError:
                        continue
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: User {user_id}")
                await manager.disconnect(websocket, user_id)
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
                await manager.disconnect(websocket, user_id)
                
        except Exception as e:
            logger.error(f"WebSocket handshake failed: {e}")
            # Cannot use websocket.close() if not accepted yet, but Starlette handles it


chat_controller = ChatController()
router = chat_controller.router
