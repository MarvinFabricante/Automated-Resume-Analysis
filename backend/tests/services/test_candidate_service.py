import pytest
from app.services import candidate_service
from app.schemas.candidate_schema import CandidateCreate, CandidateUpdate


@pytest.mark.asyncio
async def test_create_and_get_candidate_profile(db_session):
    cand_in = CandidateCreate(
        fullname="John Candidate",
        email="john_cand@example.com",
        password="secretpassword123",
        resume_url="https://example.com/resume.pdf",
        experience_years=3
    )

    candidate = await candidate_service.create_candidate_profile(db_session, cand_in)
    assert candidate.id is not None
    assert candidate.fullname == "John Candidate"
    assert candidate.email == "john_cand@example.com"
    assert candidate.experience_years == 3

    fetched = await candidate_service.get_candidate_profile(db_session, candidate.id)
    assert fetched is not None
    assert fetched.id == candidate.id
    assert fetched.email == "john_cand@example.com"


@pytest.mark.asyncio
async def test_get_nonexistent_candidate_profile(db_session):
    res = await candidate_service.get_candidate_profile(db_session, 999999)
    assert res is None


@pytest.mark.asyncio
async def test_update_candidate_profile_success(db_session):
    cand_in = CandidateCreate(
        fullname="Maria Santos",
        email="maria_santos@example.com",
        password="password123"
    )
    candidate = await candidate_service.create_candidate_profile(db_session, cand_in)

    update_in = CandidateUpdate(
        fullname="Maria Santos-Cruz",
        phone="+639171234567",
        location="Makati, Metro Manila",
        bio="Full-stack engineer with 4 years experience",
        experience_years=4
    )
    updated = await candidate_service.update_candidate_profile(db_session, candidate.id, update_in)
    assert updated is not None
    assert updated.fullname == "Maria Santos-Cruz"
    assert updated.phone == "+639171234567"
    assert updated.location == "Makati, Metro Manila"
    assert updated.experience_years == 4


@pytest.mark.asyncio
async def test_update_candidate_profile_duplicate_email(db_session):
    c1 = await candidate_service.create_candidate_profile(
        db_session,
        CandidateCreate(fullname="Candidate One", email="c1@example.com", password="pass")
    )
    c2 = await candidate_service.create_candidate_profile(
        db_session,
        CandidateCreate(fullname="Candidate Two", email="c2@example.com", password="pass")
    )

    with pytest.raises(Exception) as excinfo:
        await candidate_service.update_candidate_profile(
            db_session,
            c2.id,
            CandidateUpdate(email="c1@example.com")
        )
    assert "already in use" in str(excinfo.value)


@pytest.mark.asyncio
async def test_update_nonexistent_candidate_profile(db_session):
    res = await candidate_service.update_candidate_profile(
        db_session,
        999999,
        CandidateUpdate(fullname="Ghost Candidate")
    )
    assert res is None
