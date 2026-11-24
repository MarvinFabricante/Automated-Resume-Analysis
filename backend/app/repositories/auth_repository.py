from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, func
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
    """Check if email exists directly in the database and keep Redis cache synchronized."""
    email_clean = (email or "").strip().lower()
    if not email_clean:
        return False

    existing = await db.execute(
        text("SELECT id FROM users WHERE LOWER(email) = :email"), {"email": email_clean}
    )
    exists = existing.fetchone() is not None
    cache_key = f"user:exists:{email_clean}"
    if exists:
        await set_cache(cache_key, True, ttl=300)
    else:
        await delete_cache(cache_key)
        await delete_cache(f"user:email:{email_clean}")
        await delete_cache(f"user:raw_email:{email_clean}")
        await clear_cache_pattern(f"user:email_role:{email_clean}")
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
    """Get raw user row by email directly from the database (case-insensitive)."""
    email_clean = (email or "").strip().lower()
    if not email_clean:
        return None

    raw = await db.execute(
        text(
            "SELECT id, email, password, role, fullname, profile_image_url, is_archived, is_online, "
            "is_deactivated, deactivated_at, token_version, is_anonymized "
            "FROM users WHERE LOWER(email) = :email"
        ),
        {"email": email_clean}
    )
    row = raw.fetchone()
    if not row:
        await delete_cache(f"user:exists:{email_clean}")
        await delete_cache(f"user:email:{email_clean}")
        await delete_cache(f"user:raw_email:{email_clean}")
        await clear_cache_pattern(f"user:email_role:{email_clean}")
    return row


async def get_user_by_email_and_role(db: AsyncSession, email: str, role: str) -> Optional[User]:
    """Get user by email and role (queries DB directly to ensure live session-attached ORM instance)."""
    email_clean = (email or "").strip().lower()
    cache_key = f"user:email_role:{email_clean}:{role}"

    if role == "CANDIDATE":
        result = await db.execute(select(Candidate).where(func.lower(Candidate.email) == email_clean))
    elif role == "HR":
        result = await db.execute(select(HR).where(func.lower(HR.email) == email_clean))
    elif role == "ADMIN":
        result = await db.execute(select(Admin).where(func.lower(Admin.email) == email_clean))
    else:
        result = await db.execute(select(User).where(func.lower(User.email) == email_clean))
    user = result.scalar_one_or_none()
    if user:
        await set_cache(cache_key, user, ttl=1800)
        await set_cache(f"user:id:{user.id}", user, ttl=1800)
        await set_cache(f"user:email:{email_clean}", user, ttl=1800)
    else:
        await delete_cache(cache_key)
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
        await db.execute(
            text("UPDATE users SET is_online = true, last_active = :now WHERE id = :uid"),
            {"now": now, "uid": user.id}
        )
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"user_id": user.id})
        await invalidate_user_cache(user)
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email (case-insensitive)."""
    email_clean = (email or "").strip().lower()
    cache_key = f"user:email:{email_clean}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(func.lower(User.email) == email_clean))
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


async def get_user_by_id_fresh(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID directly from the DB (session-attached, bypasses Redis cache).
    Use this whenever the returned user will be modified and committed."""
    result = await db.execute(
        select(User).where(User.id == user_id).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_user_by_email_fresh(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email directly from the DB (session-attached, bypasses Redis cache)."""
    email_clean = (email or "").strip().lower()
    result = await db.execute(
        select(User).where(func.lower(User.email) == email_clean).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def invalidate_user_cache(user=None, *, user_id: Optional[int] = None, email: Optional[str] = None) -> None:
    """Drop all cached copies of a user so subsequent reads see committed changes."""
    uid = user_id or (getattr(user, "id", None) if user else None)
    uemail = email or (getattr(user, "email", None) if user else None)
    try:
        if uid is not None:
            await delete_cache(f"user:id:{uid}")
        if uemail:
            email_clean = uemail.strip().lower()
            await delete_cache(f"user:email:{email_clean}")
            await delete_cache(f"user:raw_email:{email_clean}")
            await delete_cache(f"user:exists:{email_clean}")
            await clear_cache_pattern(f"user:email_role:{email_clean}")
    except Exception as e:
        logger.warning(f"Could not invalidate user cache: {e}")


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
        await invalidate_user_cache(user)
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
