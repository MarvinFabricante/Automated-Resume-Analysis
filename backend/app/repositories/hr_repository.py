from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from typing import Optional, Dict, Any, List
from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from datetime import datetime

async def create_hr(db: AsyncSession, hr_data: dict) -> HR:
    new_hr = HR(**hr_data)
    db.add(new_hr)
    await db.commit()
    await db.refresh(new_hr)
    return new_hr

async def get_hr_by_id(db: AsyncSession, hr_id: int) -> Optional[HR]:
    result = await db.execute(select(HR).where(HR.id == hr_id))
    return result.scalar_one_or_none()

async def update_hr(db: AsyncSession, hr: HR, update_data: dict) -> HR:
    for key, value in update_data.items():
        setattr(hr, key, value)
    await db.commit()
    await db.refresh(hr)
    return hr

async def get_total_candidates_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Candidate.id)))
    return result.scalar()

async def get_total_resumes_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(JobApplication.id)))
    return result.scalar()

async def get_application_stats_by_status(db: AsyncSession) -> List[Any]:
    result = await db.execute(select(JobApplication.status, func.count(JobApplication.id)).group_by(JobApplication.status))
    return result.all()

async def get_daily_application_counts(db: AsyncSession, start_date: datetime) -> List[Any]:
    result = await db.execute(
        select(
            cast(JobApplication.created_at, Date),
            func.count(JobApplication.id)
        )
        .where(JobApplication.created_at >= start_date)
        .group_by(cast(JobApplication.created_at, Date))
    )
    return result.all()

async def get_department_application_counts(db: AsyncSession) -> List[Any]:
    result = await db.execute(
        select(
            JobDescription.department,
            func.count(JobApplication.id)
        )
        .join(JobApplication, JobApplication.job_id == JobDescription.id)
        .group_by(JobDescription.department)
    )
    return result.all()

async def get_distinct_departments(db: AsyncSession) -> List[str]:
    result = await db.execute(select(JobDescription.department).distinct())
    return [r[0] for r in result.all()]


class HRRepository:
    create_hr = staticmethod(create_hr)
    get_hr_by_id = staticmethod(get_hr_by_id)
    update_hr = staticmethod(update_hr)
    get_total_candidates_count = staticmethod(get_total_candidates_count)
    get_total_resumes_count = staticmethod(get_total_resumes_count)
    get_application_stats_by_status = staticmethod(get_application_stats_by_status)
    get_daily_application_counts = staticmethod(get_daily_application_counts)
    get_department_application_counts = staticmethod(get_department_application_counts)
    get_distinct_departments = staticmethod(get_distinct_departments)
