from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository

class AuditService:
    async def record_activity(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        action: str = "",
        target: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        try:
            valid_user_id = None
            if user_id is not None:
                from app.models.user import User
                from sqlalchemy import select
                user_res = await db.execute(select(User.id).where(User.id == user_id))
                if user_res.scalar_one_or_none():
                    valid_user_id = user_id

            log_data = {
                "user_id": valid_user_id,
                "action": action,
                "target": target,
                "details": details,
                "ip_address": ip_address
            }
            return await AuditRepository.create_audit_log(db, log_data)
        except Exception as e:
            print(f"WARNING: Failed to record audit log: {e}")
            return None

    async def get_recent_hr_activities(self, db: AsyncSession, limit: int = 10) -> List[AuditLog]:
        return await AuditRepository.get_recent_activities(db, limit)

    async def get_all_audit_logs(self, db: AsyncSession) -> List[AuditLog]:
        return await AuditRepository.get_all_activities(db)


audit_service = AuditService()


async def record_activity(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: str = "",
    target: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None
):
    return await audit_service.record_activity(db, user_id, action, target, details, ip_address)


async def get_recent_hr_activities(db: AsyncSession, limit: int = 10) -> List[AuditLog]:
    return await audit_service.get_recent_hr_activities(db, limit)


async def get_all_audit_logs(db: AsyncSession) -> List[AuditLog]:
    return await audit_service.get_all_audit_logs(db)
