import pytest
from app.repositories import job_application_repository
from app.models.job_description import JobDescription, JobType


@pytest.mark.asyncio
async def test_job_application_repo_lifecycle(db_session):
    # Setup Job
    job = JobDescription(
        job_id="APP-REPO-JOB-001",
        job_title="Kiln Technician",
        department="Ceramics",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Kiln control and operations",
        skills_requirements="Kiln Operation, High Heat Safety"
    )
    db_session.add(job)
    await db_session.commit()
    job_id = job.id

    # 1. Create Application
    app_data = {
        "job_id": job_id,
        "candidate_name": "Applicant Repo Tester",
        "candidate_email": "app_repo_test@example.com",
        "phone": "09181234567",
        "status": "PENDING",
        "match_score": 85.5
    }
    created = await job_application_repository.create(db_session, app_data)
    assert created.id is not None
    assert created.candidate_email == "app_repo_test@example.com"
    app_id = created.id

    # 2. Get by ID
    by_id = await job_application_repository.get_by_id(db_session, app_id)
    assert by_id is not None
    assert by_id.id == app_id

    # 3. Get by Job ID
    by_job = await job_application_repository.get_by_job_id(db_session, job_id)
    assert len(by_job) >= 1
    assert any(a.id == app_id for a in by_job)

    # 4. Get by Email
    by_email = await job_application_repository.get_by_email(db_session, "app_repo_test@example.com")
    assert len(by_email) >= 1
    assert any(a.id == app_id for a in by_email)

    # 5. Get All
    all_apps = await job_application_repository.get_all(db_session)
    assert len(all_apps) >= 1

    # 6. Update
    by_id.status = "ACCEPTED"
    by_id.match_score = 92.0
    updated = await job_application_repository.update(db_session, by_id)
    assert updated.status == "ACCEPTED"
    assert updated.match_score == 92.0

    # 7. Delete
    await job_application_repository.delete(db_session, updated)
    assert await job_application_repository.get_by_id(db_session, app_id) is None
