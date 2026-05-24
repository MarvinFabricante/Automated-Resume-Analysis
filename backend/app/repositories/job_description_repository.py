from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from app.models.job_description import JobDescription
from app.models.job_application import JobApplication


class JobDescriptionRepository:
    @staticmethod
    async def create(db: AsyncSession, job_data: dict) -> JobDescription:
        """Create a new job description."""
        db_job = JobDescription(**job_data)
        db.add(db_job)
        await db.commit()
        await db.refresh(db_job)
        return db_job

    @staticmethod
    async def get_by_job_id(db: AsyncSession, job_id: str) -> Optional[JobDescription]:
        """Get job description by job_id."""
        result = await db.execute(
            select(JobDescription).filter(JobDescription.job_id == job_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: int) -> Optional[JobDescription]:
        """Get job description by internal ID."""
        result = await db.execute(
            select(JobDescription).filter(JobDescription.id == job_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_all_active(
        db: AsyncSession, skip: int = 0, limit: int = 100, include_inactive: bool = False
    ) -> List[JobDescription]:
        """Get all job descriptions with optional pagination."""
        query = select(JobDescription)
        if not include_inactive:
            query = query.filter(JobDescription.is_active == True)
        query = query.order_by(desc(JobDescription.id)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, job: JobDescription, update_data: dict) -> JobDescription:
        """Update a job description."""
        for key, value in update_data.items():
            setattr(job, key, value)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def set_status(db: AsyncSession, job: JobDescription, is_active: bool) -> JobDescription:
        """Set job status (active/inactive)."""
        job.is_active = is_active
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def delete(db: AsyncSession, job: JobDescription) -> None:
        """Delete a job description."""
        await db.delete(job)
        await db.commit()

    @staticmethod
    async def get_applications_for_job(db: AsyncSession, job_id: int) -> List[JobApplication]:
        """Get all job applications for a specific job."""
        result = await db.execute(
            select(JobApplication).filter(JobApplication.job_id == job_id)
        )
        return result.scalars().all()

    @staticmethod
    async def bulk_update_applications(
        db: AsyncSession, applications: List[JobApplication]
    ) -> None:
        """Commit bulk updates to job applications."""
        await db.commit()
