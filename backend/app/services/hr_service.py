from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.hr import HR
from app.schemas.hr_schema import HRCreate, HRUpdate
from app.utils.auth import hash_password
from app.services.notification_service import create_notification

async def create_hr_profile(db: AsyncSession, hr_in: HRCreate):
    email_lower = hr_in.email.strip().lower()
    new_hr = HR(
        fullname=hr_in.fullname,
        email=email_lower,
        password=hash_password(hr_in.password),
        role="HR",
        company_name=hr_in.company_name,
        department=hr_in.department
    )
    
    db.add(new_hr)
    await db.commit()
    await db.refresh(new_hr)
    
    # Trigger notification for Admin
    await create_notification(
        db=db,
        title="New HR Registration",
        message=f"{new_hr.fullname} has registered as HR for {new_hr.company_name}.",
        type="hr_registration",
        target_role="ADMIN"
    )
    
    return new_hr

async def get_hr_profile(db: AsyncSession, hr_id: int):
    result = await db.execute(select(HR).where(HR.id == hr_id))
    return result.scalar_one_or_none()

async def update_hr_profile(db: AsyncSession, hr_id: int, hr_update: HRUpdate):
    result = await db.execute(select(HR).where(HR.id == hr_id))
    hr = result.scalar_one_or_none()
    if not hr:
        return None
    
    update_data = hr_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hr, key, value)
    
    await db.commit()
    await db.refresh(hr)
    return hr

async def get_total_candidates_count(db: AsyncSession):
    from app.models.candidate import Candidate
    from sqlalchemy import func
    result = await db.execute(select(func.count(Candidate.id)))
    return result.scalar()

async def get_total_resumes_count(db: AsyncSession):
    from app.models.job_application import JobApplication
    from sqlalchemy import func
    result = await db.execute(select(func.count(JobApplication.id)))
    return result.scalar()

async def get_application_stats(db: AsyncSession):
    from app.models.job_application import JobApplication
    from sqlalchemy import func
    
    # Get counts grouped by status
    result = await db.execute(select(JobApplication.status, func.count(JobApplication.id)).group_by(JobApplication.status))
    stats = {row[0]: row[1] for row in result.all()}
    
    return {
        "pending": stats.get("PENDING", 0),
        "reviewed": stats.get("REVIEWED", 0),
        "accepted": stats.get("ACCEPTED", 0),
        "rejected": stats.get("REJECTED", 0)
    }