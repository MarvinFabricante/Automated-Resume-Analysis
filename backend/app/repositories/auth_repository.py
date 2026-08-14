from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from typing import Optional
from app.models.user import User
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.admin import Admin
from app.models.password_reset import PasswordReset


async def check_email_exists_raw(db: AsyncSession, email: str) -> bool:
    existing = await db.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": email}
    )
    return existing.fetchone() is not None


async def create_user(db: AsyncSession, role: str, common_fields: dict) -> User:
    if role == "CANDIDATE":
        new_user = Candidate(**common_fields)
    elif role == "HR":
        new_user = HR(**common_fields, company_name="")
    else:  # ADMIN
        new_user = Admin(**common_fields)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_raw_user_by_email(db: AsyncSession, email: str):
    raw = await db.execute(
        text("SELECT id, email, password, role, fullname, profile_image_url, is_archived, is_online FROM users WHERE email = :email"),
        {"email": email}
    )
    return raw.fetchone()


async def get_user_by_email_and_role(db: AsyncSession, email: str, role: str) -> Optional[User]:
    if role == "CANDIDATE":
        result = await db.execute(select(Candidate).where(Candidate.email == email))
    elif role == "HR":
        result = await db.execute(select(HR).where(HR.email == email))
    elif role == "ADMIN":
        result = await db.execute(select(Admin).where(Admin.email == email))
    else:
        result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def update_online_status_raw(db: AsyncSession, user_id: int, now) -> None:
    await db.execute(
        text("UPDATE users SET is_online = true, last_active = :now WHERE id = :uid"),
        {"now": now, "uid": user_id}
    )
    await db.commit()


async def update_online_status_orm(db: AsyncSession, user: User, now) -> None:
    user.is_online = True
    user.last_active = now
    await db.commit()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_password_reset(db: AsyncSession, reset_entry: PasswordReset) -> PasswordReset:
    db.add(reset_entry)
    await db.commit()
    return reset_entry


async def get_password_reset_by_token(db: AsyncSession, token: str) -> Optional[PasswordReset]:
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
    return result.scalar_one_or_none()


async def update_user_password(db: AsyncSession, user: User, hashed_password: str) -> None:
    user.password = hashed_password
    await db.commit()


async def delete_password_reset(db: AsyncSession, reset_entry: PasswordReset) -> None:
    await db.delete(reset_entry)
    await db.commit()


class AuthRepository:
    check_email_exists_raw = staticmethod(check_email_exists_raw)
    create_user = staticmethod(create_user)
    get_raw_user_by_email = staticmethod(get_raw_user_by_email)
    get_user_by_email_and_role = staticmethod(get_user_by_email_and_role)
    update_online_status_raw = staticmethod(update_online_status_raw)
    update_online_status_orm = staticmethod(update_online_status_orm)
    get_user_by_email = staticmethod(get_user_by_email)
    get_user_by_id = staticmethod(get_user_by_id)
    create_password_reset = staticmethod(create_password_reset)
    get_password_reset_by_token = staticmethod(get_password_reset_by_token)
    update_user_password = staticmethod(update_user_password)
    delete_password_reset = staticmethod(delete_password_reset)
