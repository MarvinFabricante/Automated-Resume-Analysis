"""
Automated backend tests verifying Issues #1, #3, #5, #7, and #8:
- Issue #1: Forward-only status transitions while allowing Under Review -> Interview Scheduled directly, with audit history reasons.
- Issue #3: Booking an interview sets status to Interview Scheduled and syncs shortlist roster groups & counts; rescheduling keeps Interview Scheduled; cancelling reverts to Shortlisted (preserving roster membership) or Under Review.
- Issue #7: Withdrawn end state cancels interviews + deletes Google Calendar events, removes from shortlist rosters with audit entry, excludes from comparison/scheduling/status edits/duplicate check/active limits.
- Issue #8: Shortlist-eligible queries exclude Withdrawn, Passed, Not Selected on server; roster creation/addition rejects them; existing withdrawn items inside a roster are auto-removed with an audit entry & HR cleanup notice.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.interview import Interview
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription, JobType
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.models.status_history import ApplicationStatusHistory
from app.services import retention_service
from app.utils.auth import create_access_token, hash_password


async def _make_user(
    db,
    email: str,
    role: str = "CANDIDATE",
    fullname: str = "Test User",
    google_creds: str | None = None,
):
    from app.models.admin import Admin
    from app.models.candidate import Candidate
    from app.models.hr import HR

    clean = email.strip().lower()
    common = dict(
        email=clean,
        password=hash_password("Secret123!"),
        role=role,
        fullname=fullname,
        email_hash=retention_service.compute_email_hash(clean),
    )
    if role == "CANDIDATE":
        u = Candidate(**common)
    elif role == "HR":
        u = HR(
            **common,
            company_name="Mariwasa",
            google_credentials=google_creds,
            google_linked=bool(google_creds),
        )
    else:
        u = Admin(**common)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def _auth_headers(user) -> dict:
    token = create_access_token({
        "sub": user.email,
        "role": user.role,
        "id": user.id,
        "tv": int(getattr(user, "token_version", 0) or 0),
    })
    return {"Authorization": f"Bearer {token}"}


async def _make_job(db, job_code: str, title: str):
    job = JobDescription(
        job_id=job_code,
        job_title=title,
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Production quality and manufacturing operations.",
        skills_requirements="Python, Quality Control",
        status="ACTIVE",
        is_active=True,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _make_app(
    db,
    job: JobDescription,
    user,
    status: str = "Under Review",
    match_score: float = 85.0,
):
    app = JobApplication(
        job_id=job.id,
        user_id=user.id,
        candidate_name=user.fullname,
        candidate_email=user.email,
        contact_email=user.email,
        email_hash=retention_service.compute_email_hash(user.email),
        job_title=job.job_title,
        status=status,
        match_score=match_score,
        skills_score=82.0,
        experience_score=85.0,
        education_score=90.0,
        matched_skills=["Python"],
        missing_skills=[],
        ai_summary="Strong fit.",
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


def _next_weekday_iso(days_ahead: int = 2, hour: int = 10) -> tuple[str, str]:
    dt = datetime.utcnow() + timedelta(days=days_ahead)
    while dt.weekday() >= 5:
        dt += timedelta(days=1)
    start = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start.isoformat(), end.isoformat()


@pytest.mark.asyncio
async def test_issue1_direct_under_review_to_interview_scheduled_and_forward_only(client, db_session):
    hr = await _make_user(db_session, "hr_issue1@mariwasa.com", role="HR", fullname="HR Recruiter")
    cand1 = await _make_user(db_session, "cand1_issue1@example.com", role="CANDIDATE", fullname="Ana Direct")
    cand2 = await _make_user(db_session, "cand2_issue1@example.com", role="CANDIDATE", fullname="Ben Status")
    job = await _make_job(db_session, "JOB-ISS1", "Process Engineer")
    app1 = await _make_app(db_session, job, cand1, status="Under Review")
    app2 = await _make_app(db_session, job, cand2, status="Under Review")

    start_iso, end_iso = _next_weekday_iso(days_ahead=3, hour=10)

    # 1. Scheduling directly from Under Review (skipping Shortlisted) succeeds and sets Interview Scheduled
    with (
        patch("app.services.email_service.send_interview_invitation_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        resp = await client.post(
            "/interviews/schedule",
            headers=_auth_headers(hr),
            json={
                "job_application_id": app1.id,
                "interviewer_id": hr.id,
                "title": "Initial Interview",
                "start_time": start_iso,
                "end_time": end_iso,
                "interview_type": "Online",
                "meeting_link": "https://meet.google.com/abc-defg-hij",
            },
        )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(app1)
    assert app1.status.upper() == "INTERVIEW SCHEDULED"

    hist = (
        await db_session.execute(
            select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app1.id)
        )
    ).scalars().all()
    assert len(hist) >= 1
    assert (hist[-1].new_status or "").upper() == "INTERVIEW SCHEDULED"
    assert hist[-1].reason and len(hist[-1].reason.strip()) > 0

    # 2. Backward manual status move (Interview Scheduled -> Under Review) is rejected
    back_resp = await client.patch(
        f"/applications/{app1.id}/status",
        headers=_auth_headers(hr),
        json={"status": "Under Review"},
    )
    assert back_resp.status_code == 400
    assert "forward" in back_resp.json()["detail"].lower()

    # 3. Direct manual transition Under Review -> Interview Scheduled is allowed and logged with reason
    with (
        patch("app.services.email_service._send_smtp_sync", return_value=True),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        direct_resp = await client.patch(
            f"/applications/{app2.id}/status",
            headers=_auth_headers(hr),
            json={"status": "Interview Scheduled"},
        )
    assert direct_resp.status_code == 200, direct_resp.text
    hist2 = (
        await db_session.execute(
            select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app2.id)
        )
    ).scalars().all()
    assert len(hist2) >= 1
    assert hist2[-1].reason and len(hist2[-1].reason.strip()) > 0


@pytest.mark.asyncio
async def test_issue3_shortlist_moves_to_interview_scheduled_and_reverts_on_cancel(client, db_session):
    hr = await _make_user(db_session, "hr_issue3@mariwasa.com", role="HR", fullname="HR Lead")
    cand_short = await _make_user(db_session, "short_issue3@example.com", role="CANDIDATE", fullname="Carla Shortlisted")
    cand_direct = await _make_user(db_session, "direct_issue3@example.com", role="CANDIDATE", fullname="Dan Direct")
    job = await _make_job(db_session, "JOB-ISS3", "Quality Analyst")
    app_short = await _make_app(db_session, job, cand_short, status="Under Review")
    app_direct = await _make_app(db_session, job, cand_direct, status="Under Review")

    # Create shortlist roster with app_short -> moves app_short to Shortlisted
    create_resp = await client.post(
        "/hr/shortlists",
        headers=_auth_headers(hr),
        json={
            "job_id": job.id,
            "name": "QA Wave 1",
            "application_ids": [app_short.id],
            "non_shortlisted_action": "keep_under_review",
            "finalize": True,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    roster_id = create_resp.json()["id"]

    r_initial = await client.get(f"/hr/shortlists/{roster_id}", headers=_auth_headers(hr))
    assert r_initial.status_code == 200
    assert r_initial.json()["shortlisted_count"] == 1
    assert r_initial.json()["interview_scheduled_count"] == 0

    # Book interview for shortlisted candidate -> must immediately show in Interview Scheduled column & counts match
    start1, end1 = _next_weekday_iso(days_ahead=2, hour=10)
    with (
        patch("app.services.email_service.send_interview_invitation_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        sched_resp = await client.post(
            "/interviews/schedule",
            headers=_auth_headers(hr),
            json={
                "job_application_id": app_short.id,
                "interviewer_id": hr.id,
                "title": "Initial Interview",
                "start_time": start1,
                "end_time": end1,
                "interview_type": "Online",
                "meeting_link": "https://meet.google.com/short-1",
            },
        )
    assert sched_resp.status_code == 200, sched_resp.text
    iv_short_id = sched_resp.json()["id"]

    r_after_book = await client.get(f"/hr/shortlists/{roster_id}", headers=_auth_headers(hr))
    assert r_after_book.status_code == 200
    data_book = r_after_book.json()
    assert data_book["shortlisted_count"] == 0
    assert data_book["interview_scheduled_count"] == 1
    assert data_book["items"][0]["stage"] == "Interview Scheduled"

    # Reschedule interview -> stays in Interview Scheduled
    start2, end2 = _next_weekday_iso(days_ahead=4, hour=14)
    with (
        patch("app.services.email_service.send_interview_rescheduled_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        resched_resp = await client.put(
            f"/interviews/{iv_short_id}",
            headers=_auth_headers(hr),
            json={
                "start_time": start2,
                "end_time": end2,
                "interview_type": "Online",
                "meeting_link": "https://meet.google.com/short-2",
            },
        )
    assert resched_resp.status_code == 200, resched_resp.text
    r_after_resched = await client.get(f"/hr/shortlists/{roster_id}", headers=_auth_headers(hr))
    assert r_after_resched.json()["interview_scheduled_count"] == 1
    assert r_after_resched.json()["items"][0]["stage"] == "Interview Scheduled"

    # Cancel interview -> reverts to Shortlisted AND preserves roster membership
    with (
        patch("app.services.email_service._send_smtp_sync", return_value=True),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        cancel_resp = await client.post(
            f"/interviews/{iv_short_id}/cancel",
            headers=_auth_headers(hr),
            json={"reason": "Panelist unavailable"},
        )
    assert cancel_resp.status_code == 200, cancel_resp.text

    await db_session.refresh(app_short)
    assert app_short.status.upper() == "SHORTLISTED"

    r_after_cancel = await client.get(f"/hr/shortlists/{roster_id}", headers=_auth_headers(hr))
    data_cancel = r_after_cancel.json()
    assert len(data_cancel["items"]) == 1
    assert data_cancel["items"][0]["stage"] == "Shortlisted"
    assert data_cancel["shortlisted_count"] == 1
    assert data_cancel["interview_scheduled_count"] == 0

    # Schedule & cancel for non-shortlisted candidate (Under Review) -> reverts back to Under Review
    start3, end3 = _next_weekday_iso(days_ahead=3, hour=15)
    with (
        patch("app.services.email_service.send_interview_invitation_email", new_callable=AsyncMock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        sched2 = await client.post(
            "/interviews/schedule",
            headers=_auth_headers(hr),
            json={
                "job_application_id": app_direct.id,
                "interviewer_id": hr.id,
                "title": "Direct Interview",
                "start_time": start3,
                "end_time": end3,
                "interview_type": "Onsite",
                "location": "Mariwasa Plant",
            },
        )
    assert sched2.status_code == 200, sched2.text
    iv_direct_id = sched2.json()["id"]

    with (
        patch("app.services.email_service._send_smtp_sync", return_value=True),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
    ):
        cancel2 = await client.post(
            f"/interviews/{iv_direct_id}/cancel",
            headers=_auth_headers(hr),
            json={"reason": "Candidate requested cancellation"},
        )
    assert cancel2.status_code == 200, cancel2.text
    await db_session.refresh(app_direct)
    assert app_direct.status.upper() == "UNDER REVIEW"


@pytest.mark.asyncio
async def test_issue7_withdrawn_end_state_calendar_cleanup_roster_audit_and_guards(client, db_session):
    hr = await _make_user(
        db_session,
        "hr_issue7@mariwasa.com",
        role="HR",
        fullname="HR Manager",
        google_creds='{"token":"fake-token"}',
    )
    cand = await _make_user(db_session, "cand_issue7@example.com", role="CANDIDATE", fullname="Elena Withdraw")
    other_cand = await _make_user(db_session, "other_issue7@example.com", role="CANDIDATE", fullname="Frank Active")
    job = await _make_job(db_session, "JOB-ISS7", "Maintenance Technician")
    app_w = await _make_app(db_session, job, cand, status="Shortlisted")
    app_other = await _make_app(db_session, job, other_cand, status="Under Review")

    # Add app_w to a shortlist roster and attach a scheduled interview with a Google event ID
    roster = ShortlistRoster(job_id=job.id, name="Tech Shortlist", created_by=hr.email)
    db_session.add(roster)
    await db_session.flush()
    db_session.add(
        ShortlistRosterItem(
            roster_id=roster.id,
            application_id=app_w.id,
            stage="Interview Scheduled",
            added_by=hr.email,
        )
    )

    start_iso, end_iso = _next_weekday_iso(days_ahead=3, hour=11)
    iv = Interview(
        job_application_id=app_w.id,
        interviewer_id=hr.id,
        title="Maintenance Interview",
        start_time=datetime.fromisoformat(start_iso),
        end_time=datetime.fromisoformat(end_iso),
        status="SCHEDULED",
        google_event_id="gcal-evt-withdraw-999",
    )
    db_session.add(iv)
    await db_session.commit()

    delete_gcal_mock = MagicMock(return_value=True)
    with (
        patch("app.services.interview_service._get_valid_credentials", return_value='{"token":"fake-token"}'),
        patch("app.services.google_calendar_service.delete_real_google_event", delete_gcal_mock),
        patch("app.services.notification_service.create_notification", new_callable=AsyncMock),
        patch("app.services.email_service._send_smtp_sync", return_value=True),
    ):
        w_resp = await client.post(
            f"/applications/{app_w.id}/withdraw",
            headers=_auth_headers(cand),
            json={"reason": "Accepted another offer"},
        )
    assert w_resp.status_code == 200, w_resp.text

    await db_session.refresh(app_w)
    await db_session.refresh(iv)
    assert app_w.status.upper() == "WITHDRAWN BY APPLICANT"
    assert app_w.resolved_at is not None
    assert iv.status == "CANCELLED"
    assert iv.google_event_id is None
    delete_gcal_mock.assert_called_once()
    assert delete_gcal_mock.call_args.kwargs.get("event_id") == "gcal-evt-withdraw-999"

    # Removed from roster AND audit entry written
    remaining_items = (
        await db_session.execute(
            select(ShortlistRosterItem).where(ShortlistRosterItem.application_id == app_w.id)
        )
    ).scalars().all()
    assert remaining_items == []

    audit_entries = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "AUTO_REMOVE_WITHDRAWN_FROM_ROSTER")
        )
    ).scalars().all()
    assert len(audit_entries) >= 1

    # Cannot update status, schedule, or compare a withdrawn application
    patch_resp = await client.patch(
        f"/applications/{app_w.id}/status",
        headers=_auth_headers(hr),
        json={"status": "Shortlisted"},
    )
    assert patch_resp.status_code == 400

    sched_resp = await client.post(
        "/interviews/schedule",
        headers=_auth_headers(hr),
        json={
            "job_application_id": app_w.id,
            "interviewer_id": hr.id,
            "title": "Blocked Interview",
            "start_time": start_iso,
            "end_time": end_iso,
            "interview_type": "Online",
            "meeting_link": "https://meet.google.com/blocked",
        },
    )
    assert sched_resp.status_code == 400

    cmp_resp = await client.post(
        "/hr/compare",
        headers=_auth_headers(hr),
        json={"application_ids": [app_w.id, app_other.id]},
    )
    assert cmp_resp.status_code == 422

    # Duplicate check does not block on a withdrawn application
    dup_resp = await client.get(
        f"/applications/check-duplicate?email={cand.email}&job_id={job.id}",
        headers=_auth_headers(cand),
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["is_duplicate"] is False

    # HR stats accurately separate withdrawn from active
    stats_resp = await client.get("/hr/application-stats", headers=_auth_headers(hr))
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["withdrawn"] >= 1
    assert stats_data["active"] == 1


@pytest.mark.asyncio
async def test_issue8_shortlist_excludes_withdrawn_and_resolved_and_auto_cleans_rosters(client, db_session):
    hr = await _make_user(db_session, "hr_issue8@mariwasa.com", role="HR", fullname="HR Screener")
    c_sub = await _make_user(db_session, "sub_issue8@example.com", role="CANDIDATE", fullname="Grace Submitted")
    c_rev = await _make_user(db_session, "rev_issue8@example.com", role="CANDIDATE", fullname="Henry Review")
    c_wd = await _make_user(db_session, "wd_issue8@example.com", role="CANDIDATE", fullname="Ivy Withdrawn")
    c_pass = await _make_user(db_session, "pass_issue8@example.com", role="CANDIDATE", fullname="Jake Passed")
    c_ns = await _make_user(db_session, "ns_issue8@example.com", role="CANDIDATE", fullname="Kara NotSelected")
    job = await _make_job(db_session, "JOB-ISS8", "Logistics Coordinator")

    app_sub = await _make_app(db_session, job, c_sub, status="Submitted")
    app_rev = await _make_app(db_session, job, c_rev, status="Under Review")
    app_wd = await _make_app(db_session, job, c_wd, status="Withdrawn by applicant")
    app_pass = await _make_app(db_session, job, c_pass, status="Passed initial interview")
    app_ns = await _make_app(db_session, job, c_ns, status="Not Selected")

    # 1. Server query ?shortlist_eligible=true excludes Withdrawn, Passed, Not Selected
    all_elig = await client.get("/applications/?shortlist_eligible=true", headers=_auth_headers(hr))
    assert all_elig.status_code == 200, all_elig.text
    elig_ids = {row["id"] for row in all_elig.json()}
    assert {app_sub.id, app_rev.id}.issubset(elig_ids)
    assert app_wd.id not in elig_ids
    assert app_pass.id not in elig_ids
    assert app_ns.id not in elig_ids

    job_elig = await client.get(f"/applications/job/{job.id}?shortlist_eligible=true", headers=_auth_headers(hr))
    assert job_elig.status_code == 200
    job_elig_ids = {row["id"] for row in job_elig.json()}
    assert job_elig_ids == {app_sub.id, app_rev.id}

    # 2. Creating a roster with a withdrawn/passed/not-selected application is rejected with HTTP 400
    for bad_app in (app_wd, app_pass, app_ns):
        bad_create = await client.post(
            "/hr/shortlists",
            headers=_auth_headers(hr),
            json={
                "job_id": job.id,
                "name": "Invalid Roster",
                "application_ids": [bad_app.id],
                "non_shortlisted_action": "keep_under_review",
                "finalize": True,
            },
        )
        assert bad_create.status_code == 400, f"Expected 400 for {bad_app.status}, got {bad_create.status_code}"

    # 3. Create a valid roster, then verify adding a withdrawn app is rejected with HTTP 400
    ok_create = await client.post(
        "/hr/shortlists",
        headers=_auth_headers(hr),
        json={
            "job_id": job.id,
            "name": "Logistics Wave 1",
            "application_ids": [app_rev.id],
            "non_shortlisted_action": "keep_under_review",
            "finalize": True,
        },
    )
    assert ok_create.status_code == 201, ok_create.text
    roster_id = ok_create.json()["id"]

    bad_add = await client.post(
        f"/hr/shortlists/{roster_id}/items",
        headers=_auth_headers(hr),
        json={"application_id": app_wd.id},
    )
    assert bad_add.status_code == 400
    assert "withdrawn" in bad_add.json()["detail"].lower()

    # 4. Simulate a pre-existing withdrawn app seated in the roster -> auto-removed with audit entry & HR notice
    db_session.add(
        ShortlistRosterItem(
            roster_id=roster_id,
            application_id=app_wd.id,
            stage="Shortlisted",
            added_by=hr.email,
        )
    )
    await db_session.commit()

    detail_resp = await client.get(f"/hr/shortlists/{roster_id}", headers=_auth_headers(hr))
    assert detail_resp.status_code == 200, detail_resp.text
    detail_data = detail_resp.json()
    item_app_ids = [it["application_id"] for it in detail_data["items"]]
    assert app_wd.id not in item_app_ids
    assert app_rev.id in item_app_ids
    assert len(detail_data["auto_removed_withdrawn"]) == 1
    assert "Ivy Withdrawn" in (detail_data["cleanup_notice"] or "")

    audits = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "AUTO_REMOVE_WITHDRAWN_FROM_ROSTER")
        )
    ).scalars().all()
    assert len(audits) >= 1
