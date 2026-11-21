import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.interview_service import (
    _dispatch_candidate_sms,
    _resolve_candidate_phone,
    format_phone_for_iprogsms,
    format_to_e164,
    send_iprogsms_sync,
    send_sms_notification_sync,
)


def test_format_phone_for_iprogsms_normalizes_ph_formats():
    """Converts PH local/E.164 numbers to 639XXXXXXXXX digits for IPROG SMS."""
    assert format_phone_for_iprogsms("09771331871") == "639771331871"
    assert format_phone_for_iprogsms("+639771331871") == "639771331871"
    assert format_phone_for_iprogsms("977-133-1871") == "639771331871"
    assert format_phone_for_iprogsms("639771331871") == "639771331871"
    assert format_phone_for_iprogsms("+63 0977 133 1871") == "639771331871"
    assert format_phone_for_iprogsms("00639771331871") == "639771331871"
    assert format_phone_for_iprogsms("09771331871 / 09181234567") == "639771331871"
    assert format_phone_for_iprogsms("N/A") == ""
    assert format_to_e164("+63 0977 133 1871") == "+639771331871"
    assert format_to_e164("Not specified") is None


def test_send_iprogsms_sync_success_and_json_status_check():
    """Returns True only when HTTP 200 and IPROG JSON status indicates success."""
    mock_resp = MagicMock(
        status_code=200,
        text='{"status": 200, "message": "Queued", "message_id": "iSms-XHYBk"}',
    )
    mock_resp.json.return_value = {
        "status": 200,
        "message": "Your SMS message has been successfully added to the queue and will be processed shortly.",
        "message_id": "iSms-XHYBk",
    }

    with patch.dict(
        "os.environ",
        {
            "IPROG_SMS_API_TOKEN": "test_token_123",
            "IPROG_SMS_API_URL": "https://www.iprogsms.com/api/v1/sms_messages",
            "IPROG_SMS_PROVIDER": "1",
        },
        clear=False,
    ), patch("app.services.interview_service.requests.post", return_value=mock_resp) as mock_post:
        ok = send_iprogsms_sync("+639771331871", "Mariwasa HR Interview Test")

    assert ok is True
    mock_post.assert_called_once_with(
        "https://www.iprogsms.com/api/v1/sms_messages",
        json={
            "api_token": "test_token_123",
            "phone_number": "639771331871",
            "message": "Mariwasa HR Interview Test",
            "sms_provider": 1,
        },
        timeout=15,
    )


def test_send_iprogsms_sync_returns_false_on_http_200_api_error():
    """Treats IPROG SMS HTTP 200 responses containing {"status": 500} as failure."""
    mock_resp = MagicMock(
        status_code=200,
        text='{"status":500,"message":"Invalid Token"}',
    )
    mock_resp.json.return_value = {"status": 500, "message": "Invalid Token"}

    with patch.dict("os.environ", {"IPROG_SMS_API_TOKEN": "bad_token"}, clear=False), \
         patch("app.services.interview_service.requests.post", return_value=mock_resp):
        ok = send_iprogsms_sync("09771331871", "Test message")

    assert ok is False


def test_send_sms_notification_sync_routes_to_iprogsms():
    """Routes send_sms_notification_sync directly through IPROG SMS."""
    with patch("app.services.interview_service.send_iprogsms_sync", return_value=True) as mock_iprog:
        ok = send_sms_notification_sync("+639171234567", "Scheduled!")

    assert ok is True
    mock_iprog.assert_called_once_with("+639171234567", "Scheduled!")


def test_send_iprogsms_sync_includes_optional_sender_name():
    """Includes sender_name in payload when IPROG_SMS_SENDER_NAME is configured."""
    mock_resp = MagicMock(status_code=200, text='{"status": 200, "message_id": "iSms-1"}')
    mock_resp.json.return_value = {"status": 200, "message_id": "iSms-1"}

    with patch.dict(
        "os.environ",
        {
            "IPROG_SMS_API_TOKEN": "tok",
            "IPROG_SMS_API_URL": "https://www.iprogsms.com/api/v1/sms_messages",
            "IPROG_SMS_PROVIDER": "0",
            "IPROG_SMS_SENDER_NAME": "MARIWASA",
        },
        clear=False,
    ), patch("app.services.interview_service.requests.post", return_value=mock_resp) as mock_post:
        ok = send_iprogsms_sync("09691734877", "Hello")

    assert ok is True
    assert mock_post.call_args.kwargs["json"]["sender_name"] == "MARIWASA"


@pytest.mark.asyncio
async def test_dispatch_candidate_sms_logs_iprogsms_rejection_reason():
    """Logs the provider error reason in SMS_FAILED when IPROG SMS rejects a number."""
    mock_resp = MagicMock(
        status_code=200,
        text='{"status":500,"message":["Smart/TNT networks do not accept shared sender names."]}',
    )
    mock_resp.json.return_value = {
        "status": 500,
        "message": ["Smart/TNT networks do not accept shared sender names."],
    }

    mock_db = AsyncMock()
    with patch.dict("os.environ", {"IPROG_SMS_API_TOKEN": "tok", "IPROG_SMS_SENDER_NAME": ""}, clear=False), \
         patch("app.services.interview_service.requests.post", return_value=mock_resp), \
         patch("app.services.interview_service.InterviewRepository.add_interview_log", new_callable=AsyncMock) as mock_log, \
         patch("app.services.interview_service.InterviewRepository.commit_changes", new_callable=AsyncMock):
        ok = await _dispatch_candidate_sms(
            mock_db, 63, "0969-173-4877", "Interview scheduled", "SMS_SENT", "SMS delivered"
        )

    assert ok is False
    mock_log.assert_awaited_once()
    _, iv_id, event_name, log_desc = mock_log.call_args[0]
    assert iv_id == 63
    assert event_name == "SMS_FAILED"
    assert "+639691734877" in log_desc
    assert "Smart/TNT networks do not accept shared sender names." in log_desc


@pytest.mark.asyncio
async def test_resolve_candidate_phone_falls_back_to_physical_resume_parsed_data(db_session):
    """Resolves phone from PhysicalResume.parsed_data when JobApplication.phone is blank or N/A."""
    from app.models.physical_resume import PhysicalResume

    pr = PhysicalResume(
        candidate_name="Test Walkin",
        candidate_email="walkin_resume_phone@gmail.com",
        candidate_phone=None,
        filename="resume.pdf",
        file_url="/uploads/physical_resumes/test_walkin.pdf",
        parsed_data={"phone": "0917-555-8899", "email": "walkin_resume_phone@gmail.com"},
    )
    db_session.add(pr)
    await db_session.commit()

    app_obj = SimpleNamespace(
        phone="N/A",
        candidate_email="walkin_resume_phone@gmail.com",
        resume_url="/uploads/physical_resumes/test_walkin.pdf",
    )
    resolved = await _resolve_candidate_phone(db_session, app_obj)
    assert resolved == "0917-555-8899"
    assert app_obj.phone == "0917-555-8899"
