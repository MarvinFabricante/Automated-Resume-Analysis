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


@pytest.mark.asyncio
async def test_available_slots_endpoint_free_slot_detection_hr01(client, db_session):
    """
    TEST-ID: 1
    Module: Interview Scheduling
    Scenario: Free-slot detection
    Steps: Block 10:00-11:00 on hr01 calendar, request slots via POST /interviews/available-slots
    Expected Result: Only 9:00AM-5:00PM slots shown (excluding 10:00-11:00)
    """
    hr01 = User(
        email="hr01_controller@example.com",
        password="password123",
        role="HR",
        fullname="HR 01"
    )
    db_session.add(hr01)
    await db_session.flush()

    job = JobDescription(
        job_id="CTRL-JOB-SLOT-1",
        job_title="Backend Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="FastAPI"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Candidate Slot Test",
        candidate_email="cand_slot_test@example.com",
        job_title="Backend Engineer"
    )
    db_session.add(app)
    await db_session.flush()

    token = create_access_token({"sub": hr01.email, "id": hr01.id, "role": "HR"})
    headers_hr01 = {"Authorization": f"Bearer {token}"}

    # Step 1: Block 10:00-11:00 on hr01 calendar
    block_resp = await client.post(
        "/interviews/schedule",
        json={
            "job_application_id": app.id,
            "interviewer_id": hr01.id,
            "title": "Blocked Slot 10-11",
            "start_time": "2026-09-22T10:00:00",
            "end_time": "2026-09-22T11:00:00",
        },
        headers=headers_hr01,
    )
    assert block_resp.status_code == 200

    # Step 2: Request slots for 2026-09-22 on hr01 calendar
    slots_resp = await client.post(
        "/interviews/available-slots",
        json={
            "start_date": "2026-09-22T08:00:00",
            "end_date": "2026-09-22T18:00:00",
            "hr_id": hr01.id,
        },
        headers=headers_hr01,
    )
    assert slots_resp.status_code == 200
    slots = slots_resp.json()
    assert len(slots) > 0

    for slot in slots:
        start_dt = datetime.fromisoformat(slot["start_time"])
        end_dt = datetime.fromisoformat(slot["end_time"])
        # Only 9:00 AM - 5:00 PM slots shown
        assert start_dt.hour >= 9
        assert end_dt.hour < 17 or (end_dt.hour == 17 and end_dt.minute == 0)
        # 10:00-11:00 blocked interval must not overlap any returned slot
        assert not (
            start_dt < datetime(2026, 9, 22, 11, 0, 0)
            and end_dt > datetime(2026, 9, 22, 10, 0, 0)
        )


@pytest.mark.asyncio
async def test_available_slots_endpoint_business_hours_full_day(client, db_session):
    """
    TEST-ID: 2
    Module: Interview Scheduling
    Scenario: Business Hours
    Steps: Request slots for a full day via POST /interviews/available-slots
    Expected Result: Only 9:00AM to 5:00PM slots shown
    """
    hr_user = User(
        email="hr_ctrl_biz_hours@example.com",
        password="password123",
        role="HR",
        fullname="HR Biz Hours"
    )
    db_session.add(hr_user)
    await db_session.flush()

    token = create_access_token({"sub": hr_user.email, "id": hr_user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/interviews/available-slots",
        json={
            "start_date": "2026-09-24T00:00:00",
            "end_date": "2026-09-24T23:59:59",
            "hr_id": hr_user.id,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    slots = resp.json()
    assert len(slots) > 0

    first_start = datetime.fromisoformat(slots[0]["start_time"])
    last_end = datetime.fromisoformat(slots[-1]["end_time"])
    assert first_start == datetime(2026, 9, 24, 9, 0, 0)
    assert last_end == datetime(2026, 9, 24, 17, 0, 0)

    for slot in slots:
        start_dt = datetime.fromisoformat(slot["start_time"])
        end_dt = datetime.fromisoformat(slot["end_time"])
        assert start_dt >= datetime(2026, 9, 24, 9, 0, 0)
        assert end_dt <= datetime(2026, 9, 24, 17, 0, 0)


@pytest.mark.asyncio
async def test_available_slots_endpoint_hr_and_manager_mutually_free_slots(client, db_session):
    """
    TEST-ID: 3
    Module: Interview Scheduling
    Scenario: HR and manager both busy at different times
    Expected Result: Only mutually free slots offered
    """
    hr_user = User(
        email="hr_ctrl_mut@example.com",
        password="password123",
        role="HR",
        fullname="HR Ctrl Mut"
    )
    mgr_user = User(
        email="mgr_ctrl_mut@example.com",
        password="password123",
        role="HR",
        fullname="Mgr Ctrl Mut"
    )
    db_session.add_all([hr_user, mgr_user])
    await db_session.flush()

    job = JobDescription(
        job_id="CTRL-JOB-MUT-1",
        job_title="Frontend Specialist",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="React & Next.js"
    )
    db_session.add(job)
    await db_session.flush()

    app1 = JobApplication(
        job_id=job.id,
        candidate_name="Applicant Alpha",
        candidate_email="alpha@example.com",
        job_title="Frontend Specialist"
    )
    app2 = JobApplication(
        job_id=job.id,
        candidate_name="Applicant Beta",
        candidate_email="beta@example.com",
        job_title="Frontend Specialist"
    )
    db_session.add_all([app1, app2])
    await db_session.flush()

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr_user.email, 'id': hr_user.id, 'role': 'HR'})}"}

    # Step 1: Schedule HR interview from 10:00 to 11:00 on Monday, 2026-09-28
    block_hr = await client.post(
        "/interviews/schedule",
        json={
            "job_application_id": app1.id,
            "interviewer_id": hr_user.id,
            "title": "HR Screening",
            "start_time": "2026-09-28T10:00:00",
            "end_time": "2026-09-28T11:00:00",
        },
        headers=headers,
    )
    assert block_hr.status_code == 200

    # Step 2: Schedule Manager interview from 14:00 to 15:00 on Monday, 2026-09-28
    block_mgr = await client.post(
        "/interviews/schedule",
        json={
            "job_application_id": app2.id,
            "interviewer_id": mgr_user.id,
            "title": "Technical Deep Dive",
            "start_time": "2026-09-28T14:00:00",
            "end_time": "2026-09-28T15:00:00",
        },
        headers=headers,
    )
    assert block_mgr.status_code == 200

    # Step 3: Request available slots specifying both HR and Manager
    slots_resp = await client.post(
        "/interviews/available-slots",
        json={
            "start_date": "2026-09-28T08:00:00",
            "end_date": "2026-09-28T18:00:00",
            "hr_id": hr_user.id,
            "manager_id": mgr_user.id,
        },
        headers=headers,
    )
    assert slots_resp.status_code == 200
    slots = slots_resp.json()
    assert len(slots) > 0

    slot_windows = []
    for s in slots:
        st = datetime.fromisoformat(s["start_time"])
        et = datetime.fromisoformat(s["end_time"])
        slot_windows.append((st.strftime("%H:%M"), et.strftime("%H:%M")))
        # Ensure no slot overlaps HR's busy interval (10:00-11:00)
        assert not (st < datetime(2026, 9, 28, 11, 0, 0) and et > datetime(2026, 9, 28, 10, 0, 0))
        # Ensure no slot overlaps Manager's busy interval (14:00-15:00)
        assert not (st < datetime(2026, 9, 28, 15, 0, 0) and et > datetime(2026, 9, 28, 14, 0, 0))

    # Assert HR busy time is excluded
    assert ("10:00", "11:00") not in slot_windows
    # Assert Manager busy time is excluded
    assert ("14:00", "15:00") not in slot_windows
    # Assert lunch break is excluded
    assert ("12:00", "13:00") not in slot_windows

    # Assert mutually free slots are offered
    assert ("09:00", "10:00") in slot_windows
    assert ("11:00", "12:00") in slot_windows
    assert ("13:00", "14:00") in slot_windows
    assert ("15:00", "16:00") in slot_windows
    assert ("16:00", "17:00") in slot_windows


@pytest.mark.asyncio
async def test_one_click_scheduling_shortlisted_candidate_endpoint(client, db_session):
    """
    TEST-ID: 4
    Module: Interview Scheduling
    Scenario: One-click scheduling
    Steps: Select shortlisted candidate and a slot, confirm
    Expected Result: Event created in all calendars with correct time and duration
    """
    hr_user = User(
        email="hr_oneclick_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="HR OneClick Coordinator",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="CTRL-JOB-ONECLICK-1",
        job_title="Lead Cloud Engineer",
        department="Infrastructure",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Kubernetes & GCP"
    )
    db_session.add(job)
    await db_session.flush()

    # Step 1: Shortlisted candidate
    app = JobApplication(
        job_id=job.id,
        candidate_name="Lucas Shortlisted",
        candidate_email="lucas.shortlisted@example.com",
        job_title="Lead Cloud Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(app)

    token = create_access_token({"sub": hr_user.email, "id": hr_user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Slot selection (10:00 to 11:00, 1-hour duration)
    slot_start = "2026-09-30T10:00:00"
    slot_end = "2026-09-30T11:00:00"

    mock_google_event = {
        "id": "g_event_lucas_456",
        "summary": "Technical Interview - Lucas Shortlisted",
        "start": {"dateTime": slot_start},
        "end": {"dateTime": slot_end},
        "status": "confirmed",
    }

    # Step 3: Confirm one-click scheduling
    with patch("app.services.interview_service.create_real_google_event", return_value=mock_google_event) as mock_create_event:
        resp = await client.post(
            "/interviews/schedule",
            json={
                "job_application_id": app.id,
                "interviewer_id": hr_user.id,
                "title": "Technical Interview - Lucas Shortlisted",
                "start_time": slot_start,
                "end_time": slot_end,
            },
            headers=headers,
        )

    assert resp.status_code == 200
    interview_data = resp.json()

    # Verify event details created with correct time, duration, and candidate info
    assert interview_data["candidate_name"] == "Lucas Shortlisted"
    assert interview_data["candidate_email"] == "lucas.shortlisted@example.com"
    assert interview_data["start_time"] == slot_start
    assert interview_data["end_time"] == slot_end
    start_dt = datetime.fromisoformat(interview_data["start_time"])
    end_dt = datetime.fromisoformat(interview_data["end_time"])
    assert (end_dt - start_dt).total_seconds() == 3600  # Exactly 1 hour duration
    assert interview_data["google_event_id"] == "g_event_lucas_456"

    # Verify Google Calendar event was created with exact time and candidate attendee
    assert mock_create_event.called
    kwargs = mock_create_event.call_args.kwargs
    assert kwargs["calendar_id"] == "primary"
    assert kwargs["start_dt"] == slot_start
    assert kwargs["end_dt"] == slot_end
    assert {"email": "lucas.shortlisted@example.com"} in kwargs["attendees"]

    # Verify event appears in calendar feed
    feed_resp = await client.get("/interviews/calendar-feed", headers=headers)
    assert feed_resp.status_code == 200
    feed_data = feed_resp.json()
    feed_interviews = [iv for iv in feed_data["interviews"] if iv["id"] == interview_data["id"]]
    assert len(feed_interviews) == 1
    assert feed_interviews[0]["start_time"] == slot_start
    assert feed_interviews[0]["end_time"] == slot_end


@pytest.mark.asyncio
async def test_interview_controller_invites_sent_to_candidate_hr_and_panel(client, db_session, mock_interview_emails):
    """
    TEST-ID: 5
    Module: Interview Scheduling
    Scenario: Invites sent
    Steps: Schedule Interview
    Expected Result: Candidate, HR and panel receive invites
    """
    hr_user = User(
        email="hr_invite_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="HR Invite Coordinator",
        google_credentials='{"access_token": "valid_token"}',
    )
    panel_user = User(
        email="panel_invite_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="Panel Reviewer",
    )
    db_session.add_all([hr_user, panel_user])
    await db_session.flush()

    job = JobDescription(
        job_id="CTRL-JOB-INVITE-1",
        job_title="QA Automation Engineer",
        department="Quality Assurance",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Selenium & Pytest"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Chloe Candidate",
        candidate_email="chloe.candidate@example.com",
        job_title="QA Automation Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(panel_user)
    await db_session.refresh(app)

    token = create_access_token({"sub": hr_user.email, "id": hr_user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    slot_start = "2026-10-02T11:00:00"
    slot_end = "2026-10-02T12:00:00"

    mock_google_event = {
        "id": "g_event_invite_ctrl_111",
        "summary": "Technical QA Panel Interview",
        "start": {"dateTime": slot_start},
        "end": {"dateTime": slot_end},
        "status": "confirmed",
    }

    m_email, _ = mock_interview_emails
    m_email.reset_mock()

    with patch("app.services.interview_service.create_real_google_event", return_value=mock_google_event) as mock_create_event, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif, \
         patch("app.tasks.initiate_interview_call_task.delay"):

        resp = await client.post(
            "/interviews/schedule",
            json={
                "job_application_id": app.id,
                "interviewer_id": panel_user.id,
                "title": "Technical QA Panel Interview",
                "start_time": slot_start,
                "end_time": slot_end,
            },
            headers=headers,
        )

    assert resp.status_code == 200

    # 1. Candidate receives invite
    cand_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "chloe.candidate@example.com"]
    assert len(cand_emails) >= 1
    attendees = mock_create_event.call_args.kwargs.get("attendees", [])
    assert {"email": "chloe.candidate@example.com"} in attendees
    cand_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "chloe.candidate@example.com"]
    assert len(cand_notifs) >= 1

    # 2. HR receives invite/confirmation
    hr_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "hr_invite_ctrl@example.com"]
    assert len(hr_emails) >= 1
    assert {"email": "hr_invite_ctrl@example.com"} in attendees
    hr_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "hr_invite_ctrl@example.com"]
    assert len(hr_notifs) >= 1

    # 3. Panel receives invite
    panel_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "panel_invite_ctrl@example.com"]
    assert len(panel_emails) >= 1
    assert {"email": "panel_invite_ctrl@example.com"} in attendees
    panel_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "panel_invite_ctrl@example.com"]
    assert len(panel_notifs) >= 1


@pytest.mark.asyncio
async def test_interview_controller_double_booking_two_candidates_same_slot_blocked(client, db_session, mock_interview_emails):
    """
    TEST-ID: 6
    Module: Interview Scheduling
    Scenario: Double-booking
    Steps: Schedule two candidates in the same slot
    Expected Result: Second attempt blocked with conflict message
    """
    hr_user = User(
        email="hr_double_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="HR Double Booking Controller",
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="CTRL-JOB-DBL-1",
        job_title="Database Administrator",
        department="Database Operations",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="PostgreSQL & Redis Administration"
    )
    db_session.add(job)
    await db_session.flush()

    cand1 = JobApplication(
        job_id=job.id,
        candidate_name="Candidate Alpha",
        candidate_email="cand_alpha@example.com",
        job_title="Database Administrator",
        status="SHORTLISTED"
    )
    cand2 = JobApplication(
        job_id=job.id,
        candidate_name="Candidate Beta",
        candidate_email="cand_beta@example.com",
        job_title="Database Administrator",
        status="SHORTLISTED"
    )
    db_session.add_all([cand1, cand2])
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(cand1)
    await db_session.refresh(cand2)

    token = create_access_token({"sub": hr_user.email, "id": hr_user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    slot_start = "2026-10-12T14:00:00"
    slot_end = "2026-10-12T15:00:00"

    # Step 1: Schedule Candidate 1 in slot (14:00 - 15:00) -> 200 OK
    resp1 = await client.post(
        "/interviews/schedule",
        json={
            "job_application_id": cand1.id,
            "interviewer_id": hr_user.id,
            "title": "DBA Interview - Candidate 1",
            "start_time": slot_start,
            "end_time": slot_end,
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["candidate_name"] == "Candidate Alpha"

    # Step 2: Attempt to schedule Candidate 2 in the same slot (14:00 - 15:00) -> 409 Conflict
    resp2 = await client.post(
        "/interviews/schedule",
        json={
            "job_application_id": cand2.id,
            "interviewer_id": hr_user.id,
            "title": "DBA Interview - Candidate 2",
            "start_time": slot_start,
            "end_time": slot_end,
        },
        headers=headers,
    )
    assert resp2.status_code == 409
    detail = resp2.json()["detail"]
    assert "conflict" in detail.lower()
    assert "The selected time slot conflicts with an existing interview for this HR panelist. Please choose another slot." in detail


@pytest.mark.asyncio
async def test_interview_controller_reschedule_moves_slot_removes_old_event_creates_new_and_notifies_all(client, db_session, mock_interview_emails):
    """
    TEST-ID: 7
    Module: Interview Scheduling
    Scenario: Reschedule
    Steps: Move an interview to a new slot
    Expected Result: Old event removed, new created, all notified
    Priority: H
    """
    hr_user = User(
        email="hr_resched_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="HR Reschedule Manager",
        google_credentials='{"access_token": "valid_token"}',
    )
    panel_user = User(
        email="panel_resched_ctrl@example.com",
        password="password123",
        role="HR",
        fullname="Senior Panelist Maria",
    )
    db_session.add_all([hr_user, panel_user])
    await db_session.flush()

    job = JobDescription(
        job_id="RESCHED-CTRL-01",
        job_title="DevOps Engineer",
        department="Infrastructure",
        job_type=JobType.FULL_TIME,
        location="Taguig",
        description="Kubernetes & Cloud"
    )
    db_session.add(job)
    await db_session.flush()

    candidate = JobApplication(
        job_id=job.id,
        candidate_name="Elena Devops",
        candidate_email="elena.devops@example.com",
        phone="+639181234567",
        job_title="DevOps Engineer",
        status="SHORTLISTED"
    )
    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(panel_user)
    await db_session.refresh(candidate)

    token = create_access_token({"sub": hr_user.email, "id": hr_user.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Initial schedule via POST /interviews/schedule
    initial_start = "2026-10-13T10:00:00"
    initial_end = "2026-10-13T11:00:00"
    mock_initial_event = {
        "id": "g_event_initial_elena_111",
        "summary": "DevOps Technical Interview",
        "status": "confirmed",
    }

    with patch("app.services.interview_service.create_real_google_event", return_value=mock_initial_event):
        schedule_resp = await client.post(
            "/interviews/schedule",
            json={
                "job_application_id": candidate.id,
                "interviewer_id": hr_user.id,
                "panelist_ids": [panel_user.id],
                "title": "DevOps Technical Interview",
                "start_time": initial_start,
                "end_time": initial_end,
            },
            headers=headers,
        )

    assert schedule_resp.status_code == 200
    created_data = schedule_resp.json()
    interview_id = created_data["id"]
    assert created_data["google_event_id"] == "g_event_initial_elena_111"

    # Step 2: Reschedule to new slot via PUT /interviews/{interview_id}
    new_slot_start = "2026-10-14T15:00:00"
    new_slot_end = "2026-10-14T16:00:00"
    mock_new_event = {
        "id": "g_event_new_elena_222",
        "summary": "DevOps Technical Interview - Rescheduled",
        "status": "confirmed",
    }

    _, m2_resched = mock_interview_emails
    m2_resched.reset_mock()

    with patch("app.services.interview_service.delete_real_google_event") as mock_delete_event, \
         patch("app.services.interview_service.create_real_google_event", return_value=mock_new_event) as mock_create_event, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif:

        resched_resp = await client.put(
            f"/interviews/{interview_id}",
            json={
                "title": "DevOps Technical Interview - Rescheduled",
                "start_time": new_slot_start,
                "end_time": new_slot_end,
                "interviewer_id": hr_user.id,
                "panelist_ids": [panel_user.id],
            },
            headers=headers,
        )

    assert resched_resp.status_code == 200
    resched_data = resched_resp.json()

    # Step 3: Verification
    # (a) New slot confirmed
    assert resched_data["start_time"] == new_slot_start
    assert resched_data["end_time"] == new_slot_end
    # (b) Old event removed
    assert mock_delete_event.called
    assert mock_delete_event.call_args.kwargs.get("event_id") == "g_event_initial_elena_111"
    # (c) New event created with correct time slot and attendees
    assert mock_create_event.called
    create_kwargs = mock_create_event.call_args.kwargs
    assert create_kwargs["start_dt"] == new_slot_start
    assert create_kwargs["end_dt"] == new_slot_end
    attendee_emails = [a["email"] for a in create_kwargs.get("attendees", [])]
    assert "elena.devops@example.com" in attendee_emails
    assert "hr_resched_ctrl@example.com" in attendee_emails
    assert "panel_resched_ctrl@example.com" in attendee_emails
    # (d) Google event id updated
    assert resched_data["google_event_id"] == "g_event_new_elena_222"
    # (e) All notified (Candidate, HR, Panel)
    notified_emails = [c.kwargs.get("to_email") for c in m2_resched.call_args_list]
    assert "elena.devops@example.com" in notified_emails
    assert "hr_resched_ctrl@example.com" in notified_emails
    assert "panel_resched_ctrl@example.com" in notified_emails

    notified_roles = [c.kwargs.get("target_role") for c in mock_notif.call_args_list]
    assert "CANDIDATE" in notified_roles
    assert "HR" in notified_roles
    assert "PANELIST" in notified_roles








