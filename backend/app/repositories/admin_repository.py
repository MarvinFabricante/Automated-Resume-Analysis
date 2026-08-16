from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from app.models.user import User
from app.models.admin import Admin
from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.job_description import JobDescription


async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()


async def create_admin(db: AsyncSession, admin_data: dict) -> Admin:
    new_admin = Admin(**admin_data)
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin


async def get_admin_by_id(db: AsyncSession, admin_id: int) -> Optional[Admin]:
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    return result.scalar_one_or_none()


async def update_admin(db: AsyncSession, admin: Admin, update_data: dict) -> Admin:
    for key, value in update_data.items():
        setattr(admin, key, value)
    await db.commit()
    await db.refresh(admin)
    return admin


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raw = await db.execute(
            text("SELECT id, email, password, role, fullname, profile_image_url, is_archived, is_online FROM users WHERE id = :id"),
            {"id": user_id}
        )
        row = raw.fetchone()
        if row:
            class _FallbackUser:
                pass
            user = _FallbackUser()
            user.id = row.id
            user.email = row.email
            user.password = row.password
            user.role = row.role
            user.fullname = row.fullname
            user.profile_image_url = row.profile_image_url
            user.is_archived = row.is_archived
            user.is_online = row.is_online
    return user


async def update_user_archive_status(db: AsyncSession, user: User, is_archived: bool) -> User:
    await db.execute(
        text("UPDATE users SET is_archived = :is_archived WHERE id = :uid"),
        {"is_archived": is_archived, "uid": user.id}
    )
    await db.commit()
    user.is_archived = is_archived
    return user


async def update_user(db: AsyncSession, user: User, update_data: dict) -> User:
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: User) -> bool:
    await db.delete(user)
    await db.commit()
    return True


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


class AdminRepository:
    get_all_users = staticmethod(get_all_users)
    create_admin = staticmethod(create_admin)
    get_admin_by_id = staticmethod(get_admin_by_id)
    update_admin = staticmethod(update_admin)
    get_user_by_id = staticmethod(get_user_by_id)
    update_user_archive_status = staticmethod(update_user_archive_status)
    update_user = staticmethod(update_user)
    delete_user = staticmethod(delete_user)
    get_system_stats = staticmethod(get_system_stats)
