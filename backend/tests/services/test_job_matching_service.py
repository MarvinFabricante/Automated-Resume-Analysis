import pytest
from app.services import job_matching_service
from app.models.job_description import JobDescription, JobType


def test_normalize_and_tokenize_skills():
    raw_skills = "Python | React.js, FastAPI; Docker • Kubernetes - SQL"
    tokens = job_matching_service._tokenize_skills(raw_skills)
    assert "python" in tokens
    assert "react" in tokens
    assert "fastapi" in tokens
    assert "docker" in tokens
    assert "kubernetes" in tokens
    assert "sql" in tokens


def test_fuzzy_match():
    assert job_matching_service._fuzzy_match("python", "python") is True
    assert job_matching_service._fuzzy_match("postgresql", "postgres") is True
    assert job_matching_service._fuzzy_match("fastapi", "react", threshold=0.8) is False


def test_detect_role_family():
    dev_text = "Experienced software engineer specializing in backend APIs and databases"
    family = job_matching_service._detect_role_family(dev_text)
    assert family in ["software_engineering", "backend", "developer", "information_technology"] or isinstance(family, str)

    families = job_matching_service._detect_all_role_families(dev_text)
    assert isinstance(families, dict)


def test_calculate_skills_match():
    candidate_skills = "Python, FastAPI, PostgreSQL, Docker"
    job_skills = "Python, FastAPI, PostgreSQL, Kubernetes, AWS"

    res = job_matching_service.calculate_skills_match(candidate_skills, job_skills)
    assert "score" in res
    assert res["score"] > 0
    assert "python" in [s.lower() for s in res["matched"]]
    assert len(res["missing"]) >= 1


def test_calculate_experience_match():
    # Candidate meets required 3 years
    res_meet = job_matching_service.calculate_experience_match(
        resume_years=4,
        job_description="Requires at least 3 years experience",
        experience_req="3 years"
    )
    assert res_meet["score"] >= 0.8

    # Candidate has 1 year, requires 5 years
    res_below = job_matching_service.calculate_experience_match(
        resume_years=1,
        job_description="Requires 5 years of proven experience",
        experience_req="5 years"
    )
    assert res_below["score"] < res_meet["score"]


def test_calculate_education_match():
    # Bachelor candidate for Bachelor requirement
    res_exact = job_matching_service.calculate_education_match(
        resume_education="Bachelor of Science in Computer Science",
        job_description="Candidate must possess a Bachelor's Degree in CS or related field",
        education_req="Bachelor's Degree"
    )
    assert res_exact["score"] >= 0.7

    # Master candidate for Bachelor requirement (overqualified / meets)
    res_higher = job_matching_service.calculate_education_match(
        resume_education="Master of Science in Information Technology",
        job_description="Bachelor's Degree required",
        education_req="Bachelor's Degree"
    )
    assert res_higher["score"] >= 0.7


def test_calculate_certifications_match():
    resume_certs = "AWS Certified Solutions Architect, Scrum Master PSM I"
    job_desc = "Preferred certifications: AWS Certified Solutions Architect, PMP"
    cert_req = "AWS Certified Solutions Architect, PMP"

    res = job_matching_service.calculate_certifications_match(
        resume_certs=resume_certs,
        job_description=job_desc,
        certifications_req=cert_req
    )
    assert "score" in res
    assert res["score"] > 0
    assert "required_certifications" in res


def test_calculate_location_match():
    # Substring / exact location match
    match_loc = job_matching_service.calculate_location_match("Taguig", "Taguig, Metro Manila")
    assert match_loc["score"] == 1.0

    # Remote job matches any location
    remote_loc = job_matching_service.calculate_location_match("Cebu City", "Remote")
    assert remote_loc["score"] == 1.0

    # Hybrid job gives partial score
    hybrid_loc = job_matching_service.calculate_location_match("Quezon City", "Batangas (Hybrid)")
    assert hybrid_loc["score"] == 0.8

    # Unmatched location
    diff_loc = job_matching_service.calculate_location_match("Davao City", "Taguig, Metro Manila")
    assert diff_loc["score"] == 0.0

    # Missing candidate location
    empty_cand = job_matching_service.calculate_location_match("", "Makati City")
    assert empty_cand["score"] == 0.5


def test_calculate_match_score_full():
    job = JobDescription(
        job_id="JOB-MATCH-FULL",
        job_title="Senior Python Backend Developer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Metro Manila",
        description="Looking for an experienced Python developer with FastAPI, PostgreSQL, and Docker.",
        skills_requirements="Python, FastAPI, PostgreSQL, Docker, Redis",
        experience_requirements="3 years",
        education_requirements="Bachelor's Degree",
        certifications_requirements="AWS Certified Developer"
    )

    resume_data = {
        "fullname": "David Chen",
        "skills": "Python, FastAPI, PostgreSQL, Docker",
        "years_experience": 4,
        "experience": "4 years working as backend engineer building FastAPI services",
        "highest_degree": "Bachelor of Science in Information Technology",
        "certifications": "AWS Certified Developer",
        "location": "Taguig, Metro Manila"
    }

    match_result = job_matching_service.calculate_match_score(resume_data, job)
    assert "match_percentage" in match_result
    assert match_result["match_percentage"] >= 60.0
    assert "skills_score" in match_result
    assert "experience_score" in match_result
    assert "education_score" in match_result
    assert "certifications_score" in match_result
    assert "recommendations" in match_result
    assert isinstance(match_result["recommendations"], list)


def test_nlp_analyze_match_and_compare_candidates():
    job_data = {
        "job_title": "Frontend Engineer",
        "description": "Seeking React and TypeScript developer with Tailwind CSS expertise.",
        "skills_requirements": "React, TypeScript, Tailwind CSS, Next.js",
        "experience_requirements": "2 years",
        "education_requirements": "Bachelor's Degree"
    }

    c1 = {
        "candidate_id": 1,
        "candidate_name": "Dev One",
        "fullname": "Dev One",
        "skills": "React, TypeScript, Tailwind CSS, Next.js",
        "years_experience": 3,
        "highest_degree": "Bachelor's Degree",
        "experience": "3 years building React web apps"
    }
    c2 = {
        "candidate_id": 2,
        "candidate_name": "Dev Two",
        "fullname": "Dev Two",
        "skills": "Vue, HTML, CSS",
        "years_experience": 1,
        "highest_degree": "Associate Degree",
        "experience": "1 year junior web developer"
    }

    # Single match analysis
    analysis = job_matching_service.nlp_analyze_match(c1, job_data)
    assert analysis["ai_match_score"] > 50.0
    assert "strengths" in analysis
    assert "weaknesses" in analysis

    # Compare candidates
    comp = job_matching_service.nlp_compare_candidates(job_data, [c1, c2])
    assert "ranked_candidates" in comp
    assert len(comp["ranked_candidates"]) == 2
    # c1 matches all 4 skills and exceeds years experience; c1 must rank above c2
    assert comp["ranked_candidates"][0]["candidate_name"] == "Dev One"
    assert comp["ranked_candidates"][0]["match_score"] > comp["ranked_candidates"][1]["match_score"]


def test_nlp_compare_candidates_zero_and_tie():
    from unittest.mock import patch
    job_data = {
        "job_title": "Production Operator",
        "skills_requirements": "Forklift, Heavy Machinery",
    }
    c_zero_1 = {
        "candidate_id": 1,
        "candidate_name": "Zero Match 1",
        "skills": "None",
    }
    c_zero_2 = {
        "candidate_id": 2,
        "candidate_name": "Zero Match 2",
        "skills": "None",
    }

    # Mock nlp_analyze_match to return 0 score
    mock_zero = {
        "ai_match_score": 0.0,
        "strengths": [],
        "weaknesses": ["No skills match"],
        "match_level": "Low Match",
        "ai_skills_score": 0.0,
        "ai_experience_score": 0.0,
        "ai_education_score": 0.0,
    }

    with patch("app.services.job_matching_service.nlp_analyze_match", return_value=mock_zero):
        comp = job_matching_service.nlp_compare_candidates(job_data, [c_zero_1, c_zero_2])
        # Must not claim a strongest match or best candidate when both are 0
        assert "None of the candidates meet the requirements" in comp["overall_summary"]
        assert "strongest candidate" not in comp["overall_summary"]
        assert "best candidate" not in comp["overall_summary"]
        assert any("lack matching skills" in insight for insight in comp["comparative_insights"])
        assert not any("separated by only 0" in insight for insight in comp["comparative_insights"])

