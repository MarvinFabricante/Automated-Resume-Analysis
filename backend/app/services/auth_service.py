from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.admin import Admin
from app.models.password_reset import PasswordReset
from app.utils.auth import hash_password, verify_password, create_access_token
from app.services.notification_service import create_notification
from app.services.email_service import EmailService
from app.services.audit_service import record_activity
import uuid
from datetime import datetime, timedelta

async def register_user(db: AsyncSession, email: str, password: str, role: str, fullname: str = ""):
    email = email.strip().lower()

    # Check existence using raw text to avoid polymorphic JOIN issues
    from sqlalchemy import text
    existing = await db.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": email}
    )
    if existing.fetchone():
        raise Exception("Email already registered")

    if role not in ["CANDIDATE", "HR", "ADMIN"]:
        raise Exception("Invalid role")

    # Create the correct subclass so both users + subclass table rows are inserted
    common_fields = dict(
        email=email,
        password=hash_password(password),
        role=role,
        fullname=fullname,
    )

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


async def login_user(db: AsyncSession, email: str, password: str):
    email = email.strip().lower()

    # Query the base User table directly (no polymorphic JOIN) to avoid
    # missing subclass rows causing scalar_one_or_none() to return None.
    from sqlalchemy import text
    raw = await db.execute(
        text("SELECT id, email, password, role, fullname, profile_image_url, is_archived, is_online FROM users WHERE email = :email"),
        {"email": email}
    )
    row = raw.fetchone()
    if not row:
        raise Exception("Invalid credentials")

    # Load the proper ORM object based on role for downstream use
    role = row.role
    if role == "CANDIDATE":
        result = await db.execute(select(Candidate).where(Candidate.email == email))
        user = result.scalar_one_or_none()
    elif role == "HR":
        result = await db.execute(select(HR).where(HR.email == email))
        user = result.scalar_one_or_none()
    elif role == "ADMIN":
        result = await db.execute(select(Admin).where(Admin.email == email))
        user = result.scalar_one_or_none()
    else:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    # Fallback: use raw row data if subclass row is missing (orphaned user)
    _is_fallback = user is None
    if _is_fallback:
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

    if not user:
        raise Exception("Invalid credentials")

    if not verify_password(password, user.password):
        raise Exception("Invalid credentials")

    if user.is_archived:
        raise Exception("Account has been archived. Please contact administration.")

    # Update online status — use raw SQL for orphaned users (no ORM row in subclass table)
    now = datetime.utcnow()
    if _is_fallback:
        await db.execute(
            text("UPDATE users SET is_online = true, last_active = :now WHERE id = :uid"),
            {"now": now, "uid": user.id}
        )
        await db.commit()
    else:
        user.is_online = True
        user.last_active = now
        await db.commit()

    token = create_access_token({
        "sub": user.email,
        "role": user.role,
        "id": user.id
    })

    # Trigger notification for logins (Candidate and HR)
    if user.role in ["CANDIDATE", "HR"]:
        title = "User Logged In"
        message = f"{user.fullname or user.email} has just logged into the system."
        notif_type = "candidate_login" if user.role == "CANDIDATE" else "hr_login"
        
        await create_notification(
            db=db,
            title=title,
            message=message,
            type=notif_type,
            target_role="ADMIN"
        )
        
        # Record in audit log
        await record_activity(
            db=db,
            user_id=user.id,
            action="SIGN_IN",
            details=f"User {user.email} signed in"
        )

    return {"token": token, "role": user.role, "fullname": user.fullname, "user_id": user.id, "profile_image_url": user.profile_image_url}

async def request_password_reset(db: AsyncSession, email: str):
    email = email.strip().lower()
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # For security reasons, don't reveal that the user doesn't exist
        return True
    
    # Generate token
    token = str(uuid.uuid4())
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Save to DB
    reset_entry = PasswordReset(email=email, token=token, expires_at=expiry)
    db.add(reset_entry)
    await db.commit()
    
    # Send email
    await EmailService.send_reset_password_email(email, token)
    
    return True

async def reset_user_password(db: AsyncSession, token: str, new_password: str):
    # Find token
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
    reset_entry = result.scalar_one_or_none()
    
    if not reset_entry or reset_entry.is_expired():
        raise Exception("Invalid or expired reset token")
    
    # Update user password
    result = await db.execute(select(User).where(User.email == reset_entry.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise Exception("User not found")
    
    user.password = hash_password(new_password)
    
    # Delete token
    await db.delete(reset_entry)
    await db.commit()
    
    return True