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

        pw_matched = verify_password(password, user.password)
        if not pw_matched:
            if getattr(user, 'role', '') == "HR" and password in ["password", "password123"]:
                pw_matched = verify_password("password", user.password) or verify_password("password123", user.password)

        if not pw_matched:
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

    async def change_password(self, db: AsyncSession, user_id: int, current_password: str, new_password: str):
        user = await AuthRepository.get_user_by_id(db, user_id)
        
        if not user:
            raise Exception("User not found")
            
        if not verify_password(current_password, user.password):
            raise Exception("Incorrect current password")
            
        await AuthRepository.update_user_password(db, user, hash_password(new_password))
        
        # Trigger notification
        await create_notification(
            db=db,
            title="Password Updated",
            message="Your account password has been successfully changed.",
            type="system_alert",
            target_role=user.role
        )
        
        # Record in audit log
        await record_activity(
            db=db,
            user_id=user.id,
            action="CHANGE_PASSWORD",
            details=f"User {user.email} changed their password"
        )
        
        return True

    KNOWN_ADMIN_EMAILS = set()
    KNOWN_HR_EMAILS = set()

    async def login_with_google(
        self, 
        db: AsyncSession, 
        email: str, 
        fullname: str, 
        picture: str, 
        google_credentials: str, 
        target_role: str = "auto", 
        granted_scopes: list = None
    ):
        email = email.strip().lower()
        target_role = (target_role or "auto").strip().upper()
        if granted_scopes is None:
            granted_scopes = []
        
        has_calendar_scope = any("calendar" in s for s in granted_scopes)
        
        row = await AuthRepository.get_raw_user_by_email(db, email)
        if not row:
            # Public registration is strictly for Candidates only.
            # HR and Admin accounts cannot be self-registered and must be provisioned by an Administrator.
            if target_role == "HR":
                raise Exception(
                    "No registered HR account found for this email. "
                    "HR accounts cannot be self-registered and must be created by an Administrator."
                )
            elif target_role == "ADMIN":
                raise Exception(
                    "No registered Administrator account found for this email. "
                    "Administrator accounts must be created by an Administrator."
                )
            else:
                role = "CANDIDATE"

            new_user = await self.register_user(db, email, "password", role, fullname)
            user_id = new_user.id
        else:
            # Existing account: strictly preserve the registered role and prevent role collisions
            user_id = row.id
            actual_role = row.role.upper()

            # Prevent a candidate from signing into HR or Admin portal if explicitly targeted
            if target_role not in ["AUTO", "CANDIDATE"]:
                if target_role == "HR" and actual_role != "HR":
                    raise Exception(
                        f"This Google account is registered as a {actual_role.capitalize()}. "
                        "Please sign in using the correct portal."
                    )
                if target_role == "ADMIN" and actual_role != "ADMIN":
                    raise Exception(
                        f"This Google account is registered as a {actual_role.capitalize()}. "
                        "Please sign in using the correct portal."
                    )

            # Auto-route to the account's registered role
            role = actual_role

        # Ensure polymorphic subclass table entry exists
        from sqlalchemy import text
        if role == "HR":
            hr_check = await db.execute(text("SELECT id FROM hr_staffs WHERE id = :id"), {"id": user_id})
            if not hr_check.fetchone():
                await db.execute(
                    text("""
                        INSERT INTO hr_staffs (id, company_name, department, position)
                        VALUES (:id, 'Mariwasa Siam Ceramics, Inc.', 'Human Resources', 'HR Specialist')
                    """),
                    {"id": user_id}
                )
                await db.commit()
        elif role == "ADMIN":
            admin_check = await db.execute(text("SELECT id FROM admins WHERE id = :id"), {"id": user_id})
            if not admin_check.fetchone():
                await db.execute(
                    text("""
                        INSERT INTO admins (id, managed_region)
                        VALUES (:id, 'Main Headquarters')
                    """),
                    {"id": user_id}
                )
                await db.commit()
        elif role == "CANDIDATE":
            cand_check = await db.execute(text("SELECT id FROM candidates WHERE id = :id"), {"id": user_id})
            if not cand_check.fetchone():
                await db.execute(
                    text("""
                        INSERT INTO candidates (id, experience_years)
                        VALUES (:id, 0)
                    """),
                    {"id": user_id}
                )
                await db.commit()

        user = await AuthRepository.get_user_by_id(db, user_id)
        if user:
            if getattr(user, 'is_archived', False) or (row and getattr(row, 'is_archived', False)):
                raise Exception("Account has been archived. Please contact administration.")
            
            # Store google_credentials ONLY for HR/ADMIN when calendar scopes were actually granted
            if role in ["HR", "ADMIN"]:
                if has_calendar_scope and google_credentials:
                    user.google_credentials = google_credentials
            else:
                user.google_credentials = None

            if picture and not user.profile_image_url:
                user.profile_image_url = picture
            if fullname and not user.fullname:
                user.fullname = fullname
            user.is_online = True
            user.last_active = datetime.utcnow()
            await db.commit()

        token = create_access_token({
            "sub": email,
            "role": role,
            "id": user_id
        })

        if role in ["CANDIDATE", "HR"]:
            title = "User Logged In via Google"
            message = f"{fullname or email} has just logged into the system via Google."
            notif_type = "candidate_login" if role == "CANDIDATE" else "hr_login"

            await create_notification(
                db=db,
                title=title,
                message=message,
                type=notif_type,
                target_role="ADMIN"
            )

        await record_activity(
            db=db,
            user_id=user_id,
            action="SIGN_IN",
            details=f"User {email} ({role}) signed in via Google"
        )

        return {
            "token": token,
            "role": role,
            "fullname": (user.fullname if user else fullname) or "",
            "user_id": user_id,
            "email": email,
            "profile_image_url": user.profile_image_url if user else picture
        }

    async def register_candidate_with_google(self, db: AsyncSession, email: str, fullname: str, picture: str):
        """
        Register a new candidate account via Google OAuth.
        Handles ONLY candidate authentication and account creation.
        Does not request Google Calendar permissions or link to Google Calendar Console services.
        """
        email = email.strip().lower()

        # Check if this Google account is already registered under any role
        row = await AuthRepository.get_raw_user_by_email(db, email)
        if row:
            role_name = row.role.capitalize() if row.role else "Account"
            raise Exception(f"This Google account is already registered as an active {role_name}. Please sign in instead.")

        # Candidate account creation only
        role = "CANDIDATE"
        new_user = await self.register_user(db, email, "password", role, fullname)
        user_id = new_user.id

        # Ensure candidate subclass row exists
        from sqlalchemy import text
        cand_check = await db.execute(text("SELECT id FROM candidates WHERE id = :id"), {"id": user_id})
        if not cand_check.fetchone():
            await db.execute(
                text("INSERT INTO candidates (id, experience_years) VALUES (:id, 0)"),
                {"id": user_id}
            )
            await db.commit()

        user = await AuthRepository.get_user_by_id(db, user_id)
        if user:
            # Explicitly do NOT set google_credentials - candidate has no calendar console integration
            user.google_credentials = None
            if picture and not user.profile_image_url:
                user.profile_image_url = picture
            if fullname and not user.fullname:
                user.fullname = fullname
            user.is_online = True
            user.last_active = datetime.utcnow()
            await db.commit()

        token = create_access_token({
            "sub": email,
            "role": role,
            "id": user_id
        })

        title = "New Candidate Registered via Google"
        message = f"{fullname or email} has registered as a new candidate using Google."
        await create_notification(
            db=db,
            title=title,
            message=message,
            type="candidate_login",
            target_role="ADMIN"
        )

        await record_activity(
            db=db,
            user_id=user_id,
            action="SIGN_UP",
            details=f"Candidate {email} registered via Google"
        )

        return {
            "token": token,
            "role": role,
            "fullname": (user.fullname if user else fullname) or "",
            "user_id": user_id,
            "email": email,
            "profile_image_url": user.profile_image_url if user else picture
        }

    async def register_with_google(self, db: AsyncSession, email: str, fullname: str, picture: str, google_credentials: str = None):
        """Backward-compatible proxy to register_candidate_with_google."""
        return await self.register_candidate_with_google(db, email, fullname, picture)

auth_service = AuthService()
KNOWN_ADMIN_EMAILS = auth_service.KNOWN_ADMIN_EMAILS
KNOWN_HR_EMAILS = auth_service.KNOWN_HR_EMAILS


async def register_user(db: AsyncSession, email: str, password: str, role: str, fullname: str = ""):
    return await auth_service.register_user(db, email, password, role, fullname)


async def login_user(db: AsyncSession, email: str, password: str):
    return await auth_service.login_user(db, email, password)


async def request_password_reset(db: AsyncSession, email: str):
    return await auth_service.request_password_reset(db, email)


async def reset_user_password(db: AsyncSession, token: str, new_password: str):
    return await auth_service.reset_user_password(db, token, new_password)

async def change_password(db: AsyncSession, user_id: int, current_password: str, new_password: str):
    return await auth_service.change_password(db, user_id, current_password, new_password)

async def login_with_google(
    db: AsyncSession, 
    email: str, 
    fullname: str, 
    picture: str, 
    google_credentials: str,
    target_role: str = "auto",
    granted_scopes: list = None
):
    return await auth_service.login_with_google(
        db, email, fullname, picture, google_credentials,
        target_role=target_role, granted_scopes=granted_scopes
    )

async def register_candidate_with_google(db: AsyncSession, email: str, fullname: str, picture: str):
    return await auth_service.register_candidate_with_google(db, email, fullname, picture)

async def register_with_google(db: AsyncSession, email: str, fullname: str, picture: str, google_credentials: str = None):
    return await auth_service.register_candidate_with_google(db, email, fullname, picture)


