import pytest
from app.services import job_description_service
from app.schemas.job_description_schema import JobCreate, JobUpdate
from app.models.job_description import JobType
from app.models.job_application import JobApplication


@pytest.mark.asyncio
async def test_create_and_get_job(db_session):
    job_in = JobCreate(
        job_id="JOB-TEST-DESC-01",
        job_title="Industrial Engineer",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        salary_range="30k-45k",
        description="Oversee production lines",
        skills_requirements="Lean manufacturing, 5S, Six Sigma",
        education_requirements="BS Industrial Engineering",
        experience_requirements="2 years"
    )

    created_job = await job_description_service.create_job(db_session, job_in)
    assert created_job.id is not None
    assert created_job.job_id == "JOB-TEST-DESC-01"
    assert created_job.job_title == "Industrial Engineer"

    fetched = await job_description_service.get_job(db_session, "JOB-TEST-DESC-01")
    assert fetched is not None
    assert fetched.id == created_job.id
    assert fetched.department == "Manufacturing"


@pytest.mark.asyncio
async def test_get_all_active_jobs(db_session):
    j1 = JobCreate(
        job_id="JOB-ACTIVE-01",
        job_title="Active Job",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Makati",
        description="Active role",
        skills_requirements="Python",
        is_active=True
    )
    j2 = JobCreate(
        job_id="JOB-INACTIVE-01",
        job_title="Inactive Job",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Makati",
        description="Inactive role",
        skills_requirements="Python",
        is_active=False
    )
    await job_description_service.create_job(db_session, j1)
    await job_description_service.create_job(db_session, j2)

    active_only = await job_description_service.get_all_active_jobs(db_session, include_inactive=False)
    active_ids = [j.job_id for j in active_only]
    assert "JOB-ACTIVE-01" in active_ids
    assert "JOB-INACTIVE-01" not in active_ids

    all_jobs = await job_description_service.get_all_active_jobs(db_session, include_inactive=True)
    all_ids = [j.job_id for j in all_jobs]
    assert "JOB-ACTIVE-01" in all_ids
    assert "JOB-INACTIVE-01" in all_ids


@pytest.mark.asyncio
async def test_update_job_and_recalculate_scores(db_session):
    job_in = JobCreate(
        job_id="JOB-SYNC-01",
        job_title="Software Developer",
        department="IT",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Develop apps",
        skills_requirements="Python, Django"
    )
    created_job = await job_description_service.create_job(db_session, job_in)

    # Attach an application to this job
    app = JobApplication(
        job_id=created_job.id,
        candidate_name="Applicant One",
        candidate_email="app1@example.com",
        skills=["Python", "FastAPI"],
        degree="BS Computer Science",
        relevance="3 years software developer"
    )
    db_session.add(app)
    await db_session.commit()

    # Update job requirements
    update_data = JobUpdate(
        job_title="Senior Software Developer",
        skills_requirements="Python, Django, FastAPI, Docker",
        experience_requirements="3 years"
    )
    updated = await job_description_service.update_job(db_session, "JOB-SYNC-01", update_data)
    assert updated is not None
    assert updated.job_title == "Senior Software Developer"

    # Non-existent job update
    res = await job_description_service.update_job(db_session, "JOB-GHOST-01", update_data)
    assert res is None


@pytest.mark.asyncio
async def test_set_job_status_and_delete(db_session):
    job_in = JobCreate(
        job_id="JOB-STATUS-01",
        job_title="Operations Manager",
        department="Operations",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Manage operations",
        skills_requirements="Management"
    )
    created_job = await job_description_service.create_job(db_session, job_in)

    # Deactivate
    deactivated = await job_description_service.set_job_status(db_session, "JOB-STATUS-01", False)
    assert deactivated.is_active is False

    # Delete
    deleted = await job_description_service.delete_job(db_session, "JOB-STATUS-01")
    assert deleted is not None

    # Verify deleted
    assert await job_description_service.get_job(db_session, "JOB-STATUS-01") is None
