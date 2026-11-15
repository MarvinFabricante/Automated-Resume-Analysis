import pytest
from app.services.job_matching_service import calculate_match_score

def test_thesis_weighted_scoring_criteria():
    """
    Test STI College Ortigas-Cainta thesis proposal weighted scoring model:
    - Skills Match: 40% (0.40)
    - Work Experience Relevance: 30% (0.30)
    - Educational Background: 15% (0.15)
    - Certifications & Trainings: 10% (0.10)
    - Resume Completeness: 5% (0.05)
    """
    resume_data = {
        "skills": "Python, FastAPI, Docker, SQL, Git",
        "years_experience": 4,
        "experience": "Software Engineer at Tech Corp working on Python and APIs",
        "education": "Bachelor of Science in Computer Science",
        "certifications": "AWS Certified Solutions Architect",
        "completeness_score": 100.0
    }
    job = {
        "job_title": "Backend Software Developer",
        "department": "IT",
        "description": "Seeking Python and FastAPI backend engineer with 3+ years experience and BS CS.",
        "skills_requirements": "Python, FastAPI, SQL, Docker",
        "experience_requirements": 3,
        "education_requirements": "Bachelor's Degree in Computer Science or related field",
        "certifications_requirements": "AWS Certified"
    }

    result = calculate_match_score(resume_data, job)

    assert result["match_percentage"] > 70.0
    assert "completeness_score" in result
    assert result["completeness_score"] == 100.0

    applied_weights = result.get("applied_weights", {})
    assert applied_weights.get("skills") == 40
    assert applied_weights.get("experience") == 30
    assert applied_weights.get("education") == 15
    assert applied_weights.get("certifications") == 10
    assert applied_weights.get("completeness") == 5

def test_thesis_incomplete_profile_scoring():
    """
    Test that incomplete profile has completeness score calculated and penalizes composite score proportionally (5%).
    """
    resume_data = {
        "skills": "Python",
        "years_experience": 1,
        "completeness_score": 40.0
    }
    job = {
        "job_title": "Senior Python Developer",
        "skills_requirements": "Python, Django, AWS, Kubernetes",
    }

    result = calculate_match_score(resume_data, job)
    assert result["completeness_score"] == 40.0
    assert "Resume Completeness" in result["score_explanation"]
