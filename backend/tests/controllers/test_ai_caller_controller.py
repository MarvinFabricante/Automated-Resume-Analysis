import pytest
from unittest.mock import patch, AsyncMock


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


