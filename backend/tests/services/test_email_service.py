import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
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


@pytest.mark.asyncio
async def test_send_email_celery_dispatch_failure_fallback():
    with patch("app.utils.redis_client.redis_tx_manager.stage_transaction", new_callable=AsyncMock, return_value="tx-test-123"), \
         patch("app.utils.redis_client.push_to_queue", new_callable=AsyncMock, return_value=True), \
         patch("app.utils.redis_client.redis_tx_manager.commit_transaction", new_callable=AsyncMock, return_value=True), \
         patch("app.tasks.send_email_task.delay", side_effect=Exception("Celery broker connection refused")), \
         patch.dict("os.environ", {"SMTP_USER": "", "SMTP_PASSWORD": ""}), \
         patch.object(email_service.logger, "warning") as mock_logger_warning:

        res = await email_service._send_email_redis_first("test@example.com", "Subject", "<p>Body</p>")
        assert res is True
        mock_logger_warning.assert_called_once()
        assert "Celery dispatch failed" in mock_logger_warning.call_args[0][0]


@pytest.mark.asyncio
async def test_send_application_status_update_email_reviewed():
    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_application_status_update_email(
            to_email="cand.reviewed@example.com",
            candidate_name="Alex Smith",
            job_title="Ceramics Engineer",
            new_status="REVIEWED",
            notes="Initial screening completed with strong match."
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "cand.reviewed@example.com"
        assert "Application Status Update: Ceramics Engineer" in args[1]
        assert "Alex Smith" in args[2]
        assert "Ceramics Engineer" in args[2]
        assert "Under Review" in args[2]
        assert "Initial screening completed with strong match." in args[2]


@pytest.mark.asyncio
async def test_send_application_status_update_email_accepted():
    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_application_status_update_email(
            to_email="cand.accepted@example.com",
            candidate_name="Maria Santos",
            job_title="Production Supervisor",
            new_status="ACCEPTED"
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "cand.accepted@example.com"
        assert "Congratulations: Application Shortlisted" in args[1]
        assert "Maria Santos" in args[2]
        assert "accepted and shortlisted" in args[2]


@pytest.mark.asyncio
async def test_send_application_status_update_email_rejected():
    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_application_status_update_email(
            to_email="cand.rejected@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Logistics Manager",
            new_status="REJECTED"
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "cand.rejected@example.com"
        assert "Application Update: Logistics Manager" in args[1]
        assert "Juan Dela Cruz" in args[2]
        assert "chosen to move forward with other candidates" in args[2]
        assert "talent database" in args[2]


@pytest.mark.asyncio
async def test_send_application_status_update_email_technical_interview():
    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_send:
        res = await email_service.send_application_status_update_email(
            to_email="cand.interview@example.com",
            candidate_name="Grace Hopper",
            job_title="Systems Architect",
            new_status="TECHNICAL INTERVIEW"
        )
        assert res is True
        assert mock_send.called
        args, _ = mock_send.call_args
        assert args[0] == "cand.interview@example.com"
        assert "Technical Interview for Systems Architect" in args[1]
        assert "Grace Hopper" in args[2]
        assert "Technical Interview" in args[2]


