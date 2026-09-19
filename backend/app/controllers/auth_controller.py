import os

from fastapi import APIRouter, Depends, HTTPException, Request
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



from fastapi.responses import RedirectResponse
from app.utils.google_auth import get_google_auth_url, exchange_code_for_credentials
import requests
from urllib.parse import urlencode


def _public_origin_from_request(request: Request) -> str:
    configured_origin = os.getenv("PUBLIC_BASE_URL") or os.getenv("APP_PUBLIC_URL") or os.getenv("FRONTEND_PUBLIC_URL")
    if configured_origin:
        return configured_origin.strip().rstrip("/")

    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    if host.endswith(".trycloudflare.com"):
        proto = "https"
    return f"{proto}://{host}"

@router.get("/google/login")
async def google_login(request: Request):
    public_origin = _public_origin_from_request(request)
    redirect_uri = f"{public_origin}/api/auth/google/callback"
    url, state = get_google_auth_url(redirect_uri=redirect_uri, frontend_origin=public_origin)
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    try:
        creds, frontend_origin = exchange_code_for_credentials(code, state)
        
        # Get user info
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
        
        # We need to find or create the user and update google_credentials
        # Let's add auth_service method for google login
        data = await auth_service.login_with_google(db, email, fullname, picture, creds.to_json())
        
        # Redirect to frontend with token
        frontend_origin = frontend_origin or _public_origin_from_request(request)
        query = urlencode({
            "token": data["token"],
            "role": data["role"],
            "fullname": data["fullname"],
            "user_id": data["user_id"],
            "picture": data.get("profile_image_url", ""),
        })
        frontend_url = f"{frontend_origin}/auth/callback?{query}"
        return RedirectResponse(frontend_url)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
