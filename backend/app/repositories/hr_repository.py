from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create_hr(db: AsyncSession, hr_data: dict) -> HR:
    """Create HR user (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="hr",
        action="CREATE",
        payload=hr_data,
    )
    try:
        new_hr = HR(**hr_data)
        db.add(new_hr)
        await db.commit()
        await db.refresh(new_hr)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_hr.id})

        await set_cache(f"hr:id:{new_hr.id}", new_hr, ttl=1800)
        await clear_cache_pattern("admin:stats")

        return new_hr
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_hr failed: {e}")
        raise


async def get_hr_by_id(db: AsyncSession, hr_id: int) -> Optional[HR]:
    """Get HR by ID (checks Redis cache first)."""
    cache_key = f"hr:id:{hr_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(HR).where(HR.id == hr_id))
    hr = result.scalar_one_or_none()
    if hr:
        await set_cache(cache_key, hr, ttl=1800)
    return hr


async def update_hr(db: AsyncSession, hr: HR, update_data: dict) -> HR:
    """Update HR (Redis-first transaction)."""
    # Ensure HR instance is persistent within the current session
    result = await db.execute(select(HR).where(HR.id == hr.id))
    current_hr = result.scalar_one_or_none()
    if not current_hr:
        current_hr = await db.merge(hr)

    tx_id = await redis_tx_manager.stage_transaction(
        target="hr",
        action="UPDATE",
        payload={"id": current_hr.id, **update_data},
    )
    try:
        for key, value in update_data.items():
            if hasattr(current_hr, key):
                setattr(current_hr, key, value)
        await db.commit()
        await db.refresh(current_hr)

        await redis_tx_manager.commit_transaction(tx_id, {"id": current_hr.id})

        await delete_cache(f"hr:id:{current_hr.id}")
        await delete_cache(f"user:id:{current_hr.id}")
        if current_hr.email:
            await delete_cache(f"user:email:{current_hr.email.lower()}")

        return current_hr
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_hr failed: {e}")
        raise


async def get_total_candidates_count(db: AsyncSession) -> int:
    """Get total candidates count (checks Redis cache first)."""
    cache_key = "hr:stats:total_candidates"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(func.count(Candidate.id)))
    count = result.scalar() or 0
    await set_cache(cache_key, count, ttl=300)
    return count


async def get_total_resumes_count(db: AsyncSession) -> int:
    """Get total resumes count (checks Redis cache first)."""
    cache_key = "hr:stats:total_resumes"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(func.count(JobApplication.id)))
    count = result.scalar() or 0
    await set_cache(cache_key, count, ttl=300)
    return count


async def get_application_stats_by_status(db: AsyncSession) -> List[Any]:
    """Get application counts by status (checks Redis cache first)."""
    cache_key = "hr:stats:status_counts"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(JobApplication.status, func.count(JobApplication.id)).group_by(JobApplication.status))
    stats = result.all()
    await set_cache(cache_key, stats, ttl=300)
    return stats


async def get_daily_application_counts(db: AsyncSession, start_date: datetime) -> List[Any]:
    """Get daily application counts (checks Redis cache first)."""
    cache_key = f"hr:stats:daily:{start_date.strftime('%Y-%m-%d')}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(
            func.date(JobApplication.created_at),
            func.count(JobApplication.id)
        )
        .where(JobApplication.created_at >= start_date)
        .group_by(func.date(JobApplication.created_at))
    )
    counts = result.all()
    await set_cache(cache_key, counts, ttl=300)
    return counts


async def get_department_application_counts(db: AsyncSession) -> List[Any]:
    """Get department application counts (checks Redis cache first)."""
    cache_key = "hr:stats:dept_counts"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(
            JobDescription.department,
            func.count(JobApplication.id)
        )
        .join(JobApplication, JobApplication.job_id == JobDescription.id)
        .group_by(JobDescription.department)
    )
    counts = result.all()
    await set_cache(cache_key, counts, ttl=300)
    return counts


async def get_distinct_departments(db: AsyncSession) -> List[str]:
    """Get distinct departments list (checks Redis cache first)."""
    cache_key = "hr:stats:distinct_depts"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(JobDescription.department).distinct())
    depts = [r[0] for r in result.all()]
    await set_cache(cache_key, depts, ttl=600)
    return depts


import sys
hr_repository = sys.modules[__name__]
HRRepository = sys.modules[__name__]
