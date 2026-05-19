from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.password_reset import PasswordReset
from app.utils.auth import hash_password, verify_password, create_access_token
from app.services.notification_service import create_notification
from app.services.email_service import EmailService
from app.services.audit_service import record_activity
import uuid
from datetime import datetime, timedelta

async def register_user(db: AsyncSession, email: str, password: str, role: str, fullname: str = ""):
    email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise Exception("Email already registered")

    if role not in ["CANDIDATE", "HR", "ADMIN"]:
        raise Exception("Invalid role")

    new_user = User(
        email=email,
        password=hash_password(password),
        role=role,
        fullname=fullname
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def login_user(db: AsyncSession, email: str, password: str):
    email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise Exception("Invalid credentials")

    if not verify_password(password, user.password):
        raise Exception("Invalid credentials")
    
    if user.is_archived:
        raise Exception("Account has been archived. Please contact administration.")

    # Update online status
    user.is_online = True
    user.last_active = datetime.utcnow()
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