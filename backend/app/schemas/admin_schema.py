from typing import Optional
from pydantic import BaseModel, EmailStr


class AdminCreate(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    managed_region: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    governance_scope: Optional[str] = None


class AdminUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    managed_region: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    governance_scope: Optional[str] = None
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
    department: Optional[str] = None
    position: Optional[str] = None
    governance_scope: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

    # Live Admin & System Feature Metrics
    users_count: Optional[int] = 0
    jobs_count: Optional[int] = 0
    audits_count: Optional[int] = 0
    resumes_count: Optional[int] = 0
    active_hr_count: Optional[int] = 0
    active_candidates_count: Optional[int] = 0

    class Config:
        from_attributes = True
