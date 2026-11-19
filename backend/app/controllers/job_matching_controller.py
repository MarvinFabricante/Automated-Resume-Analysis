from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.job_matching_schema import MatchResponse, ResumeMatchRequest, JobMatchResult
from app.services import job_matching_service, resume_service


router = APIRouter(prefix="/matching", tags=["Job Matching"])


def _sanitize_for_applicant(match: dict) -> dict:
    """
    Applicants must not see numeric weights or the scoring formula.
    Replace formulaic score_explanation with a plain-language focus hint when applicable.
    """
    if not isinstance(match, dict):
        return match
    cleaned = dict(match)
    weights = cleaned.pop("applied_weights", None) or {}
    cleaned.pop("weights_source", None)

    focus_parts = []
    if weights.get("certifications", 10) >= 20:
        focus_parts.append("certifications and trainings")
    if weights.get("skills", 40) >= 50:
        focus_parts.append("technical skills")
    if weights.get("experience", 30) >= 40:
        focus_parts.append("relevant work experience")
    if weights.get("education", 15) >= 25:
        focus_parts.append("educational background")

    if focus_parts:
        cleaned["score_explanation"] = f"This job puts extra focus on {' and '.join(focus_parts)}."
    else:
        cleaned["score_explanation"] = None
    return cleaned


@router.post("/match-resume", response_model=MatchResponse)
async def match_resume_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a resume file, parse it, and match against all active jobs.
    """
    extracted_data = await resume_service.parse_resume_file(db, file)
    if not extracted_data:
        raise HTTPException(status_code=400, detail="Failed to parse resume.")
    
    results = await job_matching_service.match_resume_to_all_jobs(db, extracted_data)
    return MatchResponse(results=[_sanitize_for_applicant(r) for r in results])

@router.post("/match-data", response_model=MatchResponse)
async def match_resume_data(
    resume_data: ResumeMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Match already-parsed resume data against all active jobs.
    """
    data_dict = resume_data.model_dump()
    results = await job_matching_service.match_resume_to_all_jobs(db, data_dict)
    return MatchResponse(results=[_sanitize_for_applicant(r) for r in results])

@router.post("/match-data/{job_id}", response_model=JobMatchResult)
async def match_resume_to_single_job(
    job_id: str,
    resume_data: ResumeMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Match already-parsed resume data against a single specific job.
    """
    data_dict = resume_data.model_dump()
    result = await job_matching_service.match_resume_to_job(db, data_dict, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _sanitize_for_applicant(result)


