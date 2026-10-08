from typing import Optional
from pydantic import BaseModel, EmailStr


class HRCreate(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    company_name: str
    department: Optional[str] = None

class HRUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

class HRResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    role: str
    company_name: str
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True