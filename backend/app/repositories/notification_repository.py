from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, and_
from typing import List, Optional
from app.models.notification import Notification

class NotificationRepository:
    @staticmethod
    async def create(db: AsyncSession, notification_data: dict) -> Notification:
        new_notification = Notification(**notification_data)
        db.add(new_notification)
        await db.commit()
        await db.refresh(new_notification)
        return new_notification

    @staticmethod
    async def get_all_by_criteria(
        db: AsyncSession, 
        role: Optional[str] = None, 
        email: Optional[str] = None, 
        limit: int = 50
    ) -> List[Notification]:
        query = select(Notification).order_by(Notification.created_at.desc())
        
        if role:
            if role == 'CANDIDATE':
                email_condition = or_(Notification.target_email == None, Notification.target_email == email) if email else Notification.target_email == None
                query = query.where(
                    and_(
                        Notification.target_role == 'CANDIDATE',
                        email_condition,
                        or_(Notification.sender_role == 'HR', Notification.sender_role == 'ADMIN', Notification.sender_role == None)
                    )
                )
            elif role == 'HR':
                query = query.where(
                    and_(
                        or_(Notification.target_role == None, Notification.target_role == 'HR'),
                        or_(Notification.sender_role == 'CANDIDATE', Notification.sender_role == 'ADMIN', Notification.sender_role == None)
                    )
                )
            elif role == 'ADMIN':
                query = query.where(
                    and_(
                        or_(Notification.target_role == None, Notification.target_role == 'ADMIN', Notification.target_role == 'HR'),
                        or_(Notification.sender_role == 'HR', Notification.sender_role == 'CANDIDATE', Notification.sender_role == None)
                    )
                )
        
        result = await db.execute(query.limit(limit))
        return result.scalars().all()

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, role: Optional[str] = None, email: Optional[str] = None) -> bool:
        query = update(Notification).where(Notification.is_read == False)
        
        if role:
            if role == 'CANDIDATE':
                email_condition = or_(Notification.target_email == None, Notification.target_email == email) if email else Notification.target_email == None
                query = query.where(and_(Notification.target_role == 'CANDIDATE', email_condition))
            elif role == 'HR':
                query = query.where(or_(Notification.target_role == None, Notification.target_role == 'HR'))
            elif role == 'ADMIN':
                query = query.where(or_(Notification.target_role == None, Notification.target_role == 'ADMIN', Notification.target_role == 'HR'))

        await db.execute(query.values(is_read=True))
        await db.commit()
        return True
