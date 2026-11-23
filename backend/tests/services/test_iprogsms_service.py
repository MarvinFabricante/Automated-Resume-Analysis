from datetime import datetime
from pathlib import Path
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.interview_service import (
    _dispatch_candidate_sms,
    _resolve_candidate_phone,
    check_iprogsms_credits,
    check_iprogsms_message_status,
    detect_phone_network_iprogsms,
    format_phone_for_iprogsms,
    format_phone_for_iprogsms_detect,
    format_to_e164,
    send_iprogsms_sync,
    send_sms_notification_sync,
    validate_iprogsms_content,
    _extract_phone_from_parsed_payload,
)


@pytest.mark.parametrize("phone", [None, "N/A", "1234567", "0917123456", "091712345678", "(02) 8123-4567", "+1 202 555 0123", "ID: 09171234567"])
def test_sms_rejects_invalid_or_non_mobile_recipients(phone):
    with patch("app.services.interview_service.requests.post") as post:
        assert format_phone_for_iprogsms(phone) == ""
        assert not send_iprogsms_sync(phone, "Test")
        post.assert_not_called()


def test_sms_selects_mobile_after_landline_and_reads_nested_contact():
    assert format_phone_for_iprogsms("(02) 8123-4567 / (+63) 917 555 8899") == "639175558899"
    assert _extract_phone_from_parsed_payload({"phone": "1234567", "personal": {"phone": "0917-555-8899"}}) == "0917-555-8899"
    assert _extract_phone_from_parsed_payload({"references": [{"phone": "09175558899"}], "all_phones": ["09175558899"]}) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("phone", [None, "N/A", "(02) 8123-4567"])
async def test_missing_sms_recipient_is_logged_without_sending(phone):
    with patch("app.services.interview_service.requests.post") as post, \
         patch("app.services.interview_service.InterviewRepository.add_interview_log", new_callable=AsyncMock) as log, \
         patch("app.services.interview_service.InterviewRepository.commit_changes", new_callable=AsyncMock):
        assert not await _dispatch_candidate_sms(AsyncMock(), 1, phone, "Interview", "SMS_SENT", "SMS queued")
        post.assert_not_called()
        assert log.call_args.args[2] == "SMS_FAILED"
        assert "Missing or invalid Philippine mobile" in log.call_args.args[3]


@pytest.mark.parametrize("body", [None, [], "upstream error", {"status": 500, "message": "Insufficient credits"}])
def test_sms_handles_malformed_and_error_responses(body):
    response = MagicMock(status_code=200, text="upstream error")
    response.json.return_value = body
    with patch.dict("os.environ", {"IPROG_SMS_API_TOKEN": "test-token"}), \
         patch("app.services.interview_service.requests.post", return_value=response):
        assert not send_iprogsms_sync("09175558899", "Test")


@pytest.mark.asyncio
async def test_resume_extraction_to_sms_payload_and_queue_log(tmp_path):
    """Exercise extraction, recipient resolution, dispatch, and logging without real messages."""
    import fitz
    from app.extractors.resume_processor import process_resume

    resume_path = tmp_path / "sample-resume.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Sample Applicant\nMobile: (+63) 917 555 8899\napplicant@example.com\nSkills: Python")
        document.save(resume_path)
    parsed = process_resume(str(resume_path), "pdf")
    application = SimpleNamespace(phone=parsed["candidate_phone"])
    resolved = await _resolve_candidate_phone(AsyncMock(), application)
    response = MagicMock(status_code=200, text="{}")
    response.json.return_value = {"status": 200, "message_id": "iSms-test"}
    with patch.dict("os.environ", {"IPROG_SMS_API_TOKEN": "test-token", "IPROG_SMS_API_URL": "https://www.iprogsms.com/api/v1/"}), \
         patch("app.services.interview_service.requests.post", return_value=response) as post, \
         patch("app.services.interview_service.InterviewRepository.add_interview_log", new_callable=AsyncMock) as log, \
         patch("app.services.interview_service.InterviewRepository.commit_changes", new_callable=AsyncMock):
        assert await _dispatch_candidate_sms(AsyncMock(), 1, resolved, "Interview test", "SMS_SENT", "SMS delivered")
        assert post.call_args.args[0] == "https://www.iprogsms.com/api/v1/sms_messages"
        assert post.call_args.kwargs["json"]["phone_number"] == "639175558899"
        assert "queued" in log.call_args.args[3]
        assert "delivered" not in log.call_args.args[3]
        assert "[message_id=iSms-test]" in log.call_args.args[3]


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
@pytest.mark.parametrize("stored_phone", ["N/A", "1234567", "(02) 8123-4567"])
async def test_resolve_candidate_phone_falls_back_to_physical_resume_parsed_data(db_session, stored_phone):
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
        phone=stored_phone,
        candidate_email="walkin_resume_phone@gmail.com",
        resume_url="/uploads/physical_resumes/test_walkin.pdf",
    )
    resolved = await _resolve_candidate_phone(db_session, app_obj)
    assert resolved == "0917-555-8899"
    assert app_obj.phone == "0917-555-8899"


def test_format_phone_for_iprogsms_detect_normalizes_to_11_digit_local():
    """Formats dashed/E.164 PH numbers into 09XXXXXXXXX for /api/v1/phone_numbers/detect."""
    assert format_phone_for_iprogsms_detect("0960-246-5936") == "09602465936"
    assert format_phone_for_iprogsms_detect("+63 960 246 5936") == "09602465936"
    assert format_phone_for_iprogsms_detect("639602465936") == "09602465936"
    assert format_phone_for_iprogsms_detect("N/A") == ""


def test_send_iprogsms_sync_clamps_unsupported_sms_provider_to_default():
    """Falls back to sms_provider=0 when IPROG_SMS_PROVIDER is outside {0, 1, 2}."""
    mock_resp = MagicMock(status_code=200, text='{"status": 200, "message_id": "iSms-99"}')
    mock_resp.json.return_value = {"status": 200, "message_id": "iSms-99"}

    with patch.dict(
        "os.environ",
        {
            "IPROG_SMS_API_TOKEN": "tok",
            "IPROG_SMS_API_URL": "https://www.iprogsms.com/api/v1/sms_messages",
            "IPROG_SMS_PROVIDER": "99",
            "IPROG_SMS_SENDER_NAME": "",
        },
        clear=False,
    ), patch("app.services.interview_service.requests.post", return_value=mock_resp) as mock_post:
        ok = send_iprogsms_sync("09171234567", "Provider clamp check")

    assert ok is True
    assert mock_post.call_args.kwargs["json"]["sms_provider"] == 0


def test_iprogsms_v1_diagnostic_helpers():
    """Verifies credits, network detect, message status, and content validation helpers against v1 API."""
    env = {
        "IPROG_SMS_API_TOKEN": "tok_v1",
        "IPROG_SMS_API_URL": "https://www.iprogsms.com/api/v1/sms_messages",
    }

    detect_resp = MagicMock(status_code=200, text="{}")
    detect_resp.json.return_value = {
        "status": "success",
        "data": {"phone_number": "09602465936", "is_smart_tnt": True, "network": "Smart/TNT"},
    }
    credits_resp = MagicMock(status_code=200, text="{}")
    credits_resp.json.return_value = {"status": "success", "data": {"load_balance": "199.0"}}
    status_resp = MagicMock(status_code=200, text="{}")
    status_resp.json.return_value = {"status": 200, "message_status": "completed"}
    validate_resp = MagicMock(status_code=200, text="{}")
    validate_resp.json.return_value = {
        "status": "success",
        "message": "Message passed validation",
        "data": {"passed": True, "warnings": []},
    }

    with patch.dict("os.environ", env, clear=False), \
         patch("app.services.interview_service.requests.post", return_value=detect_resp) as mock_post, \
         patch(
             "app.services.interview_service.requests.get",
             side_effect=[credits_resp, status_resp, validate_resp],
         ) as mock_get:
        net = detect_phone_network_iprogsms("0960-246-5936")
        creds = check_iprogsms_credits()
        msg_status = check_iprogsms_message_status("iSms-abc123")
        val = validate_iprogsms_content("Mariwasa HR Interview Test")

    assert net == {
        "ok": True,
        "phone_number": "09602465936",
        "network": "Smart/TNT",
        "is_smart_tnt": True,
        "error": None,
    }
    mock_post.assert_called_once_with(
        "https://www.iprogsms.com/api/v1/phone_numbers/detect",
        json={"api_token": "tok_v1", "phone_number": "09602465936"},
        timeout=15,
    )
    assert creds == {"ok": True, "load_balance": "199.0", "error": None}
    assert msg_status == {"ok": True, "message_id": "iSms-abc123", "message_status": "completed", "error": None}
    assert val == {
        "ok": True,
        "passed": True,
        "warnings": [],
        "message": "Message passed validation",
        "error": None,
    }
    assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_john_paul_basagre_resume_sms_extraction_formatting_and_dispatch():
    """End-to-end check on John Paul Basagre's resume: extract phone, render SMS template, log message_id or Smart/TNT failure."""
    from app.extractors.resume_processor import process_resume
    from app.services.message_template_service import (
        DEFAULT_TEMPLATES,
        build_interview_template_context,
        render_template,
    )

    resume_path = Path(__file__).resolve().parents[2] / "uploads" / "resumes" / "1779865932_jampol.pdf"
    if not resume_path.is_file():
        pytest.skip("Sample resume 1779865932_jampol.pdf is not present in uploads/resumes")

    parsed = process_resume(str(resume_path), "pdf")
    assert "john paul" in (parsed.get("candidate_name") or "").lower()
    assert parsed.get("phone") == "0960-246-5936"
    assert format_phone_for_iprogsms(parsed["phone"]) == "639602465936"
    assert format_to_e164(parsed["phone"]) == "+639602465936"
    assert format_phone_for_iprogsms_detect(parsed["phone"]) == "09602465936"

    ctx = build_interview_template_context(
        candidate_name=parsed["candidate_name"],
        job_title="Software Developer",
        interview_title="Technical Interview",
        start_time=datetime(2026, 11, 25, 10, 0),
        end_time=datetime(2026, 11, 25, 11, 0),
        interviewer_name="Mariwasa HR Panel",
        location="Mariwasa Head Office",
    )
    rendered_sms = render_template(DEFAULT_TEMPLATES["interview_scheduled"]["sms_message"], ctx)
    assert "John Paul" in rendered_sms

    # 1) When accepted (e.g., with approved custom sender), logs SMS_SENT with message_id
    ok_resp = MagicMock(status_code=200, text='{"status": 200, "message_id": "iSms-JP001"}')
    ok_resp.json.return_value = {"status": 200, "message": "Queued", "message_id": "iSms-JP001"}
    mock_db = AsyncMock()
    with patch.dict(
        "os.environ",
        {"IPROG_SMS_API_TOKEN": "tok", "IPROG_SMS_PROVIDER": "0", "IPROG_SMS_SENDER_NAME": "MARIWASA"},
        clear=False,
    ), patch("app.services.interview_service.requests.post", return_value=ok_resp), \
       patch("app.services.interview_service.InterviewRepository.add_interview_log", new_callable=AsyncMock) as mock_log, \
       patch("app.services.interview_service.InterviewRepository.commit_changes", new_callable=AsyncMock):
        sent = await _dispatch_candidate_sms(
            mock_db, 101, parsed["phone"], rendered_sms, "SMS_SENT", "SMS interview notification delivered"
        )

    assert sent is True
    _, _, event_name, log_desc = mock_log.call_args[0]
    assert event_name == "SMS_SENT"
    assert "+639602465936" in log_desc
    assert "[message_id=iSms-JP001]" in log_desc

    # 2) When rejected by Smart/TNT shared-sender restriction, logs SMS_FAILED with exact provider reason
    fail_resp = MagicMock(
        status_code=200,
        text='{"status":500,"message":["Smart/TNT networks do not accept shared sender names. Please get your own sender name approved at https://www.iprogsms.com/sender-names/new to support all networks."]}',
    )
    fail_resp.json.return_value = {
        "status": 500,
        "message": [
            "Smart/TNT networks do not accept shared sender names. Please get your own sender name approved at https://www.iprogsms.com/sender-names/new to support all networks."
        ],
    }
    with patch.dict(
        "os.environ",
        {"IPROG_SMS_API_TOKEN": "tok", "IPROG_SMS_PROVIDER": "0", "IPROG_SMS_SENDER_NAME": ""},
        clear=False,
    ), patch("app.services.interview_service.requests.post", return_value=fail_resp), \
       patch("app.services.interview_service.InterviewRepository.add_interview_log", new_callable=AsyncMock) as mock_fail_log, \
       patch("app.services.interview_service.InterviewRepository.commit_changes", new_callable=AsyncMock):
        sent_fail = await _dispatch_candidate_sms(
            mock_db, 101, parsed["phone"], rendered_sms, "SMS_SENT", "SMS interview notification delivered"
        )

    assert sent_fail is False
    _, _, fail_event, fail_desc = mock_fail_log.call_args[0]
    assert fail_event == "SMS_FAILED"
    assert "+639602465936" in fail_desc
    assert "Smart/TNT networks do not accept shared sender names" in fail_desc
