from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
import logging

from app.models.job_description import JobDescription
from app.models.job_application import JobApplication
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, job_data: dict) -> JobDescription:
    """Create a new job description (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_description",
        action="CREATE",
        payload=job_data,
    )
    try:
        db_job = JobDescription(**job_data)
        db.add(db_job)
        await db.commit()
        await db.refresh(db_job)

        await redis_tx_manager.commit_transaction(tx_id, {"id": db_job.id, "job_id": db_job.job_id})

        # Cache entity in Redis
        await set_cache(f"job_desc:id:{db_job.id}", db_job, ttl=1800)
        await set_cache(f"job_desc:code:{db_job.job_id}", db_job, ttl=1800)
        await clear_cache_pattern("job_desc:active:")
        await clear_cache_pattern("admin:stats")

        return db_job
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobDescription create failed: {e}")
        raise


async def get_by_job_id(db: AsyncSession, job_id: str) -> Optional[JobDescription]:
    """Get job description by job_id code (checks Redis cache first)."""
    cache_key = f"job_desc:code:{job_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobDescription).filter(JobDescription.job_id == job_id)
    )
    job = result.scalars().first()
    if job:
        await set_cache(cache_key, job, ttl=1800)
        await set_cache(f"job_desc:id:{job.id}", job, ttl=1800)
    return job


async def get_by_id(db: AsyncSession, job_id: int) -> Optional[JobDescription]:
    """Get job description by internal ID (checks Redis cache first)."""
    cache_key = f"job_desc:id:{job_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobDescription).filter(JobDescription.id == job_id)
    )
    job = result.scalars().first()
    if job:
        await set_cache(cache_key, job, ttl=1800)
        if job.job_id:
            await set_cache(f"job_desc:code:{job.job_id}", job, ttl=1800)
    return job


async def get_all_active(
    db: AsyncSession, skip: int = 0, limit: int = 100, include_inactive: bool = False
) -> List[JobDescription]:
    """Get all job descriptions (checks Redis cache first)."""
    cache_key = f"job_desc:active:{skip}:{limit}:{include_inactive}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    query = select(JobDescription)
    if not include_inactive:
        query = query.filter(JobDescription.is_active == True)
    query = query.order_by(desc(JobDescription.id)).offset(skip).limit(limit)
        
    result = await db.execute(query)
    jobs = result.scalars().all()
    await set_cache(cache_key, jobs, ttl=600)
    return jobs


async def update(db: AsyncSession, job: JobDescription, update_data: dict) -> JobDescription:
    """Update a job description (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_description",
        action="UPDATE",
        payload={"id": job.id, "job_id": job.job_id, **update_data},
    )
    try:
        for key, value in update_data.items():
            setattr(job, key, value)
        await db.commit()
        await db.refresh(job)

        await redis_tx_manager.commit_transaction(tx_id, {"id": job.id})

        # Update / Evict cache
        await delete_cache(f"job_desc:id:{job.id}")
        if job.job_id:
            await delete_cache(f"job_desc:code:{job.job_id}")
        await clear_cache_pattern("job_desc:active:")
        await clear_cache_pattern("admin:stats")

        return job
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobDescription update failed: {e}")
        raise


async def set_status(db: AsyncSession, job: JobDescription, is_active: bool) -> JobDescription:
    """Set job status (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_description",
        action="SET_STATUS",
        payload={"id": job.id, "is_active": is_active},
    )
    try:
        job.is_active = is_active
        await db.commit()
        await db.refresh(job)

        await redis_tx_manager.commit_transaction(tx_id, {"id": job.id, "is_active": is_active})

        await delete_cache(f"job_desc:id:{job.id}")
        if job.job_id:
            await delete_cache(f"job_desc:code:{job.job_id}")
        await clear_cache_pattern("job_desc:active:")

        return job
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobDescription set_status failed: {e}")
        raise


async def delete(db: AsyncSession, job: JobDescription) -> None:
    """Delete a job description (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_description",
        action="DELETE",
        payload={"id": job.id, "job_id": job.job_id},
    )
    try:
        job_id = job.id
        job_code = job.job_id
        await db.delete(job)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"deleted_id": job_id})

        await delete_cache(f"job_desc:id:{job_id}")
        if job_code:
            await delete_cache(f"job_desc:code:{job_code}")
        await clear_cache_pattern("job_desc:active:")
        await clear_cache_pattern("admin:stats")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobDescription delete failed: {e}")
        raise


async def get_applications_for_job(db: AsyncSession, job_id: int) -> List[JobApplication]:
    """Get all job applications for a specific job."""
    result = await db.execute(
        select(JobApplication).filter(JobApplication.job_id == job_id)
    )
    return result.scalars().all()


async def bulk_update_applications(
    db: AsyncSession, applications: List[JobApplication]
) -> None:
    """Commit bulk updates to job applications (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_application",
        action="BULK_UPDATE",
        payload={"count": len(applications)},
    )
    try:
        await db.commit()
        await redis_tx_manager.commit_transaction(tx_id, {"updated_count": len(applications)})
        await clear_cache_pattern("job_apps")
        await clear_cache_pattern("cand_apps")
        await clear_cache_pattern("all_apps")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


class JobDescriptionRepository:
    create = staticmethod(create)
    get_by_job_id = staticmethod(get_by_job_id)
    get_by_id = staticmethod(get_by_id)
    get_all_active = staticmethod(get_all_active)
    update = staticmethod(update)
    set_status = staticmethod(set_status)
    delete = staticmethod(delete)
    get_applications_for_job = staticmethod(get_applications_for_job)
    bulk_update_applications = staticmethod(bulk_update_applications)
