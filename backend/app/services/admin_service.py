from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.admin_schema import AdminCreate, AdminUpdate
from app.utils.auth import hash_password
from app.repositories.admin_repository import AdminRepository

class AdminService:
    async def get_all_users(self, db: AsyncSession):
        """
        Fetches all users from the database.
        """
        return await AdminRepository.get_all_users(db)

    async def create_admin_profile(self, db: AsyncSession, admin_in: AdminCreate):
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

    async def get_admin_profile(self, db: AsyncSession, admin_id: int):
        return await AdminRepository.get_admin_by_id(db, admin_id)

    async def update_admin_profile(self, db: AsyncSession, admin_id: int, admin_update: AdminUpdate):
        admin = await AdminRepository.get_admin_by_id(db, admin_id)
        if not admin:
            return None

        update_data = admin_update.dict(exclude_unset=True)
        return await AdminRepository.update_admin(db, admin, update_data)

    async def toggle_user_archive_status(self, db: AsyncSession, user_id: int, archive_status: bool):
        user = await AdminRepository.get_user_by_id(db, user_id)
        if not user:
            return None

        return await AdminRepository.update_user_archive_status(db, user, archive_status)

    async def get_system_stats(self, db: AsyncSession):
        return await AdminRepository.get_system_stats(db)


admin_service = AdminService()


async def get_all_users(db: AsyncSession):
    return await admin_service.get_all_users(db)


async def create_admin_profile(db: AsyncSession, admin_in: AdminCreate):
    return await admin_service.create_admin_profile(db, admin_in)


async def get_admin_profile(db: AsyncSession, admin_id: int):
    return await admin_service.get_admin_profile(db, admin_id)


async def update_admin_profile(db: AsyncSession, admin_id: int, admin_update: AdminUpdate):
    return await admin_service.update_admin_profile(db, admin_id, admin_update)


async def toggle_user_archive_status(db: AsyncSession, user_id: int, archive_status: bool):
    return await admin_service.toggle_user_archive_status(db, user_id, archive_status)


async def get_system_stats(db: AsyncSession):
    return await admin_service.get_system_stats(db)
