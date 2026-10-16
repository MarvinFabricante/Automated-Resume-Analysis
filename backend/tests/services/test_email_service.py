import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.services import email_service


def test_send_smtp_sync_fallback():
    # When credentials not configured, it logs and returns True (graceful dev fallback)
    with patch.dict("os.environ", {"SMTP_USER": "", "SMTP_PASSWORD": ""}):
        success = email_service._send_smtp_sync("test@example.com", "Test Subject", "<p>Body</p>")
        assert success is True


def test_send_smtp_sync_success():
    with patch.dict("os.environ", {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "valid_user@gmail.com",
        "SMTP_PASSWORD": "valid_app_password"
    }), patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        success = email_service._send_smtp_sync("recipient@example.com", "Subject", "<h1>Hello</h1>")
        assert success is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("valid_user@gmail.com", "valid_app_password")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


def test_send_smtp_sync_failure():
    with patch.dict("os.environ", {
        "SMTP_USER": "valid_user@gmail.com",
        "SMTP_PASSWORD": "valid_app_password"
    }), patch("smtplib.SMTP", side_effect=Exception("Connection refused")):
        success = email_service._send_smtp_sync("recipient@example.com", "Subject", "<h1>Hello</h1>")
        assert success is False


@pytest.mark.asyncio
async def test_send_reset_password_email():
    with patch("app.services.email_service._send_smtp_sync", return_value=True):
        res = await email_service.send_reset_password_email("user@example.com", "reset-token-12345")
        assert res is True


@pytest.mark.asyncio
async def test_send_interview_invitation_email():
    start_dt = datetime(2026, 10, 20, 10, 0, 0)
    end_dt = datetime(2026, 10, 20, 11, 0, 0)

    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_interview_invitation_email(
            to_email="candidate@example.com",
            candidate_name="John Candidate",
            job_title="Software Architect",
            interview_title="Technical Interview",
            start_time=start_dt,
            end_time=end_dt,
            interviewer_name="Jane HR",
            notes="Please bring your portfolio."
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "candidate@example.com"
        assert "Software Architect" in args[1]
        assert "John Candidate" in args[2]
        assert "Jane HR" in args[2]
        assert "Please bring your portfolio." in args[2]


@pytest.mark.asyncio
async def test_send_interview_rescheduled_email():
    start_dt = datetime(2026, 10, 22, 14, 0, 0)
    end_dt = datetime(2026, 10, 22, 15, 0, 0)

    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_interview_rescheduled_email(
            to_email="candidate@example.com",
            candidate_name="John Candidate",
            job_title="Software Architect",
            interview_title="Rescheduled Interview",
            start_time=start_dt,
            end_time=end_dt,
            interviewer_name="Jane HR",
            notes="Rescheduled due to panelist conflict."
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "candidate@example.com"
        assert "Rescheduled" in args[1]
        assert "Rescheduled due to panelist conflict." in args[2]
