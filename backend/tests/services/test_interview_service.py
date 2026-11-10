import pytest
from datetime import datetime
from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.models.interview import Interview
from unittest.mock import patch, AsyncMock
from app.schemas.interview_schema import InterviewCreateSchema, InterviewUpdateSchema
from app.services.interview_service import interview_service

@pytest.fixture(autouse=True)
def mock_interview_emails():
    with patch("app.services.email_service.EmailService.send_interview_invitation_email", new_callable=AsyncMock) as m1, \
         patch("app.services.email_service.EmailService.send_interview_rescheduled_email", new_callable=AsyncMock) as m2:
        m1.return_value = True
        m2.return_value = True
        yield (m1, m2)

@pytest.mark.asyncio
async def test_schedule_and_get_all_interviews(db_session, mock_interview_emails):
    # Setup test HR user
    user = User(
        email="hr_test@example.com",
        password="password123",
        role="HR",
        fullname="HR Tester"
    )
    db_session.add(user)
    await db_session.flush()

    # Setup Job and Application
    job = JobDescription(
        job_id="JOB-101",
        job_title="Software Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Write code"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="John Doe",
        candidate_email="john@example.com",
        phone="+1234567890",
        job_title="Software Engineer",
        status="PENDING"
    )
    db_session.add(app)
    await db_session.flush()

    # Schedule interview (Monday 10:00 - 11:00 AM)
    create_data = InterviewCreateSchema(
        job_application_id=app.id,
        title="Technical Interview",
        description="First round technical interview",
        start_time=datetime(2026, 9, 21, 10, 0, 0), # Monday
        end_time=datetime(2026, 9, 21, 11, 0, 0)
    )
    interview = await interview_service.schedule_interview(db_session, create_data, user.id)

    assert interview.id is not None
    assert interview.title == "Technical Interview"
    assert interview.candidate_name == "John Doe"
    assert interview.candidate_email == "john@example.com"
    assert interview.status == "SCHEDULED"
    assert interview.meeting_link is None
    m1, m2 = mock_interview_emails
    assert m1.called
    assert any(c.kwargs.get("to_email") == "john@example.com" for c in m1.call_args_list)

    # Get all interviews
    all_ivs = await interview_service.get_all_interviews(db_session)
    assert len(all_ivs) >= 1
    found = next((i for i in all_ivs if i.id == interview.id), None)
    assert found is not None
    assert found.candidate_name == "John Doe"

@pytest.mark.asyncio
async def test_update_and_reschedule_interview(db_session, mock_interview_emails):
    # Setup test HR user
    user = User(
        email="hr_reschedule@example.com",
        password="password123",
        role="HR",
        fullname="HR Rescheduler"
    )
    db_session.add(user)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-102",
        job_title="Frontend Developer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="UI dev"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Jane Smith",
        candidate_email="jane@example.com",
        phone="+1987654321",
        job_title="Frontend Developer"
    )
    db_session.add(app)
    await db_session.flush()

    create_data = InterviewCreateSchema(
        job_application_id=app.id,
        title="Initial Interview",
        start_time=datetime(2026, 9, 22, 9, 0, 0), # Tuesday
        end_time=datetime(2026, 9, 22, 10, 0, 0)
    )
    interview = await interview_service.schedule_interview(db_session, create_data, user.id)

    # Reschedule to Wednesday 2:00 PM - 3:00 PM
    update_data = InterviewUpdateSchema(
        title="Rescheduled Interview",
        start_time=datetime(2026, 9, 23, 14, 0, 0),
        end_time=datetime(2026, 9, 23, 15, 0, 0),
        status="SCHEDULED"
    )
    updated = await interview_service.update_interview(db_session, interview.id, update_data, user.id)

    assert updated.title == "Rescheduled Interview"
    assert updated.start_time == datetime(2026, 9, 23, 14, 0, 0)
    assert updated.candidate_name == "Jane Smith"
    assert updated.meeting_link is None
    m1, m2 = mock_interview_emails
    assert m2.called
    assert m2.call_args.kwargs["to_email"] == "jane@example.com"

    # Weekend validation rejection (Saturday)
    weekend_update = InterviewUpdateSchema(
        start_time=datetime(2026, 9, 26, 10, 0, 0), # Saturday
        end_time=datetime(2026, 9, 26, 11, 0, 0)
    )
    with pytest.raises(ValueError, match="weekdays"):
        await interview_service.update_interview(db_session, interview.id, weekend_update, user.id)

    # Outside working hours validation rejection (7:00 AM)
    early_update = InterviewUpdateSchema(
        start_time=datetime(2026, 9, 24, 7, 0, 0),
        end_time=datetime(2026, 9, 24, 8, 0, 0)
    )
    with pytest.raises(ValueError, match="working hours"):
        await interview_service.update_interview(db_session, interview.id, early_update, user.id)

@pytest.mark.asyncio
async def test_delete_interview(db_session):
    user = User(
        email="hr_delete@example.com",
        password="password123",
        role="HR",
        fullname="HR Deletor"
    )
    db_session.add(user)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-103",
        job_title="QA Engineer",
        department="QA",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Testing"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Bob Tester",
        candidate_email="bob@example.com"
    )
    db_session.add(app)
    await db_session.flush()

    create_data = InterviewCreateSchema(
        job_application_id=app.id,
        title="QA Interview",
        start_time=datetime(2026, 9, 25, 13, 0, 0), # Friday
        end_time=datetime(2026, 9, 25, 14, 0, 0)
    )
    interview = await interview_service.schedule_interview(db_session, create_data, user.id)
    iv_id = interview.id

    # Delete
    result = await interview_service.delete_interview(db_session, iv_id, user.id)
    assert result is True

    # Verify not found
    with pytest.raises(ValueError, match="not found"):
        await interview_service.update_interview(
            db_session, iv_id, InterviewUpdateSchema(title="Won't update"), user.id
        )

@pytest.mark.asyncio
async def test_calendar_feed_and_google_status(db_session):
    user = User(
        email="hr_feed@example.com",
        password="password123",
        role="HR",
        fullname="HR Feed"
    )
    db_session.add(user)
    await db_session.flush()

    # Google status check when not connected
    status = await interview_service.get_google_calendar_status(db_session, user.id)
    assert status["connected"] is False

    # Calendar feed
    feed = await interview_service.get_calendar_feed(db_session, user.id)
    assert "interviews" in feed
    assert "google_events" in feed
    assert feed["google_connected"] is False


@pytest.mark.asyncio
async def test_free_slot_detection_blocks_10_to_11_on_hr01_calendar(db_session):
    """
    TEST-ID: 1
    Module: Interview Scheduling
    Scenario: Free-slot detection
    Steps: Block 10:00-11:00 on hr01 calendar, request slots
    Expected Result: Only 9:00AM-5:00PM slots shown (with 10:00-11:00 excluded)
    """
    hr01 = User(
        email="hr01_service@example.com",
        password="password123",
        role="HR",
        fullname="HR 01",
        google_credentials='{"token": "dummy_token"}',
    )
    db_session.add(hr01)
    await db_session.commit()
    await db_session.refresh(hr01)

    # Monday, 2026-09-21
    req_start = datetime(2026, 9, 21, 8, 0, 0)
    req_end = datetime(2026, 9, 21, 18, 0, 0)

    # Mock 10:00-11:00 blocked on hr01's Google Calendar
    mock_freebusy = {
        "primary": {
            "busy": [
                {
                    "start": "2026-09-21T10:00:00Z",
                    "end": "2026-09-21T11:00:00Z",
                }
            ]
        }
    }

    with patch("app.services.interview_service.query_freebusy", return_value=mock_freebusy):
        slots = await interview_service.get_available_slots(db_session, req_start, req_end, hr01.id)

    assert len(slots) > 0
    for slot in slots:
        # Every slot must fall strictly within 9:00 AM - 5:00 PM
        assert slot["start_time"].hour >= 9
        assert slot["end_time"].hour < 17 or (slot["end_time"].hour == 17 and slot["end_time"].minute == 0)
        # No slot may overlap the blocked 10:00-11:00 window
        blocked_start = datetime(2026, 9, 21, 10, 0, 0)
        blocked_end = datetime(2026, 9, 21, 11, 0, 0)
        assert not (slot["start_time"] < blocked_end and slot["end_time"] > blocked_start)

    slot_Windows = [(s["start_time"].strftime("%H:%M"), s["end_time"].strftime("%H:%M")) for s in slots]
    assert ("09:00", "10:00") in slot_Windows
    assert ("10:00", "11:00") not in slot_Windows
    assert ("11:00", "12:00") in slot_Windows
    assert ("16:00", "17:00") in slot_Windows


@pytest.mark.asyncio
async def test_business_hours_full_day_slot_request(db_session):
    """
    TEST-ID: 2
    Module: Interview Scheduling
    Scenario: Business Hours
    Steps: Request slots for a full day
    Expected Result: Only 9:00AM to 5:00PM slots shown
    """
    hr_user = User(
        email="hr_business_hours@example.com",
        password="password123",
        role="HR",
        fullname="HR Business Hours",
    )
    db_session.add(hr_user)
    await db_session.commit()
    await db_session.refresh(hr_user)

    # Request slots for an entire 24-hour weekday (Wednesday, 2026-09-23 00:00:00 to 23:59:59)
    full_day_start = datetime(2026, 9, 23, 0, 0, 0)
    full_day_end = datetime(2026, 9, 23, 23, 59, 59)

    slots = await interview_service.get_available_slots(db_session, full_day_start, full_day_end, hr_user.id)

    assert len(slots) > 0
    # Verify earliest slot starts at 9:00 AM and latest slot ends at 5:00 PM
    assert slots[0]["start_time"] == datetime(2026, 9, 23, 9, 0, 0)
    assert slots[-1]["end_time"] == datetime(2026, 9, 23, 17, 0, 0)

    for slot in slots:
        assert slot["start_time"] >= datetime(2026, 9, 23, 9, 0, 0)
        assert slot["end_time"] <= datetime(2026, 9, 23, 17, 0, 0)


@pytest.mark.asyncio
async def test_hr_and_manager_both_busy_at_different_times_mutually_free_slots(db_session):
    """
    TEST-ID: 3
    Module: Interview Scheduling
    Scenario: HR and manager both busy at different times
    Expected Result: Only mutually free slots offered
    """
    hr_user = User(
        email="hr_mutually_free@example.com",
        password="password123",
        role="HR",
        fullname="HR Specialist",
    )
    mgr_user = User(
        email="mgr_mutually_free@example.com",
        password="password123",
        role="HR",
        fullname="Engineering Manager",
    )
    db_session.add_all([hr_user, mgr_user])
    await db_session.flush()

    # Create dummy jobs and job applications to attach interviews
    job = JobDescription(
        job_id="MUTUAL-JOB-1",
        job_title="Lead Architect",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Architecture"
    )
    db_session.add(job)
    await db_session.flush()

    app1 = JobApplication(
        job_id=job.id,
        candidate_name="Candidate One",
        candidate_email="cand1_mutual@example.com",
        job_title="Lead Architect"
    )
    app2 = JobApplication(
        job_id=job.id,
        candidate_name="Candidate Two",
        candidate_email="cand2_mutual@example.com",
        job_title="Lead Architect"
    )
    db_session.add_all([app1, app2])
    await db_session.flush()

    # HR is busy at 10:00 - 11:00 on Friday, 2026-09-25
    iv_hr = Interview(
        job_application_id=app1.id,
        interviewer_id=hr_user.id,
        title="HR Screening",
        start_time=datetime(2026, 9, 25, 10, 0, 0),
        end_time=datetime(2026, 9, 25, 11, 0, 0),
        status="SCHEDULED"
    )
    # Manager is busy at 14:00 - 15:00 on Friday, 2026-09-25
    iv_mgr = Interview(
        job_application_id=app2.id,
        interviewer_id=mgr_user.id,
        title="Technical Interview",
        start_time=datetime(2026, 9, 25, 14, 0, 0),
        end_time=datetime(2026, 9, 25, 15, 0, 0),
        status="SCHEDULED"
    )
    db_session.add_all([iv_hr, iv_mgr])
    await db_session.commit()

    req_start = datetime(2026, 9, 25, 8, 0, 0)
    req_end = datetime(2026, 9, 25, 18, 0, 0)

    # Request slots with HR and manager
    slots = await interview_service.get_available_slots(
        db_session,
        req_start,
        req_end,
        user_id=hr_user.id,
        manager_id=mgr_user.id,
    )

    assert len(slots) > 0
    slot_windows = [(s["start_time"].strftime("%H:%M"), s["end_time"].strftime("%H:%M")) for s in slots]

    # HR busy time (10:00-11:00) must NOT be offered
    assert ("10:00", "11:00") not in slot_windows
    # Manager busy time (14:00-15:00) must NOT be offered
    assert ("14:00", "15:00") not in slot_windows
    # Lunch break (12:00-13:00) must NOT be offered
    assert ("12:00", "13:00") not in slot_windows

    # Mutually free slots MUST be offered
    assert ("09:00", "10:00") in slot_windows
    assert ("11:00", "12:00") in slot_windows
    assert ("13:00", "14:00") in slot_windows
    assert ("15:00", "16:00") in slot_windows
    assert ("16:00", "17:00") in slot_windows

    # Check that no slot overlaps with either HR or Manager busy times
    for s in slots:
        st = s["start_time"]
        et = s["end_time"]
        assert not (st < datetime(2026, 9, 25, 11, 0, 0) and et > datetime(2026, 9, 25, 10, 0, 0))
        assert not (st < datetime(2026, 9, 25, 15, 0, 0) and et > datetime(2026, 9, 25, 14, 0, 0))


@pytest.mark.asyncio
async def test_one_click_scheduling_shortlisted_candidate_creates_calendar_event(db_session, mock_interview_emails):
    """
    TEST-ID: 4
    Module: Interview Scheduling
    Scenario: One-click scheduling
    Steps: Select shortlisted candidate and a slot, confirm
    Expected Result: Event created in all calendars with correct time and duration
    """
    hr_user = User(
        email="hr_oneclick@example.com",
        password="password123",
        role="HR",
        fullname="HR Coordinator",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="ONECLICK-JOB-1",
        job_title="Senior Data Engineer",
        department="Analytics",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="ETL & Data Warehousing"
    )
    db_session.add(job)
    await db_session.flush()

    # Step 1: Select shortlisted candidate
    shortlisted_app = JobApplication(
        job_id=job.id,
        candidate_name="Elena Shortlist",
        candidate_email="elena.shortlist@example.com",
        phone="+639171234567",
        job_title="Senior Data Engineer",
        status="SHORTLISTED"
    )
    db_session.add(shortlisted_app)
    await db_session.commit()
    await db_session.refresh(shortlisted_app)
    await db_session.refresh(hr_user)

    # Step 2: Select a slot (Tuesday 2026-09-29 10:00:00 - 11:00:00, 1-hour duration)
    slot_start = datetime(2026, 9, 29, 10, 0, 0)
    slot_end = datetime(2026, 9, 29, 11, 0, 0)
    expected_duration = (slot_end - slot_start).total_seconds()  # 3600 seconds (1 hour)

    schedule_data = InterviewCreateSchema(
        job_application_id=shortlisted_app.id,
        interviewer_id=hr_user.id,
        title="Technical Interview - Elena Shortlist",
        description="Data engineering system architecture interview",
        start_time=slot_start,
        end_time=slot_end,
    )

    mock_google_event = {
        "id": "g_event_shortlisted_789",
        "summary": schedule_data.title,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "status": "confirmed",
    }

    # Step 3: Confirm one-click scheduling with Google Calendar event creation
    with patch("app.services.interview_service.create_real_google_event", return_value=mock_google_event) as mock_create_event, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay"):

        interview = await interview_service.schedule_interview(db_session, schedule_data, hr_user.id)

    # Expected Result: Event created in database calendar with correct time and duration
    assert interview.id is not None
    assert interview.start_time == slot_start
    assert interview.end_time == slot_end
    assert (interview.end_time - interview.start_time).total_seconds() == expected_duration
    assert interview.candidate_name == "Elena Shortlist"
    assert interview.candidate_email == "elena.shortlist@example.com"
    assert interview.status == "SCHEDULED"

    # Expected Result: Event created in Google Calendar with correct time, duration, and candidate attendee
    assert interview.google_event_id == "g_event_shortlisted_789"
    assert mock_create_event.called
    kwargs = mock_create_event.call_args.kwargs
    assert kwargs["calendar_id"] == "primary"
    assert kwargs["summary"] == "Technical Interview - Elena Shortlist"
    assert kwargs["start_dt"] == slot_start.isoformat()
    assert kwargs["end_dt"] == slot_end.isoformat()
    assert {"email": "elena.shortlist@example.com"} in kwargs["attendees"]

    # Verify unified calendar feed includes the created interview with matching time and duration
    feed = await interview_service.get_calendar_feed(db_session, hr_user.id)
    assert "interviews" in feed
    matched_feed_events = [iv for iv in feed["interviews"] if iv.id == interview.id]
    assert len(matched_feed_events) == 1
    feed_iv = matched_feed_events[0]
    assert feed_iv.start_time == slot_start
    assert feed_iv.end_time == slot_end
    assert feed_iv.google_event_id == "g_event_shortlisted_789"


@pytest.mark.asyncio
async def test_invites_sent_to_candidate_hr_and_panel(db_session, mock_interview_emails):
    """
    TEST-ID: 5
    Module: Interview Scheduling
    Scenario: Invites sent
    Steps: Schedule Interview
    Expected Result: Candidate, HR and panel receive invites
    """
    hr_scheduler = User(
        email="hr_scheduler@example.com",
        password="password123",
        role="HR",
        fullname="HR Scheduler",
        google_credentials='{"access_token": "valid_token"}',
    )
    panel_interviewer = User(
        email="panel_lead@example.com",
        password="password123",
        role="HR",
        fullname="Technical Lead Panelist",
    )
    db_session.add_all([hr_scheduler, panel_interviewer])
    await db_session.flush()

    job = JobDescription(
        job_id="INVITE-JOB-1",
        job_title="Principal Fullstack Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="React & FastAPI"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Sofia Candidate",
        candidate_email="sofia.candidate@example.com",
        job_title="Principal Fullstack Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr_scheduler)
    await db_session.refresh(panel_interviewer)
    await db_session.refresh(app)

    slot_start = datetime(2026, 10, 1, 14, 0, 0) # Thursday 2:00 PM
    slot_end = datetime(2026, 10, 1, 15, 0, 0)   # Thursday 3:00 PM

    schedule_data = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=panel_interviewer.id,
        title="Technical Interview Panel",
        description="Architecture and code review panel session",
        start_time=slot_start,
        end_time=slot_end,
    )

    mock_google_event = {
        "id": "g_event_invite_test_999",
        "summary": schedule_data.title,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "status": "confirmed",
    }

    m_email, _ = mock_interview_emails
    m_email.reset_mock()

    with patch("app.services.interview_service.create_real_google_event", return_value=mock_google_event) as mock_create_event, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif, \
         patch("app.tasks.initiate_interview_call_task.delay"):

        interview = await interview_service.schedule_interview(db_session, schedule_data, hr_scheduler.id)

    assert interview.id is not None

    # 1. Verify Candidate receives invite
    # - Email invitation
    cand_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "sofia.candidate@example.com"]
    assert len(cand_emails) >= 1
    # - Calendar invite attendee
    assert mock_create_event.called
    attendees = mock_create_event.call_args.kwargs.get("attendees", [])
    assert {"email": "sofia.candidate@example.com"} in attendees
    # - In-app notification
    cand_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "sofia.candidate@example.com"]
    assert len(cand_notifs) >= 1

    # 2. Verify HR receives invite/confirmation
    # - Email invitation/confirmation
    hr_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "hr_scheduler@example.com"]
    assert len(hr_emails) >= 1
    # - Calendar invite attendee
    assert {"email": "hr_scheduler@example.com"} in attendees
    # - In-app notification
    hr_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "hr_scheduler@example.com"]
    assert len(hr_notifs) >= 1

    # 3. Verify Panel receives invite
    # - Email invitation
    panel_emails = [c for c in m_email.call_args_list if c.kwargs.get("to_email") == "panel_lead@example.com"]
    assert len(panel_emails) >= 1
    # - Calendar invite attendee
    assert {"email": "panel_lead@example.com"} in attendees
    # - In-app notification
    panel_notifs = [c for c in mock_notif.call_args_list if c.kwargs.get("target_email") == "panel_lead@example.com"]
    assert len(panel_notifs) >= 1


@pytest.mark.asyncio
async def test_double_booking_two_candidates_same_slot_blocked_with_conflict(db_session, mock_interview_emails):
    """
    TEST-ID: 6
    Module: Interview Scheduling
    Scenario: Double-booking
    Steps: Schedule two candidates in the same slot
    Expected Result: Second attempt blocked with conflict message
    """
    hr_user = User(
        email="hr_doublebook_test@example.com",
        password="password123",
        role="HR",
        fullname="HR DoubleBook Reviewer",
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="DBL-BOOK-JOB-1",
        job_title="Security Analyst",
        department="Information Security",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Cybersecurity & Vulnerability Assessment"
    )
    db_session.add(job)
    await db_session.flush()

    # Create two different candidate applications
    app1 = JobApplication(
        job_id=job.id,
        candidate_name="First Candidate",
        candidate_email="cand1.dbl@example.com",
        job_title="Security Analyst",
        status="SHORTLISTED"
    )
    app2 = JobApplication(
        job_id=job.id,
        candidate_name="Second Candidate",
        candidate_email="cand2.dbl@example.com",
        job_title="Security Analyst",
        status="SHORTLISTED"
    )
    db_session.add_all([app1, app2])
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(app1)
    await db_session.refresh(app2)

    slot_start = datetime(2026, 10, 9, 10, 0, 0)
    slot_end = datetime(2026, 10, 9, 11, 0, 0)

    # Step 1: Schedule first candidate in slot (10:00 - 11:00) -> Succeeds
    schedule_data_1 = InterviewCreateSchema(
        job_application_id=app1.id,
        interviewer_id=hr_user.id,
        title="Security Interview - Candidate 1",
        description="First candidate interview session",
        start_time=slot_start,
        end_time=slot_end,
    )
    with patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay"):
        interview_1 = await interview_service.schedule_interview(db_session, schedule_data_1, hr_user.id)
    assert interview_1.id is not None
    assert interview_1.start_time == slot_start

    # Step 2: Attempt to schedule second candidate in the same slot (10:00 - 11:00) -> Blocked
    schedule_data_2 = InterviewCreateSchema(
        job_application_id=app2.id,
        interviewer_id=hr_user.id,
        title="Security Interview - Candidate 2",
        description="Second candidate interview session in same slot",
        start_time=slot_start,
        end_time=slot_end,
    )
    with pytest.raises(ValueError) as exc_info:
        await interview_service.schedule_interview(db_session, schedule_data_2, hr_user.id)

    # Verify conflict message
    assert "conflict" in str(exc_info.value).lower()
    assert "The selected time slot conflicts with an existing interview for this HR panelist. Please choose another slot." in str(exc_info.value)


@pytest.mark.asyncio
async def test_reschedule_interview_moves_slot_removes_old_event_creates_new_and_notifies_all(db_session, mock_interview_emails):
    """
    TEST-ID: 7
    Module: Interview Scheduling
    Scenario: Reschedule
    Steps: Move an interview to a new slot
    Expected Result: Old event removed, new created, all notified
    Priority: H
    """
    # 1. Setup HR user with valid Google credentials
    hr_user = User(
        email="hr_reschedule_test@example.com",
        password="password123",
        role="HR",
        fullname="HR Coordinator Maya",
        google_credentials='{"access_token": "valid_token"}',
    )
    # 2. Setup Panel Member
    panel_member = User(
        email="panel_reschedule_lead@example.com",
        password="password123",
        role="HR",
        fullname="Lead Architect Dan",
    )
    db_session.add_all([hr_user, panel_member])
    await db_session.flush()

    # 3. Setup Job and Candidate Application
    job = JobDescription(
        job_id="RESCHED-JOB-001",
        job_title="Full Stack Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Makati City",
        description="Full stack dev role"
    )
    db_session.add(job)
    await db_session.flush()

    application = JobApplication(
        job_id=job.id,
        candidate_name="Carlos Candidate",
        candidate_email="carlos.candidate@example.com",
        phone="+639171234567",
        job_title="Full Stack Engineer",
        status="SHORTLISTED"
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(panel_member)
    await db_session.refresh(application)

    initial_start = datetime(2026, 10, 14, 10, 0, 0)  # Wednesday 10:00 AM
    initial_end = datetime(2026, 10, 14, 11, 0, 0)    # Wednesday 11:00 AM
    initial_google_event = {
        "id": "old_google_event_12345",
        "summary": "Full Stack Engineer - Technical Interview",
        "status": "confirmed",
    }

    create_data = InterviewCreateSchema(
        job_application_id=application.id,
        interviewer_id=hr_user.id,
        panelist_ids=[panel_member.id],
        title="Full Stack Engineer - Technical Interview",
        description="Initial technical interview round",
        start_time=initial_start,
        end_time=initial_end,
    )

    with patch("app.services.interview_service.create_real_google_event", return_value=initial_google_event), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay"):
        interview = await interview_service.schedule_interview(db_session, create_data, hr_user.id)

    assert interview.id is not None
    assert interview.google_event_id == "old_google_event_12345"
    assert interview.start_time == initial_start

    # Now Reschedule: Move interview to new slot (Thursday 14:00 - 15:00)
    new_slot_start = datetime(2026, 10, 15, 14, 0, 0)
    new_slot_end = datetime(2026, 10, 15, 15, 0, 0)
    new_google_event = {
        "id": "new_google_event_67890",
        "summary": "Full Stack Engineer - Rescheduled Interview",
        "status": "confirmed",
    }

    reschedule_data = InterviewUpdateSchema(
        title="Full Stack Engineer - Rescheduled Interview",
        start_time=new_slot_start,
        end_time=new_slot_end,
        interviewer_id=hr_user.id,
        panelist_ids=[panel_member.id],
        status="SCHEDULED",
    )

    m1_invite, m2_resched = mock_interview_emails
    m2_resched.reset_mock()

    with patch("app.services.interview_service.delete_real_google_event") as mock_delete_event, \
         patch("app.services.interview_service.create_real_google_event", return_value=new_google_event) as mock_create_event, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif:

        updated_interview = await interview_service.update_interview(
            db_session,
            interview.id,
            reschedule_data,
            hr_user.id,
            user_role="HR"
        )

    # Verification:
    # 1. New slot updated in DB
    assert updated_interview.start_time == new_slot_start
    assert updated_interview.end_time == new_slot_end
    assert updated_interview.title == "Full Stack Engineer - Rescheduled Interview"

    # 2. Old event removed from Google Calendar
    assert mock_delete_event.called
    assert mock_delete_event.call_args.kwargs.get("event_id") == "old_google_event_12345"

    # 3. New event created on Google Calendar with updated slot and attendees
    assert mock_create_event.called
    create_kwargs = mock_create_event.call_args.kwargs
    assert create_kwargs["start_dt"] == new_slot_start.isoformat()
    assert create_kwargs["end_dt"] == new_slot_end.isoformat()
    attendee_emails = [a["email"] for a in create_kwargs.get("attendees", [])]
    assert "carlos.candidate@example.com" in attendee_emails
    assert "hr_reschedule_test@example.com" in attendee_emails
    assert "panel_reschedule_lead@example.com" in attendee_emails

    # 4. Updated interview contains new Google event ID
    assert updated_interview.google_event_id == "new_google_event_67890"

    # 5. All notified: Candidate, HR, and Panel
    # Rescheduled Emails
    resched_emails = [c.kwargs.get("to_email") for c in m2_resched.call_args_list]
    assert "carlos.candidate@example.com" in resched_emails
    assert "hr_reschedule_test@example.com" in resched_emails
    assert "panel_reschedule_lead@example.com" in resched_emails

    # SMS to Candidate
    assert mock_sms.called

    # In-App Notifications
    notif_roles = [c.kwargs.get("target_role") for c in mock_notif.call_args_list]
    assert "CANDIDATE" in notif_roles
    assert "HR" in notif_roles
    assert "PANELIST" in notif_roles


@pytest.mark.asyncio
async def test_cancellation_removes_event_notifies_participants_and_updates_status(db_session):
    """
    TEST-ID: 8
    Module: Interview Scheduling
    Scenario: Cancellation
    Steps: Cancel an interview
    Expected Result: Event removed, participant notified, status updated
    Priority: H
    """
    # 1. Setup HR user with valid Google credentials
    hr_user = User(
        email="hr_cancel_service@example.com",
        password="password123",
        role="HR",
        fullname="HR Cancellation Lead",
        google_credentials='{"access_token": "valid_token"}',
    )
    # 2. Setup Panel Member
    panel_member = User(
        email="panel_cancel_service@example.com",
        password="password123",
        role="HR",
        fullname="Lead Interviewer Marco",
    )
    db_session.add_all([hr_user, panel_member])
    await db_session.flush()

    # 3. Setup Job Description and Application
    job = JobDescription(
        job_id="CANCEL-JOB-001",
        job_title="Cloud Security Architect",
        department="Security",
        job_type=JobType.FULL_TIME,
        location="Taguig",
        description="Lead cloud cybersecurity architecture"
    )
    db_session.add(job)
    await db_session.flush()

    application = JobApplication(
        job_id=job.id,
        candidate_name="Danielle Candidate",
        candidate_email="danielle.cand@example.com",
        phone="+639191234567",
        job_title="Cloud Security Architect",
        status="SHORTLISTED"
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(panel_member)
    await db_session.refresh(application)

    initial_start = datetime(2026, 10, 20, 10, 0, 0)
    initial_end = datetime(2026, 10, 20, 11, 0, 0)
    initial_google_event = {
        "id": "g_event_cancel_test_789",
        "summary": "Cloud Security Architect Interview",
        "status": "confirmed",
    }

    create_data = InterviewCreateSchema(
        job_application_id=application.id,
        interviewer_id=hr_user.id,
        panelist_ids=[panel_member.id],
        title="Cloud Security Architect Interview",
        description="Architecture design review",
        start_time=initial_start,
        end_time=initial_end,
    )

    with patch("app.services.interview_service.create_real_google_event", return_value=initial_google_event), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay"):
        interview = await interview_service.schedule_interview(db_session, create_data, hr_user.id)

    assert interview.id is not None
    assert interview.status == "SCHEDULED"
    assert interview.google_event_id == "g_event_cancel_test_789"

    # Step: Cancel the interview
    with patch("app.services.interview_service.delete_real_google_event") as mock_delete_event, \
         patch("app.services.email_service.send_interview_cancellation_email", new_callable=AsyncMock) as mock_cancel_email, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif:

        mock_cancel_email.return_value = True

        cancelled_interview = await interview_service.cancel_interview(
            db_session,
            interview.id,
            user_id=hr_user.id,
            user_role="HR",
            reason="Candidate requested cancellation due to personal scheduling conflict."
        )

    # Verification:
    # 1. Status updated to CANCELED
    assert cancelled_interview.status == "CANCELED"

    # 2. Event removed from Google Calendar and reference cleared
    assert mock_delete_event.called
    assert mock_delete_event.call_args.kwargs.get("event_id") == "g_event_cancel_test_789"
    assert cancelled_interview.google_event_id is None

    # 3. Participants notified via email
    assert mock_cancel_email.called
    cancel_email_recipients = [c.kwargs.get("to_email") for c in mock_cancel_email.call_args_list]
    assert "danielle.cand@example.com" in cancel_email_recipients
    assert "hr_cancel_service@example.com" in cancel_email_recipients
    assert "panel_cancel_service@example.com" in cancel_email_recipients

    # 4. Candidate notified via SMS
    assert mock_sms.called

    # 5. In-app notifications generated for all participants
    assert mock_notif.called
    notif_roles = [c.kwargs.get("target_role") for c in mock_notif.call_args_list]
    assert "CANDIDATE" in notif_roles
    assert "HR" in notif_roles
    assert "PANELIST" in notif_roles


@pytest.mark.asyncio
async def test_calendar_fully_booked_offers_alternative_dates(db_session):
    """
    TEST-ID: 9
    Module: Interview Scheduling
    Scenario: Calendar Fully booked
    Steps: Request slots when no time is free
    Expected Result: Message offers alternative dates
    Priority: H
    """
    hr_user = User(
        email="hr_fullybooked_service@example.com",
        password="password123",
        role="HR",
        fullname="HR Scheduler Booked",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    # Requested date: Monday, 2026-10-26 (09:00 - 17:00)
    req_start = datetime(2026, 10, 26, 9, 0, 0)
    req_end = datetime(2026, 10, 26, 17, 0, 0)

    # Mock query_freebusy:
    # 1. On Monday (2026-10-26), calendar is completely booked (09:00 - 17:00)
    # 2. On upcoming days (Tuesday 2026-10-27, Wednesday 2026-10-28), calendar has free time
    def mock_freebusy_side_effect(credentials_json, calendars, time_min, time_max):
        if "2026-10-26" in time_min:
            return {
                "primary": {
                    "busy": [
                        {"start": "2026-10-26T09:00:00Z", "end": "2026-10-26T17:00:00Z"}
                    ]
                }
            }
        else:
            return {"primary": {"busy": []}}

    with patch("app.services.interview_service.query_freebusy", side_effect=mock_freebusy_side_effect):
        slots = await interview_service.get_available_slots(
            db_session,
            req_start,
            req_end,
            user_id=hr_user.id
        )

    # Verification:
    # 1. No slots are free on the requested fully booked date
    assert len(slots) == 0

    # 2. Message is generated and offers alternative dates
    assert hasattr(slots, "message")
    assert slots.message is not None
    assert "fully booked" in slots.message.lower()
    assert "alternative dates" in slots.message.lower()

    # 3. Alternative dates are provided (e.g. 2026-10-27, 2026-10-28)
    assert hasattr(slots, "alternative_dates")
    assert len(slots.alternative_dates) > 0
    assert any("2026-10-27" in d for d in slots.alternative_dates)


@pytest.mark.asyncio
async def test_concurrent_scheduling_five_candidates_no_duplicates_or_lost_events(db_session):
    """
    TEST-ID: 10
    Module: Interview Scheduling
    Scenario: Concurrent scheduling
    Steps: Schedule 5 candidates at once
    Expected Result: No duplicate or lost events
    Priority: M
    """
    import asyncio

    # Setup HR user with Google credentials
    hr_user = User(
        email="hr_concurrent_srv@example.com",
        password="password123",
        role="HR",
        fullname="HR Concurrent Scheduler",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    # Setup Job Description
    job = JobDescription(
        job_id="CONCUR-JOB-10",
        job_title="Software Architect",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Architecture and distributed systems"
    )
    db_session.add(job)
    await db_session.flush()

    # Setup 5 Candidate Applications
    applications = []
    for i in range(1, 6):
        app = JobApplication(
            job_id=job.id,
            candidate_name=f"Candidate Concurrent {i}",
            candidate_email=f"cand_concur_{i}@example.com",
            phone=f"+63917000000{i}",
            job_title="Software Architect",
            status="SHORTLISTED"
        )
        applications.append(app)
        db_session.add(app)

    await db_session.commit()
    await db_session.refresh(hr_user)
    for app in applications:
        await db_session.refresh(app)

    # 5 distinct 1-hour slots on Tuesday, 2026-10-27
    slot_hours = [
        (9, 10),
        (10, 11),
        (11, 12),
        (13, 14), # after lunch break (12:00 - 13:00)
        (14, 15),
    ]

    schedule_payloads = []
    for i, (sh, eh) in enumerate(slot_hours):
        payload = InterviewCreateSchema(
            job_application_id=applications[i].id,
            interviewer_id=hr_user.id,
            title=f"Architect Interview - Candidate {i+1}",
            description=f"Technical round for candidate {i+1}",
            start_time=datetime(2026, 10, 27, sh, 0, 0),
            end_time=datetime(2026, 10, 27, eh, 0, 0),
        )
        schedule_payloads.append(payload)

    # Mock Google calendar creation returning unique event IDs for each candidate
    call_count = 0
    def mock_create_event_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "id": f"g_event_concur_{call_count}_{int(datetime.utcnow().timestamp()*1000)}",
            "summary": kwargs.get("summary", "Interview Event"),
            "status": "confirmed"
        }

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def schedule_candidate(payload):
        async with session_factory() as sess:
            return await interview_service.schedule_interview(sess, payload, hr_user.id)

    with patch("app.services.interview_service.create_real_google_event", side_effect=mock_create_event_side_effect), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay"):

        # Execute 5 interview scheduling calls concurrently
        tasks = [
            schedule_candidate(payload)
            for payload in schedule_payloads
        ]
        results = await asyncio.gather(*tasks)

    # Verification:
    # 1. Exactly 5 interviews scheduled
    assert len(results) == 5

    # 2. No duplicate event IDs / exactly 5 unique interview IDs
    interview_ids = [iv.id for iv in results]
    assert len(set(interview_ids)) == 5

    # 3. No duplicate Google Calendar events
    google_event_ids = [iv.google_event_id for iv in results]
    assert len(set(google_event_ids)) == 5
    assert all(gid is not None for gid in google_event_ids)

    # 4. Each candidate has their own interview scheduled (no duplicates across candidates)
    app_ids = [iv.job_application_id for iv in results]
    assert len(set(app_ids)) == 5
    assert set(app_ids) == {a.id for a in applications}

    # 5. No lost events in database
    all_ivs = await interview_service.get_all_interviews(db_session)
    scheduled_in_db = [iv for iv in all_ivs if iv.id in interview_ids]
    assert len(scheduled_in_db) == 5


@pytest.mark.asyncio
async def test_calendar_api_rate_limit_retry_and_no_partial_booking(db_session, mock_interview_emails):
    """
    TEST-ID: 11 (Part 1 - Rate Limit 429)
    Module: Interview Scheduling
    Scenario: API timeout or rate limit
    Steps: Simulate 429 from Calendar API
    Expected Result: Graceful retry or error message; no partial booking
    Priority: M
    """
    hr_user = User(
        email="hr_ratelimit_srv@example.com",
        password="password123",
        role="HR",
        fullname="HR RateLimit Coordinator",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="RATELIMIT-JOB-11",
        job_title="DevOps Lead",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Kubernetes & Terraform"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Brandon RateLimit",
        candidate_email="brandon.ratelimit@example.com",
        phone="+639179998888",
        job_title="DevOps Lead",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(app)

    payload = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=hr_user.id,
        title="DevOps Interview - Rate Limit Test",
        start_time=datetime(2026, 11, 2, 10, 0, 0),
        end_time=datetime(2026, 11, 2, 11, 0, 0),
    )

    class MockResp:
        def __init__(self, status):
            self.status = status
            self.reason = "Too Many Requests"

    from googleapiclient.errors import HttpError
    http_429 = HttpError(resp=MockResp(429), content=b'{"error": {"code": 429, "message": "rateLimitExceeded"}}')

    m_email, _ = mock_interview_emails
    m_email.reset_mock()

    # Case A: Persistent 429 across retries -> Error message and NO partial booking
    with patch("app.services.interview_service.create_real_google_event", side_effect=http_429), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif, \
         patch("app.tasks.initiate_interview_call_task.delay") as mock_voice:

        with pytest.raises(ValueError) as exc_info:
            await interview_service.schedule_interview(db_session, payload, hr_user.id)

        # 1. Informative error message received
        err_msg = str(exc_info.value).lower()
        assert "429" in err_msg or "rate limit" in err_msg
        assert "no booking was created" in err_msg

    # 2. NO PARTIAL BOOKING Verification:
    # (a) Zero interviews in database
    all_ivs = await interview_service.get_all_interviews(db_session)
    matching_ivs = [iv for iv in all_ivs if iv.job_application_id == app.id]
    assert len(matching_ivs) == 0

    # (b) Candidate application status remains SHORTLISTED (not changed to REVIEWED)
    await db_session.refresh(app)
    assert app.status == "SHORTLISTED"

    # (c) No notification emails dispatched
    assert m_email.call_count == 0

    # (d) No in-app notifications created
    assert mock_notif.call_count == 0

    # (e) No voice call queued
    assert mock_voice.call_count == 0


@pytest.mark.asyncio
async def test_calendar_api_timeout_retry_and_no_partial_booking(db_session, mock_interview_emails):
    """
    TEST-ID: 11 (Part 2 - Timeout)
    Module: Interview Scheduling
    Scenario: API timeout or rate limit
    Steps: Simulate timeout from Calendar API
    Expected Result: Graceful retry or error message; no partial booking
    Priority: M
    """
    hr_user = User(
        email="hr_timeout_srv@example.com",
        password="password123",
        role="HR",
        fullname="HR Timeout Coordinator",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="TIMEOUT-JOB-11",
        job_title="Data Platform Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Spark & Kafka"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Timothy Timeout",
        candidate_email="timothy.timeout@example.com",
        phone="+639171112222",
        job_title="Data Platform Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr_user)
    await db_session.refresh(app)

    payload = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=hr_user.id,
        title="Data Platform Interview - Timeout Test",
        start_time=datetime(2026, 11, 3, 14, 0, 0),
        end_time=datetime(2026, 11, 3, 15, 0, 0),
    )

    m_email, _ = mock_interview_emails
    m_email.reset_mock()

    # Case B: Persistent Timeout -> Error message and NO partial booking
    with patch("app.services.interview_service.create_real_google_event", side_effect=TimeoutError("Request timed out after 30000ms")), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif, \
         patch("app.tasks.initiate_interview_call_task.delay") as mock_voice:

        with pytest.raises(ValueError) as exc_info:
            await interview_service.schedule_interview(db_session, payload, hr_user.id)

        # 1. Informative error message received
        err_msg = str(exc_info.value).lower()
        assert "timed out" in err_msg or "timeout" in err_msg
        assert "no booking was created" in err_msg

    # 2. NO PARTIAL BOOKING Verification:
    # (a) Zero interviews in database
    all_ivs = await interview_service.get_all_interviews(db_session)
    matching_ivs = [iv for iv in all_ivs if iv.job_application_id == app.id]
    assert len(matching_ivs) == 0

    # (b) Candidate application status remains SHORTLISTED
    await db_session.refresh(app)
    assert app.status == "SHORTLISTED"

    # (c) No notification emails dispatched
    assert m_email.call_count == 0

    # (d) No in-app notifications created
    assert mock_notif.call_count == 0

    # (e) No voice call queued
    assert mock_voice.call_count == 0


@pytest.mark.asyncio
async def test_calendar_api_transient_retry_success(db_session, mock_interview_emails):
    """
    TEST-ID: 11 (Part 3: Transient Retry Success)
    Scenario: Google Calendar API fails transiently on attempt 1 (429 or timeout),
              then succeeds on attempt 2.
    Expected Result: execute_with_retry recovers gracefully, interview is booked successfully,
                     application status is updated, and invitations are dispatched.
    """
    from app.services.google_calendar_service import execute_with_retry, GoogleCalendarRateLimitError, GoogleCalendarTimeoutError
    from googleapiclient.errors import HttpError
    from unittest.mock import MagicMock

    # 1. Direct unit test of execute_with_retry with transient 429
    call_counts = {"count": 0}
    def mock_flaky_429_api():
        call_counts["count"] += 1
        if call_counts["count"] == 1:
            mock_resp = MagicMock()
            mock_resp.status = 429
            mock_resp.reason = "Too Many Requests"
            raise HttpError(resp=mock_resp, content=b'{"error": "rate_limit_exceeded"}')
        return {"id": "event_transient_success_1", "status": "confirmed"}

    result = execute_with_retry(
        mock_flaky_429_api,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=1.5,
        operation_name="Flaky 429 test"
    )
    assert call_counts["count"] == 2
    assert result["id"] == "event_transient_success_1"

    # 2. Direct unit test of execute_with_retry with transient timeout
    timeout_counts = {"count": 0}
    def mock_flaky_timeout_api():
        timeout_counts["count"] += 1
        if timeout_counts["count"] == 1:
            raise TimeoutError("Connection timed out")
        return {"id": "event_transient_timeout_success", "status": "confirmed"}

    result_timeout = execute_with_retry(
        mock_flaky_timeout_api,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=1.5,
        operation_name="Flaky timeout test"
    )
    assert timeout_counts["count"] == 2
    assert result_timeout["id"] == "event_transient_timeout_success"

    # 3. Direct test of create_real_google_event recovering from transient 429
    from app.services.google_calendar_service import create_real_google_event
    mock_service = MagicMock()
    insert_call_count = {"count": 0}
    def mock_insert_execute():
        insert_call_count["count"] += 1
        if insert_call_count["count"] == 1:
            mock_resp = MagicMock()
            mock_resp.status = 429
            raise HttpError(resp=mock_resp, content=b"Rate limit exceeded")
        return {"id": "g_event_retry_recovered_123", "status": "confirmed"}

    mock_service.events().insert().execute.side_effect = mock_insert_execute

    with patch("app.services.google_calendar_service.get_google_calendar_service", return_value=(mock_service, None)):
        created_event = create_real_google_event(
            credentials_json='{"access_token": "valid"}',
            calendar_id='primary',
            summary="Test Flaky Event",
            start_dt="2026-11-20T10:00:00",
            end_dt="2026-11-20T11:00:00"
        )
        assert insert_call_count["count"] == 2
        assert created_event["id"] == "g_event_retry_recovered_123"

    # 4. End-to-end service schedule test with recovered calendar event
    hr_user = User(
        email="hr_transient_test@example.com",
        password="password123",
        role="HR",
        fullname="Transient HR",
        google_credentials='{"access_token": "valid_token"}',
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="TRANS-JOB-11",
        job_title="DevOps Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="DevOps & Cloud"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Transient Candidate",
        candidate_email="transient.candidate@example.com",
        phone="+1234567890",
        status="PENDING"
    )
    db_session.add(app)
    await db_session.commit()

    payload = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=hr_user.id,
        title="DevOps Technical Interview",
        start_time=datetime(2026, 11, 20, 10, 0),
        end_time=datetime(2026, 11, 20, 11, 0),
        meeting_link="https://meet.google.com/retry-success"
    )

    m_email, _ = mock_interview_emails
    m_email.reset_mock()

    recovered_event = {
        "id": "g_event_retry_recovered_123",
        "htmlLink": "https://calendar.google.com/event?eid=recovered",
        "hangoutLink": "https://meet.google.com/retry-success",
        "status": "confirmed"
    }

    with patch("app.services.interview_service.create_real_google_event", return_value=recovered_event), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock) as mock_notif, \
         patch("app.tasks.initiate_interview_call_task.delay"):

        interview = await interview_service.schedule_interview(db_session, payload, hr_user.id)

        assert interview is not None
        assert interview.job_application_id == app.id
        assert interview.google_event_id == "g_event_retry_recovered_123"

        # Candidate application status updated to REVIEWED
        await db_session.refresh(app)
        assert app.status == "REVIEWED"

        # Notification emails sent (candidate and HR)
        assert m_email.call_count >= 1
        assert any(c.kwargs.get("to_email") == "transient.candidate@example.com" for c in m_email.call_args_list)













