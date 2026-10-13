from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from typing import Optional
import logging

from app.models.user import User
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.admin import Admin
from app.models.password_reset import PasswordReset
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def check_email_exists_raw(db: AsyncSession, email: str) -> bool:
    """Check if email exists (checks Redis cache first)."""
    cache_key = f"user:exists:{email.lower()}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return bool(cached)

    existing = await db.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": email}
    )
    exists = existing.fetchone() is not None
    await set_cache(cache_key, exists, ttl=300)
    return exists


async def create_user(db: AsyncSession, role: str, common_fields: dict) -> User:
    """Create a new user (Redis-first transaction)."""
    tx_payload = {
        "role": role,
        "email": common_fields.get("email"),
        "fullname": common_fields.get("fullname"),
    }
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="CREATE",
        payload=tx_payload,
    )
    try:
        if role == "CANDIDATE":
            new_user = Candidate(**common_fields)
        elif role == "HR":
            new_user = HR(**common_fields, company_name="")
        else:  # ADMIN
            new_user = Admin(**common_fields)

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_user.id, "email": new_user.email})

        # Cache user in Redis
        email_clean = new_user.email.lower()
        await set_cache(f"user:id:{new_user.id}", new_user, ttl=1800)
        await set_cache(f"user:email:{email_clean}", new_user, ttl=1800)
        await set_cache(f"user:email_role:{email_clean}:{role}", new_user, ttl=1800)
        await set_cache(f"user:exists:{email_clean}", True, ttl=1800)
        await clear_cache_pattern("users:all")
        await clear_cache_pattern("admin:stats")

        return new_user
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_user failed: {e}")
        raise


async def get_raw_user_by_email(db: AsyncSession, email: str):
    """Get raw user tuple by email (checks Redis cache first)."""
    email_clean = email.lower()
    cache_key = f"user:raw_email:{email_clean}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    raw = await db.execute(
        text("SELECT id, email, password, role, fullname, profile_image_url, is_archived, is_online FROM users WHERE email = :email"),
        {"email": email}
    )
    row = raw.fetchone()
    if row:
        await set_cache(cache_key, row, ttl=600)
    return row


async def get_user_by_email_and_role(db: AsyncSession, email: str, role: str) -> Optional[User]:
    """Get user by email and role (checks Redis cache first)."""
    email_clean = email.lower()
    cache_key = f"user:email_role:{email_clean}:{role}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    if role == "CANDIDATE":
        result = await db.execute(select(Candidate).where(Candidate.email == email))
    elif role == "HR":
        result = await db.execute(select(HR).where(HR.email == email))
    elif role == "ADMIN":
        result = await db.execute(select(Admin).where(Admin.email == email))
    else:
        result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
        await set_cache(f"user:id:{user.id}", user, ttl=1800)
        await set_cache(f"user:email:{email_clean}", user, ttl=1800)
    return user


async def update_online_status_raw(db: AsyncSession, user_id: int, now) -> None:
    """Update user online status in database and Redis."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="UPDATE_ONLINE_STATUS",
        payload={"user_id": user_id, "is_online": True},
    )
    try:
        await db.execute(
            text("UPDATE users SET is_online = true, last_active = :now WHERE id = :uid"),
            {"now": now, "uid": user_id}
        )
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"user_id": user_id})
        await delete_cache(f"user:id:{user_id}")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def update_online_status_orm(db: AsyncSession, user: User, now) -> None:
    """Update user online status via ORM."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="UPDATE_ONLINE_STATUS",
        payload={"user_id": user.id, "is_online": True},
    )
    try:
        user.is_online = True
        user.last_active = now
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"user_id": user.id})
        await delete_cache(f"user:id:{user.id}")
        if user.email:
            await delete_cache(f"user:email:{user.email.lower()}")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email (checks Redis cache first)."""
    email_clean = email.lower()
    cache_key = f"user:email:{email_clean}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
        await set_cache(f"user:id:{user.id}", user, ttl=1800)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID (checks Redis cache first)."""
    cache_key = f"user:id:{user_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
        if user.email:
            await set_cache(f"user:email:{user.email.lower()}", user, ttl=1800)
    return user


async def create_password_reset(db: AsyncSession, reset_entry: PasswordReset) -> PasswordReset:
    """Create password reset entry (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="password_reset",
        action="CREATE",
        payload={"email": reset_entry.email, "token": reset_entry.token},
    )
    try:
        db.add(reset_entry)
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"token": reset_entry.token})
        await set_cache(f"pwd_reset:{reset_entry.token}", reset_entry, ttl=3600)
        return reset_entry
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def get_password_reset_by_token(db: AsyncSession, token: str) -> Optional[PasswordReset]:
    """Get password reset by token (checks Redis cache first)."""
    cache_key = f"pwd_reset:{token}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
    reset_entry = result.scalar_one_or_none()
    if reset_entry:
        await set_cache(cache_key, reset_entry, ttl=3600)
    return reset_entry


async def update_user_password(db: AsyncSession, user: User, hashed_password: str) -> None:
    """Update user password (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="user",
        action="UPDATE_PASSWORD",
        payload={"user_id": user.id},
    )
    try:
        user.password = hashed_password
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"user_id": user.id})

        # Evict cached user credentials
        await delete_cache(f"user:id:{user.id}")
        if user.email:
            await delete_cache(f"user:email:{user.email.lower()}")
            await delete_cache(f"user:raw_email:{user.email.lower()}")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def delete_password_reset(db: AsyncSession, reset_entry: PasswordReset) -> None:
    """Delete password reset entry (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="password_reset",
        action="DELETE",
        payload={"token": reset_entry.token},
    )
    try:
        token = reset_entry.token
        await db.delete(reset_entry)
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"token": token})
        await delete_cache(f"pwd_reset:{token}")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


import sys
auth_repository = sys.modules[__name__]
AuthRepository = sys.modules[__name__]
