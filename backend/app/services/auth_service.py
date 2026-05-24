from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordReset
from app.utils.auth import hash_password, verify_password, create_access_token
from app.services.notification_service import create_notification
from app.services.email_service import EmailService
from app.services.audit_service import record_activity
from app.repositories.auth_repository import AuthRepository
import uuid
from datetime import datetime, timedelta

class AuthService:
    async def register_user(self, db: AsyncSession, email: str, password: str, role: str, fullname: str = ""):
        email = email.strip().lower()

        # Check existence using raw text to avoid polymorphic JOIN issues
        if await AuthRepository.check_email_exists_raw(db, email):
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

        return await AuthRepository.create_user(db, role, common_fields)

    async def login_user(self, db: AsyncSession, email: str, password: str):
        email = email.strip().lower()

        # Query the base User table directly (no polymorphic JOIN) to avoid
        # missing subclass rows causing scalar_one_or_none() to return None.
        row = await AuthRepository.get_raw_user_by_email(db, email)
        if not row:
            raise Exception("Invalid credentials")

        # Load the proper ORM object based on role for downstream use
        role = row.role
        user = await AuthRepository.get_user_by_email_and_role(db, email, role)

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

        # Update online status - use raw SQL for orphaned users (no ORM row in subclass table)
        now = datetime.utcnow()
        if _is_fallback:
            await AuthRepository.update_online_status_raw(db, user.id, now)
        else:
            await AuthRepository.update_online_status_orm(db, user, now)

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

    async def request_password_reset(self, db: AsyncSession, email: str):
        email = email.strip().lower()
        # Check if user exists
        user = await AuthRepository.get_user_by_email(db, email)

        if not user:
            # For security reasons, don't reveal that the user doesn't exist
            return True

        # Generate token
        token = str(uuid.uuid4())
        expiry = datetime.utcnow() + timedelta(hours=1)

        # Save to DB
        reset_entry = PasswordReset(email=email, token=token, expires_at=expiry)
        await AuthRepository.create_password_reset(db, reset_entry)

        # Send email
        await EmailService.send_reset_password_email(email, token)

        return True

    async def reset_user_password(self, db: AsyncSession, token: str, new_password: str):
        # Find token
        reset_entry = await AuthRepository.get_password_reset_by_token(db, token)

        if not reset_entry or reset_entry.is_expired():
            raise Exception("Invalid or expired reset token")

        # Update user password
        user = await AuthRepository.get_user_by_email(db, reset_entry.email)

        if not user:
            raise Exception("User not found")

        await AuthRepository.update_user_password(db, user, hash_password(new_password))

        # Delete token
        await AuthRepository.delete_password_reset(db, reset_entry)

        return True


auth_service = AuthService()


async def register_user(db: AsyncSession, email: str, password: str, role: str, fullname: str = ""):
    return await auth_service.register_user(db, email, password, role, fullname)


async def login_user(db: AsyncSession, email: str, password: str):
    return await auth_service.login_user(db, email, password)


async def request_password_reset(db: AsyncSession, email: str):
    return await auth_service.request_password_reset(db, email)


async def reset_user_password(db: AsyncSession, token: str, new_password: str):
    return await auth_service.reset_user_password(db, token, new_password)
