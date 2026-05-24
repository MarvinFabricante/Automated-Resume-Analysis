from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.job_matching_schema import MatchResponse, ResumeMatchRequest, JobMatchResult
from app.services import job_matching_service, resume_service

class JobMatchingController:
    def __init__(self):
        self.router = APIRouter(prefix="/matching", tags=["Job Matching"])
        self.register_routes()

    def register_routes(self):
        self.router.post("/match-resume", response_model=MatchResponse)(self.match_resume_file)
        self.router.post("/match-data", response_model=MatchResponse)(self.match_resume_data)
        self.router.post("/match-data/{job_id}", response_model=JobMatchResult)(self.match_resume_to_single_job)

    async def match_resume_file(
        self,
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

    async def match_resume_data(
        self,
        resume_data: ResumeMatchRequest,
        db: AsyncSession = Depends(get_db)
    ):
        """
        Match already-parsed resume data against all active jobs.
        """
        data_dict = resume_data.model_dump()
        results = await job_matching_service.match_resume_to_all_jobs(db, data_dict)
        return MatchResponse(results=results)

    async def match_resume_to_single_job(
        self,
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


job_matching_controller = JobMatchingController()
router = job_matching_controller.router
