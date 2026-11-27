"""
Comprehensive tests for Grounded Hybrid NLP + Gemini AI Job Matching, Explainability,
and Token-Efficient Quota Strategy:
1. NLP baseline evidence is passed into Gemini so Gemini never flies blind.
2. Strict ATS guardrails are preserved during hybrid fusion (applicant 'No' denials,
   NOT_REQUIRED categories, unrelated experience caps, semantic skill recovery).
3. Multi-job smart matching uses ONE batched Flash-Lite call for Top-K shortlisted jobs
   instead of N per-job calls, with SHA-256 caching and token/call-savings telemetry.
4. Daily match budget cap and degraded pool pressure gracefully preserve quota for
   submitted applications while falling back transparently to NLP.
5. Deterministic `why_this_score` explanations work even when Gemini is disabled.
6. Applicant matching endpoint hides numeric weights/formulas while surfacing plain-language
   `why_this_score` reasoning.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.models.job_description import JobDescription, JobType
from app.services import ai_analysis_service, gemini_service, job_matching_service
from app.utils.gemini_client import GeminiResponse


def _fake_response(payload: dict, model: str = "gemini-2.5-flash-lite", total_tokens: int = 720) -> GeminiResponse:
    return GeminiResponse(
        text=json.dumps(payload),
        model=model,
        key_label="primary",
        attempts=1,
        rotations=0,
        latency_ms=55.0,
        finish_reason="STOP",
        usage={
            "promptTokenCount": int(total_tokens * 0.65),
            "candidatesTokenCount": int(total_tokens * 0.35),
            "totalTokenCount": total_tokens,
        },
    )


@pytest.fixture(autouse=True)
def _reset_cache_and_env(monkeypatch):
    gemini_service.clear_gemini_service_cache()
    monkeypatch.setenv("GEMINI_CACHE_IN_TESTS", "true")
    monkeypatch.setenv("GEMINI_MATCH_MODE", "smart")
    monkeypatch.setenv("GEMINI_DAILY_MATCH_BUDGET", "200")
    monkeypatch.setenv("GEMINI_SMART_MATCH_TOP_K", "3")
    monkeypatch.setenv("GEMINI_SMART_MATCH_MIN_SCORE", "20.0")
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "0")
    yield
    gemini_service.clear_gemini_service_cache()


def test_grounded_hybrid_match_passes_nlp_audit_and_enforces_guardrails():
    """
    - Deterministic NLP audit (scores, statuses, weights, denied requirements) flows into Gemini prompt.
    - Semantic matched skills from Gemini are recovered, EXCEPT explicitly applicant-denied 'No' skills.
    - NOT_REQUIRED categories remain unpenalized and why_this_score explains the result clearly.
    """
    resume_data = {
        "fullname": "Carlo Mendoza",
        "skills": "PostgreSQL, Python, REST APIs",
        "experience": "Backend Software Engineer at TechCorp (3 years) - Built FastAPI REST services and PostgreSQL databases.",
        "years_experience": 3,
        "highest_degree": "Bachelor of Science in Computer Science",
        "education": "Bachelor of Science in Computer Science",
        "clarification_responses": [
            {"field": "skills", "requirement": "Kubernetes", "answer": "no"},
        ],
    }
    job_data = {
        "job_title": "Backend Engineer",
        "department": "Engineering",
        "description": "Build Python web APIs with Relational Databases and Kubernetes.",
        "skills_requirements": "Python, FastAPI, Relational Databases, Kubernetes",
        "experience_requirements": "2 years",
        "education_requirements": "Bachelor's Degree",
        "certifications_requirements": "None",
    }

    gemini_payload = {
        "ai_match_score": 84.0,
        "match_level": "High Match",
        "skills_score": 80.0,
        "skills_explanation": "Matched Python and FastAPI; PostgreSQL semantically satisfies Relational Databases, while Kubernetes is missing.",
        "experience_score": 90.0,
        "experience_explanation": "3 years of direct backend engineering exceeds the 2-year requirement.",
        "relevance_level": "Highly Relevant",
        "transferable_skills": ["System Design"],
        "education_score": 100.0,
        "education_explanation": "BS Computer Science fulfills the Bachelor's degree requirement.",
        "certifications_score": 10.0,  # Should be ignored because Certifications is Not required!
        "certification_explanation": "No certification is required for this role.",
        "why_this_score": [
            "Strong technical overlap: Python, FastAPI, and PostgreSQL (Relational Databases).",
            "3 years of directly relevant backend engineering exceeds the 2-year minimum.",
            "Score held below 95% because Kubernetes was confirmed absent.",
        ],
        "strengths": ["Direct Python/FastAPI backend experience"],
        "weaknesses": ["No Kubernetes experience"],
        "ai_summary": "Strong backend fit with relevant Python/FastAPI/PostgreSQL experience; missing only Kubernetes.",
        "matched_skills": ["Python", "FastAPI", "Kubernetes"],  # Kubernetes MUST be blocked because applicant answered No!
        "semantic_matched_skills": ["Relational Databases"],
        "missing_skills": ["Kubernetes"],
        "recommendations": ["Explore candidate's container deployment familiarity during interview."],
    }

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _fake_response(gemini_payload, model="gemini-2.5-flash", total_tokens=810)

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        result = ai_analysis_service.analyze_match_with_fallback(
            resume_data,
            job_data,
            matching_config={"weights": dict(job_matching_service.THESIS_DEFAULT_WEIGHTS), "thresholds": {}},
        )

    assert result is not None
    assert result["ai_powered"] is True
    assert result["model_used"] == "gemini"
    assert len(result["why_this_score"]) == 3
    assert "kubernetes" not in [s.lower() for s in result["matched_skills"]], "Denied 'No' skill must never be matched"
    assert "relational databases" in [s.lower() for s in result["matched_skills"]], "Semantic skill match should be recovered"
    assert result["ai_certifications_score"] == 100.0, "NOT_REQUIRED category must not be downgraded by Gemini"
    assert "Hybrid ATS Rules (60%) + Gemini Semantic AI (40%)" in result["score_explanation"]

    # Confirm NLP grounding evidence was passed into the prompt
    sent_prompt = mock_client.generate_content.call_args.args[0]
    assert "DETERMINISTIC NLP/ATS AUDIT" in sent_prompt
    assert "Applicant Confirmed NO" in sent_prompt
    assert mock_client.generate_content.call_args.kwargs["max_output_tokens"] <= 900
    assert mock_client.generate_content.call_args.kwargs["thinking_budget"] == 0

    # Token telemetry recorded
    opt = gemini_service.get_gemini_status()["optimization"]
    assert opt["total_tokens_total"] == 810
    assert opt["daily_match_used"] == 1


@pytest.mark.asyncio
async def test_multi_job_smart_match_uses_single_batched_flash_lite_call_for_top_k(db_session, monkeypatch):
    """
    With 5 active jobs, match_resume_to_all_jobs(..., use_ai=True) MUST make ONLY ONE
    batched Gemini Flash-Lite API call for the Top-3 shortlisted jobs (saving 2+ calls),
    and a repeat call must hit SHA-256 cache with 0 additional API calls!
    """
    monkeypatch.setenv("GEMINI_MATCH_ALLOW_IN_TESTS", "true")

    jobs = [
        JobDescription(
            job_id=f"HYB-JOB-{i}",
            job_title=title,
            department=dept,
            job_type=JobType.FULL_TIME,
            location="Sto. Tomas, Batangas",
            description=desc,
            skills_requirements=skills,
            experience_requirements="2 years",
            education_requirements="Bachelor's Degree",
            is_active=True,
        )
        for i, (title, dept, desc, skills) in enumerate(
            [
                ("Process Automation Engineer", "Engineering", "Python FastAPI kiln automation and SQL.", "Python, FastAPI, SQL, Quality Control"),
                ("Backend Systems Developer", "IT", "Develop Python APIs and PostgreSQL services.", "Python, PostgreSQL, REST API"),
                ("Plant Quality Engineer", "QA", "Manage ISO 9001 quality control and SQL reporting.", "Quality Control, SQL, ISO 9001"),
                ("Senior Chef", "Cafeteria", "Prepare meals and kitchen inventory.", "Cooking, Baking, Food Safety"),
                ("Corporate Lawyer", "Legal", "Draft contracts and handle litigation.", "Litigation, Corporate Law, Bar License"),
            ],
            start=1,
        )
    ]
    db_session.add_all(jobs)
    await db_session.commit()

    resume_data = {
        "fullname": "Elena Torres",
        "skills": "Python, FastAPI, PostgreSQL, SQL, Quality Control",
        "experience": "Process Automation Engineer at Ceramics Plant (3 years) - Built Python FastAPI telemetry and SQL quality control dashboards.",
        "years_experience": 3,
        "highest_degree": "Bachelor of Science in Industrial Engineering",
        "education": "Bachelor of Science in Industrial Engineering",
    }

    batch_payload = {
        "matches": [
            {
                "job_id": "HYB-JOB-1",
                "ai_match_score": 93.0,
                "skills_score": 95.0,
                "experience_score": 92.0,
                "education_score": 100.0,
                "certifications_score": 100.0,
                "relevance_level": "Highly Relevant",
                "semantic_matched_skills": [],
                "transferable_skills": ["Lean Process Improvement"],
                "why_this_score": [
                    "Matched all 4 core skills (Python, FastAPI, SQL, Quality Control).",
                    "3 years of ceramic plant automation directly aligns with this role.",
                ],
                "ai_summary": "Top fit: direct ceramic plant automation and Python/FastAPI stack alignment.",
                "skills_explanation": "All required technical and QA skills are confirmed on the resume.",
                "experience_explanation": "3 years of relevant process automation exceeds the 2-year requirement.",
                "education_explanation": "BS Industrial Engineering satisfies the Bachelor's degree requirement.",
                "certification_explanation": "No mandatory certification required.",
                "strengths": ["Direct ceramic manufacturing automation background"],
                "weaknesses": [],
                "recommendations": ["Highlight kiln telemetry metrics in your interview."],
            },
            {
                "job_id": "HYB-JOB-2",
                "ai_match_score": 85.0,
                "skills_score": 88.0,
                "experience_score": 82.0,
                "education_score": 90.0,
                "certifications_score": 100.0,
                "relevance_level": "Highly Relevant",
                "semantic_matched_skills": ["REST API"],
                "transferable_skills": [],
                "why_this_score": [
                    "Strong Python and PostgreSQL alignment; FastAPI satisfies REST API.",
                    "3 years backend telemetry development supports this role.",
                ],
                "ai_summary": "Strong backend fit with Python, PostgreSQL, and FastAPI REST API experience.",
                "skills_explanation": "Matched Python and PostgreSQL; FastAPI semantically satisfies REST API.",
                "experience_explanation": "Relevant backend telemetry engineering tenure.",
                "education_explanation": "Engineering degree meets the Bachelor's requirement.",
                "certification_explanation": "None required.",
                "strengths": ["Production FastAPI & PostgreSQL experience"],
                "weaknesses": [],
                "recommendations": ["Mention API architecture experience."],
            },
            {
                "job_id": "HYB-JOB-3",
                "ai_match_score": 74.0,
                "skills_score": 72.0,
                "experience_score": 75.0,
                "education_score": 95.0,
                "certifications_score": 100.0,
                "relevance_level": "Partially Relevant",
                "semantic_matched_skills": [],
                "transferable_skills": ["Statistical Analysis"],
                "why_this_score": [
                    "Matches Quality Control and SQL reporting.",
                    "Missing explicit ISO 9001 certification/audit experience.",
                ],
                "ai_summary": "Solid QA fit via SQL and Quality Control, though ISO 9001 audit experience is not listed.",
                "skills_explanation": "Matched Quality Control and SQL; missing ISO 9001.",
                "experience_explanation": "Relevant plant experience focused more on automation than audits.",
                "education_explanation": "BS Industrial Engineering fits QA roles well.",
                "certification_explanation": "None required.",
                "strengths": ["Plant QC dashboard experience"],
                "weaknesses": ["No ISO 9001 listed"],
                "recommendations": ["Add any ISO 9001 exposure to your resume."],
            },
        ]
    }

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}
    mock_client.generate_content.return_value = _fake_response(batch_payload, model="gemini-2.5-flash-lite", total_tokens=1050)

    # Avoid Celery broker dependency in unit tests
    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client), \
         patch("celery.group", side_effect=RuntimeError("no broker in unit test")):
        first_results = await job_matching_service.match_resume_to_all_jobs(db_session, resume_data, use_ai=True)
        second_results = await job_matching_service.match_resume_to_all_jobs(db_session, resume_data, use_ai=True)

    assert len(first_results) == 5
    # ONLY 1 Gemini API call across all 5 jobs AND 2 runs (batching + SHA-256 cache)!
    assert mock_client.generate_content.call_count == 1
    call_kwargs = mock_client.generate_content.call_args.kwargs
    assert call_kwargs["models"][0] == "gemini-2.5-flash-lite"
    assert call_kwargs["thinking_budget"] == 0

    ai_enriched = [r for r in first_results if r.get("ai_powered")]
    nlp_only = [r for r in first_results if not r.get("ai_powered")]
    assert len(ai_enriched) == 3, "Only Top-3 shortlisted jobs should be enriched"
    assert len(nlp_only) == 2, "Unrelated low-score jobs (Chef, Lawyer) should stay pure NLP (0 tokens)"
    assert first_results[0]["job_id"] == "HYB-JOB-1"
    assert len(first_results[0]["why_this_score"]) >= 2
    assert second_results[0]["ai_powered"] is True

    opt = gemini_service.get_gemini_status()["optimization"]
    assert opt["batch_match_calls_live"] == 1
    assert opt["batch_jobs_analyzed"] == 3
    assert opt["match_calls_saved_by_batching"] == 2
    assert opt["cache_hits"] >= 1


def test_daily_match_budget_reserves_quota_for_applications_and_falls_back(monkeypatch):
    """
    At >= 85% of daily match budget, smart_match/comparison calls auto-skip to preserve
    API quota for real submitted applications; at 100%, all match calls degrade to NLP.
    """
    monkeypatch.setenv("GEMINI_DAILY_MATCH_BUDGET", "10")
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    mock_client.key_manager.get_status_snapshot.return_value = {"health": "healthy"}

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        for _ in range(9):
            gemini_service._increment_daily_match_count("match")

        allowed_preview, reason_preview = gemini_service.should_invoke_gemini_for_match(priority="smart_match")
        assert allowed_preview is False
        assert reason_preview == "budget_reserved_for_applications"

        allowed_app, _ = gemini_service.should_invoke_gemini_for_match(priority="application")
        assert allowed_app is True

        gemini_service._increment_daily_match_count("match")
        allowed_capped, reason_capped = gemini_service.should_invoke_gemini_for_match(priority="application")
        assert allowed_capped is False
        assert reason_capped == "daily_match_budget_exhausted"


def test_deterministic_why_this_score_populated_when_gemini_disabled():
    """Even with Gemini completely off, why_this_score gives concrete plain-language explanations."""
    resume_data = {
        "fullname": "Juan Cruz",
        "skills": "Python, SQL",
        "experience": "Junior Developer (1 year) - Python scripting",
        "years_experience": 1,
        "highest_degree": "Bachelor of Science in Information Technology",
    }
    job = {
        "job_id": "DET-1",
        "job_title": "Backend Engineer",
        "skills_requirements": "Python, SQL, Docker",
        "experience_requirements": "3 years",
        "education_requirements": "Bachelor's Degree",
    }
    res = job_matching_service.calculate_match_score(resume_data, job, use_ai=False, log_prediction=False)
    assert res["ai_powered"] is False
    assert isinstance(res["why_this_score"], list) and len(res["why_this_score"]) >= 2
    joined = " ".join(res["why_this_score"]).lower()
    assert "python" in joined
    assert "docker" in joined
