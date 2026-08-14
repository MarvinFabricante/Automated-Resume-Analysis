from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.models.audit_log import AuditLog


async def create_audit_log(db: AsyncSession, log_data: dict) -> AuditLog:
    new_log = AuditLog(**log_data)
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    return new_log


async def get_recent_activities(db: AsyncSession, limit: int = 10) -> List[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_activities(db: AsyncSession) -> List[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
    )
    return result.scalars().all()


class AuditRepository:
    create_audit_log = staticmethod(create_audit_log)
    get_recent_activities = staticmethod(get_recent_activities)
    get_all_activities = staticmethod(get_all_activities)
