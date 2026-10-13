from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
import logging

from app.models.user import User
from app.models.admin import Admin
from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.job_description import JobDescription
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def get_all_users(db: AsyncSession) -> List[User]:
    """Get all users (checks Redis cache first)."""
    cache_key = "users:all:list"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User))
    users = result.scalars().all()
    await set_cache(cache_key, users, ttl=600)
    return users


async def create_admin(db: AsyncSession, admin_data: dict) -> Admin:
    """Create admin user (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="admin",
        action="CREATE",
        payload=admin_data,
    )
    try:
        new_admin = Admin(**admin_data)
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_admin.id})

        await set_cache(f"admin:id:{new_admin.id}", new_admin, ttl=1800)
        await clear_cache_pattern("users:all")
        await clear_cache_pattern("admin:stats")

        return new_admin
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_admin failed: {e}")
        raise


async def get_admin_by_id(db: AsyncSession, admin_id: int) -> Optional[Admin]:
    """Get admin by ID (checks Redis cache first)."""
    cache_key = f"admin:id:{admin_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if admin:
        await set_cache(cache_key, admin, ttl=1800)
    return admin


async def update_admin(db: AsyncSession, admin: Admin, update_data: dict) -> Admin:
    """Update admin (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="admin",
        action="UPDATE",
        payload={"id": admin.id, **update_data},
    )
    try:
        for key, value in update_data.items():
            setattr(admin, key, value)
        await db.commit()
        await db.refresh(admin)

        await redis_tx_manager.commit_transaction(tx_id, {"id": admin.id})

        await delete_cache(f"admin:id:{admin.id}")
        await delete_cache(f"user:id:{admin.id}")
        await clear_cache_pattern("users:all")

        return admin
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_admin failed: {e}")
        raise


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID with raw fallback (checks Redis cache first)."""
    cache_key = f"user:id:{user_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

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

    if user:
        await set_cache(cache_key, user, ttl=1800)
    return user


async def update_user_archive_status(db: AsyncSession, user: User, is_archived: bool) -> User:
    """Update user archive status (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="UPDATE_ARCHIVE_STATUS",
        payload={"id": user.id, "is_archived": is_archived},
    )
    try:
        await db.execute(
            text("UPDATE users SET is_archived = :is_archived WHERE id = :uid"),
            {"is_archived": is_archived, "uid": user.id}
        )
        await db.commit()
        user.is_archived = is_archived

        await redis_tx_manager.commit_transaction(tx_id, {"id": user.id, "is_archived": is_archived})

        await delete_cache(f"user:id:{user.id}")
        await clear_cache_pattern("users:all")
        await clear_cache_pattern("admin:stats")

        return user
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_user_archive_status failed: {e}")
        raise


async def update_user(db: AsyncSession, user: User, update_data: dict) -> User:
    """Update user fields (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="UPDATE",
        payload={"id": user.id, **update_data},
    )
    try:
        for key, value in update_data.items():
            setattr(user, key, value)
        await db.commit()
        await db.refresh(user)

        await redis_tx_manager.commit_transaction(tx_id, {"id": user.id})

        await delete_cache(f"user:id:{user.id}")
        if user.email:
            await delete_cache(f"user:email:{user.email.lower()}")
        await clear_cache_pattern("users:all")

        return user
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_user failed: {e}")
        raise


async def delete_user(db: AsyncSession, user: User) -> bool:
    """Delete user (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="DELETE",
        payload={"id": user.id, "email": user.email},
    )
    try:
        uid = user.id
        email = user.email
        await db.delete(user)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"deleted_id": uid})

        await delete_cache(f"user:id:{uid}")
        if email:
            await delete_cache(f"user:email:{email.lower()}")
        await clear_cache_pattern("users:all")
        await clear_cache_pattern("admin:stats")

        return True
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] delete_user failed: {e}")
        raise


async def get_system_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get system stats (checks Redis cache first)."""
    cache_key = "admin:stats:summary"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    hr_count = await db.execute(select(func.count(HR.id)))
    candidate_count = await db.execute(select(func.count(Candidate.id)))
    job_count = await db.execute(select(func.count(JobDescription.id)))
    
    hr_total = hr_count.scalar() or 0
    candidate_total = candidate_count.scalar() or 0
    job_total = job_count.scalar() or 0
    
    stats = {
        "total_users": hr_total + candidate_total,
        "hr_count": hr_total,
        "candidate_count": candidate_total,
        "job_count": job_total
    }
    await set_cache(cache_key, stats, ttl=300)
    return stats


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
