from typing import Optional, List
from pydantic import BaseModel, EmailStr


class CandidateCreate(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    resume_url: Optional[str] = None
    experience_years: Optional[int] = 0

class CandidateUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_job_title: Optional[str] = None
    current_company: Optional[str] = None
    bio: Optional[str] = None
    highest_degree: Optional[str] = None
    university: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None
    profile_image_url: Optional[str] = None

class CandidateResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    resume_url: Optional[str]
    experience_years: int
    role: str
    
    # Profile Fields
    phone: Optional[str] = None
    location: Optional[str] = None
    current_job_title: Optional[str] = None
    current_company: Optional[str] = None
    bio: Optional[str] = None
    highest_degree: Optional[str] = None
    university: Optional[str] = None
    skills: Optional[List[str]] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True