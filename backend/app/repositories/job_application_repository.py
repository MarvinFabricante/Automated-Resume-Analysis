from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.job_application import JobApplication

async def create(db: AsyncSession, application_data: dict) -> JobApplication:
    new_application = JobApplication(**application_data)
    db.add(new_application)
    await db.commit()
        
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.id == new_application.id)
    )
    return result.scalars().first()

async def get_by_job_id(db: AsyncSession, job_id: int) -> List[JobApplication]:
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.job_id == job_id)
    )
    return result.scalars().all()

async def get_by_email(db: AsyncSession, email: str) -> List[JobApplication]:
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.candidate_email == email)
        .order_by(JobApplication.created_at.desc())
    )
    return result.scalars().all()

async def get_all(db: AsyncSession) -> List[JobApplication]:
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .order_by(JobApplication.created_at.desc())
    )
    return result.scalars().all()

async def get_by_id(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.id == application_id)
    )
    return result.scalars().first()

async def update(db: AsyncSession, application: JobApplication) -> JobApplication:
    await db.commit()
    await db.refresh(application)
    return application

async def delete(db: AsyncSession, application: JobApplication) -> None:
    await db.delete(application)
    await db.commit()


class JobApplicationRepository:
    create = staticmethod(create)
    get_by_job_id = staticmethod(get_by_job_id)
    get_by_email = staticmethod(get_by_email)
    get_all = staticmethod(get_all)
    get_by_id = staticmethod(get_by_id)
    update = staticmethod(update)
    delete = staticmethod(delete)
