import pytest
from datetime import datetime
from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.models.interview import Interview
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_interview_controller_endpoints(client, db_session):
    # Create HR user
    user = User(
        email="controller_hr@example.com",
        password="password123",
        role="HR",
        fullname="Controller HR"
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token({"sub": user.email, "id": user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Google Calendar status
    resp = await client.get("/interviews/google-status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["connected"] is False

    # 2. Calendar feed (empty initially)
    resp = await client.get("/interviews/calendar-feed", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "interviews" in data
    assert "google_events" in data

    # Create job & candidate application
    job = JobDescription(
        job_id="CTRL-JOB-1",
        job_title="DevOps Engineer",
        department="Infrastructure",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="CI/CD Pipelines"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Alice Candidate",
        candidate_email="alice@example.com",
        job_title="DevOps Engineer"
    )
    db_session.add(app)
    await db_session.flush()

    # 3. Schedule interview via POST /interviews/schedule
    schedule_payload = {
        "job_application_id": app.id,
        "title": "DevOps Round 1",
        "description": "Assess Kubernetes and AWS skills",
        "start_time": "2026-09-21T09:00:00", # Monday
        "end_time": "2026-09-21T10:00:00"
    }
    resp = await client.post("/interviews/schedule", json=schedule_payload, headers=headers)
    assert resp.status_code == 200
    scheduled_data = resp.json()
    assert scheduled_data["title"] == "DevOps Round 1"
    assert scheduled_data["candidate_name"] == "Alice Candidate"
    interview_id = scheduled_data["id"]

    # 4. Get all interviews via GET /interviews
    resp = await client.get("/interviews", headers=headers)
    assert resp.status_code == 200
    iv_list = resp.json()
    assert len(iv_list) >= 1
    assert any(i["id"] == interview_id for i in iv_list)

    # 5. Update interview via PUT /interviews/{id}
    update_payload = {
        "title": "DevOps Technical Deep Dive",
        "start_time": "2026-09-21T14:00:00",
        "end_time": "2026-09-21T15:00:00",
        "status": "SCHEDULED"
    }
    resp = await client.put(f"/interviews/{interview_id}", json=update_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "DevOps Technical Deep Dive"

    # 6. Delete interview via DELETE /interviews/{id}
    resp = await client.delete(f"/interviews/{interview_id}", headers=headers)
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]

    # 7. HR interviewers endpoint GET /hr/interviewers
    resp = await client.get("/hr/interviewers", headers=headers)
    assert resp.status_code == 200
    interviewers = resp.json()
    assert isinstance(interviewers, list)
    assert any(i["id"] == user.id for i in interviewers)

