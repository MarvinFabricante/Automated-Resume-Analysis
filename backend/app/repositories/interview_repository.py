from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from app.models.interview import Interview, InterviewLog
from app.models.job_application import JobApplication
from app.models.user import User


async def get_job_application(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    result = await db.execute(select(JobApplication).filter(JobApplication.id == application_id))
    return result.scalars().first()

async def create_interview(db: AsyncSession, interview_data: dict) -> Interview:
    interview = Interview(**interview_data)
    db.add(interview)
    await db.flush() # flush to get id
    return interview


async def update_interview(db: AsyncSession, interview: Interview) -> Interview:
    await db.commit()
    await db.refresh(interview)
    return interview

async def add_interview_log(db: AsyncSession, interview_id: int, log_type: str, details: str) -> None:
    db.add(InterviewLog(interview_id=interview_id, log_type=log_type, details=details))

async def commit_changes(db: AsyncSession) -> None:
    await db.commit()

async def get_interview_by_id(db: AsyncSession, interview_id: int) -> Optional[Interview]:
    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    return result.scalars().first()

async def get_interviews_for_application(db: AsyncSession, application_id: int) -> List[Interview]:
    result = await db.execute(select(Interview).filter(Interview.job_application_id == application_id))
    return result.scalars().all()

async def get_interviews_in_range(db: AsyncSession, start_time: datetime, end_time: datetime) -> List[Interview]:
    """Fetch all non-canceled interviews that overlap with the given date range."""
    result = await db.execute(
        select(Interview).filter(
            and_(
                Interview.start_time < end_time,
                Interview.end_time > start_time,
                Interview.status != "CANCELED",
            )
        )
    )
    return result.scalars().all()



class InterviewRepository:
    get_job_application = staticmethod(get_job_application)
    create_interview = staticmethod(create_interview)
    update_interview = staticmethod(update_interview)
    add_interview_log = staticmethod(add_interview_log)
    commit_changes = staticmethod(commit_changes)
    get_interview_by_id = staticmethod(get_interview_by_id)
    get_interviews_for_application = staticmethod(get_interviews_for_application)
    get_interviews_in_range = staticmethod(get_interviews_in_range)
