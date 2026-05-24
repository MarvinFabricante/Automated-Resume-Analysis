from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.candidate_schema import CandidateCreate, CandidateUpdate
from app.utils.auth import hash_password
from app.repositories.candidate_repository import CandidateRepository
from app.services.notification_service import create_notification

class CandidateService:
    async def get_candidate_profile(self, db: AsyncSession, candidate_id: int):
        """
        Fetches a candidate profile by ID.
        """
        return await CandidateRepository.get_by_id(db, candidate_id)

    async def update_candidate_profile(self, db: AsyncSession, candidate_id: int, candidate_update: CandidateUpdate):
        """
        Updates an existing candidate profile.
        """
        candidate = await CandidateRepository.get_by_id(db, candidate_id)

        if not candidate:
            return None

        update_data = candidate_update.dict(exclude_unset=True)
        return await CandidateRepository.update(db, candidate, update_data)

    async def create_candidate_profile(self, db: AsyncSession, candidate_in: CandidateCreate):
        """
        Creates a new Candidate profile.
        SQLAlchemy handles the polymorphic 'users' table entry automatically.
        """
        email_lower = candidate_in.email.strip().lower()
        candidate_data = {
            "fullname": candidate_in.fullname,
            "email": email_lower,
            "password": hash_password(candidate_in.password),
            "role": "CANDIDATE",
            "resume_url": candidate_in.resume_url,
            "experience_years": candidate_in.experience_years
        }

        new_candidate = await CandidateRepository.create(db, candidate_data)

        # Trigger notification
        await create_notification(
            db=db,
            title="New Candidate Registration",
            message=f"{new_candidate.fullname} has joined the platform.",
            type="registration"
        )

        return new_candidate


candidate_service = CandidateService()


async def get_candidate_profile(db: AsyncSession, candidate_id: int):
    return await candidate_service.get_candidate_profile(db, candidate_id)


async def update_candidate_profile(db: AsyncSession, candidate_id: int, candidate_update: CandidateUpdate):
    return await candidate_service.update_candidate_profile(db, candidate_id, candidate_update)


async def create_candidate_profile(db: AsyncSession, candidate_in: CandidateCreate):
    return await candidate_service.create_candidate_profile(db, candidate_in)
