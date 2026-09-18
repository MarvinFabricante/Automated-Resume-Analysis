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

from sqlalchemy.orm import selectinload

async def get_interview_by_id(db: AsyncSession, interview_id: int) -> Optional[Interview]:
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .filter(Interview.id == interview_id)
    )
    return result.scalars().first()

async def get_interviews_for_application(db: AsyncSession, application_id: int) -> List[Interview]:
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .filter(Interview.job_application_id == application_id)
    )
    return result.scalars().all()

async def get_interviews_in_range(db: AsyncSession, start_time: datetime, end_time: datetime, interviewer_id: Optional[int] = None) -> List[Interview]:
    """Fetch all non-canceled interviews that overlap with the given date range, optionally filtered by interviewer."""
    conditions = [
        Interview.start_time < end_time,
        Interview.end_time > start_time,
        Interview.status != "CANCELED",
    ]
    if interviewer_id:
        from sqlalchemy import or_
        conditions.append(or_(Interview.interviewer_id == interviewer_id, Interview.interviewer_id.is_(None)))
    result = await db.execute(
        select(Interview).filter(and_(*conditions))
    )
    return result.scalars().all()



async def get_interviews_for_candidate(db: AsyncSession, email: str) -> List[Interview]:
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .join(JobApplication)
        .filter(JobApplication.candidate_email == email)
    )
    return result.scalars().all()


async def get_all_interviews(db: AsyncSession) -> List[Interview]:
    """Fetch all interviews with their associated job application and interviewer details."""
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .order_by(Interview.start_time.asc())
    )
    return result.scalars().all()


async def get_interview_by_google_event_id(db: AsyncSession, google_event_id: str) -> Optional[Interview]:
    """Fetch an interview by its Google Calendar event ID."""
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .filter(Interview.google_event_id == google_event_id)
    )
    return result.scalars().first()


async def get_interviews_in_range_excluding(
    db: AsyncSession, start_time: datetime, end_time: datetime, exclude_interview_id: int
) -> List[Interview]:
    """Fetch all non-canceled interviews that overlap with the given date range, excluding a specific interview ID."""
    result = await db.execute(
        select(Interview).filter(
            and_(
                Interview.id != exclude_interview_id,
                Interview.start_time < end_time,
                Interview.end_time > start_time,
                Interview.status != "CANCELED",
            )
        )
    )
    return result.scalars().all()


async def delete_interview(db: AsyncSession, interview: Interview) -> None:
    """Delete an interview from the database."""
    await db.delete(interview)
    await db.commit()


class InterviewRepository:
    get_job_application = staticmethod(get_job_application)
    create_interview = staticmethod(create_interview)
    update_interview = staticmethod(update_interview)
    add_interview_log = staticmethod(add_interview_log)
    commit_changes = staticmethod(commit_changes)
    get_interview_by_id = staticmethod(get_interview_by_id)
    get_all_interviews = staticmethod(get_all_interviews)
    get_interview_by_google_event_id = staticmethod(get_interview_by_google_event_id)
    get_interviews_for_application = staticmethod(get_interviews_for_application)
    get_interviews_in_range = staticmethod(get_interviews_in_range)
    get_interviews_in_range_excluding = staticmethod(get_interviews_in_range_excluding)
    get_interviews_for_candidate = staticmethod(get_interviews_for_candidate)
    delete_interview = staticmethod(delete_interview)

