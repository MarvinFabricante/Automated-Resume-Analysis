from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.models.candidate import Candidate


async def get_by_id(db: AsyncSession, candidate_id: int) -> Optional[Candidate]:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def update(db: AsyncSession, candidate: Candidate, update_data: dict) -> Candidate:
    for key, value in update_data.items():
        setattr(candidate, key, value)
    await db.commit()
    await db.refresh(candidate)
    return candidate


async def create(db: AsyncSession, candidate_data: dict) -> Candidate:
    new_candidate = Candidate(**candidate_data)
    db.add(new_candidate)
    await db.commit()
    await db.refresh(new_candidate)
    return new_candidate


class CandidateRepository:
    get_by_id = staticmethod(get_by_id)
    update = staticmethod(update)
    create = staticmethod(create)
