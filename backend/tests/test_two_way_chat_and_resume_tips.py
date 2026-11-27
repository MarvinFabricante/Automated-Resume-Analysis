"""
Comprehensive tests for:
1. Two-way HR-initiated per-application chat (403 enforcement, isolation, closing rules,
   anti-abuse rate limit/max length/sanitization/attachments/report, HR templates,
   seen receipts, email digest, retention anonymization).
2. ATS-friendly resume tips (public read, admin edit/reset, one-page DOCX template)
   and non-blocking post-upload readability checks.
"""
import io
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import docx
import fitz
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from app.models.admin import Admin
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.models.message import ApplicationThread, Message, MessageReport
from app.services import chat_service
from app.services.retention_service import anonymize_user_and_records
from app.utils.auth import create_access_token, hash_password
from app.utils.database import get_db


def _auth_headers(user) -> dict:
    token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    chat_service.reset_in_memory_rate_limits()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
    chat_service.reset_in_memory_rate_limits()


async def _seed_users_and_apps(db_session):
    admin = Admin(
        fullname="Admin Tester",
        email="admin.chat@mariwasa.com",
        password=hash_password("pass123"),
        role="ADMIN",
    )
    hr1 = HR(
        fullname="Maria Santos",
        email="maria.hr@mariwasa.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa",
    )
    hr2 = HR(
        fullname="Carlo Reyes",
        email="carlo.hr@mariwasa.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa",
    )
    cand = Candidate(
        fullname="Juan Dela Cruz",
        email="juan.cand@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE",
    )
    other_cand = Candidate(
        fullname="Ana Lopez",
        email="ana.other@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE",
    )
    db_session.add_all([admin, hr1, hr2, cand, other_cand])
    await db_session.flush()

    job1 = JobDescription(
        job_id="JOB-CHAT-1",
        job_title="Production Supervisor",
        department="Manufacturing",
        job_type="Full-Time",
        location="Laguna",
        description="Supervise production line.",
        skills_requirements="Excel, Production Planning, Quality Control",
        is_active=True,
    )
    job2 = JobDescription(
        job_id="JOB-CHAT-2",
        job_title="Quality Analyst",
        department="QA",
        job_type="Full-Time",
        location="Laguna",
        description="Inspect tiles.",
        skills_requirements="ISO 9001, Quality Control",
        is_active=True,
    )
    db_session.add_all([job1, job2])
    await db_session.flush()

    app1 = JobApplication(
        job_id=job1.id,
        user_id=cand.id,
        candidate_name=cand.fullname,
        candidate_email=cand.email,
        job_title=job1.job_title,
        status="SHORTLISTED",
    )
    app2 = JobApplication(
        job_id=job2.id,
        user_id=cand.id,
        candidate_name=cand.fullname,
        candidate_email=cand.email,
        job_title=job2.job_title,
        status="UNDER REVIEW",
    )
    db_session.add_all([app1, app2])
    await db_session.commit()
    return admin, hr1, hr2, cand, other_cand, job1, job2, app1, app2


@pytest.mark.asyncio
async def test_two_way_chat_server_enforcement_isolation_and_closing_rules(client, db_session):
    admin, hr1, hr2, cand, other_cand, job1, job2, app1, app2 = await _seed_users_and_apps(db_session)

    # 1. Applicant CANNOT create a thread or message before HR starts (all return 403)
    r_start = await client.post(
        "/chat/threads",
        json={"application_id": app1.id, "content": "Hi HR!"},
        headers=_auth_headers(cand),
    )
    assert r_start.status_code == 403

    r_app_msg = await client.post(
        f"/chat/applications/{app1.id}/messages",
        json={"content": "Can I start chatting?"},
        headers=_auth_headers(cand),
    )
    assert r_app_msg.status_code == 403

    r_legacy = await client.post(
        f"/chat/messages/{hr1.id}",
        json={"content": "Cold message", "application_id": app1.id},
        headers=_auth_headers(cand),
    )
    assert r_legacy.status_code == 403

    # Applicant inbox is empty and application thread shows exists=False, can_reply=False
    inbox_before = await client.get("/chat/threads", headers=_auth_headers(cand))
    assert inbox_before.status_code == 200
    assert inbox_before.json()["threads"] == []

    app_thread_before = await client.get(
        f"/chat/applications/{app1.id}/thread",
        headers=_auth_headers(cand),
    )
    assert app_thread_before.status_code == 200
    assert app_thread_before.json()["exists"] is False
    assert app_thread_before.json()["thread_status"]["can_reply"] is False

    # 2. HR templates available to HR, forbidden to applicant
    tpl_cand = await client.get("/chat/templates", headers=_auth_headers(cand))
    assert tpl_cand.status_code == 403
    tpl_hr = await client.get(
        f"/chat/templates?candidate_name=Juan&job_title={job1.job_title}",
        headers=_auth_headers(hr1),
    )
    assert tpl_hr.status_code == 200
    labels = [t["label"] for t in tpl_hr.json()]
    assert "Request for clarification" in labels
    assert "Interview reminder" in labels
    assert "Document request" in labels

    # 3. HR1 starts conversation for app1 (status must NOT change)
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        start_res = await client.post(
            "/chat/threads",
            json={
                "application_id": app1.id,
                "content": "<b>Hello</b> <script>alert(1)</script>Juan, please confirm your availability.",
            },
            headers=_auth_headers(hr1),
        )
    assert start_res.status_code == 200
    thr_data = start_res.json()
    assert thr_data["exists"] is True
    thread_id = thr_data["thread"]["id"]
    assert thr_data["thread"]["job_title"] == "Production Supervisor"
    # HTML sanitized
    first_msg = thr_data["messages"][0]
    assert "<script>" not in first_msg["content"]
    assert "<b>" not in first_msg["content"]
    assert "Hello" in first_msg["content"]
    assert first_msg["sender_name"] == "Maria Santos"
    assert first_msg["sender_role"] == "HR"

    # Application status did not change
    await db_session.refresh(app1)
    assert app1.status == "SHORTLISTED"

    # 4. Applicant now sees the thread in combined inbox with unread_count=1 and position name
    inbox_after = await client.get("/chat/threads", headers=_auth_headers(cand))
    assert inbox_after.status_code == 200
    assert len(inbox_after.json()["threads"]) == 1
    assert inbox_after.json()["threads"][0]["job_title"] == "Production Supervisor"
    assert inbox_after.json()["threads"][0]["unread_count"] == 1

    # Opening thread marks HR's message as read (seen)
    open_res = await client.get(
        f"/chat/threads/{thread_id}/messages",
        headers=_auth_headers(cand),
    )
    assert open_res.status_code == 200
    assert open_res.json()["messages"][0]["is_read"] is True
    assert open_res.json()["messages"][0]["read_at"] is not None

    # 5. Applicant can now reply in app1, but STILL gets 403 on app2 (no HR-started thread on app2)
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        reply_res = await client.post(
            f"/chat/threads/{thread_id}/messages",
            json={"content": "Yes, I am available tomorrow morning!"},
            headers=_auth_headers(cand),
        )
    assert reply_res.status_code == 200
    assert reply_res.json()["application_id"] == app1.id

    other_app_res = await client.post(
        f"/chat/applications/{app2.id}/messages",
        json={"content": "Also asking about QA role"},
        headers=_auth_headers(cand),
    )
    assert other_app_res.status_code == 403

    # Unrelated candidate cannot view or reply to cand's thread (403)
    snoop_res = await client.get(
        f"/chat/threads/{thread_id}/messages",
        headers=_auth_headers(other_cand),
    )
    assert snoop_res.status_code == 403

    # 6. Second HR user (Carlo) replies in same thread -> shows Carlo's name
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        hr2_res = await client.post(
            f"/chat/threads/{thread_id}/messages",
            json={"content": "Great, see you then!"},
            headers=_auth_headers(hr2),
        )
    assert hr2_res.status_code == 200
    assert hr2_res.json()["sender_name"] == "Carlo Reyes"

    # 7. Report a message (applicant reports HR2's message)
    hr2_msg_id = hr2_res.json()["id"]
    rep_res = await client.post(
        f"/chat/messages/{hr2_msg_id}/report",
        json={"reason": "Testing report workflow for review."},
        headers=_auth_headers(cand),
    )
    assert rep_res.status_code == 200
    assert rep_res.json()["status"] == "OPEN"

    # 8. Closing rules: Resolved + > 30 days -> 403 "This conversation is closed" (HR can still read)
    app1.status = "PASSED INITIAL INTERVIEW"
    app1.resolved_at = datetime.utcnow() - timedelta(days=31)
    await db_session.commit()

    closed_reply = await client.post(
        f"/chat/threads/{thread_id}/messages",
        json={"content": "Late follow up"},
        headers=_auth_headers(cand),
    )
    assert closed_reply.status_code == 403
    assert "This conversation is closed" in closed_reply.json()["detail"]

    # HR can still read the closed thread
    hr_read_closed = await client.get(
        f"/chat/threads/{thread_id}/messages",
        headers=_auth_headers(hr1),
    )
    assert hr_read_closed.status_code == 200
    assert hr_read_closed.json()["thread_status"]["is_closed"] is True
    assert len(hr_read_closed.json()["messages"]) == 3

    # Withdrawn closes immediately
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        start2 = await client.post(
            "/chat/threads",
            json={"application_id": app2.id, "content": "Hi Juan about QA role"},
            headers=_auth_headers(hr1),
        )
    assert start2.status_code == 200
    thread2_id = start2.json()["thread"]["id"]
    app2.status = "WITHDRAWN BY APPLICANT"
    await db_session.commit()

    wd_reply = await client.post(
        f"/chat/threads/{thread2_id}/messages",
        json={"content": "After withdrawing"},
        headers=_auth_headers(cand),
    )
    assert wd_reply.status_code == 403
    assert "This conversation is closed" in wd_reply.json()["detail"]


@pytest.mark.asyncio
async def test_chat_anti_abuse_attachments_digest_and_retention(client, db_session):
    admin, hr1, hr2, cand, other_cand, job1, job2, app1, app2 = await _seed_users_and_apps(db_session)

    # Start thread with 3 rapid messages from HR -> email digest batches them into ONE email
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock), \
         patch("app.services.email_service.send_hr_message_notification_email", new_callable=AsyncMock) as mock_per_msg:
        r1 = await client.post(
            "/chat/threads",
            json={"application_id": app1.id, "content": "Message one"},
            headers=_auth_headers(hr1),
        )
        thread_id = r1.json()["thread"]["id"]
        await client.post(f"/chat/threads/{thread_id}/messages", json={"content": "Message two"}, headers=_auth_headers(hr1))
        await client.post(f"/chat/threads/{thread_id}/messages", json={"content": "Message three"}, headers=_auth_headers(hr1))
        # Must NOT send one email per message
        assert mock_per_msg.await_count == 0

    with patch("app.services.email_service.send_chat_digest_email", new_callable=AsyncMock) as mock_digest:
        digest_res = await chat_service.dispatch_chat_email_digests(db_session, recipient_id=cand.id)
        assert digest_res["recipients_notified"] == 1
        assert digest_res["messages_included"] == 3
        assert mock_digest.await_count == 1
        # Running again sends 0 (idempotent)
        digest_res2 = await chat_service.dispatch_chat_email_digests(db_session, recipient_id=cand.id)
        assert digest_res2["recipients_notified"] == 0

    # Max length enforcement (> 2000 chars -> 400)
    too_long = await client.post(
        f"/chat/threads/{thread_id}/messages",
        json={"content": "A" * 2005},
        headers=_auth_headers(cand),
    )
    assert too_long.status_code == 400

    # Valid PDF attachment upload + authenticated participant download
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        att_res = await client.post(
            f"/chat/threads/{thread_id}/messages",
            data={"content": "Here is my ID"},
            files={"file": ("id_card.pdf", pdf_bytes, "application/pdf")},
            headers=_auth_headers(cand),
        )
    assert att_res.status_code == 200
    att_msg_id = att_res.json()["id"]
    assert att_res.json()["attachment_name"] == "id_card.pdf"

    dl_ok = await client.get(f"/chat/attachments/{att_msg_id}", headers=_auth_headers(hr1))
    assert dl_ok.status_code == 200
    dl_forbidden = await client.get(f"/chat/attachments/{att_msg_id}", headers=_auth_headers(other_cand))
    assert dl_forbidden.status_code == 403

    # Disguised executable rejected (400)
    bad_att = await client.post(
        f"/chat/threads/{thread_id}/messages",
        data={"content": "Malicious"},
        files={"file": ("fake.pdf", b"MZ\x90\x00executable", "application/pdf")},
        headers=_auth_headers(cand),
    )
    assert bad_att.status_code == 400

    # Rate limit enforcement (10 messages / minute -> 11th returns 429)
    chat_service.reset_in_memory_rate_limits()
    from app.utils.cache import clear_cache_pattern
    await clear_cache_pattern("chat:ratelimit:*")
    try:
        from app.utils.redis_client import get_async_redis, is_redis_available
        if await is_redis_available():
            r_cli = get_async_redis()
            await r_cli.delete(f"chat:ratelimit:{cand.id}")
    except Exception:
        pass
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        for i in range(10):
            ok = await client.post(
                f"/chat/threads/{thread_id}/messages",
                json={"content": f"Burst msg {i}"},
                headers=_auth_headers(cand),
            )
            assert ok.status_code == 200
        blocked = await client.post(
            f"/chat/threads/{thread_id}/messages",
            json={"content": "Burst msg 11"},
            headers=_auth_headers(cand),
        )
        assert blocked.status_code == 429

    # Data retention anonymization scrubs message content, attachments, and thread preview
    app1.status = "NOT SELECTED"
    app2.status = "NOT SELECTED"
    await db_session.commit()
    anon_res = await anonymize_user_and_records(db_session, cand, dry_run=False)
    await db_session.commit()
    assert anon_res["anonymized"] is True

    msg_after = await db_session.get(Message, att_msg_id)
    assert msg_after.content == "[Anonymized per data retention policy]"
    assert msg_after.attachment_url is None
    thr_after = await db_session.get(ApplicationThread, thread_id)
    assert thr_after.last_message_preview == "[Anonymized per data retention policy]"


@pytest.mark.asyncio
async def test_resume_tips_config_ats_template_and_readability_checks(client, db_session):
    admin, hr1, hr2, cand, other_cand, job1, job2, app1, app2 = await _seed_users_and_apps(db_session)

    # 1. Public GET /system-config/resume-tips returns defaults with no weights/formula
    tips_res = await client.get("/system-config/resume-tips")
    assert tips_res.status_code == 200
    tips = tips_res.json()
    assert tips["title"] == "Tips for a better match"
    assert tips["honesty_reminder"] == "Only include what is true."
    assert 4 <= len(tips["bullets"]) <= 6
    combined_text = " ".join([tips["title"], tips["intro"], tips["tooltip"], *tips["bullets"]]).lower()
    assert "weight" not in combined_text
    assert "formula" not in combined_text
    assert "%" not in combined_text

    # Candidate cannot edit tips (403)
    edit_forbidden = await client.put(
        "/system-config/resume-tips",
        json={"title": "Hacked"},
        headers=_auth_headers(cand),
    )
    assert edit_forbidden.status_code == 403

    # Admin can edit and reset tips
    edit_ok = await client.put(
        "/system-config/resume-tips",
        json={"title": "Custom Resume Tips", "honesty_reminder": "Be accurate and honest."},
        headers=_auth_headers(admin),
    )
    assert edit_ok.status_code == 200
    assert edit_ok.json()["title"] == "Custom Resume Tips"

    reset_ok = await client.post("/system-config/resume-tips/reset", headers=_auth_headers(admin))
    assert reset_ok.status_code == 200
    assert reset_ok.json()["title"] == "Tips for a better match"

    # 2. Downloadable one-page ATS-friendly DOCX template (no tables, no images, fictional placeholder)
    tpl_res = await client.get("/resumes/ats-template")
    assert tpl_res.status_code == 200
    assert "wordprocessingml.document" in tpl_res.headers["content-type"]
    loaded_doc = docx.Document(io.BytesIO(tpl_res.content))
    assert len(loaded_doc.tables) == 0
    assert len(loaded_doc.inline_shapes) == 0
    full_tpl_text = "\n".join(p.text for p in loaded_doc.paragraphs)
    for heading in ("EDUCATION", "SKILLS", "WORK EXPERIENCE", "CERTIFICATIONS"):
        assert heading in full_tpl_text.upper()
    assert "Alex Rivera" in full_tpl_text or "ALEX RIVERA" in full_tpl_text

    # 3. Readability check: clean ATS DOCX -> green "Looks readable"
    fake_sb = AsyncMock(return_value={"public_url": "/uploads/resumes/mock.docx", "storage_path": "resumes/mock.docx"})
    with patch("app.utils.supabase_storage.upload_resume", fake_sb):
        clean_res = await client.post(
            "/candidate/parse-resume",
            files={
                "file": (
                    "clean_resume.docx",
                    tpl_res.content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert clean_res.status_code == 200
    rc_clean = clean_res.json().get("readability_check")
    assert rc_clean is not None
    assert rc_clean["status"] == "ok"
    assert rc_clean["summary"] == "Looks readable"
    assert rc_clean["warnings"] == []

    # 4. Readability check: multi-column table resume missing headings/contact/dates -> accepted as resume with specific non-blocking warnings
    messy_doc = docx.Document()
    tbl = messy_doc.add_table(rows=1, cols=2)
    tbl.cell(0, 0).text = (
        "Marco Villanueva\n"
        "Production Operator at Acme Manufacturing Corp.\n"
        "Operated industrial ceramic press machines and performed daily quality control checks.\n"
        "Assisted supervisors with preventive maintenance and workplace safety inspections."
    )
    tbl.cell(0, 1).text = (
        "Bachelor of Science in Industrial Technology\n"
        "Batangas State University\n"
        "Proficient in Machine Operation, Quality Control, AutoCAD, Microsoft Excel, Forklift Operation, and ISO 9001 standards."
    )
    messy_buf = io.BytesIO()
    messy_doc.save(messy_buf)

    with patch("app.utils.supabase_storage.upload_resume", fake_sb):
        messy_res = await client.post(
            "/candidate/parse-resume",
            files={
                "file": (
                    "messy.docx",
                    messy_buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert messy_res.status_code == 200
    rc_messy = messy_res.json().get("readability_check")
    assert rc_messy["status"] == "warning"
    codes = {w["code"] for w in rc_messy["warnings"]}
    assert "multi_column" in codes
    assert "missing_headings" in codes
    assert "missing_contact" in codes
    assert "missing_dates" in codes

    # 5. Password-protected PDF cannot be verified as a resume -> rejected with 400
    #    (while readability_checker itself still reports the password_protected warning directly)
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((72, 72), "Protected Resume Content")
    enc_bytes = pdf_doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret123", owner_pw="owner123")
    pdf_doc.close()

    with patch("app.utils.supabase_storage.upload_resume", fake_sb):
        enc_res = await client.post(
            "/candidate/parse-resume",
            files={"file": ("locked.pdf", enc_bytes, "application/pdf")},
        )
    assert enc_res.status_code == 400
    assert "password" in enc_res.json()["detail"].lower()
