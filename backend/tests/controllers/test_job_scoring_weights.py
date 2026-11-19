"""
Per-job scoring weights, validation, recalculation, snapshots, audit logs, and migration tests.
"""
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.models.hr import HR
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.services.job_matching_service import (
    MAX_WEIGHT_PCT,
    MIN_WEIGHT_PCT,
    THESIS_DEFAULT_WEIGHTS,
    calculate_match_score,
    nlp_analyze_match,
)
from app.utils.auth import create_access_token, hash_password
from migrations.add_job_scoring_weights import _column_exists, downgrade, upgrade


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
    "fullname": "Test Candidate",
    "email": "test@example.com",
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
    kwargs = {
        "fullname": f"{role} Tester",
        "email": email,
        "password": hash_password("pass12345"),
        "role": role,
    }
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
        "skills": 40,
        "experience": 30,
        "education": 15,
        "certifications": 10,
        "completeness": 5,
    }


def test_deterministic_scoring_for_identical_inputs():
    r1 = calculate_match_score(RESUME, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)
    r2 = calculate_match_score(RESUME, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)
    assert r1["match_percentage"] == r2["match_percentage"]
    assert r1["applied_weights"] == r2["applied_weights"]


def test_hand_computed_example_matches_87():
    """
    skills 80, experience 100, education 100, certifications 50, completeness 100
    with default weights (40/30/15/10/5) -> 80*0.40 + 100*0.30 + 100*0.15 + 50*0.10 + 100*0.05 = 87.0
    """
    with patch("app.services.job_matching_service.calculate_skills_match", return_value={"score": 0.80, "matched": ["Python"], "missing": []}), \
         patch("app.services.job_matching_service.calculate_experience_match", return_value={"score": 1.0, "reason": "ok", "below_minimum": False, "required_years": 2, "candidate_years": 4}), \
         patch("app.services.job_matching_service.calculate_experience_relevance", return_value={"relevance_score": 1.0, "relevant_count": 1, "irrelevant_count": 0, "total_entries": 1, "relevance_level": "High", "transferable_skills": [], "detailed_breakdown": ""}), \
         patch("app.services.job_matching_service.calculate_education_match", return_value={"score": 1.0, "reason": "ok", "required_education": "BS", "candidate_education": "BS"}), \
         patch("app.services.job_matching_service.calculate_certifications_match", return_value={"score": 0.50, "reason": "ok", "required_certifications": "PMP", "candidate_certifications": "PMP"}):
        res = calculate_match_score({**RESUME, "completeness_score": 100.0}, dict(JOB), matching_config=GLOBAL_CONFIG)
    assert res["match_percentage"] == 87.0


def test_certification_heavy_job_ranks_certified_candidate_higher():
    certified = {
        **RESUME,
        "skills": "Python, AWS",
        "certifications": "PMP, CISSP",
        "completeness_score": 100.0,
    }
    uncertified = {
        **RESUME,
        "skills": "Python, AWS, Terraform, Docker",
        "certifications": "",
        "completeness_score": 100.0,
    }
    default_cert = calculate_match_score(certified, dict(JOB), matching_config=GLOBAL_CONFIG)["match_percentage"]
    default_uncert = calculate_match_score(uncertified, dict(JOB), matching_config=GLOBAL_CONFIG)["match_percentage"]

    heavy_cert = calculate_match_score(certified, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)["match_percentage"]
    heavy_uncert = calculate_match_score(uncertified, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)["match_percentage"]

    # On a certification-heavy job, the certified candidate gains relative to the uncertified candidate
    assert (heavy_cert - heavy_uncert) > (default_cert - default_uncert)
    assert heavy_cert > heavy_uncert


def test_nlp_analysis_path_honours_job_weights():
    result = nlp_analyze_match(RESUME, {**JOB, "scoring_weights": CERT_HEAVY}, matching_config=GLOBAL_CONFIG)
    assert result["applied_weights"]["certifications"] == 45


def test_invalid_job_weights_fall_back_to_global_default():
    broken = {"skills_weight": "abc"}
    result = calculate_match_score(RESUME, {**JOB, "scoring_weights": broken}, matching_config=GLOBAL_CONFIG)
    assert result["weights_source"] == "global"
    assert result["applied_weights"]["skills"] == 40


# ─── API & Validation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_job_starts_with_default_weights(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job_id = _unique_job_id("W-DEF")

    res = await client.post("/admins/createjob", json=_job_payload(job_id), headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["scoring_weights"] == THESIS_DEFAULT_WEIGHTS

    stored = (
        await db_session.execute(select(JobDescription).where(JobDescription.job_id == job_id))
    ).scalar_one()
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
async def test_weights_validation_sum_bounds_and_whole_numbers(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")

    # 1. Not summing to 100%
    unbalanced = {**CERT_HEAVY, "skills_weight": 0.50}
    res = await client.post(
        "/admins/createjob",
        json=_job_payload(_unique_job_id("W-SUM"), scoring_weights=unbalanced),
        headers=headers,
    )
    assert res.status_code == 422
    assert "100%" in res.text

    # 2. Below MIN_WEIGHT_PCT (5%)
    below_min = {
        "skills_weight": 0.43,
        "experience_weight": 0.30,
        "education_weight": 0.15,
        "certifications_weight": 0.10,
        "completeness_weight": 0.02,
    }
    res = await client.post(
        "/admins/createjob",
        json=_job_payload(_unique_job_id("W-MIN"), scoring_weights=below_min),
        headers=headers,
    )
    assert res.status_code == 422
    assert f"{MIN_WEIGHT_PCT}%" in res.text

    # 3. Above MAX_WEIGHT_PCT (70%)
    above_max = {
        "skills_weight": 0.75,
        "experience_weight": 0.10,
        "education_weight": 0.05,
        "certifications_weight": 0.05,
        "completeness_weight": 0.05,
    }
    res = await client.post(
        "/admins/createjob",
        json=_job_payload(_unique_job_id("W-MAX"), scoring_weights=above_max),
        headers=headers,
    )
    assert res.status_code == 422
    assert f"{MAX_WEIGHT_PCT}%" in res.text

    # 4. Non-whole-number percentage
    fractional = {
        "skills_weight": 0.405,
        "experience_weight": 0.295,
        "education_weight": 0.15,
        "certifications_weight": 0.10,
        "completeness_weight": 0.05,
    }
    res = await client.post(
        "/admins/createjob",
        json=_job_payload(_unique_job_id("W-FRAC"), scoring_weights=fractional),
        headers=headers,
    )
    assert res.status_code == 422
    assert "whole-number" in res.text


@pytest.mark.asyncio
async def test_only_admins_can_set_job_weights_and_recalculate(client, db_session):
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

    res = await client.post(f"/admins/jobs/{job_id}/recalculate-scores", headers=hr_headers)
    assert res.status_code == 403

    # Non-weight edits keep working for HR
    res = await client.patch(f"/admins/update-job/{job_id}", json={"salary_range": "120k-160k"}, headers=hr_headers)
    assert res.status_code == 200
    assert res.json()["scoring_weights"] == THESIS_DEFAULT_WEIGHTS


@pytest.mark.asyncio
async def test_recalculate_only_affects_chosen_job_stores_snapshot_and_preserves_status_and_roster(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job1_id = _unique_job_id("W-J1")
    job2_id = _unique_job_id("W-J2")

    r1 = await client.post("/admins/createjob", json=_job_payload(job1_id), headers=headers)
    r2 = await client.post("/admins/createjob", json=_job_payload(job2_id), headers=headers)
    assert r1.status_code == 201 and r2.status_code == 201
    j1_pk, j2_pk = r1.json()["id"], r2.json()["id"]

    app1 = JobApplication(
        job_id=j1_pk,
        candidate_name="Candidate One",
        candidate_email=f"c1_{uuid.uuid4().hex[:8]}@example.com",
        skills=["Python", "AWS", "Terraform", "Docker"],
        job_title="Cloud Engineer",
        company="Acme",
        degree="BS Computer Science",
        total_experience_months=48,
        match_score=77.5,
        status="SHORTLISTED",
    )
    app2 = JobApplication(
        job_id=j2_pk,
        candidate_name="Candidate Two",
        candidate_email=f"c2_{uuid.uuid4().hex[:8]}@example.com",
        skills=["Python", "AWS"],
        job_title="Cloud Engineer",
        company="Acme",
        degree="BS Computer Science",
        total_experience_months=36,
        match_score=66.0,
        status="PENDING",
    )
    db_session.add_all([app1, app2])
    await db_session.commit()

    roster = ShortlistRoster(name="Final Roster", job_id=j1_pk, created_by="hr@example.com")
    db_session.add(roster)
    await db_session.flush()
    roster_entry = ShortlistRosterItem(roster_id=roster.id, application_id=app1.id, added_by="hr@example.com")
    db_session.add(roster_entry)
    await db_session.commit()

    # 1. Saving new weights alone does NOT overwrite existing scores ("Apply to new applications only")
    patch_res = await client.patch(
        f"/admins/update-job/{job1_id}", json={"scoring_weights": CERT_HEAVY}, headers=headers
    )
    assert patch_res.status_code == 200
    await db_session.refresh(app1)
    assert app1.match_score == 77.5

    # 2. Triggering recalculation for job1 updates ONLY app1, stores weight snapshot,
    #    and preserves status & shortlist roster
    with patch("app.tasks.recalculate_job_applications_task.delay", side_effect=RuntimeError("no broker")):
        recalc_res = await client.post(f"/admins/jobs/{job1_id}/recalculate-scores", headers=headers)
    assert recalc_res.status_code == 200, recalc_res.text
    assert recalc_res.json()["updated_applications"] == 1

    await db_session.refresh(app1)
    await db_session.refresh(app2)
    assert app1.match_score != 77.5
    assert app1.applied_weights == {"skills": 20, "experience": 20, "education": 10, "certifications": 45, "completeness": 5}
    assert app1.status == "SHORTLISTED"
    assert app2.match_score == 66.0  # Untouched!

    entries = (
        await db_session.execute(select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == roster.id))
    ).scalars().all()
    assert len(entries) == 1

    # 3. Audit log recorded old and new weights
    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "UPDATE_JOB_WEIGHTS").order_by(AuditLog.id.desc())
        )
    ).scalars().all()
    assert len(logs) >= 1
    assert "from (" in logs[0].details and "to (" in logs[0].details


@pytest.mark.asyncio
async def test_global_weight_change_writes_audit_log_with_old_and_new(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    new_global = {
        "skills_weight": 0.45,
        "experience_weight": 0.25,
        "education_weight": 0.15,
        "certifications_weight": 0.10,
        "completeness_weight": 0.05,
    }
    res = await client.put("/system-config/matching/weights", json=new_global, headers=headers)
    assert res.status_code == 200, res.text

    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.target == "Global Matching Weights").order_by(AuditLog.id.desc())
        )
    ).scalars().all()
    assert len(logs) >= 1
    assert "from (" in logs[0].details and "Skills 45%" in logs[0].details


@pytest.mark.asyncio
async def test_applicant_matching_endpoint_hides_weights_and_formula(client, db_session):
    headers = await _headers_for(db_session, Admin, "ADMIN")
    job_id = _unique_job_id("W-APP")
    await client.post(
        "/admins/createjob", json=_job_payload(job_id, scoring_weights=CERT_HEAVY), headers=headers
    )

    res = await client.post(
        f"/matching/match-data/{job_id}",
        json={"skills": "Python, AWS", "experience": "Cloud Engineer", "years_experience": 3, "education": "BS CS"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("applied_weights") is None
    assert "weight" not in (body.get("score_explanation") or "").lower()
    assert "extra focus on certifications" in (body.get("score_explanation") or "").lower()


@pytest.mark.asyncio
async def test_migration_upgrade_and_downgrade_are_idempotent_and_reversible():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE TABLE job_descriptions (id INTEGER PRIMARY KEY, job_id TEXT)")
        await conn.exec_driver_sql("CREATE TABLE job_applications (id INTEGER PRIMARY KEY, job_id INTEGER)")

        # Re-runnable upgrade
        await upgrade(conn)
        await upgrade(conn)
        assert await _column_exists(conn, "job_descriptions", "scoring_weights")
        assert await _column_exists(conn, "job_applications", "applied_weights")

        # Reversible downgrade (and re-runnable)
        await downgrade(conn)
        await downgrade(conn)
        assert not await _column_exists(conn, "job_descriptions", "scoring_weights")
        assert not await _column_exists(conn, "job_applications", "applied_weights")

    await engine.dispose()
