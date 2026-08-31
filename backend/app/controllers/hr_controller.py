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

@router.post("/register", response_model=HRResponse)
async def register_hr(hr_in: HRCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await hr_service.create_hr_profile(db, hr_in)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

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
@cache_response("hr_profile", ttl=600)
async def get_hr_profile_details(hr_id: int, db: AsyncSession = Depends(get_db)):
    profile = await hr_service.get_hr_profile(db, hr_id)
    if not profile:
        raise HTTPException(status_code=404, detail="HR profile not found")
    return profile

@router.put("/profile/{hr_id}", response_model=HRResponse)
async def update_hr_profile_details(hr_id: int, hr_update: HRUpdate, db: AsyncSession = Depends(get_db)):
    updated_profile = await hr_service.update_hr_profile(db, hr_id, hr_update)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="HR profile not found")
    return updated_profile

@router.post("/upload-profile-image/{hr_id}")
async def upload_hr_profile_image(
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
    


@router.get("/dashboard-trends")
@cache_response("dashboard_trends", ttl=300)
async def get_dashboard_trends_endpoint(db: AsyncSession = Depends(get_db)):
    return await hr_service.get_dashboard_trends(db)


