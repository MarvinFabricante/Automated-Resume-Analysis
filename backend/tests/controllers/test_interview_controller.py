import pytest
from datetime import datetime
from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from unittest.mock import patch, AsyncMock
from app.utils.auth import create_access_token

@pytest.fixture(autouse=True)
def mock_interview_emails():
    with patch("app.services.email_service.EmailService.send_interview_invitation_email", new_callable=AsyncMock) as m1, \
         patch("app.services.email_service.EmailService.send_interview_rescheduled_email", new_callable=AsyncMock) as m2:
        m1.return_value = True
        m2.return_value = True
        yield (m1, m2)

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


@pytest.mark.asyncio
async def test_interview_exclusivity_and_permissions(client, db_session):
    # HR 1 (Interviewer)
    hr1 = User(
        email="hr_owner@example.com",
        password="password123",
        role="HR",
        fullname="HR Owner"
    )
    # HR 2 (Different HR)
    hr2 = User(
        email="hr_other@example.com",
        password="password123",
        role="HR",
        fullname="HR Other"
    )
    # Admin User
    admin = User(
        email="admin_user@example.com",
        password="password123",
        role="ADMIN",
        fullname="Admin User"
    )
    db_session.add_all([hr1, hr2, admin])
    await db_session.flush()

    token_hr1 = create_access_token({"sub": hr1.email, "id": hr1.id, "role": "HR"})
    token_hr2 = create_access_token({"sub": hr2.email, "id": hr2.id, "role": "HR"})
    token_admin = create_access_token({"sub": admin.email, "id": admin.id, "role": "ADMIN"})

    headers_hr1 = {"Authorization": f"Bearer {token_hr1}"}
    headers_hr2 = {"Authorization": f"Bearer {token_hr2}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    job = JobDescription(
        job_id="CTRL-EXCL-1",
        job_title="Backend Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="FastAPI Backend"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Charlie Exclusive",
        candidate_email="charlie@example.com",
        job_title="Backend Engineer"
    )
    db_session.add(app)
    await db_session.flush()

    # 1. HR 1 schedules an active interview for Charlie
    schedule_payload = {
        "job_application_id": app.id,
        "interviewer_id": hr1.id,
        "title": "Backend Interview with HR 1",
        "start_time": "2026-09-22T09:00:00",
        "end_time": "2026-09-22T10:00:00"
    }
    resp1 = await client.post("/interviews/schedule", json=schedule_payload, headers=headers_hr1)
    assert resp1.status_code == 200
    iv_data = resp1.json()
    interview_id = iv_data["id"]

    # 2. HR 2 attempts to schedule another interview for the same candidate -> 409 Conflict
    conflict_payload = {
        "job_application_id": app.id,
        "interviewer_id": hr2.id,
        "title": "Duplicate Interview attempt",
        "start_time": "2026-09-23T10:00:00",
        "end_time": "2026-09-23T11:00:00"
    }
    resp2 = await client.post("/interviews/schedule", json=conflict_payload, headers=headers_hr2)
    assert resp2.status_code == 409
    assert "already scheduled" in resp2.json()["detail"]

    # 3. HR 2 attempts to update HR 1's interview -> 403 Forbidden
    update_payload = {
        "title": "Unauthorized Update attempt"
    }
    resp3 = await client.put(f"/interviews/{interview_id}", json=update_payload, headers=headers_hr2)
    assert resp3.status_code == 403
    assert "permission" in resp3.json()["detail"].lower()

    # 4. HR 2 attempts to change status of HR 1's interview -> 403 Forbidden
    resp4 = await client.put(f"/interviews/{interview_id}/status?status=COMPLETED", headers=headers_hr2)
    assert resp4.status_code == 403

    # 5. HR 2 attempts to delete HR 1's interview -> 403 Forbidden
    resp5 = await client.delete(f"/interviews/{interview_id}", headers=headers_hr2)
    assert resp5.status_code == 403

    # 6. Admin can update HR 1's interview -> 200 OK
    resp_admin = await client.put(f"/interviews/{interview_id}", json={"title": "Admin Updated"}, headers=headers_admin)
    assert resp_admin.status_code == 200
    assert resp_admin.json()["title"] == "Admin Updated"

    # 7. HR 1 (assigned owner) can update -> 200 OK
    resp_owner = await client.put(f"/interviews/{interview_id}", json={"title": "Owner Updated"}, headers=headers_hr1)
    assert resp_owner.status_code == 200
    assert resp_owner.json()["title"] == "Owner Updated"

    # 8. HR 1 (assigned owner) can delete -> 200 OK
    resp_del = await client.delete(f"/interviews/{interview_id}", headers=headers_hr1)
    assert resp_del.status_code == 200


