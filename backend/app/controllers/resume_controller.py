from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.resume_schema import ResumeCreate, ResumeResponse, ResumeUpdate
from app.services import resume_service


router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(resume_in: ResumeCreate, db: AsyncSession = Depends(get_db)):
    """
    Store a new resume in the database.
    """
    return await resume_service.create_resume(db, resume_in)

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific resume by ID.
    """
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.get("/candidate/{candidate_id}", response_model=List[ResumeResponse])
async def get_resumes_by_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all resumes for a specific candidate.
    """
    return await resume_service.get_resumes_by_candidate(db, candidate_id)

@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(resume_id: int, resume_in: ResumeUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing resume.
    """
    updated_resume = await resume_service.update_resume(db, resume_id, resume_in)
    if not updated_resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return updated_resume

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a resume from the database.
    """
    success = await resume_service.delete_resume(db, resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return None


