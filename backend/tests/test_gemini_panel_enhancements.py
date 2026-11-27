"""
Comprehensive unit & integration tests for the Gemini + Redis enhanced panel fixes:
1. Wrong-document AI prediction (specific predicted_label, image upload path, 7-day SHA-256 Redis cache,
   0 Gemini calls on unmistakable thesis hard rejections).
2. Below-accepted-requirements blocker (tightened anti-padding guardrails, Gemini Flash-Lite borderline
   eligibility gate with 24h Redis cache, 0 Gemini calls on unmistakably qualified applicants, semantic rescue).
3. Non-redundant email notifications (Redis cross-worker atomic SET NX EX dedup, cross-email event suppression,
   PII-free 7-day Redis-cached Gemini email polishing shared across candidates, forbidden score leak guard,
   HR message & notes deduplication).
"""
import json
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.extractors.resume_processor import process_resume
from app.extractors.resume_validator import validate_resume_file_bytes
from app.models.job_description import JobDescription, JobType
from app.services import email_service, gemini_service
from app.services.job_matching_service import calculate_match_score
from app.utils.gemini_client import GeminiResponse


class _FakeRedis:
    """Minimal in-memory Redis stand-in verifying atomic SET NX EX, SETEX, GET, and EXISTS."""

    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key: str):
        val = self.store.get(key)
        return val.encode("utf-8") if isinstance(val, str) else val

    def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value
        return True

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def incr(self, key: str) -> int:
        val = int(self.store.get(key, "0")) + 1
        self.store[key] = str(val)
        return val

    def expire(self, key: str, ttl: int) -> bool:
        return True


def _make_gemini_response(payload: dict, model: str = "gemini-2.5-flash-lite") -> GeminiResponse:
    return GeminiResponse(
        text=json.dumps(payload),
        model=model,
        key_label="primary",
        attempts=1,
        rotations=0,
        latency_ms=42.0,
        usage={"promptTokenCount": 210, "candidatesTokenCount": 65, "totalTokenCount": 275},
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. WRONG-DOCUMENT AI PREDICTION + REDIS SHA-256 CACHE
# ═════════════════════════════════════════════════════════════════════════════


def test_gemini_wrong_doc_specific_predicted_label_and_cache(tmp_path, monkeypatch):
    """Generic/tricky non-resume gets an exact AI-predicted label + 0 calls on repeat upload via cache."""
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_EXTRACTION_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_RESUME_VERIFY_MODE", "smart")

    flyer = tmp_path / "clinic_note.txt"
    flyer.write_text(
        "ST. LUKE COMMUNITY CLINIC - BATANGAS\n"
        "PATIENT VISIT SUMMARY & REST RECOMMENDATION\n"
        "Patient Name: Juan Dela Cruz\n"
        "Visit Date: November 20, 2026\n"
        "Findings: Mild seasonal influenza, advised 3 days home rest and hydration.\n"
        "Prescribed Medication: Paracetamol 500mg every 6 hours as needed.\n"
        "Attending Physician: Dr. Maria Santos, MD (License No. 0123456)\n",
        encoding="utf-8",
    )

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _make_gemini_response(
        {
            "is_resume": False,
            "document_type": "misc_non_resume",
            "predicted_label": "Medical Certificate",
            "confidence": 0.96,
            "reason": "Contains patient clinical findings, medication, and physician sign-off rather than employment or education history.",
        }
    )

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        res1 = process_resume(str(flyer), "txt")
        res2 = process_resume(str(flyer), "txt")

    assert res1["is_valid_resume"] is False
    val1 = res1["resume_validation"]
    assert val1["verified_by"] == "gemini"
    assert val1["predicted_document_label"] == "Medical Certificate"
    assert "Wrong document detected (AI Predicted: Medical Certificate)" in val1["message"]
    assert "Reason:" in val1["message"]

    # Second upload of identical file must hit cache (0 additional Gemini API calls)
    assert res2["is_valid_resume"] is False
    assert res2["resume_validation"]["gemini_cached"] is True
    assert mock_client.generate_content.call_count == 1
    call_kwargs = mock_client.generate_content.call_args.kwargs
    assert call_kwargs["thinking_budget"] == 0
    assert call_kwargs["models"][0] == "gemini-2.5-flash-lite"


def test_image_upload_wrong_document_invokes_gemini_prediction(monkeypatch):
    """Uploaded image scans (.png/.jpg) now pass through Gemini wrong-document prediction too."""
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_EXTRACTION_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")

    ocr_text = (
        "MARIWASA TOWN FIESTA CONCERT 2026\n"
        "Join us this Saturday at 7:00 PM at the Town Plaza!\n"
        "Featuring local bands, food stalls, fireworks, and community raffle.\n"
        "Free admission for all Sto. Tomas residents. Gates open at 5:30 PM.\n"
    )

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _make_gemini_response(
        {
            "is_resume": False,
            "document_type": "misc_non_resume",
            "predicted_label": "Event Poster / Flyer",
            "confidence": 0.95,
            "reason": "Promotional event announcement poster with no personal work history or qualifications.",
        }
    )

    with patch("app.extractors.resume_validator.extract_text_from_image_file", return_value=ocr_text), \
         patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        is_resume, val = validate_resume_file_bytes(b"\x89PNG\r\n\x1a\nfake", "poster.png")

    assert is_resume is False
    assert val["verified_by"] == "gemini"
    assert "Wrong document detected (AI Predicted: Event Poster / Flyer)" in val["message"]
    assert mock_client.generate_content.call_count == 1


# ═════════════════════════════════════════════════════════════════════════════
# 2. BELOW-ACCEPTED-REQUIREMENTS BLOCKER + GEMINI ELIGIBILITY GATE
# ═════════════════════════════════════════════════════════════════════════════


def test_padded_unrelated_applicant_blocked_and_qualified_skips_gemini():
    """
    1. An unrelated applicant whose raw score is padded by 'Not required' certs + completeness
       is blocked deterministically instead of sneaking past 30%.
    2. An unmistakably qualified applicant skips Gemini eligibility check completely (0 tokens).
    """
    job = JobDescription(
        job_id="JOB-CERAMIC-01",
        job_title="Ceramic Process Engineer",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Lead kiln firing optimization, glaze formulation, ISO 9001 SPC, and ceramic defect analysis.",
        skills_requirements="Ceramic Processing, Glaze Formulation, ISO 9001, Quality Control, Kiln Operations",
        experience_requirements="3+ years in ceramic manufacturing or process engineering",
        education_requirements="Bachelor's Degree in Chemical Engineering",
        certifications_requirements="",  # Not required -> awards 100% (10% weight padding!)
        is_active=True,
    )

    padded_unrelated = calculate_match_score(
        {
            "fullname": "Barista Applicant",
            "email": "barista@example.com",
            "phone": "09171234567",
            "location": "Sto. Tomas, Batangas",
            "skills_list": ["Customer Service", "Espresso Making", "Quality Control"],  # 1/5 = 20%
            "skills": "Customer Service, Espresso Making, Quality Control",
            "experience": "2 years Barista and Cashier at Coffee Shop",
            "education": "High School Diploma",
            "degree": "High School Diploma",
            "years_experience": 2,
        },
        job,
        matching_config={"minimum_match_score": 30.0},
        log_prediction=False,
    )
    assert padded_unrelated["eligible_to_apply"] is False
    assert len(padded_unrelated["eligibility_reasons"]) >= 1

    strong_qualified = calculate_match_score(
        {
            "fullname": "Engr. Maria Clara",
            "email": "maria@example.com",
            "phone": "09179998888",
            "location": "Sto. Tomas, Batangas",
            "skills_list": ["Ceramic Processing", "Glaze Formulation", "ISO 9001", "Quality Control", "Kiln Operations"],
            "skills": "Ceramic Processing, Glaze Formulation, ISO 9001, Quality Control, Kiln Operations",
            "experience": "5 years Ceramic Process Engineer managing kiln operations and glaze formulation",
            "education": "Bachelor of Science in Chemical Engineering - Batangas State University",
            "degree": "Bachelor of Science in Chemical Engineering",
            "years_experience": 5,
        },
        job,
        matching_config={"minimum_match_score": 30.0},
        log_prediction=False,
    )
    assert strong_qualified["eligible_to_apply"] is True
    should_call, reason = gemini_service.should_invoke_gemini_for_eligibility(strong_qualified)
    assert should_call is False
    assert reason == "unmistakably_qualified"


@pytest.mark.asyncio
async def test_application_endpoint_gemini_eligibility_blocks_suspect_and_caches(client, db_session, monkeypatch):
    """Borderline/suspect applicant gets verified by cached Flash-Lite; repeat check uses 0 extra calls."""
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_MATCH_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")

    job = JobDescription(
        job_id="JOB-AI-GATE",
        job_title="Senior Industrial Automation Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Design Siemens PLC ladder logic, SCADA systems, and factory robotics automation.",
        skills_requirements="PLC Programming, SCADA, Siemens, Robotics, AutoCAD",
        experience_requirements="3 years",
        education_requirements="Bachelor's Degree in Electrical Engineering",
        certifications_requirements="",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _make_gemini_response(
        {
            "eligible": False,
            "confidence": 0.91,
            "summary": "Applicant lacks PLC/SCADA engineering experience required for this senior role.",
            "blocking_reasons": [
                "Background is focused on retail sales rather than industrial PLC/SCADA engineering."
            ],
            "improvement_tips": [
                "Complete PLC & SCADA certification or consider entry-level operations roles."
            ],
        }
    )

    payload = {
        "job_id": "JOB-AI-GATE",
        "candidate_name": "Borderline Candidate",
        "candidate_email": "borderline@example.com",
        "skills": ["AutoCAD", "Sales", "Customer Support", "Excel"],
        "years_experience": 3,
        "job_title": "Retail Store Supervisor",
        "company": "Mall Shop Inc.",
        "degree": "Bachelor of Science in Business Administration",
    }

    with patch("app.tasks.analyze_application_task.delay"), \
         patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        r1 = await client.post("/applications/", json=payload)
        r2 = await client.post("/applications/", json=payload)

    assert r1.status_code == 400
    assert "below accepted requirements" in r1.json()["detail"].lower()
    assert "plc/scada" in r1.json()["detail"].lower()
    assert r2.status_code == 400
    # Second identical attempt hits SHA-256 cache -> 1 single Gemini call total!
    assert mock_client.generate_content.call_count == 1


# ═════════════════════════════════════════════════════════════════════════════
# 3. NON-REDUNDANT EMAILS + REDIS DEDUP + PII-FREE GEMINI EMAIL POLISH
# ═════════════════════════════════════════════════════════════════════════════


def test_redis_cross_worker_dedup_blocks_duplicate_across_workers(monkeypatch):
    """Simulates 2 separate workers (cleared in-process dict) sharing Redis SET NX EX dedup."""
    monkeypatch.setenv("EMAIL_REDIS_DEDUP_IN_TESTS", "true")
    fake_redis = _FakeRedis()

    with patch("app.utils.redis_client.get_sync_redis", return_value=fake_redis):
        email_service._RECENT_EMAIL_DEDUP.clear()
        first = email_service._is_duplicate_recent_email(
            "worker@example.com", "Application Status Update: Engineer", "application_status_update"
        )
        # Simulate another Uvicorn/Celery worker with an empty local dict
        email_service._RECENT_EMAIL_DEDUP.clear()
        second = email_service._is_duplicate_recent_email(
            "worker@example.com", "Application Status Update: Engineer", "application_status_update"
        )

    assert first is False
    assert second is True


@pytest.mark.asyncio
async def test_interview_invite_suppresses_redundant_back_to_back_status_email(monkeypatch):
    """Sending an interview invite immediately suppresses an overlapping generic INTERVIEW SCHEDULED status email."""
    monkeypatch.setenv("EMAIL_REDIS_DEDUP_IN_TESTS", "true")
    fake_redis = _FakeRedis()
    email_service._RECENT_EMAIL_DEDUP.clear()
    email_service._RECENT_EMAIL_EVENTS.clear()
    sent = []

    def capture_smtp(to_email, subject, html_body, attachments=None):
        sent.append({"to": to_email, "subject": subject, "body": html_body})
        return True

    with patch("app.utils.redis_client.get_sync_redis", return_value=fake_redis), \
         patch("app.services.email_service._send_smtp_sync", side_effect=capture_smtp):
        await email_service.send_interview_invitation_email(
            to_email="candidate.dedup@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Process Engineer",
            interview_title="Initial Interview",
            start_time=datetime(2026, 12, 10, 9, 0),
            end_time=datetime(2026, 12, 10, 10, 0),
            meeting_link="https://meet.google.com/xyz-abcd-efg",
            notes="Bring portfolio",
            custom_message="We scheduled your interview. Note: Bring portfolio.",
        )
        await email_service.send_application_status_update_email(
            to_email="candidate.dedup@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Process Engineer",
            new_status="INTERVIEW SCHEDULED",
        )

    # Only the detailed interview invite is dispatched; the redundant status email is suppressed!
    assert len(sent) == 1
    # And notes already inside custom_message must NOT render a duplicate Agenda / Notes box
    assert sent[0]["body"].count("Bring portfolio") == 1


@pytest.mark.asyncio
async def test_gemini_email_polish_shares_single_pii_free_cache_across_candidates(monkeypatch):
    """3 different applicants for the same job + status reuse ONE cached Gemini Flash-Lite call (0 extra calls)."""
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_EMAIL_POLISH_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")
    sent = []

    def capture_smtp(to_email, subject, html_body, attachments=None):
        sent.append({"to": to_email, "subject": subject, "body": html_body})
        return True

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    mock_client.generate_content.return_value = _make_gemini_response(
        {
            "intro": "Thank you for applying for Process Engineer. Our hiring team is now reviewing your qualifications.",
            "next_steps": [
                "We will notify you by email and portal if you advance to interviews.",
                "Track live progress anytime in your candidate dashboard.",
            ],
            "include_notes_box": False,
        }
    )

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client), \
         patch("app.services.email_service._send_smtp_sync", side_effect=capture_smtp):
        for email_addr, full_name in [
            ("juan@example.com", "Juan Dela Cruz"),
            ("maria@example.com", "Maria Clara"),
            ("jose@example.com", "Jose Rizal"),
        ]:
            await email_service.send_application_status_update_email(
                to_email=email_addr,
                candidate_name=full_name,
                job_title="Process Engineer",
                new_status="REVIEWED",
            )

    assert len(sent) == 3
    assert mock_client.generate_content.call_count == 1  # 1 Gemini call served all 3 candidates!
    assert "Juan Dela Cruz" in sent[0]["body"]
    assert "Maria Clara" in sent[1]["body"]
    assert "Jose Rizal" in sent[2]["body"]
    for item in sent:
        assert item["body"].count("Mariwasa Siam Ceramics") <= 2
        visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", item["body"])).strip()
        assert len(visible) < 1200


@pytest.mark.asyncio
async def test_gemini_not_selected_email_discards_forbidden_score_leak_and_hr_msg_clean(monkeypatch):
    """Not Selected emails discard Gemini output if it ever leaks scores/weights; HR messages avoid 4x company spam."""
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_EMAIL_POLISH_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")
    sent = []

    def capture_smtp(to_email, subject, html_body, attachments=None):
        sent.append({"to": to_email, "subject": subject, "body": html_body})
        return True

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash-lite"]
    mock_client.generate_content.return_value = _make_gemini_response(
        {
            "intro": "Your match score of 22% with skills weight 40% did not meet our cutoff.",
            "next_steps": ["Apply again later."],
            "include_notes_box": False,
        }
    )

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client), \
         patch("app.services.email_service._send_smtp_sync", side_effect=capture_smtp):
        await email_service.send_application_status_update_email(
            to_email="notselected@example.com",
            candidate_name="Ana Reyes",
            job_title="Quality Engineer",
            new_status="REJECTED",
        )
        await email_service.send_hr_message_notification_email(
            to_email="msg@example.com",
            candidate_name="Ana Reyes",
            sender_name="HR Recruiter",
            message_type="follow_up",
            content="Please confirm your preferred interview date.",
            job_title="Quality Engineer",
        )

    assert len(sent) == 2
    # Rejected email discarded the leaking Gemini text and kept clean deterministic copy
    rej_body = sent[0]["body"]
    rej_visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", rej_body)).strip().lower()
    assert "match score" not in rej_visible
    assert "weight" not in rej_visible
    assert "22%" not in rej_visible
    # HR message email no longer repeats "Mariwasa Siam Ceramics" 4 times
    hr_body = sent[1]["body"]
    assert hr_body.count("Mariwasa Siam Ceramics") <= 2
