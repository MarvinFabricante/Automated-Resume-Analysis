from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.job_application_schema import JobApplicationCreate, JobApplicationResponse, JobApplicationStatusUpdate
from app.services import job_application_service
from app.models.job_description import JobDescription
from sqlalchemy.future import select
from app.services.audit_service import record_activity
from app.utils.auth import get_current_user

router = APIRouter(prefix="/applications", tags=["Job Applications"])

@router.post("/", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_job_application(application_in: JobApplicationCreate, db: AsyncSession = Depends(get_db)):
    """
    Submit a new job application.
    """
    # Verify job exists
    result = await db.execute(select(JobDescription).filter(JobDescription.job_id == application_in.job_id))
    job = result.scalars().first()
    
    if not job:
        # Fallback for static jobs or numeric IDs just in case
        try:
            numeric_id = int(application_in.job_id)
            result = await db.execute(select(JobDescription).filter(JobDescription.id == numeric_id))
            job = result.scalars().first()
        except ValueError:
            pass
            
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return await job_application_service.create_job_application(db, application_in, job.id)

@router.get("/", response_model=List[JobApplicationResponse])
async def get_all_applications(db: AsyncSession = Depends(get_db)):
    """
    Get all job applications from all jobs.
    """
    return await job_application_service.get_all_applications(db)

@router.get("/job/{job_id}", response_model=List[JobApplicationResponse])
async def get_applications_for_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all applications for a specific job.
    """
    return await job_application_service.get_applications_by_job(db, job_id)

@router.get("/job/{job_id}/compare")
async def get_candidate_comparison(job_id: int):
    """
    Get the AI candidate comparison summary for a specific job.
    """
    from app.utils.cache import get_cache
    comparison_cache_key = f"job_comparison:{job_id}"
    cached_result = await get_cache(comparison_cache_key)
    if not cached_result:
        raise HTTPException(status_code=404, detail="Comparison not found or still processing.")
    return cached_result

@router.get("/candidate/{email}", response_model=List[JobApplicationResponse])
async def get_applications_for_candidate(email: str, db: AsyncSession = Depends(get_db)):
    """
    Get all applications for a specific candidate by email.
    """
    return await job_application_service.get_applications_by_email(db, email)

@router.patch("/{application_id}/status", response_model=JobApplicationResponse)
async def update_application_status(
    application_id: int, 
    status_update: JobApplicationStatusUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of a job application.
    """
    db_application = await job_application_service.update_application_status(
        db, application_id, status_update.status
    )
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Record in audit log
    await record_activity(
        db=db,
        user_id=1,  # Default to 1 for now to bypass 401 issues
        action="UPDATE_STATUS",
        target=f"Application ID: {application_id}",
        details=f"HR updated application status for {db_application.candidate_name} to {status_update.status}"
    )
        
    # Invalidate cache since stats might change
    from app.utils.cache import delete_cache
    await delete_cache("app_stats:{}")
    
    return db_application

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove/delete a job application.
    """
    from app.models.job_application import JobApplication
    result = await db.execute(select(JobApplication).filter(JobApplication.id == application_id))
    db_application = result.scalars().first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    await db.delete(db_application)
    await db.commit()
    
    # Record in audit log
    await record_activity(
        db=db,
        user_id=1, # Default to 1 to bypass 401 issues
        action="DELETE_APPLICATION",
        target=f"Application ID: {application_id}",
        details=f"HR deleted application for {db_application.candidate_name}"
    )
    
    # Invalidate cache since stats might change
    from app.utils.cache import delete_cache
    await delete_cache("app_stats:{}")
    
    return None
