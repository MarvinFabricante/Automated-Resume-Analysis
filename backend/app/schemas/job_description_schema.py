from pydantic import BaseModel, Field
from typing import Optional
from app.models.job_description import JobType

class JobBase(BaseModel):
    job_id: str = Field(..., example="JOB-2024-001")
    job_title: str
    department: str
    job_type: JobType
    location: str
    salary_range: Optional[str] = None
    description: str
    skills_requirements: str
    education_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    is_active: bool = True

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int

    class Config:
        from_attributes = True

class JobUpdate(BaseModel):
    job_title: Optional[str] = None
    department: Optional[str] = None
    job_type: Optional[JobType] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    description: Optional[str] = None
    skills_requirements: Optional[str] = None
    education_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True