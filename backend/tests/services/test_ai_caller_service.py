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
    with patch.object(ai_caller_service, "AI_CALLER_PROVIDER", "twilio"), \
         patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", None):
        with pytest.raises(HTTPException) as excinfo:
            await ai_caller_service.initiate_outbound_call("+639123456789", "test.com", provider="twilio")
        assert excinfo.value.status_code == 500
        assert "not configured" in excinfo.value.detail


@pytest.mark.asyncio
async def test_initiate_outbound_call_success():
    with patch.object(ai_caller_service, "AI_CALLER_PROVIDER", "twilio"), \
         patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", "AC123"), \
         patch.object(ai_caller_service, "TWILIO_AUTH_TOKEN", "token123"), \
         patch.object(ai_caller_service, "TWILIO_PHONE_NUMBER", "+1234567890"), \
         patch("app.services.ai_caller_service.TwilioClient") as mock_twilio_cls:
        
        mock_client = MagicMock()
        mock_call = MagicMock()
        mock_call.sid = "CA_test_call_sid"
        mock_client.calls.create.return_value = mock_call
        mock_twilio_cls.return_value = mock_client

        res = await ai_caller_service.initiate_outbound_call("+639999999999", "api.example.com", provider="twilio")
        assert res["message"] == "Call initiated"
        assert res["call_sid"] == "CA_test_call_sid"
        mock_client.calls.create.assert_called_once_with(
            url="https://api.example.com/ai-caller/incoming-call",
            to="+639999999999",
            from_="+1234567890"
        )


@pytest.mark.asyncio
async def test_initiate_outbound_call_twilio_error():
    with patch.object(ai_caller_service, "AI_CALLER_PROVIDER", "twilio"), \
         patch.object(ai_caller_service, "TWILIO_ACCOUNT_SID", "AC123"), \
         patch.object(ai_caller_service, "TWILIO_AUTH_TOKEN", "token123"), \
         patch("app.services.ai_caller_service.TwilioClient", side_effect=Exception("Twilio network error")):
        
        with pytest.raises(HTTPException) as excinfo:
            await ai_caller_service.initiate_outbound_call("+639999999999", "api.example.com", provider="twilio")
        assert excinfo.value.status_code == 500
        assert "Twilio network error" in excinfo.value.detail


@pytest.mark.asyncio
async def test_initiate_outbound_call_adb_success():
    with patch("app.services.ai_caller_service.get_connected_adb_device", return_value="TEST_DEVICE_123"), \
         patch("app.services.ai_caller_service.trigger_adb_dial", return_value={"success": True}):
        res = await ai_caller_service.initiate_outbound_call("+639999999999", "api.example.com", provider="adb")
        assert "DIY Call initiated" in res["message"]
        assert res["device"] == "TEST_DEVICE_123"
        assert res["status"] == "DIALER_TRIGGERED"



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
        language="en",
        location="Mariwasa Plant, Sto. Tomas, Batangas"
    )
    assert "<Response>" in twiml
    assert "<Gather" in twiml
    assert "Maria Santos" in twiml
    assert "Ceramics Engineer" in twiml
    assert "Engr. Reyes" in twiml
    assert "November 20, 2026" in twiml
    assert "2:00 PM" in twiml
    assert "Mariwasa Plant, Sto. Tomas, Batangas" in twiml
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
        language="fil",
        location="Plant 1 Sto. Tomas"
    )
    assert "<Response>" in twiml
    assert "Magandang araw Juan Dela Cruz" in twiml
    assert "Quality Inspector" in twiml
    assert "Nobyembre" in twiml
    assert "2:00 PM" in twiml
    assert "Plant 1 Sto. Tomas" in twiml
    assert "Kumpirma" in twiml or "kumpirma" in twiml
    assert "Reschedule" in twiml
    assert "language=\"fil-PH\"" in twiml


def test_voice_message_content_includes_name_date_time_location():
    """
    TEST-ID: 2
    Module: AI Voice Notification
    Scenario: Message content
    Steps: After the test call
    Expected Result: Message includes name, date, time, location in voice message
    Priority: H
    """
    # 1. On-site Interview in English
    dt = datetime(2026, 11, 27, 9, 30, 0)
    candidate_name = "Engr. Roberto Dela Cruz"
    location_onsite = "Mariwasa Plant 2, Sto. Tomas, Batangas"

    twiml_en = ai_caller_service.build_interview_voice_twiml(
        interview_id=101,
        candidate_name=candidate_name,
        job_title="Senior Kiln Specialist",
        start_time=dt,
        interviewer_name="HR Manager Tan",
        language="en",
        location=location_onsite
    )
    # Verify candidate name, date, time, location
    assert candidate_name in twiml_en
    assert "Friday, November 27, 2026" in twiml_en
    assert "9:30 AM" in twiml_en
    assert location_onsite in twiml_en

    # 2. Online Interview in Bilingual mode
    location_online = "Online via Google Meet"
    twiml_bilingual = ai_caller_service.build_interview_voice_twiml(
        interview_id=102,
        candidate_name=candidate_name,
        job_title="Senior Kiln Specialist",
        start_time=dt,
        interviewer_name="HR Manager Tan",
        language="bilingual",
        location=location_online
    )
    assert candidate_name in twiml_bilingual
    assert "Friday, November 27, 2026" in twiml_bilingual
    assert "9:30 AM" in twiml_bilingual
    assert location_online in twiml_bilingual

    # 3. Filipino mode
    twiml_fil = ai_caller_service.build_interview_voice_twiml(
        interview_id=103,
        candidate_name=candidate_name,
        job_title="Senior Kiln Specialist",
        start_time=dt,
        interviewer_name="HR Manager Tan",
        language="fil",
        location=location_onsite
    )
    assert candidate_name in twiml_fil
    assert "Biyernes" in twiml_fil
    assert "Nobyembre" in twiml_fil
    assert "9:30 AM" in twiml_fil
    assert location_onsite in twiml_fil


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


@pytest.mark.asyncio
async def test_send_backup_sms_notification_with_datetime_and_fallback(db_session):
    """Verifies send_backup_sms_notification formats start_time and safely falls back when None."""
    from app.models.interview import Interview
    from app.models.job_application import JobApplication
    from app.models.job_description import JobDescription, JobType
    from app.models.user import User

    hr = User(email="hr_fallback@example.com", password="pwd", role="HR", fullname="HR Fallback")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(job_id="JOB-FB1", job_title="Ceramics Specialist", department="Production", job_type=JobType.FULL_TIME, location="Batangas", description="Desc")
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(job_id=job.id, candidate_name="Juan Dela Cruz", candidate_email="juan@example.com", phone="09181234567", status="PENDING")
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Production Interview",
        start_time=datetime(2026, 11, 26, 13, 0, 0),
        end_time=datetime(2026, 11, 26, 14, 0, 0),
        call_attempts=3
    )
    db_session.add(interview)
    await db_session.commit()

    # 1. Test with valid start_time
    with patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms:
        result = await ai_caller_service.send_backup_sms_notification(interview.id, db_session)
        assert result is True
        mock_sms.assert_called_once()
        _, sent_msg = mock_sms.call_args[0]
        assert "Thursday, Nov 26, 2026 at 01:00 PM" in sent_msg
        assert "Juan Dela Cruz" in sent_msg
        assert "Position" in sent_msg

    # 2. Test fallback when start_time is None
    mock_interview = MagicMock()
    mock_interview.id = 999
    mock_interview.job_application_id = app.id
    mock_interview.start_time = None
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    res_interview = MagicMock()
    res_interview.scalar_one_or_none.return_value = mock_interview
    res_app = MagicMock()
    res_app.scalar_one_or_none.return_value = app
    mock_db.execute.side_effect = [res_interview, res_app]

    with patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms:
        result = await ai_caller_service.send_backup_sms_notification(999, mock_db)
        assert result is True
        mock_sms.assert_called_once()
        _, sent_msg = mock_sms.call_args[0]
        assert "the scheduled time" in sent_msg


@pytest.mark.asyncio
async def test_call_after_scheduling_test_number_placed_within_10_seconds(db_session):
    """
    TEST-ID: 1
    Module: AI Voice Notification
    Scenario: Call after scheduling
    Steps: Book interview for candidate with test number
    Expected Result: Call placed automatically within 10 seconds
    Priority: H
    """
    import time
    from sqlalchemy import select
    from app.models.interview import Interview, InterviewLog, VoiceCallRecord
    from app.models.job_application import JobApplication
    from app.models.job_description import JobDescription, JobType
    from app.models.user import User
    from app.schemas.interview_schema import InterviewCreateSchema
    from app.services import interview_service

    # 1. Setup HR and Candidate with test number
    test_phone = "+639171234567"
    hr = User(
        email="hr_voice_test1@example.com",
        password="pwd",
        role="HR",
        fullname="HR Voice Tester"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-VOICE-1",
        job_title="Ceramics Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Engineering role"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Alex TestCandidate",
        candidate_email="alex.test@example.com",
        phone=test_phone,
        job_title="Ceramics Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()

    payload = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Ceramics Technical Interview",
        start_time=datetime(2026, 11, 25, 10, 0, 0),
        end_time=datetime(2026, 11, 25, 11, 0, 0)
    )

    t_start = time.time()

    # 2. Book interview for candidate with test number
    with patch("app.services.email_service.EmailService.send_interview_invitation_email", new_callable=AsyncMock) as m_email, \
         patch("app.services.interview_service.create_real_google_event", return_value={"id": "g_evt_voice_1", "status": "confirmed"}), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay") as mock_celery_call:

        m_email.return_value = True
        interview = await interview_service.schedule_interview(db_session, payload, hr.id)

    # 3. Verify automated dispatch occurred immediately upon booking (< 10 seconds)
    t_scheduled = time.time()
    elapsed_to_dispatch = t_scheduled - t_start
    assert elapsed_to_dispatch < 10.0, f"Scheduling and dispatch took {elapsed_to_dispatch:.2f}s, expected < 10s"

    # Verify Celery task was queued with the created interview id
    mock_celery_call.assert_called_once_with(interview.id)

    # Verify InterviewLog has VOICE_CALL_QUEUED
    logs = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_QUEUED"
        )
    )
    queued_log = logs.scalars().first()
    assert queued_log is not None
    assert test_phone in queued_log.details

    # 4. Execute the call initiation (simulating worker execution) and measure placement duration
    t_call_start = time.time()
    call_result = await ai_caller_service.initiate_candidate_interview_call(interview.id, db=db_session)
    t_call_end = time.time()

    total_time_to_call_placed = t_call_end - t_start
    assert total_time_to_call_placed < 10.0, f"Total time to call placed was {total_time_to_call_placed:.2f}s, expected < 10s"

    # 5. Verify call execution results
    assert call_result["status"] == "success"
    assert call_result["attempt"] == 1
    assert call_result["phone"] == test_phone

    # Verify interview record was updated
    await db_session.refresh(interview)
    assert interview.call_attempts == 1
    assert interview.last_call_at is not None
    assert interview.call_status in ["IN_PROGRESS", "INITIATED"]

    # Verify VoiceCallRecord created with attempt #1 and test phone
    call_records = await db_session.execute(
        select(VoiceCallRecord).where(VoiceCallRecord.interview_id == interview.id)
    )
    records = call_records.scalars().all()
    assert len(records) == 1
    assert records[0].attempt_number == 1
    assert records[0].phone_number == test_phone
    assert records[0].status == "INITIATED"




