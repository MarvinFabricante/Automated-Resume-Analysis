import pytest
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
