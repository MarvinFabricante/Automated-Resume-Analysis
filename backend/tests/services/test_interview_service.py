import pytest
from datetime import datetime
from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
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
    assert m1.call_args.kwargs["to_email"] == "john@example.com"

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
