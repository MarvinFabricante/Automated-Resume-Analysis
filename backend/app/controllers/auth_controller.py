from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db

from app.schemas.user_schema import Token, UserCreate, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from app.utils.auth import get_current_user
from app.services import auth_service
from app.controllers.base_controller import BaseController, Get, Post


class AuthController(BaseController):
    prefix = "/auth"
    tags = ["Authentication"]

    @Post("/register")
    async def register(self, user: UserCreate, db: AsyncSession = Depends(get_db)):
        try:
            new_user = await auth_service.register_user(
                db, user.email, user.password, user.role, user.fullname
            )
            return {"message": "User registered successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @Post("/login", response_model=Token)
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

    @Post("/forgot-password")
    async def forgot_password(self, request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
        try:
            await auth_service.request_password_reset(db, request.email)
            return {"message": "If the email exists, a reset link has been sent."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @Post("/reset-password")
    async def reset_password(self, request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
        try:
            await auth_service.reset_user_password(db, request.token, request.new_password)
            return {"message": "Password reset successfully."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @Post("/change-password")
    async def change_password(
        self, 
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


auth_controller = AuthController()
router = auth_controller.router
