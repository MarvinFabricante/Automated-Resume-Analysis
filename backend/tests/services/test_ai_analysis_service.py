import pytest
from unittest.mock import patch
from app.services import ai_analysis_service


def test_analyze_match_with_fallback_success():
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
        "experience_level": "2 years",
        "education": "Bachelor's Degree",
        "location": "Metro Manila"
    }

    result = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)
    assert result is not None
    assert result.get("model_used") == "nlp"
    assert "ai_match_score" in result
    assert "ai_skills_score" in result


def test_analyze_match_with_fallback_failure():
    with patch("app.services.job_matching_service.nlp_analyze_match", return_value=None):
        result = ai_analysis_service.analyze_match_with_fallback({}, {})
        assert result is None


def test_compare_candidates_with_fallback_success():
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

    result = ai_analysis_service.compare_candidates_with_fallback(job_data, candidates)
    assert result is not None
    assert result.get("model_used") == "nlp"
    assert "ranked_candidates" in result
    assert "overall_summary" in result
    assert "comparative_insights" in result


def test_compare_candidates_with_fallback_failure():
    with patch("app.services.job_matching_service.nlp_compare_candidates", return_value=None):
        result = ai_analysis_service.compare_candidates_with_fallback({}, [])
        assert result is None
