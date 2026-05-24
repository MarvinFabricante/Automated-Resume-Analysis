from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository

class AuditService:
    async def record_activity(
        self,
        db: AsyncSession,
        user_id: int,
        action: str,
        target: str = None,
        details: str = None,
        ip_address: str = None
    ):
        log_data = {
            "user_id": user_id,
            "action": action,
            "target": target,
            "details": details,
            "ip_address": ip_address
        }
        return await AuditRepository.create_audit_log(db, log_data)

    async def get_recent_hr_activities(self, db: AsyncSession, limit: int = 10) -> List[AuditLog]:
        return await AuditRepository.get_recent_activities(db, limit)

    async def get_all_audit_logs(self, db: AsyncSession) -> List[AuditLog]:
        return await AuditRepository.get_all_activities(db)


audit_service = AuditService()


async def record_activity(
    db: AsyncSession,
    user_id: int,
    action: str,
    target: str = None,
    details: str = None,
    ip_address: str = None
):
    return await audit_service.record_activity(db, user_id, action, target, details, ip_address)


async def get_recent_hr_activities(db: AsyncSession, limit: int = 10) -> List[AuditLog]:
    return await audit_service.get_recent_hr_activities(db, limit)


async def get_all_audit_logs(db: AsyncSession) -> List[AuditLog]:
    return await audit_service.get_all_audit_logs(db)
