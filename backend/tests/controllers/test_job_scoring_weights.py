"""
Per-job scoring weights.

Every new job starts with the thesis default weights (Skills 40%, Work Experience
Relevance 30%, Educational Background 15%, Certifications & Trainings 10%,
Resume Completeness 5%) and admins can adjust them per job.
"""
import uuid

import pytest
from sqlalchemy import select

from app.models.admin import Admin
from app.models.hr import HR
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.job_matching_service import (
    THESIS_DEFAULT_WEIGHTS,
    calculate_match_score,
    nlp_analyze_match,
)
from app.utils.auth import hash_password, create_access_token


CERT_HEAVY = {
    "skills_weight": 0.20,
    "experience_weight": 0.20,
    "education_weight": 0.10,
    "certifications_weight": 0.45,
    "completeness_weight": 0.05,
}

GLOBAL_CONFIG = {"weights": dict(THESIS_DEFAULT_WEIGHTS), "thresholds": {}}

JOB = {
    "job_id": "UNIT-JOB",
    "job_title": "Cloud Engineer",
    "description": "Build and operate cloud infrastructure.",
    "skills_requirements": "Python, AWS, Terraform, Docker",
    "certifications_requirements": "PMP, CISSP",
}

RESUME = {
    "skills": "Python, AWS, Terraform, Docker",
    "experience": "Cloud Engineer at Acme",
    "years_experience": 4,
    "education": "BS Computer Science",
    "certifications": "",
}


def _unique_job_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _job_payload(job_id: str, **extra) -> dict:
    payload = {
        "job_id": job_id,
        "job_title": "Cloud Engineer",
        "department": "Engineering",
        "job_type": "Full-Time",
        "location": "Taguig",
        "salary_range": "100k-150k",
        "description": "Build and operate cloud infrastructure.",
        "skills_requirements": "Python, AWS, Terraform, Docker",
        "certifications_requirements": "PMP, CISSP",
        "is_active": True,
    }
    payload.update(extra)
    return payload


async def _headers_for(db_session, model, role: str) -> dict:
    email = f"{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
    kwargs = {"fullname": f"{role} Tester", "email": email, "password": hash_password("pass12345"), "role": role}
    if model is HR:
        kwargs["company_name"] = "Test Corp"
    user = model(**kwargs)
    db_session.add(user)
    await db_session.commit()
    token = create_access_token({"sub": email, "role": role, "id": user.id})
    return {"Authorization": f"Bearer {token}"}


# ─── Scoring engine ──────────────────────────────────────────────────────────

def test_thesis_defaults_total_100_percent():
    assert THESIS_DEFAULT_WEIGHTS == {
        "skills_weight": 0.40,
        "experience_weight": 0.30,
        "education_weight": 0.15,
        "certifications_weight": 0.10,
        "completeness_weight": 0.05,
    }
    assert round(sum(THESIS_DEFAULT_WEIGHTS.values()), 6) == 1.0


def test_job_without_weights_uses_global_default():
    result = calculate_match_score(RESUME, dict(JOB), matching_config=GLOBAL_CONFIG)
    assert result["weights_source"] == "global"
    assert result["applied_weights"] == {
        "skills": 40, "experience": 30, "education": 15, "certifications": 10, "completeness": 5,
    }


def test_job_weights_override_global_default_and_change_score():
    default_result = calculate_match_score(RESUME, dict(JOB), matching_config=GLOBAL_CONFIG)
    custom_result = calculate_match_score(
        RESUME, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG
    )
    assert custom_result["weights_source"] == "job"
    assert custom_result["applied_weights"]["certifications"] == 45
    assert custom_result["applied_weights"]["skills"] == 20
    # The candidate lacks the required certification, so a certification-heavy job scores them lower.
    assert custom_result["match_percentage"] < default_result["match_percentage"]


def test_nlp_analysis_path_honours_job_weights():
    result = nlp_analyze_match(RESUME, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)
    assert result["applied_weights"]["certifications"] == 45


def test_invalid_job_weights_fall_back_to_global_default():
    broken = {"skills_weight": "abc"}
    result = calculate_match_score(RESUME, {**JOB, "scoring_weights": broken}, matching_config=GLOBAL_CONFIG)
    assert result["weights_source"] == "global"
    assert result["applied_weights"]["skills"] == 40


# ─── API ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_job_starts_with_default_weights(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job_id = _unique_job_id("W-DEF")

    res = await client.post("/admins/createjob", json=_job_payload(job_id), headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["scoring_weights"] == THESIS_DEFAULT_WEIGHTS

    stored = (await db_session.execute(
        select(JobDescription).where(JobDescription.job_id == job_id)
    )).scalar_one()
    assert stored.scoring_weights == THESIS_DEFAULT_WEIGHTS


@pytest.mark.asyncio
async def test_admin_can_create_job_with_custom_weights(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job_id = _unique_job_id("W-CUS")

    res = await client.post(
        "/admins/createjob", json=_job_payload(job_id, scoring_weights=CERT_HEAVY), headers=headers
    )
    assert res.status_code == 201, res.text
    assert res.json()["scoring_weights"] == CERT_HEAVY


@pytest.mark.asyncio
async def test_weights_must_total_100_percent(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    unbalanced = {**CERT_HEAVY, "skills_weight": 0.50}  # 130%

    res = await client.post(
        "/admins/createjob",
        json=_job_payload(_unique_job_id("W-BAD"), scoring_weights=unbalanced),
        headers=headers,
    )
    assert res.status_code == 422
    assert "100%" in res.text


@pytest.mark.asyncio
async def test_only_admins_can_set_job_weights(client, db_session):
    admin_headers = await _headers_for(db_session, Admin, "ADMIN")
    hr_headers = await _headers_for(db_session, HR, "HR")
    job_id = _unique_job_id("W-AUTH")

    res = await client.post(
        "/admins/createjob", json=_job_payload(job_id, scoring_weights=CERT_HEAVY), headers=hr_headers
    )
    assert res.status_code == 403

    res = await client.post("/admins/createjob", json=_job_payload(job_id), headers=admin_headers)
    assert res.status_code == 201

    res = await client.patch(
        f"/admins/update-job/{job_id}", json={"scoring_weights": CERT_HEAVY}, headers=hr_headers
    )
    assert res.status_code == 403

    res = await client.patch(f"/admins/update-job/{job_id}", json={"scoring_weights": CERT_HEAVY})
    assert res.status_code == 403

    # Non-weight edits keep working as before.
    res = await client.patch(f"/admins/update-job/{job_id}", json={"salary_range": "120k-160k"}, headers=hr_headers)
    assert res.status_code == 200
    assert res.json()["scoring_weights"] == THESIS_DEFAULT_WEIGHTS


@pytest.mark.asyncio
async def test_updating_weights_rescores_existing_applications(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job_id = _unique_job_id("W-RES")

    res = await client.post("/admins/createjob", json=_job_payload(job_id), headers=headers)
    assert res.status_code == 201
    job_pk = res.json()["id"]

    application = JobApplication(
        job_id=job_pk,
        candidate_name="Weighted Candidate",
        candidate_email=f"cand_{uuid.uuid4().hex[:8]}@example.com",
        skills=["Python", "AWS", "Terraform", "Docker"],
        job_title="Cloud Engineer",
        company="Acme",
        degree="BS Computer Science",
        total_experience_months=48,
        status="SUBMITTED",
    )
    db_session.add(application)
    await db_session.commit()

    # Saving default weights triggers a re-score with the default distribution.
    res = await client.patch(
        f"/admins/update-job/{job_id}", json={"scoring_weights": THESIS_DEFAULT_WEIGHTS}, headers=headers
    )
    assert res.status_code == 200, res.text
    await db_session.refresh(application)
    default_score = application.match_score
    assert default_score is not None

    res = await client.patch(
        f"/admins/update-job/{job_id}", json={"scoring_weights": CERT_HEAVY}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["scoring_weights"] == CERT_HEAVY
    await db_session.refresh(application)
    assert application.match_score < default_score

    # Explicit null drops the custom weights so the job inherits the global default again.
    res = await client.patch(f"/admins/update-job/{job_id}", json={"scoring_weights": None}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["scoring_weights"] is None
    await db_session.refresh(application)
    assert application.match_score == pytest.approx(default_score)
