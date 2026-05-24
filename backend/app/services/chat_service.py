from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from jose import jwt, JWTError
from app.utils.auth import SECRET_KEY, ALGORITHM
from app.models.user import User
from app.models.message import Message
from app.schemas.message_schema import ChatUser
from app.utils.websocket import manager
from app.utils.redis_client import redis_client
import json
from datetime import datetime
from app.repositories.chat_repository import ChatRepository

async def get_allowed_roles(user_role: str) -> List[str]:
    """
    Returns the list of roles that the given user role is allowed to message.
    """
    role = user_role.upper()
    if role == "CANDIDATE":
        return ["HR"]
    elif role == "HR":
        return ["CANDIDATE", "ADMIN", "HR"]
    elif role == "ADMIN":
        return ["HR"]
    return []

async def verify_token(token: str, db: AsyncSession):
    """
    Verifies the JWT token and returns the corresponding User object.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        return await ChatRepository.get_user_by_email(db, email)
    except JWTError:
        return None

async def get_contacts(db: AsyncSession, current_user: User, search: Optional[str] = None) -> List[ChatUser]:
    """
    Fetches the list of contacts for the current user, including last message and unread count.
    Uses Redis for caching to improve performance.
    """
    cache_key = f"contacts:{current_user.id}:{search or ''}"
    redis = await redis_client.get_redis()
    
    # Try to get from cache
    cached_data = await redis.get(cache_key)
    if cached_data:
        try:
            cached_users = json.loads(cached_data)
            chat_users = []
            for u_data in cached_users:
                # Convert back to ChatUser objects and refresh online status
                u_data['is_online'] = await manager.is_user_online(u_data['id'])
                if u_data.get('last_message_time'):
                    u_data['last_message_time'] = datetime.fromisoformat(u_data['last_message_time'])
                chat_users.append(ChatUser(**u_data))
            return chat_users
        except Exception:
            pass # Fallback to DB if cache parsing fails

    allowed_roles = await get_allowed_roles(current_user.role)
    if not allowed_roles:
        return []

    users = await ChatRepository.get_contact_users(db, allowed_roles, current_user.id, search)

    chat_users = []
    for u in users:
        # Get last message
        last_msg = await ChatRepository.get_last_message_between(db, current_user.id, u.id)

        # Unread count
        unread_count = await ChatRepository.get_unread_count(db, u.id, current_user.id)

        chat_users.append(ChatUser(
            id=u.id,
            fullname=u.fullname,
            role=u.role,
            profile_image_url=u.profile_image_url,
            is_online=await manager.is_user_online(u.id),
            last_message=last_msg.content if last_msg else None,
            last_message_time=last_msg.timestamp if last_msg else None,
            unread_count=unread_count
        ))

    # Sort by recent message time
    chat_users.sort(key=lambda x: x.last_message_time.timestamp() if x.last_message_time else 0, reverse=True)
    
    # Save to cache (TTL 10 seconds for safety, though we invalidate on message events)
    cache_users = []
    for u in chat_users:
        u_dict = u.model_dump() if hasattr(u, 'model_dump') else u.dict()
        if u_dict.get('last_message_time'):
            u_dict['last_message_time'] = u_dict['last_message_time'].isoformat()
        cache_users.append(u_dict)
    
    await redis.setex(cache_key, 10, json.dumps(cache_users))
    
    return chat_users

async def invalidate_contacts_cache(user_id: int):
    """Invalidates the contacts cache for a specific user."""
    redis = await redis_client.get_redis()
    # We use keys() with pattern because there might be multiple search variants cached
    # For production, consider keeping track of keys in a set instead of using keys()
    keys = await redis.keys(f"contacts:{user_id}:*")
    if keys:
        await redis.delete(*keys)

async def get_messages(db: AsyncSession, current_user: User, other_user_id: int) -> List[Message]:
    """
    Retrieves message history between the current user and another user, 
    and marks all incoming messages as read.
    """
    # Mark messages as read
    unreads = await ChatRepository.get_unread_messages(db, other_user_id, current_user.id)
    if unreads:
        await ChatRepository.mark_messages_as_read(db, unreads)
        # Invalidate cache for current user since unread counts changed
        await invalidate_contacts_cache(current_user.id)

    # Get history
    return await ChatRepository.get_chat_history(db, current_user.id, other_user_id)

async def send_message(db: AsyncSession, current_user: User, other_user_id: int, content: str, client_id: Optional[str] = None) -> Message:
    """
    Sends a message to another user if the roles are compatible, 
    and broadcasts it via WebSocket.
    """
    # Verify allowed to message
    allowed_roles = await get_allowed_roles(current_user.role)
    receiver = await ChatRepository.get_user_by_id(db, other_user_id)
    
    if not receiver or receiver.role not in allowed_roles:
        return None

    new_msg = await ChatRepository.create_message(db, current_user.id, other_user_id, content)

    msg_data = {
        "type": "new_message",
        "id": new_msg.id,
        "sender_id": new_msg.sender_id,
        "receiver_id": new_msg.receiver_id,
        "content": new_msg.content,
        "timestamp": new_msg.timestamp.isoformat(),
        "is_read": new_msg.is_read,
        "client_id": client_id
    }

    # Broadcast to receiver
    await manager.send_personal_message(msg_data, other_user_id)
    # Also to sender (if they have multiple tabs open)
    await manager.send_personal_message(msg_data, current_user.id)

    # Invalidate caches
    await invalidate_contacts_cache(current_user.id)
    await invalidate_contacts_cache(other_user_id)

    return new_msg

async def handle_websocket_message(db_factory, sender_id: int, data: dict):
    """
    Handles a message received through a WebSocket connection.
    Parses the data, saves the message to the database, and broadcasts it.
    """
    try:
        receiver_id = data.get("receiver_id")
        content = data.get("content")
        client_id = data.get("client_id")

        if not receiver_id or not content:
            return

        async with db_factory() as db:
            # Get sender object
            sender = await ChatRepository.get_user_by_id(db, sender_id)
            if not sender:
                return

            # Use existing send_message logic
            await send_message(db, sender, receiver_id, content, client_id=client_id)
            
    except Exception as e:
        # Log error but don't crash the WS loop
        import logging
        logging.error(f"Error handling WS message: {e}")
