import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
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
    from datetime import datetime, timedelta
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
    from datetime import datetime, timedelta
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


@pytest.mark.asyncio
async def test_voice_notification_confirm_scenario_press_1_controller(client, db_session):
    """
    TEST-ID: 4
    Module: AI Voice Notification
    Scenario: Confirm
    Steps: Press 1
    Expected Result: Status becomes Confirmed; logged
    Priority: H
    """
    from app.utils.auth import create_access_token

    hr = User(
        email="hr_press1@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="Engr. Bautista"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-PRESS1",
        job_title="Electrical Supervisor",
        department="Maintenance",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 1, Sto. Tomas, Batangas",
        description="Power plant & substation monitoring"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Eduardo Ramos"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="eduardo.ramos@example.com",
        phone="+639175554433",
        job_title="Electrical Supervisor",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Electrical Supervisor Screening",
        start_time=datetime(2026, 11, 27, 11, 0, 0),
        end_time=datetime(2026, 11, 27, 12, 0, 0),
        status="SCHEDULED",
        call_status="PENDING"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # Step 1: Place automated voice call
    call_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call_resp.status_code == 200
    call_sid = call_resp.json()["call_sid"]

    # Step 2: Steps: Press 1 (candidate presses 1 on keypad during call)
    dtmf_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}",
        data={"Digits": "1", "CallSid": call_sid}
    )
    assert dtmf_resp.status_code == 200
    assert "application/xml" in dtmf_resp.headers["content-type"]
    assert "confirmed" in dtmf_resp.text.lower() or "salamat" in dtmf_resp.text.lower()

    # Step 3: Expected Result: Status becomes Confirmed
    await db_session.refresh(interview)
    assert interview.status == "CONFIRMED"
    assert interview.call_status == "CONFIRMED"
    assert interview.candidate_response == "CONFIRMED"
    assert interview.verbal_notes == "Pressed key 1"

    # Step 4: Expected Result: Logged in Call Logs endpoint
    logs_resp = await client.get(f"/ai-caller/interview/{interview.id}/logs", headers=headers)
    assert logs_resp.status_code == 200
    call_records = logs_resp.json()

    # Call record verification
    assert len(call_records) >= 1
    latest_rec = call_records[0]
    assert latest_rec["extracted_intent"] == "CONFIRMED"
    assert latest_rec["candidate_verbal_response"] == "Pressed key 1"
    assert latest_rec["status"] == "COMPLETED"

    # Interview logs verification
    logs_q = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_CONFIRMED"
        )
    )
    confirm_logs = logs_q.scalars().all()
    assert len(confirm_logs) >= 1
    assert "CONFIRMED" in confirm_logs[0].details
    assert "Pressed key 1" in confirm_logs[0].details


@pytest.mark.asyncio
async def test_voice_notification_reschedule_scenario_press_2_controller(client, db_session):
    """
    TEST-ID: 5
    Module: AI Voice Notification
    Scenario: Reschedule
    Steps: Press 2
    Expected Result: Status becomes Reschedule requested; HR notified
    Priority: H
    """
    from app.utils.auth import create_access_token
    from app.models.notification import Notification

    hr = User(
        email="hr_press2_ctrl@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Officer Mendoza"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-PRESS2",
        job_title="Quality Assurance Chemist",
        department="Quality Control",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 1, Sto. Tomas, Batangas",
        description="Raw material glaze and chemical formulation analysis"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Emilio Aguinaldo"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="emilio.aguinaldo@example.com",
        phone="+639176665544",
        job_title="Quality Assurance Chemist",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="QA Chemist Interview",
        start_time=datetime(2026, 11, 27, 13, 30, 0),
        end_time=datetime(2026, 11, 27, 14, 30, 0),
        status="SCHEDULED",
        call_status="PENDING"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # Step 1: Place automated voice call
    call_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call_resp.status_code == 200
    call_sid = call_resp.json()["call_sid"]

    # Step 2: Candidate presses 2 on keypad during call
    dtmf_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}",
        data={"Digits": "2", "CallSid": call_sid}
    )
    assert dtmf_resp.status_code == 200
    assert "application/xml" in dtmf_resp.headers["content-type"]
    assert "reschedule" in dtmf_resp.text.lower() or "naitala" in dtmf_resp.text.lower()

    # Step 3: Expected Result: Status becomes Reschedule requested
    await db_session.refresh(interview)
    assert interview.status == "RESCHEDULE_REQUESTED"
    assert interview.call_status == "RESCHEDULE_REQUESTED"
    assert interview.candidate_response == "RESCHEDULE_REQUESTED"
    assert interview.verbal_notes == "Pressed key 2"

    # Step 4: Expected Result: HR notified (notification stored in database)
    notif_q = await db_session.execute(
        select(Notification).where(
            Notification.target_role == "HR",
            Notification.title.like("%Reschedule Requested%")
        ).order_by(Notification.id.desc())
    )
    hr_notif = notif_q.scalars().first()
    assert hr_notif is not None
    assert cand_name in hr_notif.message
    assert "RESCHEDULE" in hr_notif.message
    assert "Pressed key 2" in hr_notif.message

    # Step 5: Logged in Call Logs endpoint
    logs_resp = await client.get(f"/ai-caller/interview/{interview.id}/logs", headers=headers)
    assert logs_resp.status_code == 200
    call_records = logs_resp.json()
    assert len(call_records) >= 1
    latest_rec = call_records[0]
    assert latest_rec["extracted_intent"] == "RESCHEDULE_REQUESTED"
    assert latest_rec["candidate_verbal_response"] == "Pressed key 2"
    assert latest_rec["status"] == "COMPLETED"

    # Interview logs verification
    logs_q = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_RESCHEDULE"
        )
    )
    resched_logs = logs_q.scalars().all()
    assert len(resched_logs) >= 1
    assert "RESCHEDULE" in resched_logs[0].details
    assert "Pressed key 2" in resched_logs[0].details


@pytest.mark.asyncio
async def test_voice_notification_speak_to_hr_scenario_press_3_controller(client, db_session):
    """
    TEST-ID: 6
    Module: AI Voice Notification
    Scenario: Speak to HR
    Steps: Press 3
    Expected Result: Escalated to HR; logged
    Priority: L
    """
    from app.utils.auth import create_access_token
    from app.models.notification import Notification

    hr = User(
        email="hr_press3_ctrl@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Officer Bautista"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-PRESS3",
        job_title="Automation & Robotics Technician",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 1, Sto. Tomas, Batangas",
        description="PLC, sensors, and robotics automation maintenance"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Manuel L. Quezon"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="manuel.quezon@example.com",
        phone="+639175551122",
        job_title="Automation & Robotics Technician",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Automation Technician Interview",
        start_time=datetime(2026, 11, 28, 10, 0, 0),
        end_time=datetime(2026, 11, 28, 11, 0, 0),
        status="SCHEDULED",
        call_status="PENDING"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # Step 1: Place automated voice call
    call_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call_resp.status_code == 200
    call_sid = call_resp.json()["call_sid"]

    # Step 2: Candidate presses 3 on keypad during call
    dtmf_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}",
        data={"Digits": "3", "CallSid": call_sid}
    )
    assert dtmf_resp.status_code == 200
    assert "application/xml" in dtmf_resp.headers["content-type"]
    assert "hr" in dtmf_resp.text.lower()

    # Step 3: Expected Result: Status becomes Escalated to HR
    await db_session.refresh(interview)
    assert interview.status == "ESCALATED_TO_HR"
    assert interview.call_status == "ESCALATED_TO_HR"
    assert interview.candidate_response == "ESCALATED_TO_HR"
    assert interview.verbal_notes == "Pressed key 3"

    # Step 4: Expected Result: HR notified (notification stored in database)
    notif_q = await db_session.execute(
        select(Notification).where(
            Notification.target_role == "HR",
            Notification.title.like("%Escalated to HR%")
        ).order_by(Notification.id.desc())
    )
    hr_notif = notif_q.scalars().first()
    assert hr_notif is not None
    assert cand_name in hr_notif.message
    assert "Pressed key 3" in hr_notif.message

    # Step 5: Logged in Call Logs endpoint
    logs_resp = await client.get(f"/ai-caller/interview/{interview.id}/logs", headers=headers)
    assert logs_resp.status_code == 200
    call_records = logs_resp.json()
    assert len(call_records) >= 1
    latest_rec = call_records[0]
    assert latest_rec["extracted_intent"] == "ESCALATED_TO_HR"
    assert latest_rec["candidate_verbal_response"] == "Pressed key 3"
    assert latest_rec["status"] == "COMPLETED"

    # Interview logs verification
    logs_q = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_ESCALATED"
        )
    )
    escalate_logs = logs_q.scalars().all()
    assert len(escalate_logs) >= 1
    assert "SPEAK TO HR" in escalate_logs[0].details or "ESCALATED" in escalate_logs[0].details
    assert "Pressed key 3" in escalate_logs[0].details

    # Step 6: Test simulation endpoint with Press 3
    sim_resp = await client.post(
        f"/ai-caller/interview/{interview.id}/simulate",
        json={"outcome": "ESCALATED_TO_HR", "spoken_phrase": "Pressed key 3", "language": "fil"},
        headers=headers
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["interview_status"] == "ESCALATED_TO_HR"
    assert sim_resp.json()["call_status"] == "ESCALATED_TO_HR"


@pytest.mark.asyncio
async def test_voice_notification_invalid_key_and_timeout_controller(client, db_session):
    """
    TEST-ID: 7
    Module: AI Voice Notification
    Scenario: Invalid key and timeout
    Steps: Press 9, then press nothing for 30 s
    Expected Result: Prompt repeats once; timeout logged as no response
    Priority: M
    """
    from app.utils.auth import create_access_token

    hr = User(
        email="hr_press9_ctrl@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Officer Del Pilar"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-PRESS9",
        job_title="Production Line Controller",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 2, Sto. Tomas, Batangas",
        description="Continuous tile extrusion and conveyor systems control"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Gregorio Del Pilar"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="gregorio.delpilar@example.com",
        phone="+639177778899",
        job_title="Production Line Controller",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Production Line Controller Interview",
        start_time=datetime(2026, 11, 29, 14, 0, 0),
        end_time=datetime(2026, 11, 29, 15, 0, 0),
        status="SCHEDULED",
        call_status="PENDING"
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # Step 1: Place automated voice call
    call_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call_resp.status_code == 200
    call_sid = call_resp.json()["call_sid"]

    # Step 2: Candidate presses 9 (invalid key) on attempt 1
    dtmf_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}&attempt=1",
        data={"Digits": "9", "CallSid": call_sid}
    )
    assert dtmf_resp.status_code == 200
    assert "application/xml" in dtmf_resp.headers["content-type"]
    assert "<Gather" in dtmf_resp.text
    assert 'timeout="30"' in dtmf_resp.text
    assert "attempt=2" in dtmf_resp.text
    assert "Invalid key pressed" in dtmf_resp.text or "Repeating the options" in dtmf_resp.text

    # Verify invalid input logged in InterviewLog
    inv_logs_q = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_INVALID_INPUT"
        )
    )
    inv_logs = inv_logs_q.scalars().all()
    assert len(inv_logs) >= 1
    assert "Pressed key 9" in inv_logs[0].details
    assert "Prompt repeating once" in inv_logs[0].details

    # Step 3: Candidate presses nothing for 30s (timeout callback on attempt 2)
    timeout_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}&attempt=2",
        data={"CallSid": call_sid}
    )
    assert timeout_resp.status_code == 200
    assert "application/xml" in timeout_resp.headers["content-type"]
    assert "hangup" in timeout_resp.text.lower()

    # Step 4: Expected Result: Timeout logged as no response
    await db_session.refresh(interview)
    assert interview.candidate_response == "NO_RESPONSE"
    assert "Timeout" in interview.verbal_notes
    assert interview.call_status == "RETRY_SCHEDULED"

    # Verify timeout logged in InterviewLog
    timeout_logs_q = await db_session.execute(
        select(InterviewLog).where(
            InterviewLog.interview_id == interview.id,
            InterviewLog.log_type == "VOICE_CALL_NO_RESPONSE"
        )
    )
    timeout_logs = timeout_logs_q.scalars().all()
    assert len(timeout_logs) >= 1
    assert "timed out after 30 seconds with no response" in timeout_logs[0].details
    assert "Logged as no response" in timeout_logs[0].details

    # Step 5: Verify Call Logs endpoint reflects NO_RESPONSE
    logs_resp = await client.get(f"/ai-caller/interview/{interview.id}/logs", headers=headers)
    assert logs_resp.status_code == 200
    call_records = logs_resp.json()
    assert len(call_records) >= 1
    latest_rec = call_records[0]
    assert latest_rec["extracted_intent"] == "NO_RESPONSE"
    assert latest_rec["status"] == "NO_RESPONSE"
    assert "no response" in latest_rec["notes"].lower()

    # Step 6: Test simulation endpoint with INVALID_KEY_THEN_TIMEOUT
    sim_resp = await client.post(
        f"/ai-caller/interview/{interview.id}/simulate",
        json={"outcome": "INVALID_KEY_THEN_TIMEOUT", "spoken_phrase": "Pressed key 9 -> Timeout (30s)", "language": "en"},
        headers=headers
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["call_status"] == "RETRY_SCHEDULED"


@pytest.mark.asyncio
async def test_voice_notification_retry_logic_schedule_and_max_retries_controller(client, db_session):
    """
    TEST-ID: 8
    Module: AI Voice Notification
    Scenario: Retry logic
    Steps: Let calls go unanswered
    Expected Result: Retries occur per schedule (2 h, 6 h, 12 h), maximum 3 within 24 h
    Priority: H
    """
    from datetime import timedelta
    from app.utils.auth import create_access_token

    hr = User(
        email="hr_retry_ctrl@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Scheduler Alvarez"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-RETRY-CTRL",
        job_title="Industrial Automation Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 1, Sto. Tomas, Batangas",
        description="SCADA and PLC engineering"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Antonio Luna"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="antonio.luna@example.com",
        phone="+639179998877",
        job_title="Industrial Automation Engineer",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Automation Engineer Interview",
        start_time=datetime(2026, 11, 30, 10, 0, 0),
        end_time=datetime(2026, 11, 30, 11, 0, 0),
        status="SCHEDULED",
        call_status="PENDING",
        call_attempts=0
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # 1. Place initial call (Attempt 1)
    call1_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call1_resp.status_code == 200
    call1_sid = call1_resp.json()["call_sid"]

    # Call 1 status callback: no-answer
    t1 = datetime.utcnow()
    cb1 = await client.post(
        f"/ai-caller/status-callback?interview_id={interview.id}",
        data={"CallSid": call1_sid, "CallStatus": "no-answer", "CallDuration": "0"}
    )
    assert cb1.status_code == 200
    await db_session.refresh(interview)
    assert interview.call_status == "RETRY_SCHEDULED"
    assert abs((interview.next_retry_at - (t1 + timedelta(hours=2))).total_seconds()) < 60

    # 2. Place Retry #1 (Attempt 2)
    call2_resp = await client.post(f"/ai-caller/interview/{interview.id}/retry", headers=headers)
    assert call2_resp.status_code == 200
    call2_sid = call2_resp.json()["call_sid"]

    # Call 2 status callback: no-answer
    t2 = datetime.utcnow()
    cb2 = await client.post(
        f"/ai-caller/status-callback?interview_id={interview.id}",
        data={"CallSid": call2_sid, "CallStatus": "no-answer", "CallDuration": "0"}
    )
    assert cb2.status_code == 200
    await db_session.refresh(interview)
    assert interview.call_status == "RETRY_SCHEDULED"
    assert abs((interview.next_retry_at - (t2 + timedelta(hours=6))).total_seconds()) < 60

    # 3. Place Retry #2 (Attempt 3)
    call3_resp = await client.post(f"/ai-caller/interview/{interview.id}/retry", headers=headers)
    assert call3_resp.status_code == 200
    call3_sid = call3_resp.json()["call_sid"]

    # Call 3 status callback: no-answer
    t3 = datetime.utcnow()
    cb3 = await client.post(
        f"/ai-caller/status-callback?interview_id={interview.id}",
        data={"CallSid": call3_sid, "CallStatus": "no-answer", "CallDuration": "0"}
    )
    assert cb3.status_code == 200
    await db_session.refresh(interview)
    assert interview.call_status == "RETRY_SCHEDULED"
    assert abs((interview.next_retry_at - (t3 + timedelta(hours=12))).total_seconds()) < 60

    # 4. Place Retry #3 (Attempt 4, max 3 retries within 24h)
    call4_resp = await client.post(f"/ai-caller/interview/{interview.id}/retry", headers=headers)
    assert call4_resp.status_code == 200
    call4_sid = call4_resp.json()["call_sid"]

    # Call 4 status callback: no-answer -> all retries exhausted
    with patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms:
        cb4 = await client.post(
            f"/ai-caller/status-callback?interview_id={interview.id}",
            data={"CallSid": call4_sid, "CallStatus": "no-answer", "CallDuration": "0"}
        )
        assert cb4.status_code == 200

    await db_session.refresh(interview)
    assert interview.call_status in ["UNREACHABLE", "SMS_BACKUP_SENT"]
    assert interview.next_retry_at is None
    assert interview.sms_backup_sent is True


@pytest.mark.asyncio
async def test_voice_notification_stop_retries_after_confirm_attempt_2_controller(client, db_session):
    """
    TEST-ID: 9
    Module: AI Voice Notification
    Scenario: Stop Retries after confirm
    Steps: Confirm on attempt 2
    Expected Result: No attempt 3
    Priority: M
    """
    from app.utils.auth import create_access_token

    hr = User(
        email="hr_stop_attempt2_ctrl@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Scheduler Trinidad"
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-STOP-CTRL",
        job_title="Kiln Thermal Systems Supervisor",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Mariwasa Plant 1, Sto. Tomas, Batangas",
        description="High-temperature kiln thermodynamics"
    )
    db_session.add(job)
    await db_session.flush()

    cand_name = "Teresa Magbanua"
    app = JobApplication(
        job_id=job.id,
        candidate_name=cand_name,
        candidate_email="teresa.magbanua@example.com",
        phone="+639174445566",
        job_title="Kiln Thermal Systems Supervisor",
        status="SHORTLISTED"
    )
    db_session.add(app)
    await db_session.flush()

    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Kiln Supervisor Interview",
        start_time=datetime(2026, 12, 1, 11, 0, 0),
        end_time=datetime(2026, 12, 1, 12, 0, 0),
        status="SCHEDULED",
        call_status="PENDING",
        call_attempts=0
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # 1. Place initial call (Attempt 1)
    call1_resp = await client.post(f"/ai-caller/interview/{interview.id}/call", headers=headers)
    assert call1_resp.status_code == 200
    call1_sid = call1_resp.json()["call_sid"]

    # Call 1 status callback: no-answer
    cb1 = await client.post(
        f"/ai-caller/status-callback?interview_id={interview.id}",
        data={"CallSid": call1_sid, "CallStatus": "no-answer", "CallDuration": "0"}
    )
    assert cb1.status_code == 200
    await db_session.refresh(interview)
    assert interview.call_status == "RETRY_SCHEDULED"
    assert interview.call_attempts == 1

    # 2. Place Retry #1 (Attempt 2)
    call2_resp = await client.post(f"/ai-caller/interview/{interview.id}/retry", headers=headers)
    assert call2_resp.status_code == 200
    call2_sid = call2_resp.json()["call_sid"]
    await db_session.refresh(interview)
    assert interview.call_attempts == 2

    # Steps: Candidate confirms on attempt 2 (e.g. presses 1)
    conf_resp = await client.post(
        f"/ai-caller/voice-response?interview_id={interview.id}&attempt=2",
        data={"Digits": "1", "CallSid": call2_sid}
    )
    assert conf_resp.status_code == 200
    await db_session.refresh(interview)
    assert interview.status == "CONFIRMED"
    assert interview.call_status == "CONFIRMED"
    assert interview.candidate_response == "CONFIRMED"
    assert interview.next_retry_at is None

    # Call 2 status callback: completed
    cb2 = await client.post(
        f"/ai-caller/status-callback?interview_id={interview.id}",
        data={"CallSid": call2_sid, "CallStatus": "completed", "CallDuration": "45"}
    )
    assert cb2.status_code == 200
    await db_session.refresh(interview)
    assert interview.call_status == "CONFIRMED"
    assert interview.next_retry_at is None

    # 3. Expected Result: No attempt 3
    # Check interview attempts count remains strictly at 2
    assert interview.call_attempts == 2

    # Verify call logs list exactly 2 records, not 3
    logs_resp = await client.get(f"/ai-caller/interview/{interview.id}/logs", headers=headers)
    assert logs_resp.status_code == 200
    call_records = logs_resp.json()
    assert len(call_records) == 2
    attempts_in_records = [r["attempt_number"] for r in call_records]
    assert 3 not in attempts_in_records
    assert attempts_in_records == [2, 1]  # Ordered desc


@pytest.mark.asyncio
async def test_calendar_feed_and_candidate_call_logs_endpoints(client, db_session):
    """Verify upcoming interviews in calendar feed and call logs for candidate profile endpoints."""
    from app.utils.auth import create_access_token

    hr = User(
        email="hr_calendar_calls@mariwasa.com",
        password="pwd",
        role="HR",
        fullname="HR Calendar Reviewer",
    )
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="JOB-CAL-LOGS-1",
        job_title="Ceramics Production Lead",
        department="Operations",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Lead production line",
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Liza Soberano",
        candidate_email="liza.cal.logs@example.com",
        phone="+639175551234",
        job_title="Ceramics Production Lead",
        status="REVIEWED",
    )
    db_session.add(app)
    await db_session.flush()

    upcoming_start = (datetime.utcnow() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    upcoming_end = upcoming_start + timedelta(hours=1)
    interview = Interview(
        job_application_id=app.id,
        interviewer_id=hr.id,
        title="Production Lead Panel Interview",
        start_time=upcoming_start,
        end_time=upcoming_end,
        status="SCHEDULED",
        call_status="PENDING",
        call_attempts=0,
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': hr.email, 'id': hr.id, 'role': 'HR'})}"}

    # Simulate an outbound voice call confirmation so call log + interview state are recorded
    sim_res = await client.post(
        f"/ai-caller/interview/{interview.id}/simulate",
        json={"outcome": "CONFIRMED", "spoken_phrase": "Yes, I will attend tomorrow.", "language": "en"},
        headers=headers,
    )
    assert sim_res.status_code == 200

    # 1. Calendar feed shows the upcoming interview and call attempts
    feed_res = await client.get("/interviews/calendar-feed", headers=headers)
    assert feed_res.status_code == 200
    feed_interviews = feed_res.json().get("interviews", [])
    matched_feed = [iv for iv in feed_interviews if iv["id"] == interview.id]
    assert len(matched_feed) == 1
    assert matched_feed[0]["candidate_name"] == "Liza Soberano"
    assert matched_feed[0]["call_attempts"] == 1
    assert matched_feed[0]["call_status"] == "CONFIRMED"
    assert len(matched_feed[0]["call_records"]) == 1

    # 2. Candidate profile endpoints (by application ID and case-insensitive email) return upcoming interview + call records
    app_iv_res = await client.get(f"/interviews/application/{app.id}", headers=headers)
    assert app_iv_res.status_code == 200
    assert len(app_iv_res.json()) == 1
    assert len(app_iv_res.json()[0]["call_records"]) == 1

    cand_iv_res = await client.get("/interviews/candidate/LIZA.CAL.LOGS@EXAMPLE.COM", headers=headers)
    assert cand_iv_res.status_code == 200
    assert len(cand_iv_res.json()) == 1
    assert cand_iv_res.json()[0]["id"] == interview.id

    # 3. Dedicated candidate profile call log endpoints return full call history
    app_logs_res = await client.get(f"/ai-caller/application/{app.id}/logs", headers=headers)
    assert app_logs_res.status_code == 200
    app_logs = app_logs_res.json()
    assert len(app_logs) == 1
    assert app_logs[0]["interview_title"] == "Production Lead Panel Interview"
    assert app_logs[0]["extracted_intent"] == "CONFIRMED"
    assert app_logs[0]["candidate_verbal_response"] == "Yes, I will attend tomorrow."

    cand_logs_res = await client.get("/ai-caller/candidate/LIZA.CAL.LOGS@EXAMPLE.COM/logs", headers=headers)
    assert cand_logs_res.status_code == 200
    cand_logs = cand_logs_res.json()
    assert len(cand_logs) == 1
    assert cand_logs[0]["id"] == app_logs[0]["id"]




