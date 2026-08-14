from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.models.resume import Resume


async def create(db: AsyncSession, resume_data: dict) -> Resume:
    """Create a new resume."""
    new_resume = Resume(**resume_data)
    db.add(new_resume)
    await db.commit()
    await db.refresh(new_resume)
    return new_resume

async def get_by_id(db: AsyncSession, resume_id: int) -> Optional[Resume]:
    """Get resume by ID."""
    result = await db.execute(select(Resume).filter(Resume.id == resume_id))
    return result.scalars().first()

async def get_by_candidate_id(db: AsyncSession, candidate_id: int) -> List[Resume]:
    """Get all resumes for a candidate."""
    result = await db.execute(
        select(Resume).filter(Resume.candidate_id == candidate_id)
    )
    return result.scalars().all()

async def update(db: AsyncSession, resume: Resume, update_data: dict) -> Resume:
    """Update a resume."""
    for key, value in update_data.items():
        setattr(resume, key, value)
    await db.commit()
    await db.refresh(resume)
    return resume

async def delete(db: AsyncSession, resume: Resume) -> None:
    """Delete a resume."""
    await db.delete(resume)
    await db.commit()


class ResumeRepository:
    create = staticmethod(create)
    get_by_id = staticmethod(get_by_id)
    get_by_candidate_id = staticmethod(get_by_candidate_id)
    update = staticmethod(update)
    delete = staticmethod(delete)
