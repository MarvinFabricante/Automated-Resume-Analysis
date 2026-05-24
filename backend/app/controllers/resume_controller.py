from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.resume_schema import ResumeCreate, ResumeResponse, ResumeUpdate
from app.services import resume_service

class ResumeController:
    def __init__(self):
        self.router = APIRouter(prefix="/resumes", tags=["Resumes"])
        self.register_routes()

    def register_routes(self):
        self.router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)(self.create_resume)
        self.router.get("/{resume_id}", response_model=ResumeResponse)(self.get_resume)
        self.router.get("/candidate/{candidate_id}", response_model=List[ResumeResponse])(self.get_resumes_by_candidate)
        self.router.put("/{resume_id}", response_model=ResumeResponse)(self.update_resume)
        self.router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)(self.delete_resume)

    async def create_resume(self, resume_in: ResumeCreate, db: AsyncSession = Depends(get_db)):
        """
        Store a new resume in the database.
        """
        return await resume_service.create_resume(db, resume_in)

    async def get_resume(self, resume_id: int, db: AsyncSession = Depends(get_db)):
        """
        Retrieve a specific resume by ID.
        """
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return resume

    async def get_resumes_by_candidate(self, candidate_id: int, db: AsyncSession = Depends(get_db)):
        """
        Retrieve all resumes for a specific candidate.
        """
        return await resume_service.get_resumes_by_candidate(db, candidate_id)

    async def update_resume(self, resume_id: int, resume_in: ResumeUpdate, db: AsyncSession = Depends(get_db)):
        """
        Update an existing resume.
        """
        updated_resume = await resume_service.update_resume(db, resume_id, resume_in)
        if not updated_resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return updated_resume

    async def delete_resume(self, resume_id: int, db: AsyncSession = Depends(get_db)):
        """
        Delete a resume from the database.
        """
        success = await resume_service.delete_resume(db, resume_id)
        if not success:
            raise HTTPException(status_code=404, detail="Resume not found")
        return None


resume_controller = ResumeController()
router = resume_controller.router
