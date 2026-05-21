from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobInfo(BaseModel):
    id: int
    job_title: str
    location: str
    department: str

class JobApplicationBase(BaseModel):
    candidate_name: str
    candidate_email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    relevance: Optional[str] = None
    degree: Optional[str] = None
    college: Optional[str] = None
    certifications: Optional[str] = None
    skills: Optional[List[str]] = None
    match_score: Optional[float] = None
    skills_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    certifications_score: Optional[float] = None
    profile_image_url: Optional[str] = None
    skills_reason: Optional[str] = None
    experience_reason: Optional[str] = None
    education_reason: Optional[str] = None
    certifications_reason: Optional[str] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    relevant_experience: Optional[str] = None
    experience_gaps: Optional[str] = None
    required_degree: Optional[str] = None
    candidate_degree: Optional[str] = None
    required_certifications: Optional[str] = None
    candidate_certifications: Optional[str] = None
    recommendations: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    ai_powered: Optional[bool] = False

class JobApplicationCreate(JobApplicationBase):
    job_id: str

class JobApplicationStatusUpdate(BaseModel):
    status: str

class JobApplicationResponse(JobApplicationBase):
    id: int
    job_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    job: Optional[JobInfo] = None

    class Config:
        from_attributes = True
