import pytest
import io
from unittest.mock import patch, AsyncMock
from app.models.job_description import JobDescription, JobType


@pytest.mark.asyncio
async def test_match_resume_data_endpoint(client, db_session):
    job = JobDescription(
        job_id="JOB-MATCH-CTRL-01",
        job_title="Python Developer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Taguig",
        description="FastAPI and Python development",
        skills_requirements="Python, FastAPI, SQL",
        experience_requirements="2 years"
    )
    db_session.add(job)
    await db_session.commit()

    match_payload = {
        "fullname": "John Matcher",
        "email": "matcher@example.com",
        "skills": "Python, FastAPI, SQL, Docker",
        "years_experience": 3,
        "highest_degree": "Bachelor of Science in CS",
        "location": "Taguig, Metro Manila"
    }

    # Match against all active jobs
    res = await client.post("/matching/match-data", json=match_payload)
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    matched_job = next((j for j in data["results"] if j["job_id"] == "JOB-MATCH-CTRL-01"), None)
    assert matched_job is not None
    assert matched_job["match_percentage"] > 0


@pytest.mark.asyncio
async def test_match_resume_to_single_job_endpoint(client, db_session):
    job = JobDescription(
        job_id="JOB-SINGLE-MATCH-01",
        job_title="DevOps Lead",
        department="Infrastructure",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Kubernetes, Terraform, AWS",
        skills_requirements="Kubernetes, Terraform, AWS",
        experience_requirements="3 years"
    )
    db_session.add(job)
    await db_session.commit()

    match_payload = {
        "fullname": "Cloud Engineer",
        "skills": "Kubernetes, AWS",
        "years_experience": 4
    }

    # Match single job
    res = await client.post("/matching/match-data/JOB-SINGLE-MATCH-01", json=match_payload)
    assert res.status_code == 200
    result = res.json()
    assert result["job_id"] == "JOB-SINGLE-MATCH-01"
    assert result["job_title"] == "DevOps Lead"

    # Non-existent job
    res_none = await client.post("/matching/match-data/NON-EXISTENT-JOB-999", json=match_payload)
    assert res_none.status_code == 404


@pytest.mark.asyncio
async def test_match_resume_file_endpoint(client, db_session):
    job = JobDescription(
        job_id="JOB-FILE-MATCH-01",
        job_title="Data Analyst",
        department="Business Intelligence",
        job_type=JobType.FULL_TIME,
        location="Makati",
        description="SQL, Excel, Tableau",
        skills_requirements="SQL, Excel, Tableau"
    )
    db_session.add(job)
    await db_session.commit()

    files = {"file": ("analyst_resume.pdf", io.BytesIO(b"dummy pdf bytes"), "application/pdf")}
    mock_extracted = {
        "fullname": "Analyst Applicant",
        "skills": "SQL, Excel, Tableau",
        "years_experience": 2
    }

    with patch("app.services.resume_service.parse_resume_file", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = mock_extracted

        res = await client.post("/matching/match-resume", files=files)
        assert res.status_code == 200
        assert "results" in res.json()
