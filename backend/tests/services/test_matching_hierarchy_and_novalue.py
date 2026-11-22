"""
Comprehensive test suite verifying:
- Bug 1: Shared 1-8 Philippine education hierarchy, ongoing/undergraduate completion rules,
  separate field-of-study checks, unrecognized text manual review + logging, experience >=,
  and graded certification hierarchies (TESDA NC I-IV).
- Bug 2: No-value normalization ("None", "N/A", "Wala", "-", empty, etc.) on both job and
  resume sides, non-empty preservation ("None of the above, but must know Excel"), unchanged
  40/30/15/10/5 weighting, zero division guard, re-scoring idempotency, cleanup script, and
  admin recalculation preserving statuses & shortlist rosters.
"""

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.utils.database import Base
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.schemas.job_description_schema import JobCreate, JobUpdate
from app.controllers.job_matching_controller import _sanitize_for_applicant
from app.services import job_matching_service, requirement_rules
from app.services.job_application_service import _resume_data_from_application, _sanitize_application_payload
from app.services.job_description_service import rescore_job_applications
from app.services.system_config_service import recalculate_all_applications

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.cleanup_no_value_job_requirements import cleanup_no_value_job_requirements  # noqa: E402


DEFAULT_CFG = {"weights": {}, "thresholds": {}}


# ─── Bug 1: Education Hierarchy & Graded Requirements ──────────────────────────

def test_education_hierarchy_shs_req_bachelor_candidate_exceeds():
    res = job_matching_service.calculate_education_match(
        "College graduate - Bachelor of Science in Business Administration",
        "",
        "Senior High School graduate",
    )
    assert res["score"] == 1.0
    assert res["status"] == requirement_rules.STATUS_EXCEEDS
    assert res["needs_manual_review"] is False


def test_education_hierarchy_bachelor_req_shs_candidate_fails_with_clear_reason():
    res = job_matching_service.calculate_education_match(
        "Senior High School graduate",
        "",
        "Bachelor's degree",
    )
    assert res["score"] == 0.5
    assert res["status"] == requirement_rules.STATUS_DOES_NOT_MEET
    assert "Senior High School" in res["reason"]
    assert "Bachelor" in res["reason"]


def test_education_same_level_meets_requirement():
    res = job_matching_service.calculate_education_match(
        "BS Information Technology",
        "",
        "Bachelor's degree",
    )
    assert res["score"] == 1.0
    assert res["status"] == requirement_rules.STATUS_MEETS


def test_education_masters_and_doctorate_satisfy_bachelors():
    for cand_edu in ("Master in Business Administration", "MBA", "M.S. Engineering", "Ph.D. in Chemistry", "Doctorate"):
        res = job_matching_service.calculate_education_match(cand_edu, "", "Bachelor's degree")
        assert res["score"] == 1.0, f"Failed for {cand_edu}: {res}"
        assert res["status"] == requirement_rules.STATUS_EXCEEDS


def test_education_ongoing_college_undergraduate_rules():
    # Ongoing college counts as highest completed level (3 = Senior High School)
    vs_shs = job_matching_service.calculate_education_match(
        "Currently enrolled in college",
        "",
        "Senior High School",
    )
    assert vs_shs["score"] == 1.0
    assert vs_shs["status"] == requirement_rules.STATUS_MEETS

    vs_bachelor = job_matching_service.calculate_education_match(
        "Currently enrolled in college",
        "",
        "Bachelor's degree",
    )
    assert vs_bachelor["score"] == 0.5
    assert vs_bachelor["status"] == requirement_rules.STATUS_PARTIAL

    # Also test structured education_entries where degree string says BS but status is Ongoing
    vs_bachelor_structured = job_matching_service.calculate_education_match(
        "BS Information Technology",
        "",
        "Bachelor's degree",
        education_entries=[
            {"education_level": "College", "degree_or_course": "BS Information Technology", "status": "Ongoing"}
        ],
    )
    assert vs_bachelor_structured["score"] < 1.0
    assert vs_bachelor_structured["status"] == requirement_rules.STATUS_PARTIAL


def test_education_field_check_separate_and_overqualification_does_not_fix_wrong_field():
    # Same level, wrong field
    wrong_field = job_matching_service.calculate_education_match(
        "BS in Information Technology",
        "",
        "BS in Accounting",
    )
    assert wrong_field["score"] < 1.0
    assert wrong_field["status"] == requirement_rules.STATUS_PARTIAL
    assert "does not match" in wrong_field["reason"].lower()

    # Master's degree in unrelated field still fails specific field check
    overqualified_wrong_field = job_matching_service.calculate_education_match(
        "Master of Arts in History | Bachelor of Science in Biology",
        "",
        "BS in Accounting",
    )
    assert overqualified_wrong_field["score"] < 1.0
    assert overqualified_wrong_field["status"] == requirement_rules.STATUS_PARTIAL

    # Related field gets higher partial score than totally unrelated field
    related_field = job_matching_service.calculate_education_match(
        "BS in Finance",
        "",
        "BS in Accounting",
    )
    assert wrong_field["score"] < related_field["score"] < 1.0

    # Matching field with higher degree exceeds with full credit
    overqualified_right_field = job_matching_service.calculate_education_match(
        "Master in Accountancy",
        "",
        "BS in Accounting",
    )
    assert overqualified_right_field["score"] == 1.0
    assert overqualified_right_field["status"] == requirement_rules.STATUS_EXCEEDS


def test_education_unrecognized_text_triggers_manual_review_and_warning_log(caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.job_matching_service"):
        res = job_matching_service.calculate_education_match("xyz", "", "Bachelor's degree")
    assert res["status"] == requirement_rules.STATUS_MANUAL_REVIEW
    assert res["needs_manual_review"] is True
    assert res["score"] == requirement_rules.EDUCATION_MANUAL_REVIEW_SCORE
    assert any("xyz" in rec.message for rec in caplog.records)


def test_education_aliases_normalize_to_shared_1_to_8_ranking():
    expected = {
        "Elementary graduate": 1,
        "Junior High School": 2,
        "SHS": 3,
        "K-12": 3,
        "Grade 12": 3,
        "TESDA NC II": 4,
        "Vocational Course": 4,
        "Associate Degree": 5,
        "B.S.": 6,
        "BSBA": 6,
        "BSIT": 6,
        "AB Psychology": 6,
        "MBA": 7,
        "M.S.": 7,
        "Ph.D.": 8,
    }
    for text, lvl in expected.items():
        parsed = requirement_rules.parse_education_level(text, is_job_requirement=True)
        assert parsed["recognized"] is True, f"Not recognized: {text}"
        assert parsed["level"] == lvl, f"Expected level {lvl} for {text!r}, got {parsed}"


def test_experience_hierarchy_and_phrases():
    for req_phrase in ("2 years", "at least 2 years", "2+ years", "minimum of 2 years"):
        met = job_matching_service.calculate_experience_match(5, "", req_phrase)
        assert met["score"] == 1.0
        assert met["below_minimum"] is False
        assert met["status"] == requirement_rules.STATUS_EXCEEDS

    short = job_matching_service.calculate_experience_match(2, "", "5 years")
    assert short["score"] == 0.4
    assert short["below_minimum"] is True
    assert short["status"] == requirement_rules.STATUS_PARTIAL


def test_graded_certification_hierarchy_and_skills_non_hierarchical():
    # TESDA NC III satisfies NC II
    exceeds = job_matching_service.calculate_certifications_match(
        "TESDA SMAW NC III",
        "",
        "TESDA SMAW NC II",
    )
    assert exceeds["score"] == 1.0
    assert exceeds["status"] == requirement_rules.STATUS_EXCEEDS

    # TESDA NC I is below NC II (partial credit, not 1.0)
    below = job_matching_service.calculate_certifications_match(
        "TESDA SMAW NC I",
        "",
        "TESDA SMAW NC II",
    )
    assert 0.0 < below["score"] < 1.0
    assert below["status"] == requirement_rules.STATUS_PARTIAL

    # Different trade domain with higher NC level must not match
    mismatch = job_matching_service.calculate_certifications_match(
        "TESDA Cookery NC III",
        "",
        "TESDA SMAW NC II",
    )
    assert mismatch["score"] == 0.0
    assert mismatch["status"] == requirement_rules.STATUS_DOES_NOT_MEET

    # Skills remain exact/fuzzy match / no-match (no invented hierarchy)
    skills = job_matching_service.calculate_skills_match("Java", "Python")
    assert skills["score"] == 0.0
    assert skills["status"] == requirement_rules.STATUS_DOES_NOT_MEET


# ─── Bug 2: No-Value Normalization & Weighting ─────────────────────────────────

@pytest.mark.parametrize(
    "no_val",
    ["None", "none", "N/A", "n/a", "No requirement", "", "   ", "-", "--", "wala", "nil", "null", "none required.", "any"],
)
def test_no_value_cert_requirement_gives_full_credit_as_not_required(no_val):
    for cand_cert in ("", "None", "Food Safety Certificate"):
        res = job_matching_service.calculate_certifications_match(
            cand_cert,
            "Production worker role.",
            no_val,
        )
        assert res["score"] == 1.0, f"Failed for req={no_val!r}, cand={cand_cert!r}"
        assert res["status"] == requirement_rules.STATUS_NOT_REQUIRED
        assert res["has_requirement"] is False
        assert res["reason"].startswith("Not required:")


def test_required_cert_with_candidate_none_scores_zero_with_clear_reason():
    res = job_matching_service.calculate_certifications_match(
        "None",
        "",
        "TESDA NC II",
    )
    assert res["score"] == 0.0
    assert res["status"] == requirement_rules.STATUS_DOES_NOT_MEET
    assert "no certification found" in res["reason"].lower()
    assert res["candidate_certifications"] == "None provided"


def test_partial_phrase_containing_none_is_not_treated_as_empty():
    text = "None of the above, but must know Excel"
    assert requirement_rules.is_no_value(text) is False
    assert requirement_rules.normalize_requirement_text(text) == text

    res = job_matching_service.calculate_certifications_match("None", "", text)
    assert res["status"] == requirement_rules.STATUS_DOES_NOT_MEET
    assert res["score"] == 0.0


def test_no_value_tokens_excluded_from_keywords_and_resume_cleanup():
    assert job_matching_service._tokenize_skills("Python, None, N/A, wala, -") == ["python"]
    assert "none" not in job_matching_service._extract_domain_keywords("None N/A wala Python")

    payload = {
        "skills": ["None", "Excel", "N/A", "wala"],
        "company": "None",
        "degree": "N/A",
        "certifications": "Wala",
        "candidate_certifications": "-",
    }
    _sanitize_application_payload(payload)
    assert payload["skills"] == ["Excel"]
    assert payload["company"] is None
    assert payload["degree"] is None
    assert payload["certifications"] is None


def test_all_criteria_not_required_computes_safely_without_division_by_zero():
    job = {
        "job_id": "JOB-NO-REQ",
        "job_title": "Utility Helper",
        "department": "Operations",
        "description": "General assistance around plant.",
        "skills_requirements": "None",
        "experience_requirements": "None",
        "education_requirements": "N/A",
        "certifications_requirements": "Wala",
    }
    resume = {
        "fullname": "Juan Dela Cruz",
        "email": "juan@example.com",
        "skills": "",
        "experience": "",
        "education": "",
        "certifications": "None",
        "completeness_score": 100.0,
    }
    res = job_matching_service.calculate_match_score(resume, job, matching_config=DEFAULT_CFG)
    assert res["match_percentage"] == 100.0
    assert res["skills_status"] == requirement_rules.STATUS_NOT_REQUIRED
    assert res["experience_status"] == requirement_rules.STATUS_NOT_REQUIRED
    assert res["education_status"] == requirement_rules.STATUS_NOT_REQUIRED
    assert res["certifications_status"] == requirement_rules.STATUS_NOT_REQUIRED
    assert res["followup_questions"] == []


def test_weights_unchanged_and_hand_computed_total_exact():
    # Default 40/30/15/10/5 weights:
    # Case A: 50% skills + 92.5% exp (90% semantic role relevance) + 100% edu + 100% cert (Not required) + 100% completeness
    # = 50*0.40 + 92.5*0.30 + 100*0.15 + 100*0.10 + 100*0.05 = 77.75 -> 77.8%
    job = {
        "job_id": "JOB-HAND-80",
        "job_title": "Production Operator",
        "department": "Manufacturing",
        "description": "Operates tile machinery and quality checks.",
        "skills_requirements": "machine handling, SQL",
        "experience_requirements": "2 years",
        "education_requirements": "Senior High School",
        "certifications_requirements": "None",
    }
    resume = {
        "fullname": "Maria Santos",
        "skills": "machine handling",
        "experience": "Production Operator at Ceramic Plant (2020 - 2023)",
        "years_experience": 3,
        "education": "Bachelor of Science in Industrial Engineering",
        "certifications": "None",
        "completeness_score": 100.0,
    }
    res = job_matching_service.calculate_match_score(resume, job, matching_config=DEFAULT_CFG)
    assert res["skills_score"] == 50.0
    assert res["certifications_score"] == 100.0
    assert res["certifications_status"] == requirement_rules.STATUS_NOT_REQUIRED
    assert res["education_score"] == 100.0
    assert res["education_status"] == requirement_rules.STATUS_EXCEEDS
    assert res["applied_weights"] == {
        "skills": 40,
        "experience": 30,
        "education": 15,
        "certifications": 10,
        "completeness": 5,
    }
    expected_a = round(
        res["skills_score"] * 0.40
        + res["experience_score"] * 0.30
        + res["education_score"] * 0.15
        + res["certifications_score"] * 0.10
        + res["completeness_score"] * 0.05,
        1,
    )
    assert res["match_percentage"] == expected_a
    assert res["match_percentage"] == 77.8

    # Case B: experience_requirements="None" (100% exp) & certs="None" (100% cert):
    # 50*0.40 + 100*0.30 + 100*0.15 + 100*0.10 + 100*0.05 = exact 80.0%
    job_exp_none = {**job, "experience_requirements": "None"}
    res_b = job_matching_service.calculate_match_score(resume, job_exp_none, matching_config=DEFAULT_CFG)
    assert res_b["experience_score"] == 100.0
    assert res_b["certifications_score"] == 100.0
    assert res_b["match_percentage"] == 80.0

    # Sanitization for applicant removes numeric weights while preserving status & plain-language reason
    sanitized = _sanitize_for_applicant(res)
    assert "applied_weights" not in sanitized
    assert sanitized["criteria_evaluations"]["certifications"] == {
        "status": requirement_rules.STATUS_NOT_REQUIRED,
        "has_requirement": False,
        "needs_manual_review": False,
        "reason": res["certifications_reason"],
    }


def test_job_schemas_normalize_no_value_on_create_and_update():
    created = JobCreate(
        job_id="JOB-CLEAN-1",
        job_title="Helper",
        department="Ops",
        job_type="Full-Time",
        location="Bulacan",
        description="Plant support",
        skills_requirements="None",
        education_requirements="  N/A. ",
        experience_requirements="Wala",
        certifications_requirements="No certification required",
    )
    assert created.skills_requirements is None
    assert created.education_requirements is None
    assert created.experience_requirements is None
    assert created.certifications_requirements is None

    real = JobCreate(
        job_id="JOB-CLEAN-2",
        job_title="Analyst",
        department="Ops",
        job_type="Full-Time",
        location="Bulacan",
        description="Data support",
        skills_requirements="None of the above, but must know Excel",
    )
    assert real.skills_requirements == "None of the above, but must know Excel"

    upd = JobUpdate(certifications_requirements="None")
    dumped = upd.model_dump(exclude_unset=True)
    assert dumped == {"certifications_requirements": None}


@pytest.mark.asyncio
async def test_cleanup_script_and_recalculation_preserve_statuses_and_rosters():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        job_legacy = JobDescription(
            job_id="JOB-RECALC-1",
            job_title="Warehouse Staff",
            department="Logistics",
            job_type=JobType.FULL_TIME,
            location="Bulacan",
            description="Warehouse helper",
            skills_requirements="inventory",
            education_requirements="Senior High School",
            experience_requirements="1 year",
            certifications_requirements="None",
        )
        job_keep_phrase = JobDescription(
            job_id="JOB-RECALC-2",
            job_title="Data Clerk",
            department="Admin",
            job_type=JobType.FULL_TIME,
            location="Bulacan",
            description="Clerk",
            skills_requirements="None of the above, but must know Excel",
            education_requirements="Wala",
            certifications_requirements="-",
        )
        db.add_all([job_legacy, job_keep_phrase])
        await db.flush()

        # Existing applicant still has pre-deploy stale score (45.0) and is Shortlisted in a roster
        app = JobApplication(
            job_id=job_legacy.id,
            candidate_name="Ana Reyes",
            candidate_email="ana@example.com",
            skills=["inventory"],
            job_title="Warehouse Staff",
            company="Logistics Co",
            total_experience_months=24,
            degree="Bachelor of Science in Customs Administration",
            certifications="None",
            candidate_certifications="None provided",
            match_score=45.0,
            status="Shortlisted",
        )
        db.add(app)
        await db.flush()

        roster = ShortlistRoster(name="Top Warehouse", job_id=job_legacy.id, created_by="hr@mariwasa.com")
        db.add(roster)
        await db.flush()
        db.add(
            ShortlistRosterItem(
                roster_id=roster.id,
                application_id=app.id,
                stage="Shortlisted",
                added_by="hr@mariwasa.com",
            )
        )
        await db.commit()

        # 1. Existing applicant score stays 45.0 until Admin Recalculate runs
        assert app.match_score == 45.0

        # 2. Cleanup script dry-run does not modify DB
        dry = await cleanup_no_value_job_requirements(db, dry_run=True)
        assert dry["fields_cleaned"] == 3
        await db.refresh(job_legacy)
        assert job_legacy.certifications_requirements == "None"

        # 3. Cleanup script apply converts standalone no-value strings to NULL while keeping real phrase
        applied = await cleanup_no_value_job_requirements(db, dry_run=False)
        assert applied["fields_cleaned"] == 3
        await db.refresh(job_legacy)
        await db.refresh(job_keep_phrase)
        assert job_legacy.certifications_requirements is None
        assert job_keep_phrase.education_requirements is None
        assert job_keep_phrase.certifications_requirements is None
        assert job_keep_phrase.skills_requirements == "None of the above, but must know Excel"

        # 4. Run Admin recalculation with progress callback -> updates scores, preserves status & roster
        progress_calls = []
        summary = await recalculate_all_applications(db, progress_cb=lambda c, t: progress_calls.append((c, t)))
        assert summary["updated_applications"] == 1
        assert progress_calls == [(1, 1)]

        await db.refresh(app)
        assert app.match_score > 90.0
        assert app.education_score == 100.0
        assert app.certifications_score == 100.0
        assert app.status == "Shortlisted"
        roster_entries = (await db.execute(select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == roster.id))).scalars().all()
        assert [e.application_id for e in roster_entries] == [app.id]
        assert roster_entries[0].stage == "Shortlisted"

        # 5. Re-scoring idempotency: running _resume_data_from_application -> calculate_match_score twice yields identical scores
        second = job_matching_service.calculate_match_score(_resume_data_from_application(app), job_legacy)
        assert second["match_percentage"] == app.match_score
        assert second["certifications_score"] == app.certifications_score

    await engine.dispose()


# ─── Regression Tests: Acronym Boundaries, Mariwasa Jobs, Umbrella Fields & Propagation ───

def test_degree_acronym_word_boundaries_do_not_corrupt_fields():
    cases = [
        ("BS Accounting", 6, ["accounting"]),
        ("B.S. in Accounting", 6, ["accounting"]),
        ("BS Chemical Engineering", 6, ["chemical engineering"]),
        ("BS Computer Science", 6, ["computer science"]),
        ("BS Architecture", 6, ["architecture"]),
        ("BS Nursing", 6, ["nursing"]),
        ("MS Engineering", 7, ["engineering"]),
        ("MA Economics", 7, ["economics"]),
        ("M.S. in Chemistry", 7, ["chemistry"]),
        ("Ph.D. in Chemistry", 8, ["chemistry"]),
    ]
    for raw_text, expected_lvl, expected_fields in cases:
        parsed = requirement_rules.parse_education_level(raw_text, is_job_requirement=True)
        assert parsed["recognized"] is True, f"Failed to recognize {raw_text!r}: {parsed}"
        assert parsed["level"] == expected_lvl, f"Level mismatch for {raw_text!r}: {parsed}"
        for ef in expected_fields:
            assert ef in parsed["field_options"], f"Expected field {ef!r} in {parsed['field_options']} for {raw_text!r}"

    # Verify end-to-end scoring does NOT fall through to Manual Review
    acc_match = job_matching_service.calculate_education_match("BS Accounting", "", "B.S. in Accounting")
    assert acc_match["score"] == 1.0
    assert acc_match["status"] == requirement_rules.STATUS_MEETS
    assert acc_match["needs_manual_review"] is False


def test_all_seeded_mariwasa_jobs_parse_without_corrupted_fields():
    from seed_mariwasa_jobs import JOBS

    forbidden_corruptions = {
        "chemistry engineering",
        "accounting management",
        "information technology science",
        "supply chain management administration",
        "statistics science",
        "mathematics science",
        "economics science",
        "environmental science engineering",
    }

    for job in JOBS:
        edu_req = job.get("education_requirements")
        parsed = requirement_rules.parse_education_level(edu_req, is_job_requirement=True)
        assert parsed["recognized"] is True, f"Unrecognized seeded job edu for {job['job_title']}: {edu_req!r}"
        assert parsed["level"] is not None
        assert not (set(parsed["field_options"]) & forbidden_corruptions), (
            f"Corrupted fields {parsed['field_options']} for {job['job_title']}"
        )

    # Specific multi-field & law cases
    training_officer = next(j for j in JOBS if j["job_title"] == "Training Officer")
    to_parsed = requirement_rules.parse_education_level(training_officer["education_requirements"], is_job_requirement=True)
    assert "psychology" in to_parsed["field_options"]
    assert "education" in to_parsed["field_options"]

    lawyer = next(j for j in JOBS if j["job_title"] == "Corporate Lawyer")
    law_parsed = requirement_rules.parse_education_level(lawyer["education_requirements"], is_job_requirement=True)
    assert "law" in law_parsed["field_options"]


def test_umbrella_field_exact_matching():
    res_meet = job_matching_service.calculate_education_match(
        "BS Civil Engineering",
        "",
        "Bachelor's degree in Engineering",
    )
    assert res_meet["score"] == 1.0
    assert res_meet["status"] == requirement_rules.STATUS_MEETS

    res_exceeds = job_matching_service.calculate_education_match(
        "Master of Science in Mechanical Engineering",
        "",
        "Bachelor's degree in Engineering",
    )
    assert res_exceeds["score"] == 1.0
    assert res_exceeds["status"] == requirement_rules.STATUS_EXCEEDS

    res_sc = job_matching_service.calculate_education_match(
        "BS Supply Chain Management",
        "",
        "Bachelor's degree in Business or Supply Chain",
    )
    assert res_sc["score"] == 1.0
    assert res_sc["status"] == requirement_rules.STATUS_MEETS


def test_configurable_education_partial_score_modes():
    assert requirement_rules.compute_education_partial_score(3, 6, mode="proportional") == 0.5
    assert requirement_rules.compute_education_partial_score(3, 6, mode="step") == 0.25
    assert requirement_rules.compute_education_partial_score(3, 6, mode="strict_zero") == 0.0
    assert requirement_rules.compute_education_partial_score(6, 6, mode="step") == 1.0


def test_graded_certifications_strip_qualifiers():
    bb_vs_gb = job_matching_service.calculate_certifications_match(
        "Lean Six Sigma Black Belt",
        "",
        "Lean Six Sigma Green Belt preferred",
    )
    assert bb_vs_gb["score"] == 1.0
    assert bb_vs_gb["status"] == requirement_rules.STATUS_EXCEEDS

    smaw_ok = job_matching_service.calculate_certifications_match(
        "SMAW NC IV",
        "",
        "SMAW NC II required",
    )
    assert smaw_ok["score"] == 1.0
    assert smaw_ok["status"] == requirement_rules.STATUS_EXCEEDS

    trade_mismatch = job_matching_service.calculate_certifications_match(
        "SMAW NC IV",
        "",
        "Electrical Installation NC II",
    )
    assert trade_mismatch["score"] == 0.0
    assert trade_mismatch["status"] == requirement_rules.STATUS_DOES_NOT_MEET


def test_schemas_preserve_education_entries_and_compute_statuses():
    from app.schemas.job_matching_schema import ResumeMatchRequest
    from app.schemas.job_application_schema import JobApplicationResponse
    from datetime import datetime

    req = ResumeMatchRequest(
        degree="BSIT",
        education_entries=[
            {"education_level": "Tertiary / College", "degree_or_course": "BSIT", "status": "Undergraduate / College Level"}
        ],
        highest_educational_attainment="Senior High School (SHS)",
    )
    dumped = req.model_dump()
    assert dumped["highest_educational_attainment"] == "Senior High School (SHS)"
    assert isinstance(dumped["education_entries"], list) and len(dumped["education_entries"]) == 1

    now = datetime.utcnow()
    app_resp = JobApplicationResponse(
        id=1,
        job_id=2,
        candidate_name="Test User",
        candidate_email="test@example.com",
        status="Submitted",
        created_at=now,
        updated_at=now,
        education_reason="Needs manual review: Candidate education ('xyz') could not be automatically verified.",
        skills_reason="Meets requirement: Matched all required skills.",
    )
    assert app_resp.education_status == requirement_rules.STATUS_MANUAL_REVIEW
    assert app_resp.education_needs_manual_review is True
    assert app_resp.skills_status == requirement_rules.STATUS_MEETS


def test_extractor_recognizes_nc_iv_and_preserves_high_school_degree():
    from app.extractors.content.education_extractor import extract_structured_education
    from app.extractors.content.content_extractor import extract_content

    nc4_resume = """
    EDUCATION
    SMAW NC IV | TESDA Regional Training Center | 2023
    """
    structured = extract_structured_education(nc4_resume)
    entries = structured.get("education_entries", [])
    assert any(
        e.get("education_level") == "Vocational / Technical (TESDA)"
        and "NC IV" in (e.get("degree_or_course") or "")
        for e in entries
    )

    hs_resume = """
    JUAN DELA CRUZ
    juan@example.com | 09171234567

    EDUCATION
    High School Graduate
    Batangas National High School
    2016 - 2020
    """
    content = extract_content(hs_resume)
    assert content.get("highest_degree") == "HIGH SCHOOL"


@pytest.mark.asyncio
async def test_shortlist_roster_and_comparison_expose_shared_education_statuses():
    from app.services.shortlist_roster_service import get_shortlist_roster_by_id
    from app.services.candidate_comparison_service import compare_candidates_service

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        job = JobDescription(
            job_id="JOB-PROP-1",
            job_title="Warehouse Staff",
            department="Logistics",
            job_type=JobType.FULL_TIME,
            location="Bulacan",
            description="Warehouse operations.",
            skills_requirements="inventory",
            education_requirements="Senior High School graduate",
            experience_requirements="1 year",
            certifications_requirements=None,
        )
        db.add(job)
        await db.flush()

        # Candidate 1 has higher degree (Exceeds); legacy row with None education_reason to test fallback
        app1 = JobApplication(
            job_id=job.id,
            candidate_name="Maria Clara",
            candidate_email="maria@example.com",
            skills=["inventory"],
            job_title="Warehouse Staff",
            company="Co A",
            total_experience_months=24,
            degree="BS Business Administration",
            highest_educational_attainment="Tertiary / College",
            match_score=95.0,
            status="Shortlisted",
        )
        # Candidate 2 has unrecognized education -> Needs manual review
        app2 = JobApplication(
            job_id=job.id,
            candidate_name="Pedro Penduko",
            candidate_email="pedro@example.com",
            skills=["inventory"],
            job_title="Warehouse Staff",
            company="Co B",
            total_experience_months=24,
            degree="xyz-unknown-cred",
            education_reason="Needs manual review: Candidate education ('xyz-unknown-cred') could not be automatically verified.",
            match_score=80.0,
            status="Shortlisted",
        )
        db.add_all([app1, app2])
        await db.flush()

        roster = ShortlistRoster(name="Warehouse Shortlist", job_id=job.id, created_by="hr@mariwasa.com")
        db.add(roster)
        await db.flush()
        db.add_all([
            ShortlistRosterItem(roster_id=roster.id, application_id=app1.id, stage="Shortlisted", added_by="hr@mariwasa.com"),
            ShortlistRosterItem(roster_id=roster.id, application_id=app2.id, stage="Shortlisted", added_by="hr@mariwasa.com"),
        ])
        await db.commit()

        roster_data = await get_shortlist_roster_by_id(db, roster.id)
        assert roster_data is not None
        by_name = {it["candidate_name"]: it for it in roster_data["items"]}
        assert by_name["Maria Clara"]["education_status"] == requirement_rules.STATUS_EXCEEDS
        assert by_name["Maria Clara"]["education_needs_manual_review"] is False
        assert by_name["Pedro Penduko"]["education_status"] == requirement_rules.STATUS_MANUAL_REVIEW
        assert by_name["Pedro Penduko"]["education_needs_manual_review"] is True

        cmp_data = await compare_candidates_service(db, [app1.id, app2.id], reference_job_id=job.id)
        cmp_by_name = {c["name"]: c for c in cmp_data["candidates"]}
        assert cmp_by_name["Maria Clara"]["education_status"] == requirement_rules.STATUS_EXCEEDS
        assert cmp_by_name["Maria Clara"]["education_needs_manual_review"] is False
        assert cmp_by_name["Pedro Penduko"]["education_status"] == requirement_rules.STATUS_MANUAL_REVIEW
        assert cmp_by_name["Pedro Penduko"]["education_needs_manual_review"] is True

        nlp_cmp = job_matching_service.nlp_compare_candidates(
            {
                "job_title": job.job_title,
                "skills_requirements": job.skills_requirements,
                "education_requirements": job.education_requirements,
                "experience_requirements": job.experience_requirements,
            },
            [
                {"candidate_name": "Maria Clara", "resume_data": _resume_data_from_application(app1)},
                {"candidate_name": "Pedro Penduko", "resume_data": _resume_data_from_application(app2)},
            ],
        )
        nlp_by_name = {c["candidate_name"]: c for c in nlp_cmp["ranked_candidates"]}
        assert nlp_by_name["Maria Clara"]["education_status"] == requirement_rules.STATUS_EXCEEDS
        assert nlp_by_name["Pedro Penduko"]["education_status"] == requirement_rules.STATUS_MANUAL_REVIEW
        assert nlp_by_name["Pedro Penduko"]["education_needs_manual_review"] is True

    await engine.dispose()
