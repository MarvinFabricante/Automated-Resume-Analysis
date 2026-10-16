import pytest
from unittest.mock import patch, MagicMock
from app.services import job_application_service
from app.schemas.job_application_schema import JobApplicationCreate
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication


@pytest.fixture
def mock_celery_task():
    with patch("app.tasks.analyze_application_task.delay") as mock_delay:
        yield mock_delay


@pytest.mark.asyncio
async def test_create_job_application(db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-APP-001",
        job_title="Full Stack Developer",
        department="IT",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Development role"
    )
    db_session.add(job)
    await db_session.flush()

    app_in = JobApplicationCreate(
        job_id="JOB-APP-001",
        candidate_name="Alex Morgan",
        candidate_email="alex.morgan@example.com",
        phone="+639191234567",
        job_title="Full Stack Developer",
        skills=["Python", "React", "Docker"],
        degree="BS Computer Science",
        relevance="3 years experience as full stack developer"
    )

    created_app = await job_application_service.create_job_application(
        db=db_session,
        application_in=app_in,
        db_job_id=job.id
    )

    assert created_app is not None
    assert created_app.id is not None
    assert created_app.candidate_name == "Alex Morgan"
    assert created_app.candidate_email == "alex.morgan@example.com"
    assert created_app.job_id == job.id
    mock_celery_task.assert_called_once_with(created_app.id)


@pytest.mark.asyncio
async def test_get_applications_queries(db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-APP-002",
        job_title="QA Lead",
        department="QA",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Lead QA"
    )
    db_session.add(job)
    await db_session.flush()

    app_in = JobApplicationCreate(
        job_id="JOB-APP-002",
        candidate_name="Sam QA",
        candidate_email="sam.qa@example.com",
        job_title="QA Lead"
    )
    created = await job_application_service.create_job_application(db_session, app_in, job.id)

    # By Job
    by_job = await job_application_service.get_applications_by_job(db_session, job.id)
    assert len(by_job) >= 1
    assert any(a.id == created.id for a in by_job)

    # By Email
    by_email = await job_application_service.get_applications_by_email(db_session, "sam.qa@example.com")
    assert len(by_email) >= 1
    assert any(a.id == created.id for a in by_email)

    # All applications
    all_apps = await job_application_service.get_all_applications(db_session)
    assert len(all_apps) >= 1


@pytest.mark.asyncio
async def test_update_application_status_and_notifications(db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-APP-003",
        job_title="Database Admin",
        department="IT",
        job_type=JobType.FULL_TIME,
        location="Makati",
        description="DBA role"
    )
    db_session.add(job)
    await db_session.flush()

    app_in = JobApplicationCreate(
        job_id="JOB-APP-003",
        candidate_name="DBA Candidate",
        candidate_email="dba.cand@example.com"
    )
    created = await job_application_service.create_job_application(db_session, app_in, job.id)

    # Update to ACCEPTED
    updated = await job_application_service.update_application_status(db_session, created.id, "ACCEPTED")
    assert updated is not None
    assert updated.status == "ACCEPTED"

    # Update to TECHNICAL INTERVIEW
    updated_tech = await job_application_service.update_application_status(db_session, created.id, "TECHNICAL INTERVIEW")
    assert updated_tech is not None
    assert updated_tech.status == "TECHNICAL INTERVIEW"

    # Update non-existent application
    assert await job_application_service.update_application_status(db_session, 999999, "REJECTED") is None


@pytest.mark.asyncio
async def test_delete_application(db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-APP-004",
        job_title="Security Analyst",
        department="Security",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Sec role"
    )
    db_session.add(job)
    await db_session.flush()

    app_in = JobApplicationCreate(
        job_id="JOB-APP-004",
        candidate_name="Sec Candidate",
        candidate_email="sec.cand@example.com"
    )
    created = await job_application_service.create_job_application(db_session, app_in, job.id)

    # Delete
    deleted = await job_application_service.delete_application(db_session, created.id)
    assert deleted is not None
    assert deleted.id == created.id

    # Non-existent delete
    assert await job_application_service.delete_application(db_session, 999999) is None


@pytest.mark.asyncio
async def test_get_and_validate_job(db_session):
    job = JobDescription(
        job_id="JOB-VALIDATE-01",
        job_title="DevOps Engineer",
        department="Operations",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Infra and CI/CD"
    )
    db_session.add(job)
    await db_session.flush()

    # By string job_id
    found = await job_application_service.get_and_validate_job(db_session, "JOB-VALIDATE-01")
    assert found is not None
    assert found.id == job.id

    # By numeric ID as string
    found_num = await job_application_service.get_and_validate_job(db_session, str(job.id))
    assert found_num is not None
    assert found_num.job_title == "DevOps Engineer"


def test_resume_data_and_needs_enrichment_helpers():
    app = JobApplication(
        candidate_name="Resume Helper",
        candidate_email="helper@example.com",
        skills=["Python", "Flask"],
        relevance="5 years experience",
        degree="Bachelor of Science",
        college="UP Diliman"
    )

    data = job_application_service._resume_data_from_application(app)
    assert data["fullname"] == "Resume Helper"
    assert "Python" in data["skills"]
    assert data["years_experience"] == 5
    assert "UP Diliman" in data["education"]

    assert job_application_service._needs_analysis_enrichment(app) is True
