import pytest
from datetime import datetime, timedelta
from app.repositories import hr_repository
from app.models.candidate import Candidate
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_hr_repo_crud(db_session):
    hr_data = {
        "fullname": "HR Repo Officer",
        "email": "hr_repo_officer@example.com",
        "password": hash_password("pass123"),
        "role": "HR",
        "company_name": "Mariwasa Tiles"
    }

    # 1. Create HR
    created = await hr_repository.create_hr(db_session, hr_data)
    assert created.id is not None
    assert created.company_name == "Mariwasa Tiles"
    hr_id = created.id

    # 2. Get HR by id
    fetched = await hr_repository.get_hr_by_id(db_session, hr_id)
    assert fetched is not None
    assert fetched.fullname == "HR Repo Officer"

    # 3. Update HR
    updated = await hr_repository.update_hr(db_session, fetched, {
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Talent Acquisition"
    })
    assert updated.company_name == "Mariwasa Siam Ceramics, Inc."


@pytest.mark.asyncio
async def test_hr_repo_stats_queries(db_session):
    # Candidate
    cand = Candidate(
        fullname="Stats Cand",
        email="cand_stats@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    # Job Description
    job = JobDescription(
        job_id="HR-REPO-JOB-001",
        job_title="Ceramic Glazing Specialist",
        department="Ceramics Production",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Glazing and kilns operation",
        skills_requirements="Glazing, Kilns"
    )
    db_session.add_all([cand, job])
    await db_session.commit()

    # Job Application
    app = JobApplication(
        job_id=job.id,
        candidate_name="Stats Cand",
        candidate_email="cand_stats@example.com",
        status="PENDING",
        created_at=datetime.utcnow()
    )
    db_session.add(app)
    await db_session.commit()

    # 1. Total candidates count
    cand_count = await hr_repository.get_total_candidates_count(db_session)
    assert cand_count >= 1

    # 2. Total resumes count
    res_count = await hr_repository.get_total_resumes_count(db_session)
    assert res_count >= 1

    # 3. Application stats by status
    status_stats = await hr_repository.get_application_stats_by_status(db_session)
    assert len(status_stats) >= 1

    # 4. Daily application counts
    start_date = datetime.utcnow() - timedelta(days=7)
    daily = await hr_repository.get_daily_application_counts(db_session, start_date)
    assert isinstance(daily, list)

    # 5. Department application counts & distinct departments
    dept_counts = await hr_repository.get_department_application_counts(db_session)
    assert len(dept_counts) >= 1
    assert any(dc[0] == "Ceramics Production" for dc in dept_counts)

    distinct_depts = await hr_repository.get_distinct_departments(db_session)
    assert "Ceramics Production" in distinct_depts
