import os
import shutil
from typing import List
from fastapi import Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.hr_schema import HRCreate, HRResponse, HRUpdate
from app.schemas.job_description_schema import JobCreate, JobResponse, JobUpdate
from app.services import hr_service
from app.services.job_description_service import (
    create_job,
    delete_job,
    get_all_active_jobs,
    get_job,
    set_job_status,
    update_job,
)
from app.services.audit_service import record_activity
from app.utils.cache import cache_response, clear_cache_pattern
from app.utils.auth import get_current_user
from app.controllers.base_controller import BaseController, Delete, Get, Patch, Post, Put


class HRController(BaseController):
    prefix = "/hr"
    tags = ["HR Management"]

    @Post("/register", response_model=HRResponse)
    async def register_hr(self, hr_in: HRCreate, db: AsyncSession = Depends(get_db)):
        try:
            return await hr_service.create_hr_profile(db, hr_in)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    @Get("/candidate-count")
    @cache_response("candidate_count", ttl=300)
    async def get_candidates_count(self, db: AsyncSession = Depends(get_db)):
        count = await hr_service.get_total_candidates_count(db)
        return {"count": count}

    @Get("/resume-count")
    @cache_response("resume_count", ttl=300)
    async def get_resumes_count(self, db: AsyncSession = Depends(get_db)):
        count = await hr_service.get_total_resumes_count(db)
        return {"count": count}

    @Get("/application-stats")
    @cache_response("app_stats", ttl=300)
    async def get_app_stats(self, db: AsyncSession = Depends(get_db)):
        stats = await hr_service.get_application_stats(db)
        return stats

    @Get("/profile/{hr_id}", response_model=HRResponse)
    async def get_hr_profile_details(self, hr_id: int, db: AsyncSession = Depends(get_db)):
        profile = await hr_service.get_hr_profile(db, hr_id)
        if not profile:
            raise HTTPException(status_code=404, detail="HR profile not found")
        return profile

    @Put("/profile/{hr_id}", response_model=HRResponse)
    async def update_hr_profile_details(self, hr_id: int, hr_update: HRUpdate, db: AsyncSession = Depends(get_db)):
        updated_profile = await hr_service.update_hr_profile(db, hr_id, hr_update)
        if not updated_profile:
            raise HTTPException(status_code=404, detail="HR profile not found")
        return updated_profile

    @Post("/upload-profile-image/{hr_id}")
    async def upload_hr_profile_image(
        self,
        hr_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
    ):
        upload_dir = "uploads/profile_images"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"hr_{hr_id}{file_extension}"
        file_path = os.path.join(upload_dir, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        import time
        image_url = f"http://localhost:8000/{file_path}?t={int(time.time())}"
        await hr_service.update_hr_profile(db, hr_id, HRUpdate(profile_image_url=image_url))
        
        return {"image_url": image_url}
        
    # ===================== For Job Management Section

    @Post("/createjob", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
    async def create_job_description(
        self,
        job: JobCreate, 
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(get_current_user)
    ):
        result = await create_job(db=db, job=job)
        await clear_cache_pattern("active_jobs:*")
        
        # Record in audit log
        await record_activity(
            db=db,
            user_id=current_user.get("id"),
            action="CREATE_JOB",
            target=f"Job: {result.job_title}",
            details=f"HR created a new job position: {result.job_title}"
        )
        
        return result

    @Get("/read-jobs", response_model=List[JobResponse])
    @cache_response("active_jobs", ttl=600)
    async def read_active_jobs(
        self,
        skip: int = 0, 
        limit: int = 100, 
        include_inactive: bool = False,
        db: AsyncSession = Depends(get_db)
    ):
        return await get_all_active_jobs(db, skip=skip, limit=limit, include_inactive=include_inactive)

    @Get("/read-job/{job_id}", response_model=JobResponse)
    @cache_response("job_detail", ttl=600)
    async def read_job(self, job_id: str, db: AsyncSession = Depends(get_db)):
        db_job = await get_job(db, job_id=job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return db_job

    @Patch("/update-job/{job_id}", response_model=JobResponse)
    async def update_job_details(
        self,
        job_id: str, 
        job_data: JobUpdate, 
        db: AsyncSession = Depends(get_db)
    ):
        db_job = await update_job(db=db, job_id=job_id, job_data=job_data)
        if db_job:
            await clear_cache_pattern(f"job_detail:*job_id\":\"{job_id}\"*")
            await clear_cache_pattern("active_jobs:*")
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )
        return db_job

    @Patch("/archive-job/{job_id}", response_model=JobResponse)
    async def archive_job(self, job_id: str, db: AsyncSession = Depends(get_db)):
        db_job = await set_job_status(db=db, job_id=job_id, active_status=False)
        if db_job:
            await clear_cache_pattern("active_jobs:*")
            await clear_cache_pattern(f"job_detail:*job_id\":\"{job_id}\"*")
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )
        return db_job

    @Patch("/unarchive-job/{job_id}", response_model=JobResponse)
    async def unarchive_job(self, job_id: str, db: AsyncSession = Depends(get_db)):
        db_job = await set_job_status(db=db, job_id=job_id, active_status=True)
        if db_job:
            await clear_cache_pattern("active_jobs:*")
            await clear_cache_pattern(f"job_detail:*job_id\":\"{job_id}\"*")
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )
        return db_job

    @Delete("/delete-job/{job_id}", response_model=JobResponse)
    async def delete_job_endpoint(
        self,
        job_id: str, 
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(get_current_user)
    ):
        db_job = await delete_job(db=db, job_id=job_id)
        if db_job:
            await clear_cache_pattern("active_jobs:*")
            await clear_cache_pattern(f"job_detail:*job_id\":\"{job_id}\"*")
            
            # Record in audit log
            await record_activity(
                db=db,
                user_id=current_user.get("id"),
                action="DELETE_JOB",
                target=f"Job: {db_job.job_title}",
                details=f"HR deleted the job position: {db_job.job_title}"
            )
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_442_UNPROCESSABLE_ENTITY if not db_job else status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        return db_job

    @Get("/dashboard-trends")
    async def get_dashboard_trends_endpoint(self, db: AsyncSession = Depends(get_db)):
        return await hr_service.get_dashboard_trends(db)


hr_controller = HRController()
router = hr_controller.router
