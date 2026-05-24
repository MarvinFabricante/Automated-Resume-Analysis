from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.interview import Interview, InterviewPanelist, InterviewLog
from app.models.job_application import JobApplication
from app.models.user import User

class InterviewRepository:
    @staticmethod
    async def get_panelists(db: AsyncSession, panelist_ids: List[int]) -> List[User]:
        result = await db.execute(select(User).filter(User.id.in_(panelist_ids)))
        return result.scalars().all()

    @staticmethod
    async def get_job_application(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
        result = await db.execute(select(JobApplication).filter(JobApplication.id == application_id))
        return result.scalars().first()

    @staticmethod
    async def create_interview(db: AsyncSession, interview_data: dict) -> Interview:
        interview = Interview(**interview_data)
        db.add(interview)
        await db.flush() # flush to get id
        return interview

    @staticmethod
    async def add_panelist_to_interview(db: AsyncSession, interview_id: int, user_id: int) -> None:
        db.add(InterviewPanelist(interview_id=interview_id, user_id=user_id))

    @staticmethod
    async def update_interview(db: AsyncSession, interview: Interview) -> Interview:
        await db.commit()
        await db.refresh(interview)
        return interview

    @staticmethod
    async def add_interview_log(db: AsyncSession, interview_id: int, log_type: str, details: str) -> None:
        db.add(InterviewLog(interview_id=interview_id, log_type=log_type, details=details))

    @staticmethod
    async def commit_changes(db: AsyncSession) -> None:
        await db.commit()

    @staticmethod
    async def get_interview_by_id(db: AsyncSession, interview_id: int) -> Optional[Interview]:
        result = await db.execute(select(Interview).filter(Interview.id == interview_id))
        return result.scalars().first()

    @staticmethod
    async def get_interviews_for_application(db: AsyncSession, application_id: int) -> List[Interview]:
        result = await db.execute(select(Interview).filter(Interview.job_application_id == application_id))
        return result.scalars().all()
