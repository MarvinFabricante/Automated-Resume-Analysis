from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import logging

from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import (
    get_cache,
    set_cache,
    invalidate_application_dashboard_caches,
)

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

        # Invalidate related list & HR dashboard stats caches
        await invalidate_application_dashboard_caches(created_app.id if created_app else None)

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


async def get_by_job_and_email(db: AsyncSession, job_id: int, email: str) -> Optional[JobApplication]:
    """Get existing application for a candidate and job (case-insensitive email)."""
    if not email:
        return None
    normalized_email = email.strip().lower()
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(
            JobApplication.job_id == job_id,
            JobApplication.candidate_email.ilike(normalized_email)
        )
        .order_by(JobApplication.created_at.desc())
    )
    return result.scalars().first()



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


async def get_all_summaries(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get lightweight dashboard summary rows via SQL column projection (checks Redis cache first)."""
    cache_key = "all_apps:summaries:list"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(
            JobApplication.id,
            JobApplication.job_id,
            JobApplication.candidate_name,
            JobApplication.candidate_email,
            JobApplication.phone,
            JobApplication.location,
            JobApplication.job_title,
            JobApplication.company,
            JobApplication.skills,
            JobApplication.match_score,
            JobApplication.skills_score,
            JobApplication.experience_score,
            JobApplication.education_score,
            JobApplication.certifications_score,
            JobApplication.profile_image_url,
            JobApplication.resume_url,
            JobApplication.matched_skills,
            JobApplication.missing_skills,
            JobApplication.total_experience_months,
            JobApplication.highest_educational_attainment,
            JobApplication.experience_gaps,
            JobApplication.ai_powered,
            JobApplication.status,
            JobApplication.created_at,
            JobApplication.updated_at,
            JobDescription.id.label("rel_job_id"),
            JobDescription.job_title.label("rel_job_title"),
            JobDescription.location.label("rel_job_location"),
            JobDescription.department.label("rel_job_department"),
        )
        .select_from(JobApplication)
        .outerjoin(JobDescription, JobApplication.job_id == JobDescription.id)
        .order_by(JobApplication.created_at.desc())
    )
    summaries: List[Dict[str, Any]] = []
    for row in result.all():
        summaries.append({
            "id": row.id,
            "job_id": row.job_id,
            "candidate_name": row.candidate_name,
            "candidate_email": row.candidate_email,
            "phone": row.phone,
            "location": row.location,
            "job_title": row.job_title,
            "company": row.company,
            "skills": row.skills or [],
            "match_score": row.match_score,
            "skills_score": row.skills_score,
            "experience_score": row.experience_score,
            "education_score": row.education_score,
            "certifications_score": row.certifications_score,
            "profile_image_url": row.profile_image_url,
            "resume_url": row.resume_url,
            "matched_skills": row.matched_skills or [],
            "missing_skills": row.missing_skills or [],
            "total_experience_months": row.total_experience_months,
            "highest_educational_attainment": row.highest_educational_attainment,
            "experience_gaps": row.experience_gaps,
            "ai_powered": bool(row.ai_powered),
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "job": (
                {
                    "id": row.rel_job_id,
                    "job_title": row.rel_job_title,
                    "location": row.rel_job_location,
                    "department": row.rel_job_department,
                }
                if row.rel_job_id is not None
                else None
            ),
        })
    await set_cache(cache_key, summaries, ttl=300)
    return summaries


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
        if application not in db:
            application = await db.merge(application)
        await db.commit()
        try:
            await db.refresh(application)
        except Exception:
            pass

        await redis_tx_manager.commit_transaction(tx_id, {"id": application.id})

        # Evict cache for this entity & HR dashboard stats
        await invalidate_application_dashboard_caches(application.id)

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

        await invalidate_application_dashboard_caches(application.id)
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] JobApplication delete failed: {e}")
        raise


import sys
job_application_repository = sys.modules[__name__]
JobApplicationRepository = sys.modules[__name__]
