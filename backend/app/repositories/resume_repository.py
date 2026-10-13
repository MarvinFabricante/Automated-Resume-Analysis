from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from app.models.resume import Resume
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, resume_data: dict) -> Resume:
    """Create a new resume (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="resume",
        action="CREATE",
        payload=resume_data,
    )
    try:
        new_resume = Resume(**resume_data)
        db.add(new_resume)
        await db.commit()
        await db.refresh(new_resume)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_resume.id, "candidate_id": new_resume.candidate_id})

        # Cache in Redis
        await set_cache(f"resume:id:{new_resume.id}", new_resume, ttl=3600)
        if new_resume.candidate_id:
            await clear_cache_pattern(f"resumes:cand:{new_resume.candidate_id}")
        await clear_cache_pattern("resume_count")

        return new_resume
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] Resume create failed: {e}")
        raise


async def get_by_id(db: AsyncSession, resume_id: int) -> Optional[Resume]:
    """Get resume by ID (checks Redis cache first)."""
    cache_key = f"resume:id:{resume_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Resume).filter(Resume.id == resume_id))
    resume = result.scalars().first()
    if resume:
        await set_cache(cache_key, resume, ttl=3600)
    return resume


async def get_by_candidate_id(db: AsyncSession, candidate_id: int) -> List[Resume]:
    """Get all resumes for a candidate (checks Redis cache first)."""
    cache_key = f"resumes:cand:{candidate_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Resume).filter(Resume.candidate_id == candidate_id)
    )
    resumes = result.scalars().all()
    await set_cache(cache_key, resumes, ttl=1800)
    return resumes


async def update(db: AsyncSession, resume: Resume, update_data: dict) -> Resume:
    """Update a resume (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="resume",
        action="UPDATE",
        payload={"id": resume.id, **update_data},
    )
    try:
        for key, value in update_data.items():
            setattr(resume, key, value)
        await db.commit()
        await db.refresh(resume)

        await redis_tx_manager.commit_transaction(tx_id, {"id": resume.id})

        await delete_cache(f"resume:id:{resume.id}")
        if resume.candidate_id:
            await clear_cache_pattern(f"resumes:cand:{resume.candidate_id}")

        return resume
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] Resume update failed: {e}")
        raise


async def delete(db: AsyncSession, resume: Resume) -> None:
    """Delete a resume (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="resume",
        action="DELETE",
        payload={"id": resume.id, "candidate_id": resume.candidate_id},
    )
    try:
        res_id = resume.id
        cand_id = resume.candidate_id
        await db.delete(resume)
        await db.commit()

        await redis_tx_manager.commit_transaction(tx_id, {"deleted_id": res_id})

        await delete_cache(f"resume:id:{res_id}")
        if cand_id:
            await clear_cache_pattern(f"resumes:cand:{cand_id}")
        await clear_cache_pattern("resume_count")
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] Resume delete failed: {e}")
        raise


class ResumeRepository:
    create = staticmethod(create)
    get_by_id = staticmethod(get_by_id)
    get_by_candidate_id = staticmethod(get_by_candidate_id)
    update = staticmethod(update)
    delete = staticmethod(delete)
