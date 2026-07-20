from pydantic import BaseModel
from typing import Optional


class JobMatchResult(BaseModel):
    job_id: str
    job_title: str
    department: str
    location: str
    job_type: Optional[str] = None
    match_percentage: float
    skills_score: float
    experience_score: float
    education_score: float
    certifications_score: Optional[float] = None
    location_score: Optional[float] = None
    matched_skills: list[str]
    missing_skills: list[str]
    skills_reason: Optional[str] = None
    experience_reason: Optional[str] = None
    education_reason: Optional[str] = None
    certifications_reason: Optional[str] = None
    location_reason: Optional[str] = None
    relevant_experience: Optional[str] = None
    experience_gaps: Optional[str] = None
    required_degree: Optional[str] = None
    candidate_degree: Optional[str] = None
    required_certifications: Optional[str] = None
    candidate_certifications: Optional[str] = None
    recommendations: Optional[list[str]] = None
    # ── Gemini AI Insights (populated when AI is available) ──────────────────
    ai_summary: Optional[str] = None
    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    ai_powered: Optional[bool] = False


class MatchResponse(BaseModel):
    results: list[JobMatchResult]


class ResumeMatchRequest(BaseModel):
    """Accept already-parsed resume data for matching."""
    skills: Optional[str] = ""
    years_experience: Optional[int] = 0
    highest_degree: Optional[str] = ""
    fullname: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    experience: Optional[str] = ""
    education: Optional[str] = ""
    profile_image_url: Optional[str] = None
    ai_summary: Optional[str] = None
