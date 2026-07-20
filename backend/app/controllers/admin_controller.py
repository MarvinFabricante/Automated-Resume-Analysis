import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.admin_schema import AdminCreate, AdminResponse, AdminUpdate
from app.schemas.user_schema import UserResponse
from app.services import admin_service, audit_service
from app.utils.cache import cache_response, clear_cache_pattern


router = APIRouter(prefix="/admins", tags=["Adminstrators"])

@router.get("/hr-activities")
async def get_hr_activities(db: AsyncSession = Depends(get_db)):
    activities = await audit_service.get_recent_hr_activities(db)
    return activities

@router.get("/system-stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    return await admin_service.get_system_stats(db)

@router.get("/audit-logs")
async def get_audit_logs(db: AsyncSession = Depends(get_db)):
    return await audit_service.get_all_audit_logs(db)

@router.get("/users", response_model=List[UserResponse])
@cache_response("admin_users", ttl=600)
async def read_users(db: AsyncSession = Depends(get_db)):
    users = await admin_service.get_all_users(db)
    return users

@router.patch("/users/{user_id}/archive")
async def archive_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await admin_service.toggle_user_archive_status(db, user_id, True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await clear_cache_pattern("admin_users:*")
    return {"message": "User archived successfully"}

@router.patch("/users/{user_id}/unarchive")
async def unarchive_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await admin_service.toggle_user_archive_status(db, user_id, False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await clear_cache_pattern("admin_users:*")
    return {"message": "User unarchived successfully"}

@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_200_OK)
async def register_admin(
    admin_in: AdminCreate, 
    db: AsyncSession = Depends(get_db)
):

    new_admin = await admin_service.create_admin_profile(db, admin_in)
    return new_admin

@router.get("/profile/{admin_id}", response_model=AdminResponse)
@cache_response("admin_profile", ttl=1800)
async def get_admin_profile_details(admin_id: int, db: AsyncSession = Depends(get_db)):
    profile = await admin_service.get_admin_profile(db, admin_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    return profile

@router.put("/profile/{admin_id}", response_model=AdminResponse)
async def update_admin_profile_details(
    admin_id: int,
    admin_update: AdminUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated_profile = await admin_service.update_admin_profile(db, admin_id, admin_update)
    if updated_profile:
        await clear_cache_pattern(f"admin_profile:*\"admin_id\": {admin_id}*")
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    return updated_profile

@router.post("/upload-profile-image/{admin_id}")
async def upload_admin_profile_image(
    admin_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    upload_dir = "uploads/profile_images"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"admin_{admin_id}{file_extension}"
    file_path = os.path.join(upload_dir, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    import time
    image_url = f"http://localhost:8000/{file_path}?t={int(time.time())}"
    await admin_service.update_admin_profile(db, admin_id, AdminUpdate(profile_image_url=image_url))
    await clear_cache_pattern(f"admin_profile:*\"admin_id\": {admin_id}*")
    
    return {"image_url": image_url}


