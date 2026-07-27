from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


# ─── System Config Schemas ────────────────────────────────────────────────────

class SystemConfigBase(BaseModel):
    key: str
    value: str
    category: str
    description: Optional[str] = None


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class SystemConfigResponse(SystemConfigBase):
    id: int
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Matching Algorithm Parameters ────────────────────────────────────────────

class MatchingWeightsUpdate(BaseModel):
    skills_weight: Optional[float] = None
    experience_weight: Optional[float] = None
    education_weight: Optional[float] = None
    certifications_weight: Optional[float] = None
    location_weight: Optional[float] = None


class MatchingThresholdsUpdate(BaseModel):
    fuzzy_match_threshold: Optional[float] = None
    minimum_match_score: Optional[float] = None
    ai_score_weight: Optional[float] = None
    rule_score_weight: Optional[float] = None
    transferable_skills_cap: Optional[int] = None


class MatchingConfigResponse(BaseModel):
    weights: dict
    thresholds: dict


# ─── Role Management ─────────────────────────────────────────────────────────

class RoleUpdate(BaseModel):
    role: str   # e.g., "ADMIN", "HR", "CANDIDATE"


class UserRoleResponse(BaseModel):
    id: int
    fullname: str
    email: str
    role: str
    is_archived: bool = False

    class Config:
        from_attributes = True


# ─── Form Template Schemas ────────────────────────────────────────────────────

class FormFieldDefinition(BaseModel):
    field_name: str
    field_type: str   # "text", "textarea", "select", "checkbox", "file", "date", "number"
    label: str
    required: bool = False
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None


class FormTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fields: List[FormFieldDefinition]
    is_default: bool = False


class FormTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormFieldDefinition]] = None
    is_default: Optional[bool] = None


class FormTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    fields: Any
    is_default: bool = False
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── System Performance & Usage Stats ─────────────────────────────────────────

class SystemPerformanceResponse(BaseModel):
    total_users: int
    active_users: int
    archived_users: int
    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    total_applications: int
    pending_applications: int
    reviewed_applications: int
    accepted_applications: int
    rejected_applications: int
    total_audit_logs: int
    recent_logins: int
    avg_match_score: Optional[float] = None
    ai_analysis_count: int
    data_points: int
    conversion_rate: float
    users_by_role: dict
    applications_by_status: dict
    applications_trend: List[dict] = []
    top_jobs: List[dict] = []
