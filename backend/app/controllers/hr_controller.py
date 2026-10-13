import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.hr_schema import HRCreate, HRResponse, HRUpdate
from app.services import hr_service
from app.services.audit_service import record_activity
from app.utils.cache import cache_response, clear_cache_pattern
from app.utils.auth import get_current_user


router = APIRouter(prefix="/hr", tags=["HR Management"])

@router.post("/register")
async def register_hr(hr_in: HRCreate, db: AsyncSession = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public HR registration is disabled. HR accounts must be created by an Administrator."
    )

@router.get("/candidate-count")
@cache_response("candidate_count", ttl=300)
async def get_candidates_count(db: AsyncSession = Depends(get_db)):
    count = await hr_service.get_total_candidates_count(db)
    return {"count": count}

@router.get("/resume-count")
@cache_response("resume_count", ttl=300)
async def get_resumes_count(db: AsyncSession = Depends(get_db)):
    count = await hr_service.get_total_resumes_count(db)
    return {"count": count}

@router.get("/application-stats")
@cache_response("app_stats", ttl=300)
async def get_app_stats(db: AsyncSession = Depends(get_db)):
    stats = await hr_service.get_application_stats(db)
    return stats

@router.get("/profile/{hr_id}", response_model=HRResponse)
async def get_hr_profile_details(hr_id: int, db: AsyncSession = Depends(get_db)):
    profile = await hr_service.get_hr_profile(db, hr_id)
    if not profile:
        raise HTTPException(status_code=404, detail="HR profile not found")

    screened_count = 0
    job_posts_count = 0
    reports_count = 0
    try:
        from app.models.job_application import JobApplication
        from app.models.job_description import JobDescription
        from app.models.interview import Interview
        from sqlalchemy import select, func

        apps_res = await db.execute(select(func.count(JobApplication.id)))
        screened_count = apps_res.scalar() or 0

        jobs_res = await db.execute(select(func.count(JobDescription.id)).where(JobDescription.is_active == True))
        job_posts_count = jobs_res.scalar() or 0

        interviews_res = await db.execute(select(func.count(Interview.id)))
        reports_count = interviews_res.scalar() or 0
    except Exception as e:
        print(f"Error computing HR profile stats: {e}")

    data = HRResponse.from_orm(profile)
    data.screened_count = screened_count
    data.job_posts_count = job_posts_count
    data.reports_count = reports_count
    return data

@router.put("/profile/{hr_id}", response_model=HRResponse)
async def update_hr_profile_details(hr_id: int, hr_update: HRUpdate, db: AsyncSession = Depends(get_db)):
    try:
        updated_profile = await hr_service.update_hr_profile(db, hr_id, hr_update)
        if not updated_profile:
            raise HTTPException(status_code=404, detail="HR profile not found")
        await clear_cache_pattern(f"hr_profile:*\"hr_id\": {hr_id}*")
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-profile-image/{hr_id}")
async def upload_hr_profile_image(
    hr_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    image_url = None

    # 1. Upload to Supabase Storage (bucket: profile_images, path: profiles/)
    try:
        from app.utils.supabase_storage import upload_profile_image as sb_upload_profile_image
        result = await sb_upload_profile_image(
            file_bytes=file_bytes,
            original_filename=file.filename or f"hr_{hr_id}.png",
            user_role="hr",
            user_id=hr_id,
        )
        image_url = result["public_url"]
        print(f"Uploaded HR {hr_id} profile image to Supabase: {image_url}")
    except Exception as e:
        print(f"Supabase HR profile upload failed, falling back to local: {e}")
        upload_dir = "uploads/profile_images"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_extension = os.path.splitext(file.filename or "")[1] or ".png"
        file_name = f"hr_{hr_id}{file_extension}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        import time
        image_url = f"/{file_path}?t={int(time.time())}"

    await hr_service.update_hr_profile(db, hr_id, HRUpdate(profile_image_url=image_url))
    await clear_cache_pattern(f"hr_profile:*\"hr_id\": {hr_id}*")
    return {"image_url": image_url}
    


@router.get("/dashboard-trends")
@cache_response("dashboard_trends", ttl=300)
async def get_dashboard_trends_endpoint(db: AsyncSession = Depends(get_db)):
    return await hr_service.get_dashboard_trends(db)


@router.get("/interviewers")
async def get_hr_interviewers(db: AsyncSession = Depends(get_db)):
    """Fetch all active HR interviewers/panelists with their details and Google Calendar status."""
    from sqlalchemy import text
    query = text("""
        SELECT u.id, u.fullname, u.email, u.profile_image_url, 
               (u.google_credentials IS NOT NULL) AS has_google_calendar,
               h.company_name, h.department, h.position
        FROM users u
        LEFT JOIN hr_staffs h ON h.id = u.id
        WHERE u.role = 'HR' AND u.is_archived = false
        ORDER BY u.fullname ASC
    """)
    result = await db.execute(query)
    rows = result.fetchall()
    return [
        {
            "id": r.id,
            "fullname": r.fullname,
            "email": r.email,
            "profile_image_url": r.profile_image_url,
            "has_google_calendar": bool(r.has_google_calendar),
            "company_name": r.company_name or "Mariwasa Siam Ceramics, Inc.",
            "department": r.department or "Human Resources",
            "position": r.position or "HR Specialist",
        }
        for r in rows
    ]

