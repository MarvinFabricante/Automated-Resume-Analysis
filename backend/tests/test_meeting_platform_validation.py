"""
Verification tests for online interview meeting platform detection and strict platform/link matching:
- Panel feedback: selecting Zoom and submitting a Google Meet link must be rejected.
- Auto-detection of platform from meeting URL when omitted or when meeting link changes.
- Dynamic platform CTA label in interview emails.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import pytest

from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.services import email_service
from app.services.interview_details import (
    detect_known_meeting_platform,
    detect_meeting_platform,
    resolve_meeting_platform,
    validate_interview_details,
)
from app.utils.auth import create_access_token


def _next_weekday_iso(days_ahead: int = 3, hour: int = 10):
    target = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    while target.weekday() >= 5:
        target += timedelta(days=1)
    return target.isoformat(), (target + timedelta(hours=1)).isoformat()


def _auth_headers(user: User) -> dict:
    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_detect_and_validate_meeting_platforms():
    assert detect_known_meeting_platform("https://meet.google.com/abc-defg-hij") == "Google Meet"
    assert detect_known_meeting_platform("https://g.co/meet/mariwasa") == "Google Meet"
    assert detect_known_meeting_platform("https://zoom.us/j/1234567890") == "Zoom"
    assert detect_known_meeting_platform("https://us02web.zoom.us/j/9876543210") == "Zoom"
    assert detect_known_meeting_platform("https://teams.microsoft.com/l/meetup-join/19%3ameeting") == "Microsoft Teams"
    assert detect_known_meeting_platform("https://teams.live.com/meet/123456") == "Microsoft Teams"
    assert detect_known_meeting_platform("https://meet.jit.si/mariwasa-hr") is None
    assert detect_meeting_platform("https://meet.jit.si/mariwasa-hr") == "Other"

    # Matching platform + link succeeds
    validate_interview_details("Online", None, "https://meet.google.com/abc-defg-hij", "Google Meet")
    validate_interview_details("Online", None, "https://us02web.zoom.us/j/1234567890", "Zoom")
    validate_interview_details("Online", None, "https://teams.microsoft.com/l/meetup-join/123", "Microsoft Teams")
    validate_interview_details("Online", None, "https://meet.jit.si/mariwasa", "Other")
    validate_interview_details("Online", None, "https://meet.google.com/abc-defg-hij", None)

    assert resolve_meeting_platform("https://zoom.us/j/1234567890", None) == "Zoom"
    assert resolve_meeting_platform("https://meet.google.com/abc-defg-hij", None) == "Google Meet"

    # Mismatches raise ValueError
    with pytest.raises(ValueError, match="Google Meet.*Zoom"):
        validate_interview_details("Online", None, "https://meet.google.com/abc-defg-hij", "Zoom")

    with pytest.raises(ValueError, match="Zoom.*Google Meet"):
        validate_interview_details("Online", None, "https://zoom.us/j/1234567890", "Google Meet")

    with pytest.raises(ValueError, match="Zoom"):
        validate_interview_details("Online", None, "https://meet.jit.si/mariwasa", "Zoom")

    with pytest.raises(ValueError, match="Google Meet.*Other"):
        validate_interview_details("Online", None, "https://meet.google.com/abc-defg-hij", "Other")


@pytest.mark.asyncio
async def test_schedule_and_update_endpoints_enforce_platform_link_match(client, db_session):
    hr = User(email="platform_hr@example.com", password="pw", role="HR", fullname="Platform HR")
    db_session.add(hr)
    await db_session.flush()

    job = JobDescription(
        job_id="PLAT-JOB-1",
        job_title="Process Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Bulacan Plant",
        description="Plant process engineering",
    )
    db_session.add(job)
    await db_session.flush()

    app_record = JobApplication(
        job_id=job.id,
        candidate_name="Alex Santos",
        candidate_email="alex.santos@example.com",
        phone="+639171112233",
        status="SHORTLISTED",
    )
    db_session.add(app_record)
    await db_session.commit()

    start_iso, end_iso = _next_weekday_iso(days_ahead=3, hour=10)

    # 1. Choosing Zoom with a Google Meet link MUST be rejected (422)
    mismatch_resp = await client.post(
        "/interviews/schedule",
        headers=_auth_headers(hr),
        json={
            "job_application_id": app_record.id,
            "interviewer_id": hr.id,
            "title": "Initial Interview",
            "start_time": start_iso,
            "end_time": end_iso,
            "interview_type": "Online",
            "platform": "Zoom",
            "meeting_link": "https://meet.google.com/abc-defg-hij",
        },
    )
    assert mismatch_resp.status_code == 422
    assert "google meet" in mismatch_resp.text.lower()
    assert "zoom" in mismatch_resp.text.lower()

    # 2. Choosing Zoom with a generic non-Zoom link MUST be rejected (422)
    generic_mismatch = await client.post(
        "/interviews/schedule",
        headers=_auth_headers(hr),
        json={
            "job_application_id": app_record.id,
            "interviewer_id": hr.id,
            "title": "Initial Interview",
            "start_time": start_iso,
            "end_time": end_iso,
            "interview_type": "Online",
            "platform": "Zoom",
            "meeting_link": "https://example.com/room-1",
        },
    )
    assert generic_mismatch.status_code == 422

    # 3. Valid Google Meet link without explicit platform auto-populates platform = "Google Meet"
    with (
        patch("app.services.email_service.send_interview_invitation_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        ok_resp = await client.post(
            "/interviews/schedule",
            headers=_auth_headers(hr),
            json={
                "job_application_id": app_record.id,
                "interviewer_id": hr.id,
                "title": "Initial Interview",
                "start_time": start_iso,
                "end_time": end_iso,
                "interview_type": "Online",
                "meeting_link": "https://meet.google.com/abc-defg-hij",
            },
        )
    assert ok_resp.status_code == 200, ok_resp.text
    iv = ok_resp.json()
    assert iv["platform"] == "Google Meet"

    # 4. Updating platform to Zoom while keeping the Google Meet link MUST be rejected (400)
    bad_update = await client.put(
        f"/interviews/{iv['id']}",
        headers=_auth_headers(hr),
        json={"platform": "Zoom"},
    )
    assert bad_update.status_code == 400
    assert "google meet" in bad_update.json()["detail"].lower()

    # 5. Updating meeting_link to a Zoom link without specifying platform auto-switches platform to Zoom
    with (
        patch("app.services.email_service.send_interview_rescheduled_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        auto_switch_update = await client.put(
            f"/interviews/{iv['id']}",
            headers=_auth_headers(hr),
            json={"meeting_link": "https://us02web.zoom.us/j/1234567890"},
        )
    assert auto_switch_update.status_code == 200, auto_switch_update.text
    assert auto_switch_update.json()["platform"] == "Zoom"


@pytest.mark.asyncio
async def test_email_invitation_uses_detected_platform_label():
    sent = []

    def capture_smtp(to_email, subject, html_body, attachments=None):
        sent.append(html_body)
        return True

    with patch("app.services.email_service._send_smtp_sync", side_effect=capture_smtp):
        await email_service.send_interview_invitation_email(
            to_email="zoom@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Engineer",
            interview_title="Zoom Interview",
            start_time=datetime(2026, 12, 5, 10, 0),
            end_time=datetime(2026, 12, 5, 11, 0),
            meeting_link="https://us02web.zoom.us/j/1234567890",
            interviewer_name="HR Panel",
        )
        await email_service.send_interview_invitation_email(
            to_email="meet@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Engineer",
            interview_title="Meet Interview",
            start_time=datetime(2026, 12, 5, 13, 0),
            end_time=datetime(2026, 12, 5, 14, 0),
            meeting_link="https://meet.google.com/abc-defg-hij",
            interviewer_name="HR Panel",
        )

    assert "Join Zoom" in sent[0]
    assert "Join Google Meet" in sent[1]
