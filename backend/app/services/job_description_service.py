from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job_description_schema import JobCreate, JobUpdate
from app.services.notification_service import create_notification
from app.repositories.job_description_repository import JobDescriptionRepository


async def create_job(db: AsyncSession, job: JobCreate):
    """Create a new job and trigger notification."""
    job_data = job.dict()
    db_job = await JobDescriptionRepository.create(db, job_data)
    
    # Trigger notification
    await create_notification(
        db=db,
        title="New Job Created",
        message=f"A new position '{db_job.job_title}' has been posted.",
        type="job_creation"
    )
    
    return db_job


async def get_job(db: AsyncSession, job_id: str):
    """Get a job by job_id."""
    return await JobDescriptionRepository.get_by_job_id(db, job_id)


async def get_all_active_jobs(db: AsyncSession, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    """Get all active jobs with pagination."""
    return await JobDescriptionRepository.get_all_active(db, skip, limit, include_inactive)


async def update_job(db: AsyncSession, job_id: str, job_data: JobUpdate):
    """Update job and re-calculate match scores for all existing applications."""
    # Fetch the job
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)
    
    if not db_job:
        return None

    # Update job with provided data
    update_data = job_data.model_dump(exclude_unset=True)
    db_job = await JobDescriptionRepository.update(db, db_job, update_data)
    
    # Re-calculate match scores for all existing applications of this job to sync them
    try:
        from app.services.job_matching_service import calculate_match_score, _extract_years_from_text
        
        applications = await JobDescriptionRepository.get_applications_for_job(db, db_job.id)
        
        for app in applications:
            skills_str = ", ".join(app.skills) if isinstance(app.skills, list) else (app.skills or "")
            candidate_years = _extract_years_from_text(app.relevance) if app.relevance else 0
            
            resume_data = {
                "skills": skills_str,
                "years_experience": candidate_years,
                "highest_degree": app.degree or ""
            }
            
            match_res = calculate_match_score(resume_data, db_job)
            app.match_score = match_res["match_percentage"]
            app.skills_reason = match_res["skills_reason"]
            app.experience_reason = match_res["experience_reason"]
            app.education_reason = match_res["education_reason"]
            
        await JobDescriptionRepository.bulk_update_applications(db, applications)
    except Exception as match_sync_err:
        print(f"WARNING: Failed to sync application scores: {match_sync_err}")
        
    # Trigger notification
    await create_notification(
        db=db,
        title="Job Description Modified",
        message=f"The job details for '{db_job.job_title}' have been updated.",
        type="job_update"
    )
    
    return db_job


async def set_job_status(db: AsyncSession, job_id: str, active_status: bool):
    """Set job status (active/inactive)."""
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)
    
    if db_job:
        db_job = await JobDescriptionRepository.set_status(db, db_job, active_status)
        
    return db_job


async def delete_job(db: AsyncSession, job_id: str):
    """Delete a job."""
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)
    
    if db_job:
        await JobDescriptionRepository.delete(db, db_job)
        
    return db_job