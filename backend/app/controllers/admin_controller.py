import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.admin_schema import AdminCreate, AdminResponse, AdminUpdate
from app.schemas.user_schema import UserResponse, UserCreate, UserUpdate
from app.schemas.job_description_schema import JobCreate, JobResponse, JobUpdate
from app.services import admin_service, audit_service
from app.services.job_description_service import (
    create_job,
    delete_job,
    get_all_active_jobs,
    get_job,
    set_job_status,
    update_job,
)
from typing import List, Optional
from fastapi import Header
from jose import jwt
from app.utils.auth import get_current_user
from app.utils.cache import cache_response, clear_cache_pattern

def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "").strip()
        from app.utils.auth import SECRET_KEY, ALGORITHM
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

router = APIRouter(prefix="/admins", tags=["Adminstrators"])

@router.get("/system-stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    return await admin_service.get_system_stats(db)

@router.get("/users", response_model=List[UserResponse])
@cache_response("admin_users", ttl=600)
async def read_users(db: AsyncSession = Depends(get_db)):
    users = await admin_service.get_all_users(db)
    return users

@router.patch("/users/{user_id}/archive")
async def archive_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    if current_user and current_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="You cannot suspend/archive your own account.")

    user = await admin_service.toggle_user_archive_status(db, user_id, True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user and current_user.get("id"):
        await audit_service.record_activity(
            db=db,
            user_id=current_user.get("id"),
            action="SUSPEND_USER",
            target=f"User: {user.email}",
            details=f"Admin suspended user account: {user.email}"
        )

    await clear_cache_pattern("admin_users:*")
    return {"message": "User archived successfully"}

@router.patch("/users/{user_id}/unarchive")
async def unarchive_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    user = await admin_service.toggle_user_archive_status(db, user_id, False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user and current_user.get("id"):
        await audit_service.record_activity(
            db=db,
            user_id=current_user.get("id"),
            action="RESTORE_USER",
            target=f"User: {user.email}",
            details=f"Admin restored user account: {user.email}"
        )

    await clear_cache_pattern("admin_users:*")
    return {"message": "User unarchived successfully"}

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    from app.services.auth_service import auth_service
    try:
        new_user = await auth_service.register_user(db, user_in.email, user_in.password, user_in.role, user_in.fullname)
        await clear_cache_pattern("admin_users:*")
        return new_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    update_data = user_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update")
        
    updated_user = await admin_service.update_user(db, user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await clear_cache_pattern("admin_users:*")
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    if current_user and current_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    target_user = await admin_service.get_user_by_id(db, user_id)
    user_email = target_user.email if target_user else f"ID: {user_id}"

    success = await admin_service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user and current_user.get("id"):
        await audit_service.record_activity(
            db=db,
            user_id=current_user.get("id"),
            action="DELETE_USER",
            target=f"User: {user_email}",
            details=f"Admin deleted user account: {user_email}"
        )
        
    await clear_cache_pattern("admin_users:*")
    return {"message": "User removed successfully"}

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

# ===================== For Job Management Section

@router.post("/createjob", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    job: JobCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await create_job(db=db, job=job)
    await clear_cache_pattern("active_jobs:*")
    
    # Record in audit log
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="CREATE_JOB",
        target=f"Job: {result.job_title}",
        details=f"Admin created a new job position: {result.job_title}"
    )
    
    return result

@router.get("/read-jobs", response_model=List[JobResponse])
@cache_response("active_jobs", ttl=600)
async def read_active_jobs(
    skip: int = 0, 
    limit: int = 100, 
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    return await get_all_active_jobs(db, skip=skip, limit=limit, include_inactive=include_inactive)

@router.get("/read-job/{job_id}", response_model=JobResponse)
@cache_response("job_detail", ttl=600)
async def read_job(job_id: str, db: AsyncSession = Depends(get_db)):
    db_job = await get_job(db, job_id=job_id)
    if not db_job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return db_job

@router.patch("/update-job/{job_id}", response_model=JobResponse)
async def update_job_details(
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

@router.patch("/archive-job/{job_id}", response_model=JobResponse)
async def archive_job(job_id: str, db: AsyncSession = Depends(get_db)):
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

@router.patch("/unarchive-job/{job_id}", response_model=JobResponse)
async def unarchive_job(job_id: str, db: AsyncSession = Depends(get_db)):
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

@router.delete("/delete-job/{job_id}", response_model=JobResponse)
async def delete_job_endpoint(
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_job = await delete_job(db=db, job_id=job_id)
    if db_job:
        await clear_cache_pattern("active_jobs:*")
        await clear_cache_pattern(f"job_detail:*job_id\":\"{job_id}\"*")
        
        # Record in audit log
        await audit_service.record_activity(
            db=db,
            user_id=current_user.get("id"),
            action="DELETE_JOB",
            target=f"Job: {db_job.job_title}",
            details=f"Admin deleted the job position: {db_job.job_title}"
        )
    if not db_job:
        raise HTTPException(
            status_code=status.HTTP_442_UNPROCESSABLE_ENTITY if not db_job else status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return db_job

# ===================== For Data Management & Security Section

from datetime import datetime

@router.post("/data-backup")
async def create_data_backup(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Mock backup implementation
    
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="DATA_BACKUP",
        target="System Database",
        details="Admin triggered a manual data backup"
    )
    return {"message": "Data backup completed successfully", "timestamp": datetime.now().isoformat()}

@router.post("/data-recovery")
async def recover_data(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Mock recovery implementation
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="DATA_RECOVERY",
        target="System Database",
        details="Admin initiated data recovery process"
    )
    return {"message": "Data recovery initiated successfully"}

@router.get("/retention-policy")
async def get_retention_policy(db: AsyncSession = Depends(get_db)):
    # Mock retrieval of retention policy
    return {"retention_days": 90, "auto_delete": True}

@router.put("/retention-policy")
async def update_retention_policy(
    policy: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Mock update of retention policy
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="UPDATE_RETENTION",
        target="System Config",
        details=f"Admin updated data retention policy to {policy.get('retention_days', 90)} days"
    )
    return {"message": "Retention policy updated successfully", "policy": policy}
