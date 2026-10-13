from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.models.candidate import Candidate
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)


async def get_by_id(db: AsyncSession, candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID (checks Redis cache first)."""
    cache_key = f"candidate:id:{candidate_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate:
        await set_cache(cache_key, candidate, ttl=1800)
    return candidate


async def update(db: AsyncSession, candidate: Candidate, update_data: dict) -> Candidate:
    """Update candidate (Redis-first transaction)."""
    # Ensure candidate instance is persistent within the current session
    result = await db.execute(select(Candidate).where(Candidate.id == candidate.id))
    current_candidate = result.scalar_one_or_none()
    if not current_candidate:
        current_candidate = await db.merge(candidate)

    tx_id = await redis_tx_manager.stage_transaction(
        target="candidate",
        action="UPDATE",
        payload={"id": current_candidate.id, **update_data},
    )
    try:
        for key, value in update_data.items():
            if hasattr(current_candidate, key):
                setattr(current_candidate, key, value)
        await db.commit()
        await db.refresh(current_candidate)

        await redis_tx_manager.commit_transaction(tx_id, {"id": current_candidate.id})

        # Evict / Update Redis cache
        await delete_cache(f"candidate:id:{current_candidate.id}")
        await delete_cache(f"user:id:{current_candidate.id}")
        if current_candidate.email:
            await delete_cache(f"user:email:{current_candidate.email.lower()}")

        return current_candidate
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] candidate update failed: {e}")
        raise


async def create(db: AsyncSession, candidate_data: dict) -> Candidate:
    """Create candidate (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="candidate",
        action="CREATE",
        payload=candidate_data,
    )
    try:
        new_candidate = Candidate(**candidate_data)
        db.add(new_candidate)
        await db.commit()
        await db.refresh(new_candidate)

        await redis_tx_manager.commit_transaction(tx_id, {"id": new_candidate.id})

        await set_cache(f"candidate:id:{new_candidate.id}", new_candidate, ttl=1800)
        await clear_cache_pattern("admin:stats")
        await clear_cache_pattern("hr:stats")

        return new_candidate
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] candidate create failed: {e}")
        raise


import sys
candidate_repository = sys.modules[__name__]
CandidateRepository = sys.modules[__name__]
