from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.admin import Admin
from app.schemas.admin_schema import AdminCreate, AdminUpdate
from app.utils.auth import hash_password
from app.repositories.admin_repository import AdminRepository

async def get_all_users(db: AsyncSession):
    """
    Fetches all users from the database.
    """
    return await AdminRepository.get_all_users(db)

async def create_admin_profile(db: AsyncSession, admin_in: AdminCreate):
    """
    Creates a new Admin profile. 
    SQLAlchemy handles the polymorphic 'users' table entry automatically.
    """
    email_lower = admin_in.email.strip().lower()
    admin_data = {
        "fullname": admin_in.fullname,
        "email": email_lower,
        "password": hash_password(admin_in.password),
        "role": "ADMIN",
        "managed_region": admin_in.managed_region
    }
    return await AdminRepository.create_admin(db, admin_data)

async def get_admin_profile(db: AsyncSession, admin_id: int):
    return await AdminRepository.get_admin_by_id(db, admin_id)

async def update_admin_profile(db: AsyncSession, admin_id: int, admin_update: AdminUpdate):
    admin = await AdminRepository.get_admin_by_id(db, admin_id)
    if not admin:
        return None
    
    update_data = admin_update.dict(exclude_unset=True)
    return await AdminRepository.update_admin(db, admin, update_data)

async def toggle_user_archive_status(db: AsyncSession, user_id: int, archive_status: bool):
    user = await AdminRepository.get_user_by_id(db, user_id)
    if not user:
        return None
    
    return await AdminRepository.update_user_archive_status(db, user, archive_status)

async def get_system_stats(db: AsyncSession):
    return await AdminRepository.get_system_stats(db)