from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "CANDIDATE"
    fullname: str
    fresh_start: Optional[bool] = False
    verification_token: Optional[str] = None
    confirm_fresh_start: bool = False

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    fullname: str
    user_id: int
    profile_image_url: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    role: str
    profile_image_url: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    is_archived: bool = False
    is_online: bool = False
    last_active: Optional[object] = None

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class SetPasswordRequest(BaseModel):
    new_password: str


class AccountDeleteRequest(BaseModel):
    password: Optional[str] = None
    otp_code: Optional[str] = None
    reason: Optional[str] = None


class ReactivateRequestOTP(BaseModel):
    email: EmailStr


class ReactivateVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str


class FreshStartRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    fullname: str
    verification_token: Optional[str] = None
    confirm_fresh_start: bool = False