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
