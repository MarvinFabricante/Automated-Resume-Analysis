from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db

from app.schemas.user_schema import Token, UserCreate, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from app.utils.auth import get_current_user
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_user = await auth_service.register_user(
            db, user.email, user.password, user.role, user.fullname
        )
        return {"message": "User registered successfully"}
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
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

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
            raise HTTPException(status_code=401, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))



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
        return {
            "exists": True, 
            "role": (row.role or "CANDIDATE").upper(),
            "fullname": row.fullname or ""
        }

    # If not registered yet in DB, check pre-authorized staff lists
    if clean_email in auth_service.KNOWN_ADMIN_EMAILS:
        return {"exists": False, "role": "ADMIN", "is_authorized_staff": True}
    elif clean_email in auth_service.KNOWN_HR_EMAILS:
        return {"exists": False, "role": "HR", "is_authorized_staff": True}
    
    return {"exists": False, "role": "CANDIDATE", "is_authorized_staff": False}

@router.get("/google/candidate-register")
async def google_candidate_register():
    """
    Dedicated endpoint for candidate Google OAuth registration.
    Handles ONLY user authentication and account creation.
    Does NOT request Google Calendar permissions or touch Google Calendar Console services.
    """
    url, state = get_candidate_google_auth_url(flow_type="candidate_register")
    return RedirectResponse(url)

@router.get("/google/register")
async def google_register():
    """Alias for candidate Google registration."""
    return await google_candidate_register()

@router.get("/google/login")
async def google_login(flow: str = "login", role: str = "candidate"):
    """
    Role-aware Google OAuth login endpoint.
    - Candidate: requests ONLY basic profile scopes (no Google Calendar / Console restrictions).
    - HR: requests Calendar scopes for authorized HR accounts configured in Google Console.
    - Admin: requests basic profile scopes for System Administrators.
    """
    norm_role = (role or "candidate").strip().lower()
    if flow in ["candidate_register", "register"]:
        url, state = get_candidate_google_auth_url(flow_type="candidate_register")
    elif norm_role == "hr" or flow == "hr_login":
        url, state = get_hr_google_auth_url(flow_type="hr_login")
    elif norm_role == "admin" or flow == "admin_login":
        url, state = get_admin_google_auth_url(flow_type="admin_login")
    else:
        url, state = get_candidate_google_auth_url(flow_type="candidate_login")
    
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173").rstrip("/")
    flow_type = "login"
    role_requested = "candidate"
    try:
        creds, flow_info = exchange_code_for_credentials(code, state)
        if isinstance(flow_info, dict):
            flow_type = flow_info.get("flow_type", "login")
            role_requested = flow_info.get("role", "candidate")
        else:
            flow_type = flow_info
            role_requested = "candidate"
        
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
                granted_scopes=granted_scopes
            )
        
        # Redirect to frontend with token, role, email, and user details
        params = {
            "token": data["token"],
            "role": data["role"],
            "fullname": data["fullname"],
            "user_id": data["user_id"],
            "email": email,
            "picture": data.get("profile_image_url", "")
        }
        frontend_url = f"{base_url}/auth/callback?{urllib.parse.urlencode(params)}"
        return RedirectResponse(frontend_url)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = urllib.parse.quote(str(e))
        target_path = "/register" if flow_type in ["candidate_register", "register"] else "/login"
        return RedirectResponse(f"{base_url}{target_path}?error={error_msg}")



