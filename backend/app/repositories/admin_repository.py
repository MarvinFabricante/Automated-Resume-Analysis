from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from app.models.user import User
from app.models.admin import Admin
from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.job_description import JobDescription

class AdminRepository:
    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[User]:
        result = await db.execute(select(User))
        return result.scalars().all()

    @staticmethod
    async def create_admin(db: AsyncSession, admin_data: dict) -> Admin:
        new_admin = Admin(**admin_data)
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        return new_admin

    @staticmethod
    async def get_admin_by_id(db: AsyncSession, admin_id: int) -> Optional[Admin]:
        result = await db.execute(select(Admin).where(Admin.id == admin_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_admin(db: AsyncSession, admin: Admin, update_data: dict) -> Admin:
        for key, value in update_data.items():
            setattr(admin, key, value)
        await db.commit()
        await db.refresh(admin)
        return admin

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_archive_status(db: AsyncSession, user: User, is_archived: bool) -> User:
        user.is_archived = is_archived
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_system_stats(db: AsyncSession) -> Dict[str, Any]:
        hr_count = await db.execute(select(func.count(HR.id)))
        candidate_count = await db.execute(select(func.count(Candidate.id)))
        job_count = await db.execute(select(func.count(JobDescription.id)))
        
        hr_total = hr_count.scalar()
        candidate_total = candidate_count.scalar()
        job_total = job_count.scalar()
        
        return {
            "total_users": hr_total + candidate_total,
            "hr_count": hr_total,
            "candidate_count": candidate_total,
            "job_count": job_total
        }
