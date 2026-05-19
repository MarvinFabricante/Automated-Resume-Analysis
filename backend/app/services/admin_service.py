from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.admin import Admin
from app.schemas.admin_schema import AdminCreate, AdminUpdate
from app.utils.auth import hash_password

async def get_all_users(db: AsyncSession):
    """
    Fetches all users from the database.
    """
    result = await db.execute(select(User))
    return result.scalars().all()

async def create_admin_profile(db: AsyncSession, admin_in: AdminCreate):
    """
    Creates a new Admin profile. 
    SQLAlchemy handles the polymorphic 'users' table entry automatically.
    """
    email_lower = admin_in.email.strip().lower()
    new_admin = Admin(
        fullname=admin_in.fullname,
        email=email_lower,
        password=hash_password(admin_in.password),
        role="ADMIN",
        managed_region=admin_in.managed_region
    )
    
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin

async def get_admin_profile(db: AsyncSession, admin_id: int):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    return result.scalar_one_or_none()

async def update_admin_profile(db: AsyncSession, admin_id: int, admin_update: AdminUpdate):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        return None
    
    update_data = admin_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(admin, key, value)
    
    await db.commit()
    await db.refresh(admin)
    return admin

async def toggle_user_archive_status(db: AsyncSession, user_id: int, archive_status: bool):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    
    user.is_archived = archive_status
    await db.commit()
    await db.refresh(user)
    return user

async def get_system_stats(db: AsyncSession):
    from sqlalchemy import func
    from app.models.hr import HR
    from app.models.candidate import Candidate
    from app.models.job_description import JobDescription
    
    hr_count = await db.execute(select(func.count(HR.id)))
    candidate_count = await db.execute(select(func.count(Candidate.id)))
    job_count = await db.execute(select(func.count(JobDescription.id)))
    
    hr_total = hr_count.scalar()
    candidate_total = candidate_count.scalar()
    job_total = job_count.scalar()
    
    return {
        "total_users": hr_total + candidate_total,
        "hr_count": hr_total,
        "candidate_count": candidate_total,
        "job_count": job_total
    }