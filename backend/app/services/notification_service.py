from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
import json
from app.models.notification import Notification
from app.schemas.notification_schema import NotificationCreate
from app.utils.websocket_manager import manager

async def create_notification(db: AsyncSession, title: str, message: str, type: str, target_role: str = None, target_email: str = None) -> Notification:
    new_notification = Notification(title=title, message=message, type=type, target_role=target_role, target_email=target_email)
    db.add(new_notification)
    await db.commit()
    await db.refresh(new_notification)
    
    # Broadcast to connected clients
    try:
        notification_data = {
            "id": new_notification.id,
            "title": new_notification.title,
            "message": new_notification.message,
            "type": new_notification.type,
            "target_role": new_notification.target_role,
            "target_email": new_notification.target_email,
            "created_at": new_notification.created_at.isoformat(),
            "is_read": False
        }
        await manager.broadcast(json.dumps(notification_data), target_role=new_notification.target_role, target_email=new_notification.target_email)
    except Exception as e:
        print(f"Error broadcasting notification: {e}")
        
    return new_notification

async def get_all_notifications(db: AsyncSession, role: str = None, email: str = None) -> list[Notification]:
    from sqlalchemy import or_, and_
    query = select(Notification).order_by(Notification.created_at.desc())
    
    if role:
        if role == 'CANDIDATE':
            # Candidates see notifications targeting 'CANDIDATE' and their specific email (or no email)
            if email:
                query = query.where(
                    and_(
                        Notification.target_role == 'CANDIDATE',
                        or_(Notification.target_email == None, Notification.target_email == email)
                    )
                )
            else:
                query = query.where(
                    and_(
                        Notification.target_role == 'CANDIDATE',
                        Notification.target_email == None
                    )
                )
        else:
            # HR and ADMIN see notifications where target_role matches, OR target_role is None
            query = query.where(or_(Notification.target_role == None, Notification.target_role == role))
    
    result = await db.execute(query.limit(50))
    return result.scalars().all()

async def mark_all_as_read(db: AsyncSession) -> bool:
    await db.execute(update(Notification).where(Notification.is_read == False).values(is_read=True))
    await db.commit()
    return True
