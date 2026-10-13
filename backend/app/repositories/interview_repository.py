from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import logging

from app.models.interview import Interview, InterviewLog
from app.models.job_application import JobApplication
from app.models.user import User
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def get_job_application(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    """Get job application for interview (checks Redis cache first)."""
    cache_key = f"job_app:{application_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(JobApplication).filter(JobApplication.id == application_id))
    app = result.scalars().first()
    if app:
        await set_cache(cache_key, app, ttl=600)
    return app


async def create_interview(db: AsyncSession, interview_data: dict) -> Interview:
    """Create interview (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="interview",
        action="CREATE",
        payload=interview_data,
    )
    try:
        interview = Interview(**interview_data)
        db.add(interview)
        await db.flush()  # flush to get id

        await redis_tx_manager.commit_transaction(tx_id, {"id": interview.id})

        await clear_cache_pattern("interviews:")
        return interview
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_interview failed: {e}")
        raise


async def update_interview(db: AsyncSession, interview: Interview) -> Interview:
    """Update interview (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="interview",
        action="UPDATE",
        payload={"id": interview.id, "status": interview.status},
    )
    try:
        await db.commit()
        await db.refresh(interview)

        await redis_tx_manager.commit_transaction(tx_id, {"id": interview.id, "status": interview.status})

        await delete_cache(f"interview:id:{interview.id}")
        await clear_cache_pattern("interviews:")
        return interview
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_interview failed: {e}")
        raise


async def add_interview_log(db: AsyncSession, interview_id: int, log_type: str, details: str) -> None:
    """Add interview log (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="interview_log",
        action="CREATE",
        payload={"interview_id": interview_id, "log_type": log_type, "details": details[:200]},
    )
    try:
        db.add(InterviewLog(interview_id=interview_id, log_type=log_type, details=details))
        await redis_tx_manager.commit_transaction(tx_id, {"interview_id": interview_id})
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def commit_changes(db: AsyncSession) -> None:
    """Commit changes to database."""
    await db.commit()


async def get_interview_by_id(db: AsyncSession, interview_id: int) -> Optional[Interview]:
    """Get interview by ID (checks Redis cache first)."""
    cache_key = f"interview:id:{interview_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .filter(Interview.id == interview_id)
    )
    interview = result.scalars().first()
    if interview:
        await set_cache(cache_key, interview, ttl=600)
    return interview


async def get_interviews_for_application(db: AsyncSession, application_id: int) -> List[Interview]:
    """Get interviews for job application (checks Redis cache first)."""
    cache_key = f"interviews:app:{application_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .filter(Interview.job_application_id == application_id)
    )
    interviews = result.scalars().all()
    await set_cache(cache_key, interviews, ttl=300)
    return interviews


async def get_interviews_in_range(
    db: AsyncSession, start_time: datetime, end_time: datetime, interviewer_id: Optional[int] = None
) -> List[Interview]:
    """Fetch non-canceled interviews overlapping with range."""
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
    """Get interviews for candidate by email (checks Redis cache first)."""
    cache_key = f"interviews:cand:{email}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .join(JobApplication)
        .filter(JobApplication.candidate_email == email)
    )
    interviews = result.scalars().all()
    await set_cache(cache_key, interviews, ttl=300)
    return interviews


async def get_all_interviews(db: AsyncSession) -> List[Interview]:
    """Get all interviews (checks Redis cache first)."""
    cache_key = "interviews:all"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.job_application), selectinload(Interview.interviewer))
        .order_by(Interview.start_time.asc())
    )
    interviews = result.scalars().all()
    await set_cache(cache_key, interviews, ttl=300)
    return interviews


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
    """Fetch overlapping interviews excluding specific ID."""
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
    """Delete an interview (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="interview",
        action="DELETE",
        payload={"id": interview.id},
    )
    try:
        int_id = interview.id
        await db.delete(interview)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"deleted_id": int_id})

        await delete_cache(f"interview:id:{int_id}")
        await clear_cache_pattern("interviews:")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] delete_interview failed: {e}")
        raise


import sys
interview_repository = sys.modules[__name__]
InterviewRepository = sys.modules[__name__]
