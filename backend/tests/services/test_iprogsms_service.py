from unittest.mock import MagicMock, patch

from app.services.interview_service import (
    format_phone_for_iprogsms,
    send_iprogsms_sync,
    send_sms_notification_sync,
)


def test_format_phone_for_iprogsms_normalizes_ph_formats():
    """Converts PH local/E.164 numbers to 639XXXXXXXXX digits for IPROG SMS."""
    assert format_phone_for_iprogsms("09771331871") == "639771331871"
    assert format_phone_for_iprogsms("+639771331871") == "639771331871"
    assert format_phone_for_iprogsms("977-133-1871") == "639771331871"
    assert format_phone_for_iprogsms("639771331871") == "639771331871"


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
