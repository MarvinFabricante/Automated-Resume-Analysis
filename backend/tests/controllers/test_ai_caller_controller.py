import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from app.models.user import User
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription, JobType
from app.models.interview import Interview, InterviewLog, VoiceCallRecord


@pytest.mark.asyncio
async def test_ai_caller_status(client):
    res = await client.get("/ai-caller/status")
    assert res.status_code == 200
    assert res.json()["message"] == "AI Caller Service is active"


@pytest.mark.asyncio
async def test_ai_caller_incoming_call_get_and_post(client):
    with patch("app.services.ai_caller_service.generate_incoming_twiml", new_callable=AsyncMock) as mock_twiml:
        mock_twiml.return_value = "<Response><Say>Hello</Say></Response>"

        res_get = await client.get("/ai-caller/incoming-call")
        assert res_get.status_code == 200
        assert "<Response>" in res_get.text
        assert "application/xml" in res_get.headers["content-type"]

        res_post = await client.post("/ai-caller/incoming-call")
        assert res_post.status_code == 200
        assert "<Response>" in res_post.text


@pytest.mark.asyncio
async def test_ai_caller_call_candidate(client):
    with patch("app.services.ai_caller_service.initiate_outbound_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"message": "Call initiated", "call_sid": "CA12345"}

        res = await client.post("/ai-caller/call-candidate/+639123456789")
        assert res.status_code == 200
        assert res.json()["call_sid"] == "CA12345"


@pytest.mark.asyncio
async def test_place_interview_call_endpoint(client):
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'test@example.com', 'id': 1, 'role': 'HR'})}"}
    with patch("app.services.ai_caller_service.initiate_candidate_interview_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"status": "success", "attempt": 1, "call_sid": "CA999", "phone": "+639171234567"}

        res = await client.post("/ai-caller/interview/1/call", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert res.json()["attempt"] == 1


@pytest.mark.asyncio
async def test_retry_interview_call_endpoint(client):
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'test@example.com', 'id': 1, 'role': 'HR'})}"}
    with patch("app.services.ai_caller_service.initiate_candidate_interview_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"status": "success", "attempt": 2, "call_sid": "CA888", "phone": "+639171234567"}

        res = await client.post("/ai-caller/interview/1/retry", headers=headers)
        assert res.status_code == 200
        assert res.json()["attempt"] == 2


@pytest.mark.asyncio
async def test_send_backup_sms_endpoint(client):
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'test@example.com', 'id': 1, 'role': 'HR'})}"}
    with patch("app.services.ai_caller_service.send_backup_sms_notification", new_callable=AsyncMock) as mock_sms:
        mock_sms.return_value = True

        res = await client.post("/ai-caller/interview/1/send-backup-sms", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert res.json()["sms_sent"] is True


@pytest.mark.asyncio
async def test_simulate_call_endpoint(client):
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'test@example.com', 'id': 1, 'role': 'HR'})}"}
    with patch("app.services.ai_caller_service.simulate_voice_call", new_callable=AsyncMock) as mock_sim:
        mock_sim.return_value = {
            "status": "success",
            "interview_id": 1,
            "call_status": "CONFIRMED",
            "interview_status": "CONFIRMED",
            "candidate_response": "CONFIRMED"
        }

        res = await client.post(
            "/ai-caller/interview/1/simulate",
            json={"outcome": "CONFIRMED", "spoken_phrase": "I confirm", "language": "en"},
            headers=headers
        )
        assert res.status_code == 200
        assert res.json()["call_status"] == "CONFIRMED"
        assert res.json()["interview_status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_get_call_logs_endpoint(client):
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'test@example.com', 'id': 1, 'role': 'HR'})}"}
    with patch("app.services.ai_caller_service.get_interview_call_logs", new_callable=AsyncMock) as mock_logs:
        mock_logs.return_value = [
            {
                "id": 1,
                "interview_id": 1,
                "attempt_number": 1,
                "status": "COMPLETED",
                "candidate_verbal_response": "I confirm",
                "extracted_intent": "CONFIRMED",
                "created_at": "2026-11-20T10:00:00"
            }
        ]

        res = await client.get("/ai-caller/interview/1/logs", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["extracted_intent"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_voice_response_webhook_endpoint(client):
    with patch("app.services.ai_caller_service.handle_voice_response", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = "<Response><Say>Confirmed</Say></Response>"

        res = await client.post(
            "/ai-caller/voice-response?interview_id=1&attempt=1",
            data={"SpeechResult": "Yes I will attend", "Digits": "1"}
        )
        assert res.status_code == 200
        assert "<Response>" in res.text
        assert "application/xml" in res.headers["content-type"]


@pytest.mark.asyncio
async def test_status_callback_webhook_endpoint(client):
    with patch("app.services.ai_caller_service.handle_call_status_callback", new_callable=AsyncMock) as mock_cb:
        res = await client.post(
            "/ai-caller/status-callback?interview_id=1&attempt=1",
            data={"CallSid": "CA111", "CallStatus": "completed", "CallDuration": "45"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "received"
        assert mock_cb.called


@pytest.mark.asyncio
async def test_interview_booking_places_ai_voice_call_within_10_seconds(client, db_session):
    """
    TEST-ID: 1 (Controller E2E)
    Module: AI Voice Notification
    Scenario: Call after scheduling
    Steps: Book interview for candidate with test number
    Expected Result: Call placed automatically within 10 seconds
    Priority: H
    """
    import time
    from datetime import datetime
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.utils.auth import create_access_token

    test_phone = "+639171234567"

    # 1. Setup HR user and Candidate with test number
    hr = User(
        email="ctrl_voice_hr@example.com",
        password="password123",
        role="HR",
        fullname="Voice Ctrl HR"
    )
    db_session.add(hr)
    await db_session.flush()

    token = create_access_token({"sub": hr.email, "id": hr.id, "role": "HR"})
    headers = {"Authorization": f"Bearer {token}"}

    job = JobDescription(
        job_id="CTRL-VOICE-1",
        job_title="Ceramics Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="Engineering"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Alex Ctrl Candidate",
        candidate_email="alex.ctrl@example.com",
        phone=test_phone,
        job_title="Ceramics Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(hr)
    await db_session.refresh(app)

    schedule_payload = {
        "job_application_id": app.id,
        "interviewer_id": hr.id,
        "title": "Ceramics Engineering Technical Interview",
        "start_time": "2026-11-27T10:00:00",
        "end_time": "2026-11-27T11:00:00"
    }

    t_start = time.time()

    # 2. Book interview via /interviews/schedule
    with patch("app.services.email_service.EmailService.send_interview_invitation_email", new_callable=AsyncMock) as mock_email, \
         patch("app.services.interview_service.create_real_google_event", return_value={"id": "g_evt_ctrl_voice", "status": "confirmed"}), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock), \
         patch("app.tasks.initiate_interview_call_task.delay") as mock_voice_task:

        mock_email.return_value = True
        resp = await client.post("/interviews/schedule", json=schedule_payload, headers=headers)

    t_end = time.time()

    # 3. Assert successful booking
    assert resp.status_code == 200
    interview_data = resp.json()
    interview_id = interview_data["id"]
    assert interview_data["job_application_id"] == app.id

    # 4. Verify call placed automatically within 10 seconds
    elapsed_time = t_end - t_start
    assert elapsed_time < 10.0, f"Booking and call queueing took {elapsed_time:.2f}s, expected < 10s"

    # Verify background Celery task was queued with the created interview id
    mock_voice_task.assert_called_once_with(interview_id)


@pytest.mark.asyncio
async def test_interview_twiml_endpoint_includes_name_date_time_location(client, db_session):
    """
    TEST-ID: 2 (Controller TwiML Content Verification)
    Module: AI Voice Notification
    Scenario: Message content
    Steps: After the test call, request interview TwiML
    Expected Result: Message includes name, date, time, location in voice message
    Priority: H
    """
    from datetime import datetime
    from app.models.user import User
    from app.models.job_description import JobDescription, JobType
    from app.models.job_application import JobApplication
    from app.models.interview import Interview

    hr = User(
        email="ctrl_twiml_hr@example.com",
        password="password123",
        role="HR",
        fullname="Engr. Antonio Reyes"
    )
    db_session.add(hr)
    await db_session.flush()

    job_loc = "Mariwasa Plant 1, Sto. Tomas, Batangas"
    job = JobDescription(
        job_id="CTRL-JOB-TWIML",
        job_title="Lead Kiln Operator",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location=job_loc,
        description="Operating industrial kilns"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Marvin Dela Torre"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="marvin.delatorre@example.com",
        phone="+639179998888",
        job_title="Lead Kiln Operator",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.commit()

    start_dt = datetime(2026, 11, 30, 15, 30, 0)
    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Technical Kiln Interview",
        start_time=start_dt,
        end_time=datetime(2026, 11, 30, 16, 30, 0),
        status="SCHEDULED"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    # 1. Fetch TwiML from endpoint in English
    resp_en = await client.get(f"/ai-caller/interview-twiml/{interview.id}?lang=en")
    assert resp_en.status_code == 200
    assert "application/xml" in resp_en.headers["content-type"]
    text_en = resp_en.text

    # Verify Name, Date, Time, Location in English
    assert cand_name in text_en
    assert "November 30, 2026" in text_en
    assert "3:30 PM" in text_en
    assert job_loc in text_en

    # 2. Fetch TwiML from endpoint in Filipino
    resp_fil = await client.get(f"/ai-caller/interview-twiml/{interview.id}?lang=fil")
    assert resp_fil.status_code == 200
    text_fil = resp_fil.text

    # Verify Name, Date, Time, Location in Filipino
    assert cand_name in text_fil
    assert "Nobyembre" in text_fil
    assert "3:30 PM" in text_fil
    assert job_loc in text_fil


@pytest.mark.asyncio
async def test_filipino_message_call_delivers_clear_audio_and_correct_dates_times(client, db_session):
    """
    TEST-ID: 3
    Module: AI Voice Notification
    Scenario: Filipino message
    Steps: Set language to Filipino and call
    Expected Result: Clear Filipino audio with correct dates and times
    Priority: H
    """
    # Setup HR user
    hr = User(
        email="recruiter_fil@mariwasa.com",
        password="pw",
        role="HR",
        fullname="Recruiter Santos"
    )
    db_session.add(hr)
    await db_session.flush()

    # Setup Job Description
    job = JobDescription(
        job_id="JOB-FIL-CTRL",
        job_title="Maintenance Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant, Sto. Tomas, Batangas",
        description="Maintenance of manufacturing equipment"
    )
    db_session.add(job)
    await db_session.flush()

    # Setup Candidate Application
    cand_name = "Basilio Dela Cruz"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="basilio@example.com",
        phone="+639198765432",
        job_title="Maintenance Engineer",
        status="PENDING"
    )
    db_session.add(app)
    await db_session.flush()

    # Schedule interview on Wednesday at 10:30 AM
    sched_dt = datetime(2026, 11, 25, 10, 30, 0)
    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Maintenance Engineer Screening",
        start_time=sched_dt,
        end_time=datetime(2026, 11, 25, 11, 30, 0),
        status="SCHEDULED",
        call_language="fil"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    # Step 1: Set language to Filipino and call candidate via POST /ai-caller/interview/{id}/call?language=fil
    from app.utils.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}
    call_resp = await client.post(f"/ai-caller/interview/{interview.id}/call?language=fil", headers=headers)
    assert call_resp.status_code == 200
    call_data = call_resp.json()
    assert call_data["status"] == "success"
    assert call_data["call_status"] == "IN_PROGRESS"

    # Step 2: Fetch generated TwiML from /ai-caller/interview-twiml/{id}
    twiml_resp = await client.get(f"/ai-caller/interview-twiml/{interview.id}")
    assert twiml_resp.status_code == 200
    twiml_text = twiml_resp.text

    # Expected Result: Clear Filipino audio settings with correct dates and times
    # 1) Natural high-quality Filipino voice & language tag
    assert 'language="fil-PH"' in twiml_text
    assert 'voice="Google.fil-PH-Standard-A"' in twiml_text

    # 2) Candidate personalized name
    assert cand_name in twiml_text
    assert "Magandang araw Basilio Dela Cruz" in twiml_text

    # 3) Correct Filipino Date & Time
    assert "Miyerkules" in twiml_text # Wednesday
    assert "ika-25 ng Nobyembre, 2026" in twiml_text # November 25, 2026
    assert "10:30 AM" in twiml_text # 10:30 AM

    # 4) Filipino DTMF & Verbal instructions
    assert "Kumpirma" in twiml_text or "kumpirma" in twiml_text
    assert "Reschedule" in twiml_text
    assert "Mariwasa Plant, Sto. Tomas, Batangas" in twiml_text

    # Step 3: Candidate confirms in Filipino via voice response webhook
    confirm_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}&lang=fil",
        data={"SpeechResult": "Opo, kumpirma", "CallSid": call_data["call_sid"]}
    )
    assert confirm_resp.status_code == 200
    confirm_text = confirm_resp.text
    assert 'language="fil-PH"' in confirm_text
    assert "Maraming salamat!" in confirm_text
    assert "Kumpirmado na ang inyong pagdalo" in confirm_text




