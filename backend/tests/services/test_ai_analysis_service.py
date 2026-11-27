import pytest
from unittest.mock import patch
from app.services import ai_analysis_service


def test_analyze_match_with_fallback_nlp_when_gemini_disabled():
    resume_data = {
        "fullname": "Jane Doe",
        "skills": "Python, FastAPI, SQL",
        "experience": "3 years software engineer",
        "years_experience": 3,
        "highest_degree": "Bachelor of Science in Computer Science",
        "location": "Taguig, Metro Manila"
    }
    job_data = {
        "job_title": "Backend Developer",
        "description": "Looking for Python and FastAPI developer with SQL experience.",
        "skills": "Python, FastAPI, SQL",
        "skills_requirements": "Python, FastAPI, SQL",
        "experience_level": "2 years",
        "education": "Bachelor's Degree",
        "location": "Metro Manila"
    }

    with patch("app.services.gemini_service.is_gemini_enabled", return_value=False):
        result = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)

    assert result is not None
    assert result.get("model_used") == "nlp"
    assert result.get("ai_powered") is False
    assert "ai_match_score" in result
    assert "ai_skills_score" in result


def test_analyze_match_with_fallback_uses_gemini_primary_when_available():
    resume_data = {
        "fullname": "Jane Doe",
        "skills": "Python, FastAPI, SQL",
        "experience": "3 years software engineer",
        "years_experience": 3,
        "highest_degree": "Bachelor of Science in Computer Science",
    }
    job_data = {
        "job_title": "Backend Developer",
        "description": "Python, FastAPI, SQL backend APIs.",
        "skills_requirements": "Python, FastAPI, SQL",
        "experience_requirements": "2 years",
        "education_requirements": "Bachelor's Degree",
    }
    mock_gemini = {
        "ai_match_score": 92.0,
        "match_level": "High Match",
        "ai_skills_score": 95.0,
        "skills_explanation": "Matched all core backend skills.",
        "ai_experience_score": 90.0,
        "experience_explanation": "Directly relevant engineering tenure.",
        "relevance_level": "Highly Relevant",
        "transferable_skills": [],
        "ai_education_score": 95.0,
        "education_explanation": "BS CS satisfies degree requirement.",
        "ai_certifications_score": 100.0,
        "certification_explanation": "No certification required.",
        "strengths": ["Strong Python & FastAPI expertise"],
        "weaknesses": [],
        "ai_summary": "Strong backend engineering candidate.",
        "matched_skills": ["Python", "FastAPI", "SQL"],
        "missing_skills": [],
        "recommendations": ["Proceed to technical interview."],
        "model_used": "gemini",
        "gemini_model": "gemini-2.5-flash",
        "ai_powered": True,
    }

    with patch("app.services.gemini_service.is_gemini_enabled", return_value=True), \
         patch("app.services.gemini_service.gemini_analyze_match", return_value=mock_gemini):
        result = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)

    assert result is not None
    assert result.get("model_used") == "gemini"
    assert result.get("ai_powered") is True
    assert result.get("fallback_used") is False
    assert result.get("ai_summary") == "Strong backend engineering candidate."


def test_analyze_match_with_fallback_degrades_to_nlp_when_gemini_exhausted():
    resume_data = {
        "fullname": "Jane Doe",
        "skills": "Python, FastAPI, SQL",
        "experience": "3 years software engineer",
        "years_experience": 3,
    }
    job_data = {
        "job_title": "Backend Developer",
        "description": "Python and FastAPI",
        "skills_requirements": "Python, FastAPI, SQL",
    }

    with patch("app.services.gemini_service.is_gemini_enabled", return_value=True), \
         patch("app.services.gemini_service.gemini_analyze_match", return_value=None):
        result = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)

    assert result is not None
    assert result.get("model_used") == "nlp"
    assert result.get("ai_powered") is False
    assert result.get("fallback_used") is True


def test_analyze_match_with_fallback_failure():
    with patch("app.services.gemini_service.is_gemini_enabled", return_value=False), \
         patch("app.services.job_matching_service.nlp_analyze_match", return_value=None):
        result = ai_analysis_service.analyze_match_with_fallback({}, {})
        assert result is None


def test_compare_candidates_with_fallback_nlp_when_gemini_disabled():
    job_data = {
        "job_title": "Python Engineer",
        "description": "Python, SQL, Docker",
        "skills": "Python, SQL, Docker"
    }
    candidates = [
        {
            "id": 1,
            "candidate_name": "Alice",
            "skills": "Python, SQL",
            "match_score": 85,
            "skills_score": 80,
            "experience_score": 90
        },
        {
            "id": 2,
            "candidate_name": "Bob",
            "skills": "Docker, Kubernetes",
            "match_score": 70,
            "skills_score": 65,
            "experience_score": 75
        }
    ]

    with patch("app.services.gemini_service.is_gemini_enabled", return_value=False):
        result = ai_analysis_service.compare_candidates_with_fallback(job_data, candidates)
    assert result is not None
    assert result.get("model_used") == "nlp"
    assert result.get("ai_powered") is False
    assert "ranked_candidates" in result
    assert "overall_summary" in result
    assert "comparative_insights" in result


def test_compare_candidates_with_fallback_uses_gemini_when_available():
    job_data = {
        "job_title": "Python Engineer",
        "description": "Python, SQL, Docker",
        "skills_requirements": "Python, SQL, Docker",
    }
    candidates = [
        {"candidate_name": "Alice", "skills": "Python, SQL, Docker", "years_experience": 4},
        {"candidate_name": "Bob", "skills": "Excel", "years_experience": 1},
    ]
    mock_gemini_comp = {
        "rankings": [
            {"rank": 1, "candidate_name": "Alice", "match_score": 94.0, "reasoning": "Strong Python/SQL/Docker fit."},
            {"rank": 2, "candidate_name": "Bob", "match_score": 30.0, "reasoning": "Missing core technical stack."},
        ],
        "ranked_candidates": [
            {"rank": 1, "candidate_name": "Alice", "match_score": 94.0, "reasoning": "Strong Python/SQL/Docker fit."},
            {"rank": 2, "candidate_name": "Bob", "match_score": 30.0, "reasoning": "Missing core technical stack."},
        ],
        "overall_summary": "Alice is the clear top candidate.",
        "comparison_summary": "Alice is the clear top candidate.",
        "comparative_insights": ["Alice matches all required backend technologies."],
        "model_used": "gemini",
        "gemini_model": "gemini-2.5-flash",
        "ai_powered": True,
    }

    with patch("app.services.gemini_service.is_gemini_enabled", return_value=True), \
         patch("app.services.gemini_service.gemini_compare_candidates", return_value=mock_gemini_comp):
        result = ai_analysis_service.compare_candidates_with_fallback(job_data, candidates)

    assert result is not None
    assert result.get("model_used") == "gemini"
    assert result.get("ai_powered") is True
    assert result["ranked_candidates"][0]["candidate_name"] == "Alice"
    assert result["overall_summary"] == "Alice is the clear top candidate."


def test_compare_candidates_with_fallback_failure():
    with patch("app.services.gemini_service.is_gemini_enabled", return_value=False), \
         patch("app.services.job_matching_service.nlp_compare_candidates", return_value=None):
        result = ai_analysis_service.compare_candidates_with_fallback({}, [])
        assert result is None
