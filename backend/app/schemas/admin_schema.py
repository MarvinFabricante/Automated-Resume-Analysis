from typing import Optional
from pydantic import BaseModel, EmailStr


class AdminCreate(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    managed_region: Optional[str] = None


class AdminUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    managed_region: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None


class AdminResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    role: str
    managed_region: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True
