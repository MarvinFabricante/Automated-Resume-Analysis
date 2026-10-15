from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, and_, func
from typing import List, Optional
import logging

from app.models.notification import Notification
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, notification_data: dict) -> Notification:
    """Create notification (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="notification",
        action="CREATE",
        payload={
            "title": notification_data.get("title"),
            "target_role": notification_data.get("target_role"),
            "target_email": notification_data.get("target_email"),
        },
    )
    try:
        new_notification = Notification(**notification_data)
        db.add(new_notification)
        await db.commit()
        await db.refresh(new_notification)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_notification.id})

        await clear_cache_pattern("notifs:criteria:")
        return new_notification
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] notification create failed: {e}")
        raise


async def get_all_by_criteria(
    db: AsyncSession, 
    role: Optional[str] = None, 
    email: Optional[str] = None, 
    limit: int = 50
) -> List[Notification]:
    """Get all notifications by criteria (checks Redis cache first)."""
    norm_role = (role or "").upper()
    norm_email = (email or "").lower()

    if norm_role not in ["ADMIN", "HR", "CANDIDATE"]:
        return []

    cache_key = f"notifs:criteria:{norm_role}:{norm_email or 'none'}:{limit}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(Notification).order_by(Notification.created_at.desc())
        
    if norm_role == 'CANDIDATE':
        if norm_email:
            email_condition = or_(
                Notification.target_email == None,
                func.lower(Notification.target_email) == norm_email
            )
        else:
            email_condition = Notification.target_email == None

        query = query.where(
            and_(
                Notification.target_role == 'CANDIDATE',
                email_condition,
                or_(
                    Notification.sender_role.in_(['HR', 'ADMIN', 'SYSTEM']),
                    Notification.sender_role == None
                )
            )
        )
    elif norm_role == 'HR':
        query = query.where(
            and_(
                or_(Notification.target_role == None, Notification.target_role == 'HR'),
                or_(
                    Notification.target_email == None,
                    func.lower(Notification.target_email) == norm_email
                ),
                or_(
                    Notification.sender_role.in_(['CANDIDATE', 'ADMIN', 'HR', 'SYSTEM']),
                    Notification.sender_role == None
                )
            )
        )
    elif norm_role == 'ADMIN':
        query = query.where(
            and_(
                or_(Notification.target_role == None, Notification.target_role == 'ADMIN', Notification.target_role == 'HR'),
                or_(
                    Notification.sender_role.in_(['HR', 'CANDIDATE', 'ADMIN', 'SYSTEM']),
                    Notification.sender_role == None
                )
            )
        )
        
    result = await db.execute(query.limit(limit))
    notifications = result.scalars().all()
    await set_cache(cache_key, notifications, ttl=60)
    return notifications


async def mark_all_as_read(db: AsyncSession, role: Optional[str] = None, email: Optional[str] = None) -> bool:
    """Mark all notifications as read (Redis-first transaction)."""
    norm_role = (role or "").upper()
    norm_email = (email or "").lower()

    if norm_role not in ["ADMIN", "HR", "CANDIDATE"]:
        return False

    tx_id = await redis_tx_manager.stage_transaction(
        target="notification",
        action="MARK_ALL_READ",
        payload={"role": norm_role, "email": norm_email},
    )
    try:
        query = update(Notification).where(Notification.is_read == False)
            
        if norm_role == 'CANDIDATE':
            if norm_email:
                email_condition = or_(
                    Notification.target_email == None,
                    func.lower(Notification.target_email) == norm_email
                )
            else:
                email_condition = Notification.target_email == None
            query = query.where(and_(Notification.target_role == 'CANDIDATE', email_condition))
        elif norm_role == 'HR':
            query = query.where(or_(Notification.target_role == None, Notification.target_role == 'HR'))
        elif norm_role == 'ADMIN':
            query = query.where(or_(Notification.target_role == None, Notification.target_role == 'ADMIN', Notification.target_role == 'HR'))

        await db.execute(query.values(is_read=True))
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"marked": True})

        await clear_cache_pattern("notifs:criteria:")
        return True
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] mark_all_as_read failed: {e}")
        raise


import sys
notification_repository = sys.modules[__name__]
NotificationRepository = sys.modules[__name__]
