from pydantic import BaseModel, EmailStr, field_validator, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.services.requirement_rules import extract_criterion_status, STATUS_MANUAL_REVIEW

class JobInfo(BaseModel):
    id: int
    job_title: str
    location: str
    department: str

    class Config:
        from_attributes = True

class JobApplicationBase(BaseModel):
    user_id: Optional[int] = None
    applicant_id: Optional[int] = None
    candidate_name: str
    candidate_email: EmailStr
    resume_email: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    relevance: Optional[str] = None
    degree: Optional[str] = None
    college: Optional[str] = None
    certifications: Optional[str] = None
    clarification_responses: Optional[List[Dict[str, Any]]] = None
    requirement_evaluations: Optional[List[Dict[str, Any]]] = None
    skills: Optional[List[str]] = None
    match_score: Optional[float] = None
    skills_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    certifications_score: Optional[float] = None
    profile_image_url: Optional[str] = None
    resume_url: Optional[str] = None
    skills_reason: Optional[str] = None
    experience_reason: Optional[str] = None
    education_reason: Optional[str] = None
    certifications_reason: Optional[str] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    relevant_experience: Optional[str] = None
    experience_gaps: Optional[str] = None
    years_experience: Optional[int] = None
    work_experiences: Optional[List[Dict[str, Any]]] = None
    total_experience_months: Optional[int] = None
    education_entries: Optional[List[Dict[str, Any]]] = None
    highest_educational_attainment: Optional[str] = None
    required_degree: Optional[str] = None
    candidate_degree: Optional[str] = None
    required_certifications: Optional[str] = None
    candidate_certifications: Optional[str] = None
    recommendations: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    ai_powered: Optional[bool] = False
    completeness_score: Optional[float] = None
    completeness_status: Optional[str] = None
    missing_sections: Optional[List[str]] = None
    applied_weights: Optional[dict] = None
    hr_shortlist_notes: Optional[str] = None
    is_flagged_for_review: Optional[bool] = False
    review_flag_reason: Optional[str] = None
    source: Optional[str] = "Online"
    import_origin: Optional[str] = None
    imported_by: Optional[str] = None

    @field_validator("years_experience", "total_experience_months", mode="before")
    @classmethod
    def coerce_optional_int(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, (int, float)):
            return round(v)
        if isinstance(v, str):
            try:
                return round(float(v.strip()))
            except ValueError:
                return v
        return v

class JobApplicationCreate(JobApplicationBase):
    job_id: str

class JobApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    hr_shortlist_notes: Optional[str] = None
    custom_email_subject: Optional[str] = None
    custom_email_message: Optional[str] = None

class JobApplicationNotesUpdate(BaseModel):
    hr_shortlist_notes: str


class ApplicationWithdrawRequest(BaseModel):
    reason: Optional[str] = None


class PostPassActionRequest(BaseModel):
    action: str  # "on_hold" | "continue"
    target_application_ids: List[int] = []
    note: Optional[str] = None


class ApplicationResumeRequest(BaseModel):
    note: Optional[str] = None


class HiredElsewhereWithdrawRequest(BaseModel):
    note: Optional[str] = None

class JobApplicationViewedEvent(BaseModel):
    view_duration_seconds: float
    visible_focused: bool = True
    engaged: bool = True # scroll, expanded section, or opened resume

class StatusHistoryResponse(BaseModel):
    id: int
    application_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: str
    change_type: str # 'auto', 'manual', 'undo'
    reason: Optional[str] = None
    can_undo: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class OtherApplicationSummary(BaseModel):
    id: int
    job_id: int
    job_title: str
    status: str
    match_score: Optional[float] = None
    created_at: Optional[datetime] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True

class RecommendedPositionSummary(BaseModel):
    id: int
    job_id: str
    job_title: str
    department: Optional[str] = ""
    location: Optional[str] = ""
    match_percentage: float
    match_level: Optional[str] = None
    skills_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    certifications_score: Optional[float] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    reason: Optional[str] = None
    already_applied: bool = False
    existing_application_id: Optional[int] = None
    existing_application_status: Optional[str] = None

class JobApplicationResponse(JobApplicationBase):
    id: int
    job_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    messaging_closed_at: Optional[datetime] = None
    hold_reason: Optional[str] = None
    is_anonymized: Optional[bool] = False
    anonymized_token: Optional[str] = None
    job: Optional[JobInfo] = None
    active_applications_count: Optional[int] = 0
    has_other_active_applications: Optional[bool] = False
    other_applications: Optional[List[OtherApplicationSummary]] = None
    recommended_positions: Optional[List[RecommendedPositionSummary]] = None

    @computed_field
    @property
    def status_display(self) -> str:
        from app.services.status_management_service import get_status_display_label
        return get_status_display_label(self.status)

    @computed_field
    @property
    def is_read_only(self) -> bool:
        from app.services.status_management_service import is_passed_status, is_withdrawn_status
        return is_passed_status(self.status) or is_withdrawn_status(self.status)

    @computed_field
    @property
    def skills_status(self) -> Optional[str]:
        return extract_criterion_status(self.skills_reason)

    @computed_field
    @property
    def experience_status(self) -> Optional[str]:
        return extract_criterion_status(self.experience_reason)

    @computed_field
    @property
    def education_status(self) -> Optional[str]:
        return extract_criterion_status(self.education_reason)

    @computed_field
    @property
    def certifications_status(self) -> Optional[str]:
        return extract_criterion_status(self.certifications_reason)

    @computed_field
    @property
    def education_needs_manual_review(self) -> bool:
        return extract_criterion_status(self.education_reason) == STATUS_MANUAL_REVIEW

    class Config:
        from_attributes = True
