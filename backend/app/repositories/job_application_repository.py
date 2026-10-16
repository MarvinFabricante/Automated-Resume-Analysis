from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
import logging

from app.models.job_application import JobApplication
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, application_data: dict) -> JobApplication:
    """Create a new job application (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_application",
        action="CREATE",
        payload=application_data,
    )
    try:
        new_application = JobApplication(**application_data)
        db.add(new_application)
        await db.commit()
            
        result = await db.execute(
            select(JobApplication)
            .options(selectinload(JobApplication.job))
            .filter(JobApplication.id == new_application.id)
        )
        created_app = result.scalars().first()

        await redis_tx_manager.commit_transaction(tx_id, {"id": created_app.id if created_app else None})

        # Invalidate related list caches
        await clear_cache_pattern("job_apps")
        await clear_cache_pattern("cand_apps")
        await clear_cache_pattern("all_apps")
        await clear_cache_pattern("app_stats")

        return created_app
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobApplication create failed: {e}")
        raise


async def get_by_job_id(db: AsyncSession, job_id: int) -> List[JobApplication]:
    """Get all applications for a job (checks Redis cache first)."""
    cache_key = f"job_apps:by_job:{job_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.job_id == job_id)
    )
    apps = result.scalars().all()
    await set_cache(cache_key, apps, ttl=300)
    return apps


async def get_by_email(db: AsyncSession, email: str) -> List[JobApplication]:
    """Get all applications by email (checks Redis cache first)."""
    cache_key = f"cand_apps:by_email:{email}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.candidate_email == email)
        .order_by(JobApplication.created_at.desc())
    )
    apps = result.scalars().all()
    await set_cache(cache_key, apps, ttl=300)
    return apps


async def get_all(db: AsyncSession) -> List[JobApplication]:
    """Get all applications (checks Redis cache first)."""
    cache_key = "all_apps:list"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .order_by(JobApplication.created_at.desc())
    )
    apps = result.scalars().all()
    await set_cache(cache_key, apps, ttl=300)
    return apps


async def get_by_id(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    """Get application by ID (checks Redis cache first)."""
    cache_key = f"job_app:{application_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.id == application_id)
    )
    app = result.scalars().first()
    if app:
        await set_cache(cache_key, app, ttl=600)
    return app


async def update(db: AsyncSession, application: JobApplication) -> JobApplication:
    """Update job application (Redis-first transaction)."""
    tx_payload = {
        "id": application.id,
        "status": getattr(application, "status", None),
        "match_score": getattr(application, "match_score", None),
    }
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_application",
        action="UPDATE",
        payload=tx_payload,
    )
    try:
        await db.commit()
        await db.refresh(application)

        await redis_tx_manager.commit_transaction(tx_id, {"id": application.id})

        # Evict cache for this entity & lists
        await delete_cache(f"job_app:{application.id}")
        await clear_cache_pattern("job_apps")
        await clear_cache_pattern("cand_apps")
        await clear_cache_pattern("all_apps")
        await clear_cache_pattern("app_stats")

        return application
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobApplication update failed: {e}")
        raise


async def delete(db: AsyncSession, application: JobApplication) -> None:
    """Delete job application (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="job_application",
        action="DELETE",
        payload={"id": application.id, "job_id": application.job_id},
    )
    try:
        try:
            await db.execute(
                text("""
                    DELETE FROM interview_panelists 
                    WHERE interview_id IN (SELECT id FROM interviews WHERE job_application_id = :app_id)
                """),
                {"app_id": application.id}
            )
        except Exception:
            pass
        await db.execute(
            text("""
                DELETE FROM interview_logs 
                WHERE interview_id IN (SELECT id FROM interviews WHERE job_application_id = :app_id)
            """),
            {"app_id": application.id}
        )
        await db.execute(
            text("DELETE FROM interviews WHERE job_application_id = :app_id"),
            {"app_id": application.id}
        )
        await db.delete(application)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"deleted_id": application.id})

        await delete_cache(f"job_app:{application.id}")
        await clear_cache_pattern("job_apps")
        await clear_cache_pattern("cand_apps")
        await clear_cache_pattern("all_apps")
        await clear_cache_pattern("app_stats")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobApplication delete failed: {e}")
        raise


import sys
job_application_repository = sys.modules[__name__]
JobApplicationRepository = sys.modules[__name__]
