import pytest
from app.repositories import job_description_repository
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication


@pytest.mark.asyncio
async def test_job_description_repo_lifecycle(db_session):
    job_data = {
        "job_id": "JD-REPO-001",
        "job_title": "Production Supervisor",
        "department": "Tile Manufacturing",
        "job_type": JobType.FULL_TIME,
        "location": "Sto. Tomas, Batangas",
        "salary_range": "40k-60k",
        "description": "Supervise tile sorting line",
        "skills_requirements": "Supervision, 5S, Quality Inspection",
        "is_active": True
    }

    # 1. Create
    created = await job_description_repository.create(db_session, job_data)
    assert created.id is not None
    assert created.job_id == "JD-REPO-001"
    job_id = created.id

    # 2. Get by job_id code
    by_code = await job_description_repository.get_by_job_id(db_session, "JD-REPO-001")
    assert by_code is not None
    assert by_code.id == job_id

    # 3. Get by internal ID
    by_id = await job_description_repository.get_by_id(db_session, job_id)
    assert by_id is not None
    assert by_id.job_title == "Production Supervisor"

    # 4. Get all active
    active_jobs = await job_description_repository.get_all_active(db_session)
    assert len(active_jobs) >= 1
    assert any(j.id == job_id for j in active_jobs)

    # 5. Update
    updated = await job_description_repository.update(db_session, by_id, {
        "salary_range": "45k-65k",
        "job_title": "Senior Production Supervisor"
    })
    assert updated.salary_range == "45k-65k"
    assert updated.job_title == "Senior Production Supervisor"

    # 6. Set status (deactivate / reactivate)
    deactivated = await job_description_repository.set_status(db_session, updated, False)
    assert deactivated.is_active is False

    reactivated = await job_description_repository.set_status(db_session, deactivated, True)
    assert reactivated.is_active is True

    # 7. Applications for job & bulk update
    app = JobApplication(
        job_id=job_id,
        candidate_name="Test Applicant",
        candidate_email="applicant@example.com",
        status="PENDING"
    )
    db_session.add(app)
    await db_session.commit()

    apps = await job_description_repository.get_applications_for_job(db_session, job_id)
    assert len(apps) >= 1

    app.status = "REVIEWED"
    await job_description_repository.bulk_update_applications(db_session, [app])

    # 8. Delete
    await job_description_repository.delete(db_session, reactivated)
    assert await job_description_repository.get_by_id(db_session, job_id) is None
