from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, update
from typing import List, Optional
import logging

from app.models.user import User
from app.models.message import Message
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email (checks Redis cache first)."""
    cache_key = f"user:email:{email.lower()}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID (checks Redis cache first)."""
    cache_key = f"user:id:{user_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
    return user


async def get_contact_users(db: AsyncSession, allowed_roles: List[str], exclude_user_id: int, search: Optional[str] = None) -> List[User]:
    """Get contact users (checks Redis cache first)."""
    cache_key = f"chat:contacts:{','.join(sorted(allowed_roles))}:{exclude_user_id}:{search or ''}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(User).where(User.role.in_(allowed_roles), User.id != exclude_user_id)
    if search:
        query = query.where(User.fullname.ilike(f"%{search}%"))
    result = await db.execute(query)
    users = result.scalars().all()
    await set_cache(cache_key, users, ttl=120)
    return users


async def get_last_message_between(db: AsyncSession, user1_id: int, user2_id: int) -> Optional[Message]:
    """Get last message between two users (checks Redis cache first)."""
    u1, u2 = min(user1_id, user2_id), max(user1_id, user2_id)
    cache_key = f"chat:last_msg:{u1}_{u2}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(Message).where(
        or_(
            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
        )
    ).order_by(desc(Message.timestamp)).limit(1)
    result = await db.execute(query)
    msg = result.scalar_one_or_none()
    if msg:
        await set_cache(cache_key, msg, ttl=120)
    return msg


async def get_unread_count(db: AsyncSession, sender_id: int, receiver_id: int) -> int:
    """Get unread count from sender to receiver (checks Redis cache first)."""
    cache_key = f"chat:unread_cnt:{sender_id}_{receiver_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(Message).where(
        Message.sender_id == sender_id,
        Message.receiver_id == receiver_id,
        Message.is_read == False
    )
    result = await db.execute(query)
    count = len(result.scalars().all())
    await set_cache(cache_key, count, ttl=60)
    return count


async def get_unread_messages(db: AsyncSession, sender_id: int, receiver_id: int) -> List[Message]:
    """Get unread messages from sender to receiver."""
    query = select(Message).where(
        Message.sender_id == sender_id,
        Message.receiver_id == receiver_id,
        Message.is_read == False
    )
    result = await db.execute(query)
    return result.scalars().all()


async def mark_messages_as_read(db: AsyncSession, messages: List[Message]):
    """Mark messages as read (Redis-first transaction)."""
    if not messages:
        return
    msg_ids = [m.id for m in messages if m.id]
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_message",
        action="MARK_READ",
        payload={"message_ids": msg_ids},
    )
    try:
        for msg in messages:
            msg.is_read = True
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"count": len(messages)})

        await clear_cache_pattern("chat:unread_cnt:")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def get_chat_history(db: AsyncSession, user1_id: int, user2_id: int) -> List[Message]:
    """Get chat history between two users (checks Redis cache first)."""
    u1, u2 = min(user1_id, user2_id), max(user1_id, user2_id)
    cache_key = f"chat:history:{u1}_{u2}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(Message).where(
        or_(
            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
        )
    ).order_by(Message.timestamp)
    result = await db.execute(query)
    messages = result.scalars().all()
    await set_cache(cache_key, messages, ttl=120)
    return messages


async def create_message(db: AsyncSession, sender_id: int, receiver_id: int, content: str) -> Message:
    """Create a new chat message (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_message",
        action="CREATE",
        payload={"sender_id": sender_id, "receiver_id": receiver_id, "content_preview": content[:100]},
    )
    try:
        new_msg = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        db.add(new_msg)
        await db.commit()
        await db.refresh(new_msg)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_msg.id})

        # Evict chat history & last msg caches
        u1, u2 = min(sender_id, receiver_id), max(sender_id, receiver_id)
        await delete_cache(f"chat:history:{u1}_{u2}")
        await delete_cache(f"chat:last_msg:{u1}_{u2}")
        await delete_cache(f"chat:unread_cnt:{sender_id}_{receiver_id}")
        await clear_cache_pattern(f"contacts:{sender_id}:")
        await clear_cache_pattern(f"contacts:{receiver_id}:")

        return new_msg
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_message failed: {e}")
        raise


import sys
chat_repository = sys.modules[__name__]
ChatRepository = sys.modules[__name__]
