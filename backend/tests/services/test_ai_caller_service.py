import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from app.services import ai_caller_service


@pytest.mark.asyncio
async def test_generate_incoming_twiml():
    twiml = await ai_caller_service.generate_incoming_twiml("example.com")
    assert isinstance(twiml, str)
    assert "<Response>" in twiml
    assert "wss://example.com/ai-caller/media-stream" in twiml
    assert "Connecting you to the Mariwasa AI Interview Assistant" in twiml


@pytest.mark.asyncio
async def test_initiate_outbound_call_missing_credentials():
    with patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", None):
        with pytest.raises(HTTPException) as excinfo:
            await ai_caller_service.initiate_outbound_call("+639123456789", "test.com")
        assert excinfo.value.status_code == 500
        assert "not configured" in excinfo.value.detail


@pytest.mark.asyncio
async def test_initiate_outbound_call_success():
    with patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", "AC123"), \
         patch.object(ai_caller_service, "TWILIO_AUTH_TOKEN", "token123"), \
         patch.object(ai_caller_service, "TWILIO_PHONE_NUMBER", "+1234567890"), \
         patch("app.services.ai_caller_service.TwilioClient") as mock_twilio_cls:
        
        mock_client = MagicMock()
        mock_call = MagicMock()
        mock_call.sid = "CA_test_call_sid"
        mock_client.calls.create.return_value = mock_call
        mock_twilio_cls.return_value = mock_client

        res = await ai_caller_service.initiate_outbound_call("+639999999999", "api.example.com")
        assert res["message"] == "Call initiated"
        assert res["call_sid"] == "CA_test_call_sid"
        mock_client.calls.create.assert_called_once_with(
            url="https://api.example.com/ai-caller/incoming-call",
            to="+639999999999",
            from_="+1234567890"
        )


@pytest.mark.asyncio
async def test_initiate_outbound_call_twilio_error():
    with patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", "AC123"), \
         patch.object(ai_caller_service, "TWILIO_AUTH_TOKEN", "token123"), \
         patch("app.services.ai_caller_service.TwilioClient", side_effect=Exception("Twilio network error")):
        
        with pytest.raises(HTTPException) as excinfo:
            await ai_caller_service.initiate_outbound_call("+639999999999", "api.example.com")
        assert excinfo.value.status_code == 500
        assert "Twilio network error" in excinfo.value.detail


@pytest.mark.asyncio
async def test_handle_ai_media_stream_graceful_close():
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.close = AsyncMock()
    
    # Simulate connection error to Gemini WS to ensure it catches and closes websocket
    with patch("websockets.connect", side_effect=Exception("Failed to connect to Gemini")):
        await ai_caller_service.handle_ai_media_stream(mock_ws)
        mock_ws.accept.assert_called_once()
        mock_ws.close.assert_called_once()


# ── AI Voice Notification Tests (REQ028 - REQ034) ───────────────────────────

def test_build_interview_voice_twiml_english():
    """REQ029 & REQ030: English voice prompt delivers details clearly and asks confirmation."""
    dt = datetime(2026, 11, 20, 14, 0, 0)
    twiml = ai_caller_service.build_interview_voice_twiml(
        interview_id=1,
        candidate_name="Maria Santos",
        job_title="Ceramics Engineer",
        start_time=dt,
        interviewer_name="Engr. Reyes",
        language="en"
    )
    assert "<Response>" in twiml
    assert "<Gather" in twiml
    assert "Maria Santos" in twiml
    assert "Ceramics Engineer" in twiml
    assert "Engr. Reyes" in twiml
    assert "confirm" in twiml.lower()
    assert "reschedule" in twiml.lower()
    assert "language=\"en-US\"" in twiml


def test_build_interview_voice_twiml_filipino():
    """REQ029 & REQ030: Filipino voice prompt delivers details in Filipino."""
    dt = datetime(2026, 11, 20, 14, 0, 0)
    twiml = ai_caller_service.build_interview_voice_twiml(
        interview_id=2,
        candidate_name="Juan Dela Cruz",
        job_title="Quality Inspector",
        start_time=dt,
        interviewer_name="Ms. Gomez",
        language="fil"
    )
    assert "<Response>" in twiml
    assert "Magandang araw Juan Dela Cruz" in twiml
    assert "Quality Inspector" in twiml
    assert "Kumpirma" in twiml or "kumpirma" in twiml
    assert "Reschedule" in twiml
    assert "language=\"fil-PH\"" in twiml


def test_interpret_verbal_response():
    """REQ030: Interprets candidate verbal confirmations and reschedule requests."""
    # Confirm verbal responses
    intent, _ = ai_caller_service.interpret_verbal_response("Yes, I confirm my attendance", None)
    assert intent == "CONFIRMED"

    intent, _ = ai_caller_service.interpret_verbal_response("Kumpirmado po, pupunta ako", None)
    assert intent == "CONFIRMED"

    intent, _ = ai_caller_service.interpret_verbal_response("Oo, pwede ako sa Friday", None)
    assert intent == "CONFIRMED"

    # Confirm keypad DTMF
    intent, _ = ai_caller_service.interpret_verbal_response(None, "1")
    assert intent == "CONFIRMED"

    # Reschedule verbal responses
    intent, _ = ai_caller_service.interpret_verbal_response("Please reschedule, I have a conflict", None)
    assert intent == "RESCHEDULE_REQUESTED"

    intent, _ = ai_caller_service.interpret_verbal_response("Hindi po ako pwede, pwede bang ilipat?", None)
    assert intent == "RESCHEDULE_REQUESTED"

    # Reschedule keypad DTMF
    intent, _ = ai_caller_service.interpret_verbal_response(None, "2")
    assert intent == "RESCHEDULE_REQUESTED"


@pytest.mark.asyncio
async def test_initiate_candidate_interview_call(db_session):
    """REQ028 & REQ032: Initiates voice call and logs call attempt in VoiceCallRecord and InterviewLog."""
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.models.interview import Interview

    hr = User(email="hr_voice@example.com", password="pwd", role="HR", fullname="HR Caller")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(job_id="JOB-V1", job_title="Accountant", department="Finance", job_type=JobType.FULL_TIME, location="Remote", description="Desc")
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(job_id=job.id, candidate_name="Carlo Rossi", candidate_email="carlo@example.com", phone="09171234567", status="PENDING")
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Finance Interview",
        start_time=datetime(2026, 11, 23, 10, 0, 0),
        end_time=datetime(2026, 11, 23, 11, 0, 0)
    )
    db_session.add(interview)
    await db_session.commit()

    res = await ai_caller_service.initiate_candidate_interview_call(interview.id, db=db_session)
    assert res["status"] == "success"
    assert res["attempt"] == 1
    assert "+639171234567" in res["phone"]

    # Verify interview was updated and logs created
    await db_session.refresh(interview)
    assert interview.call_attempts == 1
    assert len(interview.call_records) == 1
    assert interview.call_records[0].attempt_number == 1
    assert interview.call_records[0].phone_number == "+639171234567"


@pytest.mark.asyncio
async def test_handle_voice_response_confirm_updates_status(db_session):
    """REQ034 & REQ032: Updates interview status to CONFIRMED and logs candidate response."""
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.models.interview import Interview

    hr = User(email="hr_confirm@example.com", password="pwd", role="HR", fullname="HR Confirm")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(job_id="JOB-V2", job_title="Developer", department="IT", job_type=JobType.FULL_TIME, location="Remote", description="Desc")
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(job_id=job.id, candidate_name="Ana Santos", candidate_email="ana@example.com", phone="09181234567", status="PENDING")
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Dev Interview",
        start_time=datetime(2026, 11, 24, 14, 0, 0),
        end_time=datetime(2026, 11, 24, 15, 0, 0)
    )
    db_session.add(interview)
    await db_session.commit()

    # Call initiated
    await ai_caller_service.initiate_candidate_interview_call(interview.id, db=db_session)

    # Candidate verbally confirms
    twiml_reply = await ai_caller_service.handle_voice_response(
        interview_id=interview.id,
        speech_result="I confirm my attendance for this interview",
        digits=None,
        call_sid="SIM_TEST",
        db=db_session
    )

    await db_session.refresh(interview)
    assert interview.status == "CONFIRMED"
    assert interview.call_status == "CONFIRMED"
    assert interview.candidate_response == "CONFIRMED"
    assert "confirm" in twiml_reply.lower() or "salamat" in twiml_reply.lower()


@pytest.mark.asyncio
async def test_handle_voice_response_reschedule_updates_status(db_session):
    """REQ034 & REQ032: Updates interview status to RESCHEDULE_REQUESTED and logs candidate response."""
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.models.interview import Interview

    hr = User(email="hr_resched@example.com", password="pwd", role="HR", fullname="HR Resched")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(job_id="JOB-V3", job_title="Marketing Analyst", department="Marketing", job_type=JobType.FULL_TIME, location="Remote", description="Desc")
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(job_id=job.id, candidate_name="Ben Lim", candidate_email="ben@example.com", phone="09191234567", status="PENDING")
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Marketing Interview",
        start_time=datetime(2026, 11, 25, 10, 0, 0),
        end_time=datetime(2026, 11, 25, 11, 0, 0)
    )
    db_session.add(interview)
    await db_session.commit()

    await ai_caller_service.initiate_candidate_interview_call(interview.id, db=db_session)

    # Candidate requests reschedule via keypad 2
    twiml_reply = await ai_caller_service.handle_voice_response(
        interview_id=interview.id,
        speech_result=None,
        digits="2",
        call_sid="SIM_TEST",
        db=db_session
    )

    await db_session.refresh(interview)
    assert interview.status == "RESCHEDULE_REQUESTED"
    assert interview.call_status == "RESCHEDULE_REQUESTED"
    assert interview.candidate_response == "RESCHEDULE_REQUESTED"


@pytest.mark.asyncio
async def test_retry_and_sms_backup_after_3_attempts(db_session):
    """REQ031 & REQ033: Retries up to 3 times within 24h, sends SMS backup on 3rd failure."""
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.models.interview import Interview

    hr = User(email="hr_sms@example.com", password="pwd", role="HR", fullname="HR SMS")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(job_id="JOB-V4", job_title="Warehouse Lead", department="Logistics", job_type=JobType.FULL_TIME, location="Remote", description="Desc")
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(job_id=job.id, candidate_name="Pedro Cruz", candidate_email="pedro@example.com", phone="09201234567", status="PENDING")
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Warehouse Interview",
        start_time=datetime(2026, 11, 26, 13, 0, 0),
        end_time=datetime(2026, 11, 26, 14, 0, 0),
        call_attempts=1
    )
    db_session.add(interview)
    await db_session.commit()

    # Attempt 1 failed -> status callback triggers retry schedule
    await ai_caller_service.handle_call_status_callback(
        interview_id=interview.id,
        call_sid="TEST_SID_1",
        call_status="no-answer",
        duration=0,
        db=db_session
    )
    await db_session.refresh(interview)
    assert interview.call_status == "RETRY_SCHEDULED"
    assert interview.next_retry_at is not None

    # Simulate 3rd attempt failure
    interview.call_attempts = 3
    await db_session.commit()

    with patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms:
        await ai_caller_service.handle_call_status_callback(
            interview_id=interview.id,
            call_sid="TEST_SID_3",
            call_status="no-answer",
            duration=0,
            db=db_session
        )
        assert mock_sms.called

    await db_session.refresh(interview)
    assert interview.call_status in ["UNREACHABLE", "SMS_BACKUP_SENT"]
    assert interview.sms_backup_sent is True

