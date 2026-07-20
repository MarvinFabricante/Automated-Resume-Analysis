from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.job_matching_schema import MatchResponse, ResumeMatchRequest, JobMatchResult
from app.services import job_matching_service, resume_service


router = APIRouter(prefix="/matching", tags=["Job Matching"])

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
    return MatchResponse(results=results)

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
    return MatchResponse(results=results)

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
    return result


