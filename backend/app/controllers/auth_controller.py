from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db

from app.schemas.user_schema import Token, UserCreate, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from app.services import auth_service


class AuthController:
    def __init__(self):
        self.router = APIRouter(prefix="/auth", tags=["Authentication"])
        self.register_routes()

    def register_routes(self):
        self.router.post("/register")(self.register)
        self.router.post("/login", response_model=Token)(self.login)
        self.router.post("/forgot-password")(self.forgot_password)
        self.router.post("/reset-password")(self.reset_password)

    async def register(self, user: UserCreate, db: AsyncSession = Depends(get_db)):
        try:
            new_user = await auth_service.register_user(
                db, user.email, user.password, user.role, user.fullname
            )
            return {"message": "User registered successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def login(self, user: UserLogin, db: AsyncSession = Depends(get_db)):
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

    async def forgot_password(self, request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
        try:
            await auth_service.request_password_reset(db, request.email)
            return {"message": "If the email exists, a reset link has been sent."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def reset_password(self, request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
        try:
            await auth_service.reset_user_password(db, request.token, request.new_password)
            return {"message": "Password reset successfully."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


auth_controller = AuthController()
router = auth_controller.router
