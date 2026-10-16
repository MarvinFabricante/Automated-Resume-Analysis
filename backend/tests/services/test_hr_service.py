import pytest
from app.services import hr_service
from app.schemas.hr_schema import HRCreate, HRUpdate
from app.models.candidate import Candidate
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication


@pytest.mark.asyncio
async def test_create_and_get_hr_profile(db_session):
    hr_in = HRCreate(
        fullname="Elena Gomez",
        email="elena_gomez@example.com",
        password="secretpassword123",
        company_name="Mariwasa Siam Ceramics",
        department="Talent Acquisition"
    )

    hr = await hr_service.create_hr_profile(db_session, hr_in)
    assert hr.id is not None
    assert hr.fullname == "Elena Gomez"
    assert hr.email == "elena_gomez@example.com"
    assert hr.company_name == "Mariwasa Siam Ceramics"
    assert hr.department == "Talent Acquisition"
    assert hr.role == "HR"

    fetched = await hr_service.get_hr_profile(db_session, hr.id)
    assert fetched is not None
    assert fetched.id == hr.id
    assert fetched.email == "elena_gomez@example.com"


@pytest.mark.asyncio
async def test_update_hr_profile(db_session):
    hr_in = HRCreate(
        fullname="Carlos Reyes",
        email="carlos_reyes@example.com",
        password="password123",
        company_name="Mariwasa",
        department="Operations"
    )
    hr = await hr_service.create_hr_profile(db_session, hr_in)

    update_in = HRUpdate(
        fullname="Carlos Reyes Jr.",
        position="Senior Recruiter",
        phone="+639181112222",
        location="Batangas"
    )
    updated = await hr_service.update_hr_profile(db_session, hr.id, update_in)
    assert updated is not None
    assert updated.fullname == "Carlos Reyes Jr."
    assert updated.position == "Senior Recruiter"
    assert updated.phone == "+639181112222"
    assert updated.location == "Batangas"

    # Non-existent profile
    assert await hr_service.update_hr_profile(db_session, 999999, update_in) is None


@pytest.mark.asyncio
async def test_update_hr_duplicate_email(db_session):
    hr1 = await hr_service.create_hr_profile(
        db_session,
        HRCreate(fullname="HR 1", email="hr1@example.com", password="pass", company_name="M")
    )
    hr2 = await hr_service.create_hr_profile(
        db_session,
        HRCreate(fullname="HR 2", email="hr2@example.com", password="pass", company_name="M")
    )

    with pytest.raises(Exception) as excinfo:
        await hr_service.update_hr_profile(
            db_session,
            hr2.id,
            HRUpdate(email="hr1@example.com")
        )
    assert "already in use" in str(excinfo.value)


@pytest.mark.asyncio
async def test_hr_counts_and_stats(db_session):
    # Setup candidate
    cand = Candidate(
        fullname="Stat Candidate",
        email="stat_cand@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(cand)

    # Setup Job and Application
    job = JobDescription(
        job_id="JOB-HR-001",
        job_title="Ceramic Specialist",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Ceramics production"
    )
    db_session.add(job)
    await db_session.flush()

    app1 = JobApplication(
        job_id=job.id,
        candidate_name="Stat Candidate",
        candidate_email="stat_cand@example.com",
        job_title="Ceramic Specialist",
        status="PENDING"
    )
    app2 = JobApplication(
        job_id=job.id,
        candidate_name="Stat Candidate 2",
        candidate_email="stat_cand2@example.com",
        job_title="Ceramic Specialist",
        status="ACCEPTED"
    )
    db_session.add_all([app1, app2])
    await db_session.commit()

    cand_count = await hr_service.get_total_candidates_count(db_session)
    assert cand_count >= 1

    stats = await hr_service.get_application_stats(db_session)
    assert stats["pending"] >= 1
    assert stats["accepted"] >= 1
    assert "reviewed" in stats
    assert "rejected" in stats

    trends = await hr_service.get_dashboard_trends(db_session)
    assert "weekly_trends" in trends
    assert len(trends["weekly_trends"]) == 7
    assert "department_distribution" in trends
    assert trends["total_applications"] >= 2
