"""
Automated backend tests for the 7 Mariwasa Recruitment lifecycle, privacy,
retention, reactivation, end-state, and multi-application rules.
"""
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.account_otp import AccountOTP
from app.models.audit_log import AuditLog
from app.models.interview import Interview
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription, JobType
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.retention_run_log import RetentionRunLog
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.models.status_history import ApplicationStatusHistory
from app.models.user import User
from app.services import auth_service, job_description_service, retention_service, shortlist_roster_service
from app.services.message_template_service import update_templates
from app.utils.auth import create_access_token, hash_password
from app.utils.database import Base


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _make_user(db, email: str, role: str = "CANDIDATE", fullname: str = "Test User", password: str = "Secret123!"):
    from app.models.candidate import Candidate
    from app.models.hr import HR
    from app.models.admin import Admin

    clean = email.strip().lower()
    common = dict(
        email=clean,
        password=hash_password(password),
        role=role,
        fullname=fullname,
        email_hash=retention_service.compute_email_hash(clean),
    )
    if role == "CANDIDATE":
        u = Candidate(**common)
    elif role == "HR":
        u = HR(**common, company_name="Mariwasa")
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


async def _make_job(db, job_code: str, title: str, status: str = "ACTIVE"):
    job = JobDescription(
        job_id=job_code,
        job_title=title,
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Bulacan",
        description="Ceramic tile production and quality assurance.",
        skills_requirements="Python, Quality Control",
        status=status,
        is_active=(status == "ACTIVE"),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _make_application(
    db,
    job: JobDescription,
    user: User,
    status: str = "SUBMITTED",
    resume_url: str = None,
    resolved_at: datetime = None,
    match_score: float = 82.5,
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
        resume_url=resume_url,
        resolved_at=resolved_at,
        match_score=match_score,
        skills_score=80.0,
        experience_score=85.0,
        education_score=90.0,
        matched_skills=["Python"],
        missing_skills=["Six Sigma"],
        ai_summary="Strong technical background.",
        strengths=["Solid Python experience"],
        weaknesses=["Missing Six Sigma certification"],
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


# ── 0. Reversible & Re-runnable Migration ────────────────────────────────────

@pytest.mark.asyncio
async def test_migration_is_idempotent_and_reversible():
    from migrations.add_recruitment_lifecycle_rules import upgrade, downgrade

    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Re-running upgrade multiple times must be idempotent
        await upgrade(conn)
        await upgrade(conn)

        cols = {row[1] for row in (await conn.execute(text("PRAGMA table_info(job_descriptions)"))).fetchall()}
        assert {"status", "closed_at", "archived_at"}.issubset(cols)

        # Reverse newer migrations before removing their referenced columns.
        from migrations.add_active_email_uniqueness import downgrade as downgrade_email_index
        await downgrade_email_index(conn)
        # Downgrade must cleanly remove added columns & tables
        await downgrade(conn)
        cols_after = {row[1] for row in (await conn.execute(text("PRAGMA table_info(job_descriptions)"))).fetchall()}
        assert "status" not in cols_after
        assert "closed_at" not in cols_after

        # Re-upgrade after downgrade must succeed cleanly
        await upgrade(conn)
        cols_re = {row[1] for row in (await conn.execute(text("PRAGMA table_info(job_descriptions)"))).fetchall()}
        assert {"status", "closed_at", "archived_at"}.issubset(cols_re)

    await eng.dispose()


# ── 1 & 2. Job Opening Lifecycle & Auto Not-Selected on Close ────────────────

@pytest.mark.asyncio
async def test_job_lifecycle_transitions_close_auto_not_selected_and_archive(client, db_session):
    hr = await _make_user(db_session, "hr.lifecycle@mariwasa.com", role="HR", fullname="HR Lead")
    cand1 = await _make_user(db_session, "cand.submitted@example.com", role="CANDIDATE", fullname="Submitted Cand")
    cand2 = await _make_user(db_session, "cand.review@example.com", role="CANDIDATE", fullname="Review Cand")
    cand3 = await _make_user(db_session, "cand.shortlisted@example.com", role="CANDIDATE", fullname="Shortlisted Cand")
    cand4 = await _make_user(db_session, "cand.interviewed@example.com", role="CANDIDATE", fullname="Interviewed Cand")

    job = await _make_job(db_session, "JOB-LIFE-01", "Process Engineer", status="DRAFT")

    # Candidate must NOT be allowed to change job status
    resp_unauth = await client.patch(
        f"/admins/jobs/{job.job_id}/status",
        json={"status": "ACTIVE"},
        headers=_auth_headers(cand1),
    )
    assert resp_unauth.status_code == 403

    # DRAFT -> ACTIVE by HR
    resp_pub = await client.post(f"/admins/jobs/{job.job_id}/publish", headers=_auth_headers(hr))
    assert resp_pub.status_code == 200
    assert resp_pub.json()["new_status"] == "ACTIVE"

    app_sub = await _make_application(db_session, job, cand1, status="SUBMITTED")
    app_rev = await _make_application(db_session, job, cand2, status="UNDER REVIEW")
    app_short = await _make_application(db_session, job, cand3, status="SHORTLISTED")
    app_int = await _make_application(db_session, job, cand4, status="INTERVIEWED")

    # Put cand3 on a shortlist roster
    roster = ShortlistRoster(job_id=job.id, name="R1", created_by=hr.email)
    db_session.add(roster)
    await db_session.commit()
    await db_session.refresh(roster)
    db_session.add(ShortlistRosterItem(roster_id=roster.id, application_id=app_short.id, stage="Shortlisted", added_by=hr.email))
    await db_session.commit()

    # Close preview must show 2 non-shortlisted affected & 2 protected
    prev_resp = await client.get(f"/admins/jobs/{job.job_id}/close-preview", headers=_auth_headers(hr))
    assert prev_resp.status_code == 200
    assert prev_resp.json()["affected_count"] == 2
    assert prev_resp.json()["protected_count"] == 2

    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock) as mock_email:
        close_resp = await client.post(f"/admins/jobs/{job.job_id}/close", headers=_auth_headers(hr))
        assert close_resp.status_code == 200
        assert close_resp.json()["new_status"] == "CLOSED"
        assert close_resp.json()["auto_not_selected_count"] == 2
        assert mock_email.await_count == 2

    await db_session.refresh(app_sub)
    await db_session.refresh(app_rev)
    await db_session.refresh(app_short)
    await db_session.refresh(app_int)

    assert app_sub.status == "NOT SELECTED"
    assert app_rev.status == "NOT SELECTED"
    assert app_short.status == "SHORTLISTED"
    assert app_int.status == "INTERVIEWED"

    # Audit history must record reason "Position closed"
    hist_res = await db_session.execute(
        select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app_sub.id)
    )
    histories = list(hist_res.scalars().all())
    assert any(h.reason == "Position closed" and h.new_status == "Not Selected" for h in histories)

    # Closed job rejects new applications on the server with "This position is closed"
    cand5 = await _make_user(db_session, "cand.late@example.com", role="CANDIDATE", fullname="Late Applicant")
    apply_resp = await client.post(
        "/applications/",
        json={
            "job_id": job.job_id,
            "candidate_name": cand5.fullname,
            "candidate_email": cand5.email,
        },
        headers=_auth_headers(cand5),
    )
    assert apply_resp.status_code == 400
    assert "This position is closed" in apply_resp.json()["detail"]

    # Reopen CLOSED -> ACTIVE and re-close: already Not Selected applicants must NOT be re-notified (idempotent once only)
    reopen_resp = await client.post(f"/admins/jobs/{job.job_id}/reopen", headers=_auth_headers(hr))
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["new_status"] == "ACTIVE"

    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock) as mock_email2:
        close_again = await client.post(f"/admins/jobs/{job.job_id}/close", headers=_auth_headers(hr))
        assert close_again.status_code == 200
        assert close_again.json()["auto_not_selected_count"] == 0
        assert mock_email2.await_count == 0

    # Archive job: hidden from default lists, visible with include_archived=True, cannot be reopened
    arch_resp = await client.post(f"/admins/jobs/{job.job_id}/archive", headers=_auth_headers(hr))
    assert arch_resp.status_code == 200
    assert arch_resp.json()["new_status"] == "ARCHIVED"

    default_list = await client.get("/admins/read-jobs?include_inactive=true&include_archived=false")
    assert all(j["job_id"] != job.job_id for j in default_list.json())

    with_archived = await client.get("/admins/read-jobs?include_inactive=true&include_archived=true")
    assert any(j["job_id"] == job.job_id and j["status"] == "ARCHIVED" for j in with_archived.json())

    reopen_arch = await client.post(f"/admins/jobs/{job.job_id}/reopen", headers=_auth_headers(hr))
    assert reopen_arch.status_code == 400

    # Job status audit logs exist
    audit_res = await db_session.execute(select(AuditLog).where(AuditLog.action == "CHANGE_JOB_STATUS"))
    assert len(list(audit_res.scalars().all())) >= 4


# ── 1. Shortlist Prompt Options & Editable Template Safeguard ────────────────

@pytest.mark.asyncio
async def test_shortlist_prompt_options_and_not_selected_template_guard(client, db_session):
    hr = await _make_user(db_session, "hr.shortlist@mariwasa.com", role="HR", fullname="HR Screener")
    c_win = await _make_user(db_session, "win@example.com", role="CANDIDATE", fullname="Winner Cand")
    c_lose1 = await _make_user(db_session, "lose1@example.com", role="CANDIDATE", fullname="NonShort 1")
    c_lose2 = await _make_user(db_session, "lose2@example.com", role="CANDIDATE", fullname="NonShort 2")
    job = await _make_job(db_session, "JOB-SL-01", "Quality Inspector", status="ACTIVE")

    app_win = await _make_application(db_session, job, c_win, status="UNDER REVIEW")
    app_l1 = await _make_application(db_session, job, c_lose1, status="SUBMITTED")
    app_l2 = await _make_application(db_session, job, c_lose2, status="UNDER REVIEW")

    # Template validation: must reject scores, weights, or formulas in Not Selected template
    with pytest.raises(ValueError):
        await update_templates(
            db_session,
            {"application_status_rejected": {"email_message": "Your match score was {match_score}% based on weights."}},
        )

    # Preview returns accurate affected count (2) & message preview without scores
    prev = await client.post(
        "/hr/shortlists/preview-non-shortlisted",
        json={"job_id": job.id, "shortlisted_application_ids": [app_win.id]},
        headers=_auth_headers(hr),
    )
    assert prev.status_code == 200
    assert prev.json()["affected_count"] == 2
    assert "score" not in prev.json()["message_preview"]["message"].lower()

    # Create draft roster with default 'keep_under_review' (finalize=False)
    create_resp = await client.post(
        "/hr/shortlists",
        json={
            "job_id": job.id,
            "name": "Batch A",
            "application_ids": [app_win.id],
            "non_shortlisted_action": "keep_under_review",
            "finalize": False,
        },
        headers=_auth_headers(hr),
    )
    assert create_resp.status_code == 201
    roster_id = create_resp.json()["id"]
    assert create_resp.json()["non_shortlisted_action"] == "keep_under_review"
    assert create_resp.json()["is_finalized"] is False

    # Change policy to decide_later, then to notify_on_finalize before finalizing
    pol1 = await client.patch(
        f"/hr/shortlists/{roster_id}/non-shortlisted-policy",
        json={"non_shortlisted_action": "decide_later"},
        headers=_auth_headers(hr),
    )
    assert pol1.status_code == 200
    assert pol1.json()["non_shortlisted_action"] == "decide_later"

    # Never apply silently: confirm=False with notify_on_finalize must fail
    silent_attempt = await client.post(
        f"/hr/shortlists/{roster_id}/finalize",
        json={"non_shortlisted_action": "notify_on_finalize", "confirm": False},
        headers=_auth_headers(hr),
    )
    assert silent_attempt.status_code == 400

    # Finalize with explicit confirm=True notifies the 2 non-shortlisted applicants once
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock) as mock_em:
        fin_resp = await client.post(
            f"/hr/shortlists/{roster_id}/finalize",
            json={"non_shortlisted_action": "notify_on_finalize", "confirm": True},
            headers=_auth_headers(hr),
        )
        assert fin_resp.status_code == 200
        assert fin_resp.json()["notified_count"] == 2
        assert mock_em.await_count == 2

    await db_session.refresh(app_l1)
    await db_session.refresh(app_l2)
    await db_session.refresh(app_win)
    assert app_l1.status == "NOT SELECTED"
    assert app_l2.status == "NOT SELECTED"
    assert app_win.status == "SHORTLISTED"

    # Changing policy after finalizing must be blocked
    after_pol = await client.patch(
        f"/hr/shortlists/{roster_id}/non-shortlisted-policy",
        json={"non_shortlisted_action": "keep_under_review"},
        headers=_auth_headers(hr),
    )
    assert after_pol.status_code == 400


# ── 3. Single Withdrawal, Account Deletion & No Hard-Delete Endpoints ────────

@pytest.mark.asyncio
async def test_single_withdrawal_account_deletion_and_hard_delete_locks(client, db_session):
    admin = await _make_user(db_session, "admin.del@mariwasa.com", role="ADMIN", fullname="Sys Admin")
    hr = await _make_user(db_session, "hr.del@mariwasa.com", role="HR", fullname="HR Staff")
    cand = await _make_user(db_session, "cand.del@example.com", role="CANDIDATE", fullname="Jane Applicant", password="MyPassword123!")

    j1 = await _make_job(db_session, "JOB-WD-1", "Role One")
    j2 = await _make_job(db_session, "JOB-WD-2", "Role Two")
    j3 = await _make_job(db_session, "JOB-WD-3", "Role Three")
    j4 = await _make_job(db_session, "JOB-WD-4", "Role Four")

    a1 = await _make_application(db_session, j1, cand, status="SHORTLISTED")
    a2 = await _make_application(db_session, j2, cand, status="UNDER REVIEW")
    a3 = await _make_application(db_session, j3, cand, status="SUBMITTED")

    # Schedule an interview on a1
    iv1 = Interview(
        job_application_id=a1.id,
        interviewer_id=hr.id,
        title="Initial Interview",
        start_time=datetime.utcnow() + timedelta(days=2),
        end_time=datetime.utcnow() + timedelta(days=2, hours=1),
        status="SCHEDULED",
    )
    db_session.add(iv1)
    await db_session.commit()

    # 4th application is blocked by 3-active limit
    cand_hdrs = _auth_headers(cand)
    blocked_4th = await client.post(
        "/applications/",
        json={"job_id": j4.job_id, "candidate_name": cand.fullname, "candidate_email": cand.email},
        headers=cand_hdrs,
    )
    assert blocked_4th.status_code == 400

    # Hard-delete endpoints must ALL return 403 for applicants, applications, resumes
    assert (await client.delete(f"/admins/users/{cand.id}", headers=_auth_headers(admin))).status_code == 403
    assert (await client.delete(f"/applications/{a1.id}", headers=_auth_headers(hr))).status_code == 403
    assert (await client.delete("/resumes/1", headers=_auth_headers(hr))).status_code == 403
    assert (await client.delete("/hr/physical-resumes/1", headers=_auth_headers(hr))).status_code == 403

    # Single application withdrawal: cancels interview, notifies HR, frees active slot immediately
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        wd_resp = await client.post(
            f"/applications/{a1.id}/withdraw",
            json={"reason": "Found another role"},
            headers=cand_hdrs,
        )
    assert wd_resp.status_code == 200
    assert wd_resp.json()["cancelled_interviews"] == 1
    await db_session.refresh(a1)
    await db_session.refresh(iv1)
    assert a1.status == "WITHDRAWN BY APPLICANT"
    assert iv1.status == "CANCELLED"
    assert a1.messaging_closed_at is not None

    # Now applying to j4 succeeds because slot freed immediately!
    ok_4th = await client.post(
        "/applications/",
        json={
            "job_id": j4.job_id,
            "candidate_name": cand.fullname,
            "candidate_email": cand.email,
            "skills": ["Python", "Quality Control"],
        },
        headers=cand_hdrs,
    )
    assert ok_4th.status_code == 201

    # Account deletion with wrong password fails
    bad_del = await client.post(
        "/auth/account/delete",
        json={"password": "WrongPassword"},
        headers=cand_hdrs,
    )
    assert bad_del.status_code == 400

    # Account deletion with valid password: immediate deactivation, withdraws remaining active apps,
    # invalidates existing JWT token everywhere, notifies HR with affected applications list
    del_resp = await client.post(
        "/auth/account/delete",
        json={"password": "MyPassword123!", "reason": "No longer looking"},
        headers=cand_hdrs,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["withdrawn_count"] == 3  # a2, a3, and the newly created j4 app

    # Old token is IMMEDIATELY invalidated on any authenticated endpoint
    stale_check = await client.get("/applications/my", headers=cand_hdrs)
    assert stale_check.status_code == 401

    # HR received notification listing affected applications
    notif_res = await db_session.execute(
        select(Notification).where(Notification.target_role == "HR", Notification.type == "account_deletion")
    )
    hr_notifs = list(notif_res.scalars().all())
    assert len(hr_notifs) >= 1
    assert "Role Two" in hr_notifs[-1].message


# ── 4. Retention Period, Dry-Run, Anonymization & Email-Hash Repeat Flag ─────

@pytest.mark.asyncio
async def test_retention_dry_run_anonymization_active_protection_and_repeat_flag(client, db_session):
    admin = await _make_user(db_session, "admin.ret@mariwasa.com", role="ADMIN", fullname="Ret Admin")
    hr = await _make_user(db_session, "hr.ret@mariwasa.com", role="HR", fullname="Ret HR")
    job = await _make_job(db_session, "JOB-RET-1", "Tile Technician")

    # Create a real temp resume file to verify physical file deletion
    fd, temp_resume_path = tempfile.mkstemp(suffix=".pdf")
    os.write(fd, b"%PDF-1.4 dummy resume content")
    os.close(fd)
    assert os.path.isfile(temp_resume_path)

    old_date = datetime.utcnow() - timedelta(days=400)  # > 12 months

    # Candidate A: deactivated > 12 months ago, only resolved application -> MUST be anonymized
    cand_old = await _make_user(db_session, "repeat.person@example.com", role="CANDIDATE", fullname="Old Sensitive Name")
    cand_old.is_deactivated = True
    cand_old.deactivated_at = old_date
    db_session.add(Resume(candidate_id=cand_old.id, filename="cv.pdf", file_url=temp_resume_path, parsed_data={"phone": "09171234567"}))
    app_old = await _make_application(
        db_session, job, cand_old, status="NOT SELECTED", resume_url=temp_resume_path, resolved_at=old_date, match_score=77.5
    )

    # Candidate B: has an ACTIVE application -> MUST NEVER be purged
    cand_active = await _make_user(db_session, "still.active@example.com", role="CANDIDATE", fullname="Active Person")
    cand_active.is_deactivated = True
    cand_active.deactivated_at = old_date
    app_active = await _make_application(db_session, job, cand_active, status="SHORTLISTED")
    await db_session.commit()

    # 1. Dry-run mode must NOT mutate DB or delete files, and must write a run log
    dry_resp = await client.post(
        "/system-config/retention/run",
        json={"dry_run": True},
        headers=_auth_headers(admin),
    )
    assert dry_resp.status_code == 200
    assert dry_resp.json()["dry_run"] is True
    assert dry_resp.json()["candidates_anonymized"] == 1
    assert dry_resp.json()["skipped_active"] >= 1
    assert os.path.isfile(temp_resume_path)  # File untouched on dry run!

    # 2. Live run anonymizes Candidate A, removes file, keeps job/dates/scores, skips active Candidate B
    live_resp = await client.post(
        "/system-config/retention/run",
        json={"dry_run": False},
        headers=_auth_headers(admin),
    )
    assert live_resp.status_code == 200
    assert live_resp.json()["dry_run"] is False
    assert live_resp.json()["candidates_anonymized"] == 1
    assert live_resp.json()["files_deleted"] >= 1
    assert live_resp.json()["skipped_active"] >= 1
    assert not os.path.isfile(temp_resume_path)  # Physical file deleted!

    await db_session.refresh(cand_old)
    await db_session.refresh(app_old)
    await db_session.refresh(cand_active)

    assert cand_old.is_anonymized is True
    assert cand_old.fullname.startswith("Anonymized applicant #")
    assert "repeat.person@example.com" not in cand_old.email
    assert app_old.is_anonymized is True
    assert app_old.job_id == job.id
    assert app_old.match_score == 77.5
    assert app_old.status == "NOT SELECTED"
    assert app_old.resume_url is None
    assert cand_active.is_anonymized is False  # Active candidate untouched!

    # 3. Safe to re-run (idempotent: 0 newly anonymized)
    rerun_resp = await client.post(
        "/system-config/retention/run",
        json={"dry_run": False},
        headers=_auth_headers(admin),
    )
    assert rerun_resp.status_code == 200
    assert rerun_resp.json()["candidates_anonymized"] == 0

    # 4. New registration with same email gets empty account AND HR sees repeat-applicant flag from email_hash only
    reg_new = await client.post(
        "/auth/register",
        json={"email": "REPEAT.PERSON@example.com ", "password": "NewPassword1!", "role": "CANDIDATE", "fullname": "Brand New Profile"},
    )
    assert reg_new.status_code == 200

    new_user = (await db_session.execute(select(User).where(User.email == "repeat.person@example.com"))).scalar_one()
    await _make_application(db_session, job, new_user, status="SUBMITTED")

    prof_resp = await client.get(
        f"/hr/applicant-profile/{new_user.id}",
        headers=_auth_headers(hr),
    )
    assert prof_resp.status_code == 200
    assert prof_resp.json()["has_previous_anonymized_application"] is True
    assert prof_resp.json()["previous_application_flag"] == "Previous application on record (anonymized)"
    # Old PII ("Old Sensitive Name") must NOT appear anywhere in new applicant's profile
    assert "Old Sensitive Name" not in str(prof_resp.json())


# ── 5. OTP Reactivation, Duplicate Email Check & Fresh Start ─────────────────

@pytest.mark.asyncio
async def test_otp_reactivation_duplicate_email_and_fresh_start(client, db_session):
    # Register initial candidate
    r1 = await client.post(
        "/auth/register",
        json={"email": "Alice.Smith@Example.COM ", "password": "Password123!", "role": "CANDIDATE", "fullname": "Alice Smith"},
    )
    assert r1.status_code == 200

    # Duplicate active email blocked case-insensitively with trimmed spaces
    r_dup = await client.post(
        "/auth/register",
        json={"email": "  alice.smith@example.com", "password": "Password123!", "role": "CANDIDATE", "fullname": "Alice Dup"},
    )
    assert r_dup.status_code == 409

    # Login & create an application, then delete account
    login_resp = await client.post("/auth/login", json={"email": "alice.smith@example.com", "password": "Password123!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    alice = (await db_session.execute(select(User).where(User.email == "alice.smith@example.com"))).scalar_one()
    job = await _make_job(db_session, "JOB-REACT-1", "Safety Officer")
    app = await _make_application(db_session, job, alice, status="UNDER REVIEW")

    del_resp = await client.post(
        "/auth/account/delete",
        json={"password": "Password123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200

    # Registering again without fresh_start returns 409 offering Reactivate or Fresh Start
    r_deact = await client.post(
        "/auth/register",
        json={"email": "ALICE.SMITH@example.com", "password": "NewPassword123!", "role": "CANDIDATE", "fullname": "Alice"},
    )
    assert r_deact.status_code == 409
    assert r_deact.json()["detail"]["code"] == "DEACTIVATED_ACCOUNT_EXISTS"
    assert r_deact.json()["detail"]["can_reactivate"] is True
    assert r_deact.json()["detail"]["can_fresh_start"] is True

    # Request OTP for reactivation, verify wrong code increments attempts, valid code restores profile
    captured_code = {}

    async def _capture_otp(to_email, otp_code, purpose="reactivate_account"):
        captured_code["code"] = otp_code
        return True

    with patch("app.services.auth_service.send_otp_email", side_effect=_capture_otp):
        otp_req = await client.post("/auth/reactivate/request-otp", json={"email": "alice.smith@example.com"})
    assert otp_req.status_code == 200
    assert len(captured_code["code"]) == 6

    bad_otp = await client.post("/auth/reactivate/verify", json={"email": "alice.smith@example.com", "otp_code": "000000" if captured_code["code"] != "000000" else "111111"})
    assert bad_otp.status_code == 400

    good_otp = await client.post(
        "/auth/reactivate/verify",
        json={"email": "alice.smith@example.com", "otp_code": captured_code["code"]},
    )
    assert good_otp.status_code == 200
    assert "access_token" in good_otp.json()

    # Profile restored, but withdrawn application STAYS withdrawn!
    await db_session.refresh(alice)
    await db_session.refresh(app)
    assert alice.is_deactivated is False
    assert app.status == "WITHDRAWN BY APPLICANT"

    # Now deactivate again and test Fresh Start before purge -> old account anonymized, new starts empty
    fresh_token = good_otp.json()["access_token"]
    await client.post(
        "/auth/account/delete",
        json={"password": "Password123!"},
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    with patch("app.services.auth_service.send_otp_email", side_effect=_capture_otp):
        await client.post("/auth/fresh-start/request-otp", json={"email": "alice.smith@example.com"})
    verified = await client.post("/auth/fresh-start/verify", json={"email": "alice.smith@example.com", "otp_code": captured_code["code"]})
    assert verified.status_code == 200
    fs_resp = await client.post(
        "/auth/fresh-start",
        json={"email": "alice.smith@example.com", "password": "BrandNewPassword1!", "fullname": "Alice Fresh", "verification_token": verified.json()["verification_token"], "confirm_fresh_start": True},
    )
    assert fs_resp.status_code == 200

    await db_session.refresh(alice)
    assert alice.is_anonymized is True  # Old record immediately anonymized

    new_login = await client.post("/auth/login", json={"email": "alice.smith@example.com", "password": "BrandNewPassword1!"})
    assert new_login.status_code == 200
    assert new_login.json()["user_id"] != alice.id

    my_apps = await client.get("/applications/my", headers={"Authorization": f"Bearer {new_login.json()['access_token']}"})
    assert my_apps.status_code == 200
    assert len(my_apps.json()) == 0  # Brand-new empty account!


# ── 6. Clear End States, Messaging 30-Day Closure & 3-Active Limit ───────────

@pytest.mark.asyncio
async def test_end_states_messaging_closure_and_active_slot_limit(client, db_session):
    hr = await _make_user(db_session, "hr.end@mariwasa.com", role="HR", fullname="HR Coord")
    cand = await _make_user(db_session, "cand.end@example.com", role="CANDIDATE", fullname="End State Cand")

    j1 = await _make_job(db_session, "JOB-END-1", "Machinist")
    j2 = await _make_job(db_session, "JOB-END-2", "Electrician")
    j3 = await _make_job(db_session, "JOB-END-3", "Technician")
    j4 = await _make_job(db_session, "JOB-END-4", "Planner")

    a1 = await _make_application(db_session, j1, cand, status="INTERVIEWED")
    a2 = await _make_application(db_session, j2, cand, status="UNDER REVIEW")
    a3 = await _make_application(db_session, j3, cand, status="SUBMITTED")

    # Mark a1 as Passed Initial Interview -> read-only, displays endorsed message, frees slot
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        p_resp = await client.patch(
            f"/applications/{a1.id}/status",
            json={"status": "PASSED INITIAL INTERVIEW"},
            headers=_auth_headers(hr),
        )
    assert p_resp.status_code == 200
    assert p_resp.json()["status_display"] == "Passed Initial Interview – Endorsed for next stage"
    assert p_resp.json()["is_read_only"] is True

    # Candidate cannot withdraw a Passed (read-only) application
    wd_passed = await client.post(f"/applications/{a1.id}/withdraw", headers=_auth_headers(cand))
    assert wd_passed.status_code == 400

    # Mark a2 as Not Selected -> feedback report stays viewable
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        ns_resp = await client.patch(
            f"/applications/{a2.id}/status",
            json={"status": "NOT SELECTED"},
            headers=_auth_headers(hr),
        )
    assert ns_resp.status_code == 200
    assert ns_resp.json()["matched_skills"] == ["Python"]
    assert ns_resp.json()["ai_summary"] == "Strong technical background."

    # Candidate can apply to j4 since a1 (Passed) and a2 (Not Selected) freed slots!
    apply_j4 = await client.post(
        "/applications/",
        json={
            "job_id": j4.job_id,
            "candidate_name": cand.fullname,
            "candidate_email": cand.email,
            "skills": ["Python", "Quality Control"],
        },
        headers=_auth_headers(cand),
    )
    assert apply_j4.status_code == 201

    # Messaging: applicant CANNOT start a thread before HR sends the first message (403)
    msg_before_hr = await client.post(
        f"/chat/messages/{hr.id}",
        json={"content": "Trying before HR starts", "application_id": a1.id},
        headers=_auth_headers(cand),
    )
    assert msg_before_hr.status_code == 403

    # Once HR starts the conversation on a1, candidate CAN reply while within 30 days of resolution
    hr_first = await client.post(
        f"/chat/messages/{cand.id}",
        json={"content": "Hi! Congratulations on passing the initial interview.", "application_id": a1.id},
        headers=_auth_headers(hr),
    )
    assert hr_first.status_code == 200

    msg_ok = await client.post(
        f"/chat/messages/{hr.id}",
        json={"content": "Hello HR, thank you!", "application_id": a1.id},
        headers=_auth_headers(cand),
    )
    assert msg_ok.status_code == 200

    # Simulate 31 days after resolution -> messaging thread locks with "This conversation is closed"
    a1.resolved_at = datetime.utcnow() - timedelta(days=31)
    await db_session.commit()

    ts_closed = await client.get(f"/chat/thread-status/{hr.id}?application_id={a1.id}", headers=_auth_headers(cand))
    assert ts_closed.status_code == 200
    assert ts_closed.json()["is_closed"] is True
    assert ts_closed.json()["reason"] == "This conversation is closed"

    msg_locked = await client.post(
        f"/chat/messages/{hr.id}",
        json={"content": "Late message", "application_id": a1.id},
        headers=_auth_headers(cand),
    )
    assert msg_locked.status_code == 403
    assert "This conversation is closed" in msg_locked.json()["detail"]

    # Withdrawn application closes messaging IMMEDIATELY
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        await client.post(f"/applications/{a3.id}/withdraw", headers=_auth_headers(cand))
    msg_wd = await client.post(
        f"/chat/messages/{hr.id}",
        json={"content": "After withdraw", "application_id": a3.id},
        headers=_auth_headers(cand),
    )
    assert msg_wd.status_code == 403


# ── 7. Multi-Application Rules, Combined Invite, On Hold, Hired Elsewhere ────

@pytest.mark.asyncio
async def test_multi_application_flag_combined_interview_on_hold_and_hired_elsewhere(client, db_session):
    admin = await _make_user(db_session, "admin.multi@mariwasa.com", role="ADMIN", fullname="Multi Admin")
    hr = await _make_user(db_session, "hr.multi@mariwasa.com", role="HR", fullname="Multi HR")
    cand = await _make_user(db_session, "cand.multi@example.com", role="CANDIDATE", fullname="Multi Cand")

    j1 = await _make_job(db_session, "JOB-M-1", "Production Lead")
    j2 = await _make_job(db_session, "JOB-M-2", "QA Specialist")
    j3 = await _make_job(db_session, "JOB-M-3", "Logistics Analyst")
    j4 = await _make_job(db_session, "JOB-M-4", "Plant Supervisor")

    a1 = await _make_application(db_session, j1, cand, status="SHORTLISTED")
    a2 = await _make_application(db_session, j2, cand, status="SHORTLISTED")
    a3 = await _make_application(db_session, j3, cand, status="UNDER REVIEW")

    # 1. HR sees multi-application flag on profile (2 other active applications)
    prof = await client.get(f"/hr/applicant-profile/{cand.id}", headers=_auth_headers(hr))
    assert prof.status_code == 200
    assert prof.json()["other_active_count"] == 2
    assert prof.json()["other_active_flag"] == "This applicant has 2 other active applications"
    assert len(prof.json()["active_applications"]) == 3

    # 2. Combined interview: scheduler sees both shortlisted positions
    comb_opts = await client.get(f"/interviews/candidate-shortlisted/{a1.id}", headers=_auth_headers(hr))
    assert comb_opts.status_code == 200
    assert comb_opts.json()["can_combine"] is True
    assert len(comb_opts.json()["shortlisted_applications"]) == 2

    # Schedule ONE combined interview for a1 & a2 (pick next Monday 10:00-11:00)
    today = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    days_until_mon = (7 - today.weekday()) % 7 or 7
    slot_start = today + timedelta(days=days_until_mon)
    slot_end = slot_start + timedelta(hours=1)

    with patch("app.services.email_service.send_interview_invitation_email", new_callable=AsyncMock) as mock_iv_email, \
         patch("app.services.interview_service._dispatch_candidate_sms", new_callable=AsyncMock) as mock_sms:
        sched_resp = await client.post(
            "/interviews/schedule",
            json={
                "job_application_id": a1.id,
                "combined_application_ids": [a1.id, a2.id],
                "title": "Combined Initial Interview",
                "start_time": slot_start.isoformat(),
                "end_time": slot_end.isoformat(),
            },
            headers=_auth_headers(hr),
        )
        assert sched_resp.status_code == 200
        # Candidate gets ONE invite listing both positions & ONE SMS
        cand_email_calls = [c for c in mock_iv_email.call_args_list if c.kwargs.get("to_email") == cand.email]
        assert len(cand_email_calls) == 1
        assert "Production Lead" in cand_email_calls[0].kwargs["job_title"]
        assert "QA Specialist" in cand_email_calls[0].kwargs["job_title"]
        assert mock_sms.await_count == 1

    await db_session.refresh(a1)
    await db_session.refresh(a2)
    await db_session.refresh(a3)
    assert a1.status == "INTERVIEW SCHEDULED"
    assert a2.status == "INTERVIEW SCHEDULED"
    assert a3.status == "UNDER REVIEW"  # Other applications never auto-withdrawn

    # 3. Independent pass/fail: a1 Passed, a2 stays independent -> HR puts a2 On Hold and continues a3
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        await client.patch(f"/applications/{a1.id}/status", json={"status": "PASSED INITIAL INTERVIEW"}, headers=_auth_headers(hr))
        hold_resp = await client.post(
            f"/applications/{a1.id}/post-pass-action",
            json={"action": "on_hold", "target_application_ids": [a2.id], "note": "Waiting on final offer"},
            headers=_auth_headers(hr),
        )
        assert hold_resp.status_code == 200
        cont_resp = await client.post(
            f"/applications/{a1.id}/post-pass-action",
            json={"action": "continue", "target_application_ids": [a3.id]},
            headers=_auth_headers(hr),
        )
        assert cont_resp.status_code == 200

    await db_session.refresh(a2)
    assert a2.status == "ON HOLD"

    # On Hold STILL counts as active (a2=On Hold + a3=Under Review + j4=Submitted -> 3 active; j5 blocked)
    await _make_application(db_session, j4, cand, status="SUBMITTED")
    j5 = await _make_job(db_session, "JOB-M-5", "Extra Role")
    blocked_5th = await client.post(
        "/applications/",
        json={"job_id": j5.job_id, "candidate_name": cand.fullname, "candidate_email": cand.email},
        headers=_auth_headers(cand),
    )
    assert blocked_5th.status_code == 400  # Because On Hold counts as active!

    # HR can resume On Hold application back to prior active status
    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        res_resp = await client.post(f"/applications/{a2.id}/resume", json={}, headers=_auth_headers(hr))
    assert res_resp.status_code == 200
    await db_session.refresh(a2)
    assert a2.status != "ON HOLD"

    # 4. "Withdrawn – hired elsewhere in company" is DISABLED by default (403), then works when enabled in System Config
    dis_resp = await client.post(
        f"/applications/{a3.id}/withdraw-hired-elsewhere",
        json={"note": "Accepted Production Lead offer"},
        headers=_auth_headers(hr),
    )
    assert dis_resp.status_code == 403

    cfg_resp = await client.put(
        "/system-config/recruitment",
        json={"allow_hired_elsewhere_withdrawal": True},
        headers=_auth_headers(admin),
    )
    assert cfg_resp.status_code == 200
    assert cfg_resp.json()["allow_hired_elsewhere_withdrawal"] is True

    with patch("app.services.email_service.send_application_status_update_email", new_callable=AsyncMock):
        en_resp = await client.post(
            f"/applications/{a3.id}/withdraw-hired-elsewhere",
            json={"note": "Accepted Production Lead offer"},
            headers=_auth_headers(hr),
        )
    assert en_resp.status_code == 200
    await db_session.refresh(a3)
    assert a3.status == "WITHDRAWN – HIRED ELSEWHERE IN COMPANY"
