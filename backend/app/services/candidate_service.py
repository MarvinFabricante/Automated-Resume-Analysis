from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.candidate import Candidate
from app.schemas.candidate_schema import CandidateCreate, CandidateUpdate
from app.utils.auth import hash_password

async def get_candidate_profile(db: AsyncSession, candidate_id: int):
    """
    Fetches a candidate profile by ID.
    """
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()

async def update_candidate_profile(db: AsyncSession, candidate_id: int, candidate_update: CandidateUpdate):
    """
    Updates an existing candidate profile.
    """
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        return None
        
    update_data = candidate_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(candidate, key, value)
        
    await db.commit()
    await db.refresh(candidate)
    return candidate

from app.services.notification_service import create_notification

async def create_candidate_profile(db: AsyncSession, candidate_in: CandidateCreate):
    """
    Creates a new Candidate profile. 
    SQLAlchemy handles the polymorphic 'users' table entry automatically.
    """
    email_lower = candidate_in.email.strip().lower()
    new_candidate = Candidate(
        fullname=candidate_in.fullname,
        email=email_lower,
        password=hash_password(candidate_in.password),
        role="CANDIDATE",
        resume_url=candidate_in.resume_url,
        experience_years=candidate_in.experience_years
    )
    
    db.add(new_candidate)
    await db.commit()
    await db.refresh(new_candidate)
    
    # Trigger notification
    await create_notification(
        db=db,
        title="New Candidate Registration",
        message=f"{new_candidate.fullname} has joined the platform.",
        type="registration"
    )
    
    return new_candidate