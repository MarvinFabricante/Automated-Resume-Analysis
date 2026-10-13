from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import logging

from app.models.audit_log import AuditLog
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create_audit_log(db: AsyncSession, log_data: dict) -> AuditLog:
    """Create audit log (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="audit_log",
        action="CREATE",
        payload={
            "action": log_data.get("action"),
            "details": str(log_data.get("details", ""))[:150],
            "user_id": log_data.get("user_id"),
        },
    )
    try:
        new_log = AuditLog(**log_data)
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_log.id})

        await clear_cache_pattern("audit:activities:")
        return new_log
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_audit_log failed: {e}")
        raise


async def get_recent_activities(db: AsyncSession, limit: int = 10) -> List[AuditLog]:
    """Get recent activities (checks Redis cache first)."""
    cache_key = f"audit:activities:recent:{limit}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    await set_cache(cache_key, logs, ttl=120)
    return logs


async def get_all_activities(db: AsyncSession) -> List[AuditLog]:
    """Get all activities (checks Redis cache first)."""
    cache_key = "audit:activities:all"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    await set_cache(cache_key, logs, ttl=120)
    return logs


class AuditRepository:
    create_audit_log = staticmethod(create_audit_log)
    get_recent_activities = staticmethod(get_recent_activities)
    get_all_activities = staticmethod(get_all_activities)
