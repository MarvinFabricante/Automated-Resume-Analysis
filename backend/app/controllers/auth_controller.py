from datetime import datetime
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db

from app.schemas.user_schema import (
    Token, UserCreate, UserLogin, ForgotPasswordRequest, 
    ResetPasswordRequest, ChangePasswordRequest, SetPasswordRequest,
    AccountDeleteRequest, ReactivateRequestOTP, ReactivateVerifyRequest,
    FreshStartRegisterRequest,
)
from app.utils.auth import get_current_user, get_optional_current_user, verify_password
from app.services import auth_service
from app.services.auth_service import DuplicateEmailError, DeactivatedAccountExistsError


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/check-email-status")
async def check_email_status(email: str, db: AsyncSession = Depends(get_db)):
    """Check whether an email is available, active, or belongs to a deactivated (reactivable) account."""
    return await auth_service.check_email_registration_status(db, email)


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        requested_role = (user.role or "CANDIDATE").strip().upper()
        if requested_role != "CANDIDATE":
            raise HTTPException(
                status_code=400,
                detail="Public registration is only available for Candidate accounts. HR and Admin accounts must be created by an Administrator."
            )
        await auth_service.register_user(
            db,
            user.email,
            user.password,
            "CANDIDATE",
            user.fullname,
            fresh_start=bool(getattr(user, "fresh_start", False)),
        )
        return {"message": "User registered successfully"}
    except HTTPException:
        raise
    except DeactivatedAccountExistsError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DEACTIVATED_ACCOUNT_EXISTS",
                "message": str(e),
                "can_reactivate": True,
                "can_fresh_start": True,
            },
        )
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        data = await auth_service.login_user(
            db, user.email, user.password
        )
        return {
            "access_token": data["token"],
            "token_type": "bearer",
            "role": data["role"],
            "fullname": data["fullname"],
            "user_id": data["user_id"],
            "profile_image_url": data.get("profile_image_url")
        }
    except DeactivatedAccountExistsError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ACCOUNT_DEACTIVATED",
                "message": str(e),
                "can_reactivate": True,
                "can_fresh_start": True,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/account/request-delete-otp")
async def request_delete_account_otp(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send a 6-digit OTP email to confirm applicant account deletion."""
    email = current_user.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return await auth_service.request_account_otp(db, email, purpose="delete_account")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/account/delete")
async def delete_own_account(
    payload: AccountDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Applicant-initiated account deletion: confirms via password or OTP, deactivates immediately,
    invalidates all tokens, withdraws active applications, cancels interviews, and notifies HR.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return await auth_service.request_account_deletion(
            db=db,
            user_id=int(user_id),
            password=payload.password,
            otp_code=payload.otp_code,
            reason=payload.reason,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate/request-otp")
async def request_reactivation_otp(
    payload: ReactivateRequestOTP,
    db: AsyncSession = Depends(get_db),
):
    """Request a 6-digit email OTP (valid 10 minutes) to reactivate a deactivated account."""
    try:
        return await auth_service.request_account_otp(db, payload.email, purpose="reactivate_account")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate/verify")
async def verify_reactivation_otp(
    payload: ReactivateVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify the 6-digit email OTP and restore the deactivated account (withdrawn apps stay withdrawn)."""
    try:
        return await auth_service.reactivate_account_with_otp(db, payload.email, payload.otp_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fresh-start")
async def register_fresh_start(
    payload: FreshStartRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Re-register with a fresh start when the email belongs to a deactivated (not-yet-purged) account.
    Immediately anonymizes the old account & records and creates a brand-new empty account.
    """
    try:
        await auth_service.register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            role="CANDIDATE",
            fullname=payload.fullname,
            fresh_start=True,
        )
        return {"message": "Fresh account registered successfully. No data from the previous account was restored."}
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        await auth_service.request_password_reset(db, request.email)
        return {"message": "If the email exists, a reset link has been sent."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        await auth_service.reset_user_password(db, request.token, request.new_password)
        return {"message": "Password reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token structure")
        
        await auth_service.change_password(
            db, 
            user_id, 
            request.current_password, 
            request.new_password
        )
        return {"message": "Password successfully updated."}
    except Exception as e:
        if str(e) == "Incorrect current password":
            raise HTTPException(status_code=400, detail="Incorrect current password. Please check your credentials and try again.")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/set-password")
async def set_password_endpoint(
    request: SetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not request.new_password or len(request.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters long.")
        await auth_service.set_password(db, user_id, request.new_password)
        return {"message": "Password successfully established."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/security-status")
async def get_security_status(
    user_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_optional_current_user)
):
    target_id = (current_user.get("id") if current_user else None) or user_id
    if not target_id:
        return {
            "email": "",
            "role": "",
            "fullname": "",
            "is_google_linked": False,
            "google_email": None,
            "has_calendar_sync": False,
            "has_custom_password": True,
            "last_active": None
        }
    
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id(db, target_id)
    if not user:
        return {
            "email": "",
            "role": "",
            "fullname": "",
            "is_google_linked": False,
            "google_email": None,
            "has_calendar_sync": False,
            "has_custom_password": True,
            "last_active": None
        }
        
    # If real Google OAuth credentials exist (has client_id), verify/auto-refresh them
    # so revoked or invalid_grant refresh tokens are detected immediately.
    linked_google_account = None
    if user.google_credentials:
        try:
            import json as _json
            c_dict = _json.loads(user.google_credentials) if isinstance(user.google_credentials, str) else {}
            if isinstance(c_dict, dict):
                linked_google_account = c_dict.get("account")
                if c_dict.get("client_id"):
                    from app.services.interview_service import _get_valid_credentials
                    fresh_user = await AuthRepository.get_user_by_id_fresh(db, target_id)
                    if fresh_user:
                        valid_creds = _get_valid_credentials(fresh_user)
                        await db.commit()
                        await AuthRepository.invalidate_user_cache(fresh_user)
                        user = fresh_user
                        if not valid_creds:
                            linked_google_account = None
        except Exception:
            pass

    # Check if Google OAuth token has expired (1 hour limit)
    is_google_expired = False
    if user.google_token_expiry:
        from datetime import datetime
        if user.google_token_expiry < datetime.utcnow():
            is_google_expired = True

    # Check if user has non-default password
    has_custom_password = True
    try:
        if verify_password("password", user.password):
            has_custom_password = False
    except Exception:
        pass

    is_google_linked = bool(
        getattr(user, "google_linked", False)
        or user.google_credentials
        or user.google_access_token
        or not has_custom_password
    )
    if not is_google_linked:
        try:
            from sqlalchemy import select
            from app.models.audit_log import AuditLog
            audit_res = await db.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user.id)
                .order_by(AuditLog.id.desc())
                .limit(20)
            )
            for log in audit_res.scalars().all():
                if log.action == "DISCONNECT_GOOGLE":
                    break
                if log.action in {"SIGN_IN", "SIGN_UP"} and "google" in (log.details or "").lower():
                    is_google_linked = True
                    break
        except Exception:
            pass

    has_refresh = bool(
        user.google_refresh_token
        or (user.google_credentials and "refresh_token" in user.google_credentials)
    )
    has_calendar = bool(
        user.google_credentials
        and "calendar" in user.google_credentials
        and (not is_google_expired or has_refresh)
    )

    return {
        "email": user.email,
        "role": user.role,
        "fullname": user.fullname,
        "is_google_linked": is_google_linked,
        "google_email": (linked_google_account or user.email) if is_google_linked else None,
        "has_calendar_sync": has_calendar,
        "google_token_expired": is_google_expired,
        "has_custom_password": has_custom_password,
        "last_active": user.last_active.isoformat() if user.last_active else None
    }


@router.post("/logout")
async def logout_user(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Log out user: marks online status offline and updates last_active.
    """
    if current_user and current_user.get("id"):
        from app.repositories.auth_repository import AuthRepository
        user = await AuthRepository.get_user_by_id(db, current_user.get("id"))
        if user:
            user.is_online = False
            user.last_active = datetime.utcnow()
            await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/google/disconnect")
async def disconnect_google(
    user_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_optional_current_user)
):
    target_id = (current_user.get("id") if current_user else None) or user_id
    if not target_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id(db, target_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.google_credentials = None
    user.google_access_token = None
    user.google_refresh_token = None
    user.google_token_expiry = None
    user.google_linked = False
    await db.commit()
    await AuthRepository.invalidate_user_cache(user)
    
    from app.services.audit_service import record_activity
    await record_activity(
        db=db,
        user_id=user.id,
        action="DISCONNECT_GOOGLE",
        details=f"User {user.email} unlinked their Google account"
    )
    
    return {"message": "Google account unlinked successfully."}



import os
import urllib.parse
from fastapi.responses import RedirectResponse
from app.utils.google_auth import (
    get_google_auth_url,
    get_candidate_google_auth_url,
    get_hr_google_auth_url,
    get_admin_google_auth_url,
    exchange_code_for_credentials,
)
from app.repositories.auth_repository import AuthRepository
import requests
from urllib.parse import urlencode


def _public_origin_from_request(request: Request, client_origin: str = None) -> str:
    # 1. Explicit client origin from query param or header
    if client_origin:
        clean = client_origin.strip().rstrip("/")
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean

    # 2. Check Referer header from frontend
    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urllib.parse.urlparse(referer)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    # 3. Check X-Forwarded-Host or Host
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    if forwarded_host:
        if forwarded_host.endswith(".trycloudflare.com"):
            forwarded_proto = "https"
        # If accessing directly from localhost or 127.0.0.1, prioritize that
        if "localhost" in forwarded_host or "127.0.0.1" in forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}"
        if ".trycloudflare.com" in forwarded_host:
            return f"https://{forwarded_host}"

    # 4. Fallback to configured PUBLIC_BASE_URL
    configured_origin = os.getenv("PUBLIC_BASE_URL") or os.getenv("APP_PUBLIC_URL") or os.getenv("FRONTEND_PUBLIC_URL")
    if configured_origin:
        return configured_origin.strip().rstrip("/")

    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"

    return "http://localhost:8080"


def _redirect_uri_for_origin(origin: str) -> str:
    clean = origin.rstrip("/")
    if clean.endswith(":8000"):
        return f"{clean}/auth/google/callback"
    return f"{clean}/api/auth/google/callback"

@router.get("/check-role")
async def check_email_role(email: str, db: AsyncSession = Depends(get_db)):
    """
    Check the role associated with an email to detect if it is registered as
    CANDIDATE, HR, or ADMIN. Helps frontend adapt the Google login portal
    and avoid login/calendar permission conflicts before OAuth begins.
    """
    clean_email = email.strip().lower()
    if not clean_email:
        return {"exists": False, "role": "CANDIDATE"}

    row = await AuthRepository.get_raw_user_by_email(db, clean_email)
    if row:
        detected_role = (row.role or "CANDIDATE").upper()
        return {
            "exists": True, 
            "role": detected_role,
            "fullname": row.fullname or "",
            "is_authorized_staff": detected_role in ["HR", "ADMIN"]
        }

    if clean_email in auth_service.KNOWN_HR_EMAILS:
        return {
            "exists": True,
            "role": "HR",
            "fullname": "",
            "is_authorized_staff": True
        }

    return {"exists": False, "role": "CANDIDATE", "is_authorized_staff": False}

@router.get("/google/candidate-register")
async def google_candidate_register(request: Request, origin: str = None):
    """
    Dedicated endpoint for candidate Google OAuth registration.
    Handles ONLY user authentication and account creation.
    Does NOT request Google Calendar permissions or touch Google Calendar Console services.
    """
    base_origin = _public_origin_from_request(request, origin)
    redirect_uri = _redirect_uri_for_origin(base_origin)
    url, state = get_candidate_google_auth_url(flow_type="candidate_register", redirect_uri=redirect_uri)
    return RedirectResponse(url)

@router.get("/google/register")
async def google_register(request: Request, origin: str = None):
    """Alias for candidate Google registration."""
    return await google_candidate_register(request, origin)

@router.get("/google/login")
async def google_login(
    request: Request,
    flow: str = "login",
    role: str = "auto",
    origin: str = None,
    user_id: int = None,
    return_to: str = None,
    login_hint: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Role-aware Google OAuth login and account-linking endpoint.
    - If flow is 'link_account': links Google credentials to an existing user session.
    - If role is 'auto' (default for universal login): requests basic profile scopes (no Google Calendar / Console restrictions),
      allowing ANY Google account (Candidate, HR, Admin) to sign in seamlessly.
      The user's actual role is automatically detected upon callback.
    - Candidate: requests ONLY basic profile scopes.
    - HR: requests Calendar scopes for authorized HR accounts configured in Google Console.
    - Admin: requests basic profile scopes.
    """
    base_origin = _public_origin_from_request(request, origin)
    redirect_uri = _redirect_uri_for_origin(base_origin)
    norm_role = (role or "auto").strip().lower()
    hint_clean = (login_hint or "").strip().lower() or None

    # If role is 'auto' but login_hint or user_id identifies an HR user, request HR calendar scopes directly
    if norm_role == "auto" and flow == "login":
        if hint_clean:
            row = await AuthRepository.get_raw_user_by_email(db, hint_clean)
            if (row and (row.role or "").upper() == "HR") or hint_clean in auth_service.KNOWN_HR_EMAILS:
                norm_role = "hr"
        elif user_id:
            u_obj = await AuthRepository.get_user_by_id(db, user_id)
            if u_obj and (u_obj.role or "").upper() == "HR":
                norm_role = "hr"
                if not hint_clean and u_obj.email and u_obj.email.endswith("@gmail.com"):
                    hint_clean = u_obj.email

    if flow in ["link_account", "link_google"]:
        if norm_role == "hr":
            url, state = get_hr_google_auth_url(
                flow_type="link_account",
                redirect_uri=redirect_uri,
                user_id=user_id,
                return_to=return_to,
                login_hint=hint_clean,
            )
        elif norm_role == "admin":
            url, state = get_admin_google_auth_url(flow_type="link_account", redirect_uri=redirect_uri, user_id=user_id)
        else:
            url, state = get_candidate_google_auth_url(flow_type="link_account", redirect_uri=redirect_uri, user_id=user_id)
    elif flow in ["candidate_register", "register"]:
        url, state = get_candidate_google_auth_url(flow_type="candidate_register", redirect_uri=redirect_uri, user_id=user_id)
    elif norm_role == "hr" or flow == "hr_login":
        url, state = get_hr_google_auth_url(
            flow_type="hr_login",
            redirect_uri=redirect_uri,
            user_id=user_id,
            return_to=return_to,
            login_hint=hint_clean,
        )
    elif norm_role == "admin" or flow == "admin_login":
        url, state = get_admin_google_auth_url(flow_type="admin_login", redirect_uri=redirect_uri, user_id=user_id)
    elif norm_role == "candidate":
        url, state = get_candidate_google_auth_url(flow_type="candidate_login", redirect_uri=redirect_uri, user_id=user_id)
    else:
        url, state = get_google_auth_url(role="auto", flow_type="login", redirect_uri=redirect_uri, user_id=user_id)

    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: str = "",
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    base_url = _public_origin_from_request(request)
    flow_type = "login"
    role_requested = "auto"
    try:
        if error or not code:
            from app.utils.google_auth import _pop_pending_flow
            pending = _pop_pending_flow(state) if state else {}
            if pending.get("flow_type") == "hr_calendar_upgrade" and pending.get("user_id"):
                user = await AuthRepository.get_user_by_id_fresh(db, int(pending["user_id"]))
                if user:
                    from app.utils.auth import create_access_token
                    flow_redirect = pending.get("redirect_uri")
                    if flow_redirect:
                        parsed = urllib.parse.urlparse(flow_redirect)
                        if parsed.scheme and parsed.netloc:
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                    token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
                    params = {
                        "token": token,
                        "role": user.role,
                        "fullname": user.fullname or "",
                        "user_id": user.id,
                        "email": user.email,
                        "picture": user.profile_image_url or "",
                    }
                    if pending.get("return_to"):
                        params["return_to"] = pending["return_to"]
                    return RedirectResponse(f"{base_url}/auth/callback?{urlencode(params)}")
            raise Exception(error or "Google authentication was canceled or missing authorization code.")

        creds, flow_info = exchange_code_for_credentials(code, state)
        flow_redirect = None
        if isinstance(flow_info, dict):
            flow_type = flow_info.get("flow_type", "login")
            role_requested = flow_info.get("role", "auto")
            flow_redirect = flow_info.get("redirect_uri")
            if flow_redirect:
                try:
                    parsed = urllib.parse.urlparse(flow_redirect)
                    if parsed.scheme and parsed.netloc:
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                except Exception:
                    pass
        else:
            flow_type = flow_info
            role_requested = "auto"
        
        # Get user info from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {creds.token}'}
        )
        user_info = user_info_response.json()
        email = user_info.get("email")
        fullname = user_info.get("name")
        picture = user_info.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="Failed to retrieve email from Google")
        
        creds_json = creds.to_json() if creds else ""
        granted_scopes = getattr(creds, 'scopes', [])

        # Google OAuth credential tokens strictly expire in 1 hour
        google_expiry = None
        if hasattr(creds, 'expiry') and creds.expiry:
            google_expiry = creds.expiry
            if hasattr(google_expiry, 'tzinfo') and google_expiry.tzinfo is not None:
                from datetime import timezone
                google_expiry = google_expiry.astimezone(timezone.utc).replace(tzinfo=None)
        if not google_expiry:
            from datetime import datetime, timedelta
            google_expiry = datetime.utcnow() + timedelta(hours=1)

        google_access_tok = getattr(creds, 'token', None)
        google_refresh_tok = getattr(creds, 'refresh_token', None)

        if flow_type in ["link_account", "link_google"]:
            target_user_id = flow_info.get("user_id") if isinstance(flow_info, dict) else None
            return_to = flow_info.get("return_to") if isinstance(flow_info, dict) else None
            user = None
            if target_user_id:
                try:
                    user = await AuthRepository.get_user_by_id_fresh(db, int(target_user_id))
                except Exception:
                    pass
            if not user and email:
                user = await AuthRepository.get_user_by_email_fresh(db, email)
                
            if user:
                merged_creds = creds_json
                effective_refresh = google_refresh_tok or user.google_refresh_token
                try:
                    import json as _json
                    c_dict = _json.loads(creds_json)
                    if isinstance(c_dict, dict):
                        if effective_refresh and not c_dict.get("refresh_token"):
                            c_dict["refresh_token"] = effective_refresh
                        if email:
                            c_dict["account"] = email
                        merged_creds = _json.dumps(c_dict)
                except Exception:
                    pass
                user.google_credentials = merged_creds
                user.google_access_token = google_access_tok
                if effective_refresh:
                    user.google_refresh_token = effective_refresh
                user.google_token_expiry = google_expiry
                user.google_linked = True
                if picture and not user.profile_image_url:
                    user.profile_image_url = picture
                await db.commit()
                await AuthRepository.invalidate_user_cache(user)
                try:
                    from app.services.google_calendar_service import invalidate_google_calendar_cache
                    invalidate_google_calendar_cache(merged_creds)
                except Exception:
                    pass
                
                if return_to and str(return_to).startswith("/"):
                    sep = "&" if "?" in str(return_to) else "?"
                    return RedirectResponse(f"{base_url}{return_to}{sep}google_linked=success")
                role_path = (user.role or "candidate").lower()
                return RedirectResponse(f"{base_url}/{role_path}/settings?tab=security&google_linked=success")
            else:
                role_path = (role_requested or "candidate").lower()
                return RedirectResponse(f"{base_url}/{role_path}/settings?tab=security&google_linked=not_found")

        if flow_type in ["candidate_register", "register"]:
            # Pure user authentication and account creation for Candidate - no Google Calendar logic or linking
            data = await auth_service.register_candidate_with_google(db, email, fullname, picture)
        else:
            data = await auth_service.login_with_google(
                db=db,
                email=email,
                fullname=fullname,
                picture=picture,
                google_credentials=creds_json,
                target_role=role_requested,
                granted_scopes=granted_scopes,
                google_access_token=google_access_tok,
                google_refresh_token=google_refresh_tok,
                google_token_expiry=google_expiry
            )

        return_to = flow_info.get("return_to") if isinstance(flow_info, dict) else None

        # When an HR user logs in via universal Google Sign-In without Calendar permissions yet,
        # automatically chain the HR Calendar authorization step so Google Calendar is connected
        # to the HR module right away.
        if (
            flow_type == "login"
            and (data.get("role") or "").upper() == "HR"
            and not data.get("has_calendar_sync")
        ):
            cal_redirect = flow_redirect or _redirect_uri_for_origin(base_url)
            cal_url, _ = get_hr_google_auth_url(
                flow_type="hr_calendar_upgrade",
                redirect_uri=cal_redirect,
                user_id=data["user_id"],
                return_to=return_to,
                login_hint=email,
            )
            return RedirectResponse(cal_url)
        
        # Redirect to frontend with token, role, email, and user details
        params = {
            "token": data["token"],
            "role": data["role"],
            "fullname": data["fullname"],
            "user_id": data["user_id"],
            "email": email,
            "picture": data.get("profile_image_url", "")
        }
        if return_to:
            params["return_to"] = return_to
        frontend_url = f"{base_url}/auth/callback?{urlencode(params)}"
        return RedirectResponse(frontend_url)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = urllib.parse.quote(str(e))
        target_path = "/register" if flow_type in ["candidate_register", "register"] else "/login"
        return RedirectResponse(f"{base_url}{target_path}?error={error_msg}")
