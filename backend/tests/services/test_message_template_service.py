import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.schemas.interview_schema import InterviewCreateSchema, InterviewUpdateSchema
from app.services import message_template_service, email_service
from app.services.interview_service import interview_service
from app.utils.auth import create_access_token


def test_build_context_and_render_template_omits_fake_link_and_local_email():
    """Default SMS rendering includes complete details and avoids fake meeting links or .local emails."""
    ctx = message_template_service.build_interview_template_context(
        candidate_name="Juan Dela Cruz",
        job_title="Production Supervisor",
        interview_title="Panel Interview",
        start_time=datetime(2026, 11, 24, 10, 0),
        end_time=datetime(2026, 11, 24, 11, 0),
        interviewer_name="Jane HR",
        location="Mariwasa HR Office, Bulacan",
        meeting_link=None,
        notes="Bring 2 valid IDs",
        candidate_email="imported_12@walkin.mariwasa.local",
    )
    rendered = message_template_service.render_template(
        message_template_service.DEFAULT_TEMPLATES["interview_scheduled"]["sms_message"],
        ctx,
    )
    assert "Juan Dela Cruz" in rendered
    assert "Panel Interview" in rendered
    assert "Production Supervisor" in rendered
    assert "10:00 AM - 11:00 AM" in rendered
    assert "Jane HR" in rendered
    assert "Venue: Mariwasa HR Office, Bulacan" in rendered
    assert "Bring 2 valid IDs" in rendered
    assert "meeting link" not in rendered.lower()
    assert ".local" not in rendered


def test_render_template_preserves_unknown_placeholders():
    result = message_template_service.render_template(
        "Hello {candidate_name}, custom {unknown_tag}!",
        {"candidate_name": "Maria"},
    )
    assert result == "Hello Maria, custom {unknown_tag}!"


@pytest.mark.asyncio
async def test_email_invitation_renders_location_meeting_link_and_custom_message():
    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_smtp:
        ok = await email_service.send_interview_invitation_email(
            to_email="maria@gmail.com",
            candidate_name="Maria Clara",
            job_title="Ceramics Engineer",
            interview_title="Technical Panel",
            start_time=datetime(2026, 11, 24, 14, 0),
            end_time=datetime(2026, 11, 24, 15, 0),
            interviewer_name="Ana HR",
            interviewer_email="ana.hr@mariwasa.com",
            location="Mariwasa Plant B",
            meeting_link="https://meet.google.com/xyz-1234",
            notes="Bring portfolio",
            custom_subject="Custom Invite Subject",
            custom_message="Custom intro body for Maria Clara.",
        )

    assert ok is True
    to_addr, subj, html_body = mock_smtp.call_args[0]
    assert to_addr == "maria@gmail.com"
    assert subj == "Custom Invite Subject"
    assert "Custom intro body for Maria Clara." in html_body
    assert "Mariwasa Plant B" in html_body
    assert "https://meet.google.com/xyz-1234" in html_body
    assert "ana.hr@mariwasa.com" in html_body
    assert "02:00 PM" in html_body
    assert "03:00 PM" in html_body


@pytest.mark.asyncio
async def test_saved_template_persists_and_applies_to_schedule_and_sms(db_session):
    hr_user = User(
        email="tmpl_hr@example.com",
        password="password123",
        role="HR",
        fullname="Template HR",
    )
    db_session.add(hr_user)
    await db_session.flush()

    await message_template_service.update_templates(
        db_session,
        {
            "interview_scheduled": {
                "email_subject": "Saved Subject: {interview_title} for {candidate_name}",
                "email_message": "Saved Email Intro for {job_title} at {location}.",
                "sms_message": "CUSTOM SMS {candidate_name} | {job_title} | {date} {time_range} | {location}",
            }
        },
        user_id=hr_user.id,
    )

    job = JobDescription(
        job_id="TMPL-JOB-1",
        job_title="Maintenance Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Bulacan Plant",
        description="Maintain equipment",
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Pedro Penduko",
        candidate_email="pedro@gmail.com",
        phone="09171234567",
        status="SHORTLISTED",
    )
    db_session.add(app)
    await db_session.commit()

    payload = InterviewCreateSchema(
        job_application_id=app.id,
        interviewer_id=hr_user.id,
        title="Final Interview",
        description="Meet engineering head",
        start_time=datetime(2026, 11, 24, 10, 0),
        end_time=datetime(2026, 11, 24, 11, 0),
        location="Conference Room A",
        meeting_link="https://meet.google.com/tmpl-test",
    )

    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_smtp, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock):
        interview = await interview_service.schedule_interview(db_session, payload, hr_user.id)

    assert interview.location == "Conference Room A"
    assert interview.meeting_link == "https://meet.google.com/tmpl-test"

    mock_sms.assert_called_once()
    sms_text = mock_sms.call_args[0][1]
    assert sms_text == "CUSTOM SMS Pedro Penduko | Maintenance Engineer | Tuesday, Nov 24, 2026 10:00 AM - 11:00 AM | Conference Room A"

    cand_emails = [c.args for c in mock_smtp.call_args_list if c.args[0] == "pedro@gmail.com"]
    assert len(cand_emails) >= 1
    assert any(subj == "Saved Subject: Final Interview for Pedro Penduko" for _, subj, _ in cand_emails)
    assert any("Saved Email Intro for Maintenance Engineer at Conference Room A." in body for _, _, body in cand_emails)


@pytest.mark.asyncio
async def test_per_action_custom_message_overrides_saved_template_on_reschedule_and_cancel(db_session):
    hr_user = User(
        email="override_hr@example.com",
        password="password123",
        role="HR",
        fullname="Override HR",
    )
    db_session.add(hr_user)
    await db_session.flush()

    job = JobDescription(
        job_id="OVR-JOB-1",
        job_title="QA Analyst",
        department="QA",
        job_type=JobType.FULL_TIME,
        location="Manila",
        description="QA",
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Liza Soberano",
        candidate_email="liza@gmail.com",
        phone="09181112222",
        status="SHORTLISTED",
    )
    db_session.add(app)
    await db_session.commit()

    with patch("app.services.email_service._send_smtp_sync", return_value=True), \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True), \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock):
        iv = await interview_service.schedule_interview(
            db_session,
            InterviewCreateSchema(
                job_application_id=app.id,
                interviewer_id=hr_user.id,
                title="Initial QA Interview",
                start_time=datetime(2026, 11, 24, 9, 0),
                end_time=datetime(2026, 11, 24, 10, 0),
                location="Room 1",
            ),
            hr_user.id,
        )

    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_smtp, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock):
        await interview_service.update_interview(
            db_session,
            iv.id,
            InterviewUpdateSchema(
                start_time=datetime(2026, 11, 25, 13, 0),
                end_time=datetime(2026, 11, 25, 14, 0),
                location="Room 2",
                custom_email_subject="One-off Reschedule Subject",
                custom_email_message="One-off reschedule email message.",
                custom_sms_message="One-off reschedule SMS for Liza.",
            ),
            hr_user.id,
        )

    assert mock_sms.call_args[0][1] == "One-off reschedule SMS for Liza."
    cand_resched = [c.args for c in mock_smtp.call_args_list if c.args[0] == "liza@gmail.com"]
    assert any(s == "One-off Reschedule Subject" and "One-off reschedule email message." in b for _, s, b in cand_resched)

    with patch("app.services.email_service._send_smtp_sync", return_value=True) as mock_smtp_cancel, \
         patch("app.services.interview_service.send_sms_notification_sync", return_value=True) as mock_sms_cancel, \
         patch("app.services.notification_service.create_notification", new_callable=AsyncMock):
        await interview_service.cancel_interview(
            db_session,
            iv.id,
            hr_user.id,
            reason="Interviewer sick leave",
            custom_email_subject="One-off Cancel Subject",
            custom_email_message="One-off cancel email body.",
            custom_sms_message="One-off cancel SMS for Liza.",
        )

    assert mock_sms_cancel.call_args[0][1] == "One-off cancel SMS for Liza."
    cand_cancel = [c.args for c in mock_smtp_cancel.call_args_list if c.args[0] == "liza@gmail.com"]
    assert any(s == "One-off Cancel Subject" and "One-off cancel email body." in b for _, s, b in cand_cancel)


@pytest.mark.asyncio
async def test_notification_templates_endpoints_hr_admin_and_candidate_forbidden(client, db_session):
    hr_user = User(email="api_hr@example.com", password="pw", role="HR", fullname="API HR")
    cand_user = User(email="api_cand@example.com", password="pw", role="CANDIDATE", fullname="API Cand")
    db_session.add_all([hr_user, cand_user])
    await db_session.flush()

    hr_headers = {"Authorization": f"Bearer {create_access_token({'sub': hr_user.email, 'id': hr_user.id, 'role': 'HR'})}"}
    cand_headers = {"Authorization": f"Bearer {create_access_token({'sub': cand_user.email, 'id': cand_user.id, 'role': 'CANDIDATE'})}"}

    # Candidate is forbidden
    resp_forbidden = await client.get("/system-config/notification-templates", headers=cand_headers)
    assert resp_forbidden.status_code == 403

    # HR can read defaults
    resp_get = await client.get("/system-config/notification-templates", headers=hr_headers)
    assert resp_get.status_code == 200
    assert "interview_scheduled" in resp_get.json()["templates"]

    # HR can update a template
    resp_put = await client.put(
        "/system-config/notification-templates",
        headers=hr_headers,
        json={
            "templates": {
                "interview_scheduled": {
                    "sms_message": "API Updated SMS for {candidate_name} at {time_range}"
                }
            }
        },
    )
    assert resp_put.status_code == 200
    assert resp_put.json()["templates"]["interview_scheduled"]["sms_message"] == "API Updated SMS for {candidate_name} at {time_range}"

    # HR can reset that template back to default
    resp_reset = await client.post(
        "/system-config/notification-templates/reset",
        headers=hr_headers,
        json={"template_key": "interview_scheduled"},
    )
    assert resp_reset.status_code == 200
    assert (
        resp_reset.json()["templates"]["interview_scheduled"]["sms_message"]
        == message_template_service.DEFAULT_TEMPLATES["interview_scheduled"]["sms_message"]
    )
