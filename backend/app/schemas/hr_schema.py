from typing import Optional, List, Dict, Any
from datetime import datetime
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

    # Live HR Metrics
    screened_count: Optional[int] = 0
    job_posts_count: Optional[int] = 0
    reports_count: Optional[int] = 0

    class Config:
        from_attributes = True

class ShortlistRosterItemCreate(BaseModel):
    application_id: int

class ShortlistRosterItemStageUpdate(BaseModel):
    stage: str # "Shortlisted", "Interview Scheduled", "Interviewed", "Passed initial interview", "Not selected"

class ShortlistRosterCreate(BaseModel):
    job_id: int
    name: str
    notes: Optional[str] = None
    application_ids: Optional[List[int]] = []

class ShortlistRosterItemResponse(BaseModel):
    id: int
    roster_id: int
    application_id: int
    stage: str
    added_by: str
    added_at: datetime
    updated_at: datetime
    application: Optional[Any] = None

    class Config:
        from_attributes = True

class ShortlistRosterResponse(BaseModel):
    id: int
    job_id: int
    job_title: Optional[str] = None
    job_department: Optional[str] = None
    name: str
    created_by: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_candidates: int = 0
    shortlisted_count: int = 0
    interview_scheduled_count: int = 0
    interviewed_count: int = 0
    passed_count: int = 0
    not_selected_count: int = 0
    items: Optional[List[ShortlistRosterItemResponse]] = []

    class Config:
        from_attributes = True

class HRCandidateNoteCreate(BaseModel):
    content: str

class HRCandidateNoteResponse(BaseModel):
    id: int
    candidate_email: str
    author_email: str
    author_name: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UniversalSearchApplicantResult(BaseModel):
    id: int
    name: str
    email: str
    job_title: str
    status: str
    match_score: Optional[float] = None
    created_at: datetime

class UniversalSearchJobResult(BaseModel):
    id: int
    title: str
    department: str
    location: str
    is_active: bool

class UniversalSearchShortlistResult(BaseModel):
    id: int
    name: str
    job_title: str
    candidate_count: int
    created_at: datetime

class UniversalSearchResponse(BaseModel):
    applicants: List[UniversalSearchApplicantResult] = []
    jobs: List[UniversalSearchJobResult] = []
    shortlists: List[UniversalSearchShortlistResult] = []

class CandidateCompareRequest(BaseModel):
    application_ids: List[int]
    reference_job_id: Optional[int] = None
