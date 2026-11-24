import sys
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.candidate_schema import CandidateCreate, CandidateUpdate
from app.repositories.candidate_repository import CandidateRepository
from app.services.notification_service import create_notification


async def get_candidate_profile(db: AsyncSession, candidate_id: int):
    """
    Fetches a candidate profile by ID.
    """
    return await CandidateRepository.get_by_id(db, candidate_id)


async def update_candidate_profile(db: AsyncSession, candidate_id: int, candidate_update: CandidateUpdate):
    """
    Updates an existing candidate profile.
    """
    candidate = await CandidateRepository.get_by_id(db, candidate_id)

    if not candidate:
        return None

    update_data = candidate_update.dict(exclude_unset=True)
    # Profile/resume review must never change the login identity.
    update_data.pop("email", None)

    return await CandidateRepository.update(db, candidate, update_data)


async def create_candidate_profile(db: AsyncSession, candidate_in: CandidateCreate):
    """
    Creates a new Candidate profile.
    SQLAlchemy handles the polymorphic 'users' table entry automatically.
    """
    from app.services.auth_service import register_user
    new_candidate = await register_user(
        db, candidate_in.email, candidate_in.password, "CANDIDATE", candidate_in.fullname,
        candidate_fields={"resume_url": candidate_in.resume_url, "experience_years": candidate_in.experience_years or 0},
    )

    # Trigger notification for HR and Admin
    await create_notification(
        db=db,
        title="New Candidate Registration",
        message=f"{new_candidate.fullname} has joined the platform.",
        type="registration",
        target_role="HR",
        sender_role="CANDIDATE"
    )

    return new_candidate


candidate_service = sys.modules[__name__]
