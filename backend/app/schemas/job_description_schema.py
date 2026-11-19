from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Optional
from app.models.job_description import JobType


class JobScoringWeights(BaseModel):
    """
    Per-job scoring priorities, expressed as fractions (0.40 = 40%).
    Each weight must be a whole-number percentage within [5%, 70%] and the
    five components must add up to exactly 100%.
    """
    skills_weight: float = Field(..., ge=0, le=1, description="Skills Match")
    experience_weight: float = Field(..., ge=0, le=1, description="Work Experience Relevance")
    education_weight: float = Field(..., ge=0, le=1, description="Educational Background")
    certifications_weight: float = Field(..., ge=0, le=1, description="Certifications and Trainings")
    completeness_weight: float = Field(..., ge=0, le=1, description="Resume Completeness")

    @model_validator(mode="after")
    def _validate_weights(self):
        from app.services.job_matching_service import validate_scoring_weights
        cleaned = validate_scoring_weights({
            "skills_weight": self.skills_weight,
            "experience_weight": self.experience_weight,
            "education_weight": self.education_weight,
            "certifications_weight": self.certifications_weight,
            "completeness_weight": self.completeness_weight,
        })
        for key, val in cleaned.items():
            setattr(self, key, val)
        return self


class JobBase(BaseModel):
    job_id: str = Field(..., example="JOB-2024-001")
    job_title: str
    department: str
    job_type: JobType
    location: str
    salary_range: Optional[str] = None
    description: str
    skills_requirements: Optional[str] = None
    education_requirements: Optional[str] = None
    certifications_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    is_active: bool = True


class JobCreate(JobBase):
    # Omit to start the job with the global default weights.
    scoring_weights: Optional[JobScoringWeights] = None


class JobResponse(JobBase):
    id: int
    # None = job has no custom weights and inherits the global default.
    scoring_weights: Optional[dict] = None
    applicant_count: Optional[int] = None

    @field_validator("scoring_weights", mode="before")
    @classmethod
    def _clean_weights(cls, value: Any):
        from app.services.job_matching_service import normalize_scoring_weights
        return normalize_scoring_weights(value)

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
    certifications_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    is_active: Optional[bool] = None
    # Send explicit null to drop custom weights and inherit the global default again.
    scoring_weights: Optional[JobScoringWeights] = None

    class Config:
        from_attributes = True
