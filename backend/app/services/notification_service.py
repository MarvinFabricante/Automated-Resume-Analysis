from sqlalchemy.ext.asyncio import AsyncSession
import json
from app.models.notification import Notification
from app.schemas.notification_schema import NotificationCreate
from app.utils.websocket_manager import manager
from app.repositories.notification_repository import NotificationRepository

async def create_notification(db: AsyncSession, title: str, message: str, type: str, target_role: str = None, target_email: str = None, sender_role: str = None) -> Notification:
    notification_data = {
        "title": title,
        "message": message,
        "type": type,
        "target_role": target_role,
        "target_email": target_email,
        "sender_role": sender_role
    }
    new_notification = await NotificationRepository.create(db, notification_data)

    # Broadcast to connected clients
    try:
        notification_data = {
            "id": new_notification.id,
            "title": new_notification.title,
            "message": new_notification.message,
            "type": new_notification.type,
            "target_role": new_notification.target_role,
            "target_email": new_notification.target_email,
            "sender_role": new_notification.sender_role,
            "created_at": new_notification.created_at.isoformat(),
            "is_read": False
        }
        await manager.broadcast(json.dumps(notification_data), target_role=new_notification.target_role, target_email=new_notification.target_email)
    except Exception as e:
        print(f"Error broadcasting notification: {e}")

    return new_notification


async def get_all_notifications(db: AsyncSession, role: str = None, email: str = None) -> list[Notification]:
    return await NotificationRepository.get_all_by_criteria(db, role=role, email=email)


async def mark_all_as_read(db: AsyncSession, role: str = None, email: str = None) -> bool:
    return await NotificationRepository.mark_all_as_read(db, role=role, email=email)


class NotificationService:
    create_notification = staticmethod(create_notification)
    get_all_notifications = staticmethod(get_all_notifications)
    mark_all_as_read = staticmethod(mark_all_as_read)


notification_service = NotificationService()

