from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, update, delete, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.models.user import User
from app.models.message import (
    Message,
    ArchivedConversation,
    ApplicationThread,
    MessageReport,
    ArchivedThread,
)
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email (checks Redis cache first)."""
    cache_key = f"user:email:{email.lower()}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
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
    """Mark messages as read with timestamp (Redis-first transaction)."""
    if not messages:
        return
    now = datetime.now(timezone.utc)
    msg_ids = [m.id for m in messages if m.id]
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_message",
        action="MARK_READ",
        payload={"message_ids": msg_ids},
    )
    try:
        for msg in messages:
            msg.is_read = True
            if not msg.read_at:
                msg.read_at = now
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
    ).options(selectinload(Message.sender)).order_by(Message.timestamp)
    result = await db.execute(query)
    messages = result.scalars().all()
    await set_cache(cache_key, messages, ttl=120)
    return messages


async def create_message(
    db: AsyncSession,
    sender_id: int,
    receiver_id: int,
    content: str,
    message_type: Optional[str] = "general",
    application_id: Optional[int] = None,
    thread_id: Optional[int] = None,
    attachment_url: Optional[str] = None,
    attachment_name: Optional[str] = None,
    attachment_type: Optional[str] = None,
    attachment_size: Optional[int] = None,
) -> Message:
    """Create a new chat message (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_message",
        action="CREATE",
        payload={
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content_preview": (content or "")[:100],
            "message_type": message_type,
            "application_id": application_id,
            "thread_id": thread_id,
        },
    )
    try:
        new_msg = Message(
            thread_id=thread_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type or "general",
            application_id=application_id,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_type=attachment_type,
            attachment_size=attachment_size,
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


async def delete_messages_between(db: AsyncSession, user1_id: int, user2_id: int):
    """Delete all messages exchanged between two users and evict caches."""
    query = delete(Message).where(
        or_(
            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
        )
    )
    await db.execute(query)
    await db.commit()

    u1, u2 = min(user1_id, user2_id), max(user1_id, user2_id)
    await delete_cache(f"chat:history:{u1}_{u2}")
    await delete_cache(f"chat:last_msg:{u1}_{u2}")
    await delete_cache(f"chat:unread_cnt:{user1_id}_{user2_id}")
    await delete_cache(f"chat:unread_cnt:{user2_id}_{user1_id}")
    await clear_cache_pattern(f"contacts:{user1_id}:")
    await clear_cache_pattern(f"contacts:{user2_id}:")


async def delete_message_by_id(db: AsyncSession, message_id: int, user_id: int, user_role: str) -> bool:
    """Delete a single message if the user is the sender or an admin."""
    query = select(Message).where(Message.id == message_id)
    result = await db.execute(query)
    msg = result.scalar_one_or_none()
    if not msg:
        return False
    if msg.sender_id != user_id and user_role.upper() != "ADMIN":
        return False

    sender_id, receiver_id = msg.sender_id, msg.receiver_id
    await db.delete(msg)
    await db.commit()

    u1, u2 = min(sender_id, receiver_id), max(sender_id, receiver_id)
    await delete_cache(f"chat:history:{u1}_{u2}")
    await delete_cache(f"chat:last_msg:{u1}_{u2}")
    await delete_cache(f"chat:unread_cnt:{sender_id}_{receiver_id}")
    await clear_cache_pattern(f"contacts:{sender_id}:")
    await clear_cache_pattern(f"contacts:{receiver_id}:")
    return True


async def get_archived_contact_ids(db: AsyncSession, user_id: int) -> List[int]:
    """Get list of contact IDs archived by user_id (checks Redis cache first)."""
    cache_key = f"chat:archived:{user_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(ArchivedConversation.contact_id).where(ArchivedConversation.user_id == user_id)
    result = await db.execute(query)
    archived_ids = [row[0] for row in result.fetchall()]
    await set_cache(cache_key, archived_ids, ttl=300)
    return archived_ids


async def archive_conversation(db: AsyncSession, user_id: int, contact_id: int) -> bool:
    """Archive a conversation between user_id and contact_id (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_archive",
        action="ARCHIVE",
        payload={"user_id": user_id, "contact_id": contact_id},
    )
    try:
        query = select(ArchivedConversation).where(
            ArchivedConversation.user_id == user_id,
            ArchivedConversation.contact_id == contact_id
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if not existing:
            new_archive = ArchivedConversation(user_id=user_id, contact_id=contact_id)
            db.add(new_archive)
            await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"status": "archived"})
        await delete_cache(f"chat:archived:{user_id}")
        await clear_cache_pattern(f"contacts:{user_id}:")
        return True
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] archive_conversation failed: {e}")
        raise


async def unarchive_conversation(db: AsyncSession, user_id: int, contact_id: int) -> bool:
    """Unarchive a conversation between user_id and contact_id (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="chat_archive",
        action="UNARCHIVE",
        payload={"user_id": user_id, "contact_id": contact_id},
    )
    try:
        query = delete(ArchivedConversation).where(
            ArchivedConversation.user_id == user_id,
            ArchivedConversation.contact_id == contact_id
        )
        await db.execute(query)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"status": "unarchived"})
        await delete_cache(f"chat:archived:{user_id}")
        await clear_cache_pattern(f"contacts:{user_id}:")
        return True
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] unarchive_conversation failed: {e}")
        raise


async def get_sent_messages(db: AsyncSession, sender_id: int) -> List[Message]:
    """Get all messages sent by sender_id, ordered by timestamp descending (REQ065)."""
    query = select(Message).where(
        Message.sender_id == sender_id
    ).options(
        selectinload(Message.receiver),
        selectinload(Message.job_application)
    ).order_by(desc(Message.timestamp))
    result = await db.execute(query)
    return result.scalars().all()


async def mark_single_message_read(db: AsyncSession, message_id: int, user_id: int) -> Optional[Message]:
    """Mark a single message as read when opened by the recipient (REQ063)."""
    query = select(Message).where(Message.id == message_id, Message.receiver_id == user_id)
    result = await db.execute(query)
    msg = result.scalar_one_or_none()
    if msg and not msg.is_read:
        msg.is_read = True
        msg.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        await clear_cache_pattern(f"chat:unread_cnt:*_{user_id}")
    return msg


# ─── Application Thread Repository Helpers ────────────────────────────────────

async def get_thread_by_id(db: AsyncSession, thread_id: int) -> Optional[ApplicationThread]:
    res = await db.execute(
        select(ApplicationThread)
        .where(ApplicationThread.id == thread_id)
        .options(
            selectinload(ApplicationThread.job_application),
            selectinload(ApplicationThread.candidate),
            selectinload(ApplicationThread.started_by),
        )
    )
    return res.scalar_one_or_none()


async def get_thread_by_application_id(db: AsyncSession, application_id: int) -> Optional[ApplicationThread]:
    res = await db.execute(
        select(ApplicationThread)
        .where(ApplicationThread.application_id == application_id)
        .options(
            selectinload(ApplicationThread.job_application),
            selectinload(ApplicationThread.candidate),
            selectinload(ApplicationThread.started_by),
        )
    )
    return res.scalar_one_or_none()


async def create_application_thread(
    db: AsyncSession,
    application_id: int,
    candidate_id: int,
    started_by_id: int,
) -> ApplicationThread:
    thread = ApplicationThread(
        application_id=application_id,
        candidate_id=candidate_id,
        started_by_id=started_by_id,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def get_thread_messages(db: AsyncSession, thread_id: int) -> List[Message]:
    res = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .options(selectinload(Message.sender))
        .order_by(Message.timestamp, Message.id)
    )
    return list(res.scalars().all())


async def get_message_by_id(db: AsyncSession, message_id: int) -> Optional[Message]:
    res = await db.execute(
        select(Message)
        .where(Message.id == message_id)
        .options(selectinload(Message.sender), selectinload(Message.thread))
    )
    return res.scalar_one_or_none()


async def thread_has_hr_message(db: AsyncSession, thread_id: int) -> bool:
    """Return True if at least one message in this thread was sent by HR or Admin."""
    res = await db.execute(
        select(Message.id)
        .join(User, User.id == Message.sender_id)
        .where(
            Message.thread_id == thread_id,
            func.upper(User.role).in_(["HR", "ADMIN", "SUPERADMIN"]),
        )
        .limit(1)
    )
    return res.first() is not None


async def has_hr_started_message_between(
    db: AsyncSession,
    candidate_id: int,
    hr_user_id: Optional[int] = None,
    application_id: Optional[int] = None,
) -> bool:
    """Return True if HR or Admin has already sent at least one message to this candidate (optionally scoped to application)."""
    conditions = [
        Message.receiver_id == candidate_id,
        func.upper(User.role).in_(["HR", "ADMIN", "SUPERADMIN"]),
    ]
    if application_id is not None:
        conditions.append(Message.application_id == application_id)
    elif hr_user_id is not None:
        conditions.append(Message.sender_id == hr_user_id)

    res = await db.execute(
        select(Message.id)
        .join(User, User.id == Message.sender_id)
        .where(*conditions)
        .limit(1)
    )
    return res.first() is not None


async def get_archived_thread_ids(db: AsyncSession, user_id: int) -> List[int]:
    res = await db.execute(
        select(ArchivedThread.thread_id).where(ArchivedThread.user_id == user_id)
    )
    return [row[0] for row in res.fetchall()]


async def archive_thread(db: AsyncSession, user_id: int, thread_id: int) -> bool:
    existing = await db.execute(
        select(ArchivedThread).where(
            ArchivedThread.user_id == user_id,
            ArchivedThread.thread_id == thread_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(ArchivedThread(user_id=user_id, thread_id=thread_id))
        await db.commit()
    return True


async def unarchive_thread(db: AsyncSession, user_id: int, thread_id: int) -> bool:
    await db.execute(
        delete(ArchivedThread).where(
            ArchivedThread.user_id == user_id,
            ArchivedThread.thread_id == thread_id,
        )
    )
    await db.commit()
    return True


async def create_message_report(
    db: AsyncSession,
    message_id: int,
    thread_id: Optional[int],
    reporter_id: int,
    reason: str,
) -> MessageReport:
    report = MessageReport(
        message_id=message_id,
        thread_id=thread_id,
        reporter_id=reporter_id,
        reason=reason,
        status="OPEN",
    )
    db.add(report)
    await db.execute(
        update(Message).where(Message.id == message_id).values(is_reported=True)
    )
    await db.commit()
    await db.refresh(report)
    return report


import sys
chat_repository = sys.modules[__name__]
ChatRepository = sys.modules[__name__]
