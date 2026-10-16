import pytest
from unittest.mock import patch
from app.models.job_description import JobDescription, JobType


@pytest.fixture
def mock_celery_task():
    with patch("app.tasks.analyze_application_task.delay") as mock_delay:
        yield mock_delay


@pytest.mark.asyncio
async def test_job_application_crud_endpoints(client, db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-CTRL-01",
        job_title="Software Architect",
        department="IT",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Architecture and systems design"
    )
    db_session.add(job)
    await db_session.commit()

    # Submit application
    app_payload = {
        "job_id": "JOB-CTRL-01",
        "candidate_name": "Alice Architect",
        "candidate_email": "alice.arch@example.com",
        "phone": "+639112223344",
        "skills": ["Python", "Microservices", "Docker"]
    }
    create_res = await client.post("/applications/", json=app_payload)
    assert create_res.status_code == 201
    data = create_res.json()
    app_id = data["id"]
    assert data["candidate_name"] == "Alice Architect"

    # Get all applications
    all_res = await client.get("/applications/")
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 1

    # Get applications by job
    by_job_res = await client.get(f"/applications/job/{job.id}")
    assert by_job_res.status_code == 200
    assert any(a["id"] == app_id for a in by_job_res.json())

    # Get applications by candidate email
    by_email_res = await client.get("/applications/candidate/alice.arch@example.com")
    assert by_email_res.status_code == 200
    assert any(a["id"] == app_id for a in by_email_res.json())

    # Update status (PATCH)
    status_payload = {"status": "TECHNICAL INTERVIEW"}
    patch_res = await client.patch(f"/applications/{app_id}/status", json=status_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "TECHNICAL INTERVIEW"

    # Delete application (204)
    del_res = await client.delete(f"/applications/{app_id}")
    assert del_res.status_code == 204

    # Delete non-existent
    assert (await client.delete("/applications/999999")).status_code == 404


@pytest.mark.asyncio
async def test_create_application_nonexistent_job(client):
    app_payload = {
        "job_id": "NON-EXISTENT-JOB-999",
        "candidate_name": "Ghost Candidate",
        "candidate_email": "ghost@example.com"
    }
    res = await client.post("/applications/", json=app_payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"
