from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class PhysicalResumeBase(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    target_job_id: Optional[int] = None
    target_job_title: Optional[str] = None
    physical_location: Optional[str] = None  # e.g., "Cabinet A - Shelf 2 - Folder 12"
    submission_date: Optional[datetime] = None
    status: Optional[str] = "RECEIVED"
    notes: Optional[str] = None

class PhysicalResumeCreate(PhysicalResumeBase):
    pass

class PhysicalResumeUpdate(BaseModel):
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    target_job_id: Optional[int] = None
    target_job_title: Optional[str] = None
    physical_location: Optional[str] = None
    submission_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class PhysicalResumeResponse(BaseModel):
    id: int
    hr_id: Optional[int] = None
    hr_name: Optional[str] = None
    candidate_name: str
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    target_job_id: Optional[int] = None
    target_job_title: Optional[str] = None
    physical_location: Optional[str] = None
    submission_date: Optional[datetime] = None
    filename: str
    file_url: str
    storage_path: Optional[str] = None
    file_size: Optional[int] = None
    formatted_file_size: Optional[str] = None
    file_type: Optional[str] = None
    status: str
    notes: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PhysicalResumeListResponse(BaseModel):
    items: List[PhysicalResumeResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class PhysicalResumeStats(BaseModel):
    total_stored: int
    received_this_month: int
    received_this_week: int
    status_counts: Dict[str, int]
    top_departments_or_jobs: List[Dict[str, Any]]
