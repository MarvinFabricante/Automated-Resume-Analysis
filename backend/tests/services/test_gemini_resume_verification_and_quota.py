"""
Tests for Quota-Efficient Gemini Resume Verification, Semantic Extraction Enhancement,
and Cross-Operation Caching / Budget Guard Strategy.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import fitz
import pytest

from app.extractors.resume_processor import process_resume
from app.services import gemini_service
from app.utils.gemini_client import GeminiAllKeysExhaustedError, GeminiResponse


def _write_pdf(text: str, pages: int = 1) -> str:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text if i == 0 else f"Page {i + 1}\n{text}")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(doc.tobytes())
    tmp.close()
    doc.close()
    return tmp.name


def _fake_gemini_response(payload: dict, model: str = "gemini-2.5-flash-lite", key_label: str = "primary") -> GeminiResponse:
    return GeminiResponse(
        text=json.dumps(payload),
        model=model,
        key_label=key_label,
        attempts=1,
        rotations=0,
        latency_ms=42.0,
        finish_reason="STOP",
        usage={"promptTokenCount": 420, "candidatesTokenCount": 140, "totalTokenCount": 560},
    )


@pytest.fixture(autouse=True)
def _reset_gemini_service_cache(monkeypatch):
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_EXTRACTION_ALLOW_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_RESUME_VERIFY_MODE", "smart")
    monkeypatch.setenv("GEMINI_DAILY_EXTRACTION_BUDGET", "150")
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "0")
    yield
    gemini_service.clear_gemini_service_cache()


def test_obvious_thesis_manuscript_uses_zero_gemini_api_calls():
    """
    Quota Strategy Pillar 1: Unmistakable non-resumes (Thesis Manuscripts, Manuals, Invoices, etc.)
    must be rejected locally with ZERO Gemini API calls.
    """
    thesis_path = _write_pdf(
        """
        BATANGAS STATE UNIVERSITY
        SMART INVENTORY SYSTEM
        A Thesis Manuscript
        In Partial Fulfillment of the Requirements for the Degree Bachelor of Science in Information Technology

        CHAPTER 1: THE PROBLEM AND ITS BACKGROUND
        Statement of the Problem
        Scope and Delimitation
        CHAPTER 2: REVIEW OF RELATED LITERATURE
        APPENDIX A: CURRICULUM VITAE OF THE RESEARCHERS
        EDUCATION
        SKILLS
        WORK EXPERIENCE
        """
    )
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}

    try:
        with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
            result = process_resume(thesis_path, "pdf")
    finally:
        os.unlink(thesis_path)

    assert result["is_valid_resume"] is False
    assert result["resume_validation"]["reason_code"] == "detected_thesis_manuscript"
    assert mock_client.generate_content.call_count == 0, "Obvious thesis must consume 0 Gemini calls"
    status = gemini_service.get_gemini_status()
    assert status["optimization"]["local_prefilter_skips"] >= 1


def test_valid_resume_verified_and_enhanced_in_single_cached_flash_lite_call():
    """
    Quota Strategy Pillars 2, 3, 4:
    - 1st upload makes ONE combined Flash-Lite call (thinking_budget=0) to verify + enrich.
    - Enriches ai_summary, career_domain, seniority_level, ai_inferred_skills, and skills_list.
    - 2nd upload of the exact same resume hits SHA-256 cache -> 0 additional Gemini calls!
    """
    resume_path = _write_pdf(
        """
        ELENA MARIE TORRES
        elena.torres@gmail.com | 0917-555-8899 | Sta. Rosa, Laguna

        WORK EXPERIENCE
        Production Supervisor | Laguna Tile Corp. | Jan 2021 - Present
        - Led 25 kiln and press line operators to meet daily ceramic tile output targets.
        - Implemented root cause analysis to reduce defective tile scrap by 18%.

        EDUCATION
        Bachelor of Science in Industrial Engineering
        Batangas State University | 2016 - 2020

        SKILLS
        Lean Manufacturing, Quality Control, Microsoft Excel
        """
    )
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _fake_gemini_response(
        {
            "is_resume": True,
            "document_type": "resume",
            "confidence": 0.97,
            "reason": "Structured candidate resume with industrial engineering education and production leadership experience.",
            "ai_summary": "Industrial Engineering graduate with 5+ years supervising ceramic tile manufacturing lines and driving defect reduction.",
            "inferred_skills": ["Root Cause Analysis", "Production Scheduling", "Team Leadership", "ISO 9001"],
            "career_domain": "Ceramic Manufacturing Operations",
            "seniority_level": "Mid-Level",
            "corrected_fullname": "",
            "corrected_job_title": "",
            "corrected_degree": "",
        }
    )

    try:
        with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
            first = process_resume(resume_path, "pdf")
            second = process_resume(resume_path, "pdf")
    finally:
        os.unlink(resume_path)

    # First upload: 1 live call using Flash-Lite first with thinking_budget=0
    assert first["is_valid_resume"] is True
    assert first["resume_validation"]["verified_by"] == "local+gemini"
    assert first["ai_extraction_enhanced"] is True
    assert first["career_domain"] == "Ceramic Manufacturing Operations"
    assert first["seniority_level"] == "Mid-Level"
    assert "ceramic tile manufacturing" in first["ai_summary"].lower()
    assert "Root Cause Analysis" in first["skills_list"]
    assert "Team Leadership" in first["ai_inferred_skills"]

    assert mock_client.generate_content.call_count == 1, "Second identical upload must be a 0-call cache hit"
    call_kwargs = mock_client.generate_content.call_args.kwargs
    assert call_kwargs["models"][0] == "gemini-2.5-flash-lite"
    assert call_kwargs["thinking_budget"] == 0
    assert call_kwargs["max_output_tokens"] <= 512

    # Second upload: served from cache with identical enhancements
    assert second["is_valid_resume"] is True
    assert second["ai_extraction_cached"] is True
    assert second["career_domain"] == "Ceramic Manufacturing Operations"
    assert gemini_service.get_gemini_status()["optimization"]["cache_hits"] >= 1


def test_gemini_catches_tricky_disguised_non_resume_that_passed_local_heuristics():
    """
    When a subtly crafted non-resume somehow sneaks past local heuristics, Gemini's semantic
    verification rejects it cleanly.
    """
    tricky_path = _write_pdf(
        """
        MARCO SANTOS
        marco.santos@gmail.com | 0917-222-3333 | Manila

        EDUCATION
        Bachelor of Science in Computer Science, University of the Philippines (2020 - 2024)

        EXPERIENCE
        Software Engineer | Acme Systems Inc. | 2024 - Present
        - Built internal prototypes for an example fictional persona used in UX wireframes.

        SKILLS
        Python, SQL, React
        """
    )
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _fake_gemini_response(
        {
            "is_resume": False,
            "document_type": "academic_paper",
            "confidence": 0.93,
            "reason": "This is a fictional UX persona / academic case-study snippet, not a real candidate resume.",
            "ai_summary": "",
            "inferred_skills": [],
            "career_domain": "",
            "seniority_level": "",
            "corrected_fullname": "",
            "corrected_job_title": "",
            "corrected_degree": "",
        }
    )

    try:
        with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
            result = process_resume(tricky_path, "pdf")
    finally:
        os.unlink(tricky_path)

    assert result["is_valid_resume"] is False
    assert result["resume_validation"]["verified_by"] == "gemini"
    assert result["resume_validation"]["detected_document_type"] == "academic_paper"
    assert "resume" in result["resume_validation"]["message"].lower()


def test_daily_budget_auto_downgrades_and_caps_extraction_calls(monkeypatch):
    """
    Quota Strategy Pillar 5:
    - At >= 70% of GEMINI_DAILY_EXTRACTION_BUDGET, 'smart' auto-downgrades to 'borderline'
      so high-confidence complete local resumes skip Gemini and preserve quota for HR matching.
    - At 100% budget, extraction skips Gemini completely and degrades cleanly to local validation.
    """
    monkeypatch.setenv("GEMINI_DAILY_EXTRACTION_BUDGET", "10")
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        # Simulate 7 calls already used (70% threshold) -> effective mode downgrades to 'borderline'
        for _ in range(7):
            gemini_service._increment_daily_extraction_count()
        assert gemini_service._effective_verify_mode() == "borderline"

        high_conf_local = {
            "is_resume": True,
            "confidence": 0.96,
            "reason_code": "valid_resume",
            "negative_score": 0.0,
            "metrics": {"core_headings": ["EDUCATION", "EXPERIENCE", "SKILLS"], "pillar_count": 4},
        }
        complete_data = {
            "fullname": "Juan Dela Cruz",
            "summary": "Experienced plant supervisor.",
            "skills_list": ["Lean Manufacturing", "ISO 9001", "Excel"],
            "is_incomplete": False,
        }
        should_call_high, reason_high = gemini_service.should_invoke_gemini_for_resume(high_conf_local, complete_data)
        assert should_call_high is False
        assert reason_high == "high_confidence_local_skip_in_borderline_mode"

        # Borderline doc STILL gets verified while under 100% cap
        borderline_local = {
            "is_resume": True,
            "confidence": 0.72,
            "reason_code": "valid_resume",
            "negative_score": 2.0,
            "metrics": {"core_headings": [], "pillar_count": 2},
        }
        should_call_border, _ = gemini_service.should_invoke_gemini_for_resume(borderline_local, complete_data)
        assert should_call_border is True

        # Reach 100% budget (10/10) -> skips cleanly
        for _ in range(3):
            gemini_service._increment_daily_extraction_count()
        assert gemini_service._effective_verify_mode() == "off"
        should_call_capped, reason_capped = gemini_service.should_invoke_gemini_for_resume(borderline_local, complete_data)
        assert should_call_capped is False
        assert reason_capped == "daily_budget_or_pool_exhausted"


def test_graceful_fallback_when_all_gemini_keys_exhausted():
    """When all Gemini keys are exhausted, valid resumes still succeed locally without errors."""
    resume_path = _write_pdf(
        """
        CARLO MENDOZA
        carlo.mendoza@gmail.com | 0917-444-5555 | Lipa City, Batangas

        WORK EXPERIENCE
        Maintenance Technician | Batangas Ceramics Inc. | 2020 - Present
        - Performed preventive maintenance on hydraulic presses and PLC control panels.

        EDUCATION
        BS Mechanical Engineering | Batangas State University | 2015 - 2019

        SKILLS
        PLC Troubleshooting, Preventive Maintenance, Welding, AutoCAD
        """
    )
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.side_effect = GeminiAllKeysExhaustedError("All keys in cooldown")

    try:
        with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
            result = process_resume(resume_path, "pdf")
    finally:
        os.unlink(resume_path)

    assert result["is_valid_resume"] is True
    assert result["fullname"] == "Carlo Mendoza"
    assert result["resume_validation"]["gemini_decision"] == "fallback_local_unavailable"


def test_match_analysis_and_comparison_content_hash_caching_saves_api_calls():
    """Duplicate match analysis and candidate comparison calls hit SHA-256 cache -> 0 extra API calls."""
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}

    match_payload = {
        "ai_match_score": 88.0,
        "match_level": "High Match",
        "skills_score": 90.0,
        "skills_explanation": "Strong match.",
        "experience_score": 85.0,
        "experience_explanation": "Relevant tenure.",
        "relevance_level": "Highly Relevant",
        "transferable_skills": ["Lean"],
        "education_score": 95.0,
        "education_explanation": "Matches degree.",
        "certifications_score": 100.0,
        "certification_explanation": "None required.",
        "strengths": ["Manufacturing leadership"],
        "weaknesses": [],
        "ai_summary": "Strong candidate.",
        "matched_skills": ["Quality Control"],
        "missing_skills": [],
        "recommendations": ["Interview"],
    }
    comp_payload = {
        "rankings": [
            {"rank": 1, "candidate_name": "Elena Torres", "match_score": 88.0, "reasoning": "Best fit."}
        ],
        "overall_summary": "Elena leads.",
        "comparative_insights": ["Strong leadership."],
    }

    resume_data = {
        "fullname": "Elena Torres",
        "career_domain": "Ceramic Manufacturing Operations",
        "seniority_level": "Mid-Level",
        "ai_summary": "Industrial Engineer with 5+ years supervising ceramic lines.",
        "skills": "Quality Control, Lean Manufacturing",
        "years_experience": 5,
    }
    job_data = {"job_title": "Production Supervisor", "skills_requirements": "Quality Control, Lean Manufacturing"}

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        mock_client.generate_content.return_value = _fake_gemini_response(match_payload, model="gemini-2.5-flash")
        m1 = gemini_service.gemini_analyze_match(resume_data, job_data)
        m2 = gemini_service.gemini_analyze_match(resume_data, job_data)
        assert m1 is not None and m2 is not None
        assert m1["ai_match_score"] == m2["ai_match_score"] == 88.0
        assert mock_client.generate_content.call_count == 1
        # Verify enhanced resume context (domain, seniority, summary) flowed into the match prompt
        sent_prompt = mock_client.generate_content.call_args.args[0]
        assert "Ceramic Manufacturing Operations | Mid-Level" in sent_prompt
        assert "5+ years supervising ceramic lines" in sent_prompt
        assert mock_client.generate_content.call_args.kwargs["thinking_budget"] == 0

        mock_client.generate_content.return_value = _fake_gemini_response(comp_payload, model="gemini-2.5-flash")
        c1 = gemini_service.gemini_compare_candidates(job_data, [resume_data])
        c2 = gemini_service.gemini_compare_candidates(job_data, [resume_data])
        assert c1 is not None and c2 is not None
        assert mock_client.generate_content.call_count == 2  # +1 for compare, 2nd compare was cached!
