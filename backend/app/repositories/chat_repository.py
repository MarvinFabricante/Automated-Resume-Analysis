from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, update
from typing import List, Optional
from app.models.user import User
from app.models.message import Message

class ChatRepository:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_contact_users(db: AsyncSession, allowed_roles: List[str], exclude_user_id: int, search: Optional[str] = None) -> List[User]:
        query = select(User).where(User.role.in_(allowed_roles), User.id != exclude_user_id)
        if search:
            query = query.where(User.fullname.ilike(f"%{search}%"))
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_last_message_between(db: AsyncSession, user1_id: int, user2_id: int) -> Optional[Message]:
        query = select(Message).where(
            or_(
                and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
            )
        ).order_by(desc(Message.timestamp)).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_unread_count(db: AsyncSession, sender_id: int, receiver_id: int) -> int:
        query = select(Message).where(
            Message.sender_id == sender_id,
            Message.receiver_id == receiver_id,
            Message.is_read == False
        )
        result = await db.execute(query)
        return len(result.scalars().all())

    @staticmethod
    async def get_unread_messages(db: AsyncSession, sender_id: int, receiver_id: int) -> List[Message]:
        query = select(Message).where(
            Message.sender_id == sender_id,
            Message.receiver_id == receiver_id,
            Message.is_read == False
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def mark_messages_as_read(db: AsyncSession, messages: List[Message]):
        for msg in messages:
            msg.is_read = True
        await db.commit()

    @staticmethod
    async def get_chat_history(db: AsyncSession, user1_id: int, user2_id: int) -> List[Message]:
        query = select(Message).where(
            or_(
                and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
            )
        ).order_by(Message.timestamp)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_message(db: AsyncSession, sender_id: int, receiver_id: int, content: str) -> Message:
        new_msg = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        db.add(new_msg)
        await db.commit()
        await db.refresh(new_msg)
        return new_msg
