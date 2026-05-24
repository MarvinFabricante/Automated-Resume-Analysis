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


class AdminController:
    def __init__(self):
        self.router = APIRouter(prefix="/admins", tags=["Adminstrators"])
        self.register_routes()

    def register_routes(self):
        self.router.get("/hr-activities")(self.get_hr_activities)
        self.router.get("/system-stats")(self.get_system_stats)
        self.router.get("/audit-logs")(self.get_audit_logs)
        self.router.get("/users", response_model=List[UserResponse])(cache_response("admin_users", ttl=600)(self.read_users))
        self.router.patch("/users/{user_id}/archive")(self.archive_user)
        self.router.patch("/users/{user_id}/unarchive")(self.unarchive_user)
        self.router.post("/register", response_model=AdminResponse, status_code=status.HTTP_200_OK)(self.register_admin)
        self.router.get("/profile/{admin_id}", response_model=AdminResponse)(cache_response("admin_profile", ttl=1800)(self.get_admin_profile_details))
        self.router.put("/profile/{admin_id}", response_model=AdminResponse)(self.update_admin_profile_details)
        self.router.post("/upload-profile-image/{admin_id}")(self.upload_admin_profile_image)

    async def get_hr_activities(self, db: AsyncSession = Depends(get_db)):
        activities = await audit_service.get_recent_hr_activities(db)
        return activities

    async def get_system_stats(self, db: AsyncSession = Depends(get_db)):
        return await admin_service.get_system_stats(db)

    async def get_audit_logs(self, db: AsyncSession = Depends(get_db)):
        return await audit_service.get_all_audit_logs(db)

    async def read_users(self, db: AsyncSession = Depends(get_db)):
        users = await admin_service.get_all_users(db)
        return users

    async def archive_user(self, user_id: int, db: AsyncSession = Depends(get_db)):
        user = await admin_service.toggle_user_archive_status(db, user_id, True)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await clear_cache_pattern("admin_users:*")
        return {"message": "User archived successfully"}

    async def unarchive_user(self, user_id: int, db: AsyncSession = Depends(get_db)):
        user = await admin_service.toggle_user_archive_status(db, user_id, False)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await clear_cache_pattern("admin_users:*")
        return {"message": "User unarchived successfully"}

    async def register_admin(
        self,
        admin_in: AdminCreate, 
        db: AsyncSession = Depends(get_db)
    ):

        new_admin = await admin_service.create_admin_profile(db, admin_in)
        return new_admin

    async def get_admin_profile_details(self, admin_id: int, db: AsyncSession = Depends(get_db)):
        profile = await admin_service.get_admin_profile(db, admin_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")
        return profile

    async def update_admin_profile_details(self, admin_id: int, admin_update: AdminUpdate, db: AsyncSession = Depends(get_db)):
        updated_profile = await admin_service.update_admin_profile(db, admin_id, admin_update)
        if updated_profile:
            await clear_cache_pattern(f"admin_profile:*\"admin_id\": {admin_id}*")
        if not updated_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")
        return updated_profile

    async def upload_admin_profile_image(self, admin_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
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


admin_controller = AdminController()
router = admin_controller.router
