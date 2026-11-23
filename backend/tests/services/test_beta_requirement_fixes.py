from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.extractors.content.education_extractor import extract_structured_education
from app.extractors.content.skills_extractor import extract_skills_list
from app.extractors.text_normalization import repair_line_hyphenation
from app.services.requirement_rules import education_display_label, parse_education_level
from app.services.requirement_confirmation import evaluate_requirements, confirmation_questions, apply_confirmations
from app.services.job_matching_service import _tokenize_skills, calculate_match_score, calculate_education_match


SAMPLE = """EDUCATION
STI Colleges Ortigas-Cainta, June 2023 - Expected 2027
Bachelor of Science in Computer Science
4th Year College Student
"""


def test_basagre_is_one_ongoing_entry_with_campus_and_expected_year():
    entries = extract_structured_education(SAMPLE)["education_entries"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["institution_name"] == "STI Colleges Ortigas-Cainta"
    assert entry["start_year"] == "2023"
    assert entry["end_year"] == "2027"
    assert entry["status"] == "Undergraduate / In progress"
    assert education_display_label("", entries) == "Bachelor's degree in Computer Science (4th year, expected 2027)"
    assert parse_education_level("", entries=entries)["level"] == 3


@pytest.mark.parametrize("degree", ["Bachelor of Science in Computer Science", "BS Computer Science", "B.S. in Computer Science", "Bachelor of Science\nComputer Science"])
def test_degree_labels_do_not_duplicate_field(degree):
    entries = extract_structured_education(f"EDUCATION\nSTI Colleges\n{degree}\nGraduated 2020")["education_entries"]
    assert len(entries) == 1
    assert education_display_label(degree, entries) == "Bachelor's degree in Computer Science"
    result = calculate_education_match(degree, "", "BS Computer Science", entries)
    assert result["score"] == 1


def test_placeholders_and_start_year_do_not_invent_degree_or_graduation():
    assert extract_structured_education("EDUCATION\nDegree / Course")["education_entries"] == []
    entries = extract_structured_education("EDUCATION\nSTI Colleges\n2023")["education_entries"]
    assert entries[0]["status"] != "Graduated"
    assert not entries[0]["degree_or_course"]


def test_duplicate_education_blocks_merge():
    entries = extract_structured_education(SAMPLE + "\nSTI Colleges Ortigas-Cainta\nBS Computer Science\n2023 - Expected 2027")["education_entries"]
    assert len(entries) == 1


def test_hyphenated_skills_and_pdf_wrap():
    sentence = "Core Skills: Communication, attention to detail, time management, problem-\nsolving, adaptability"
    skills = extract_skills_list(sentence)
    keys = _tokenize_skills(skills)
    assert "problem solving" in keys
    assert "problem" not in keys and "solving" not in keys
    assert _tokenize_skills("Problem-Solving | problem solving | Problem Solving") == ["problem solving"] * 3
    assert _tokenize_skills("Wi-Fi, E-commerce; Back-end / Point-of-Sale\nMulti-tasking") == ["wi fi", "e commerce", "back end", "point of sale", "multi tasking"]
    assert repair_line_hyphenation("communi-\ncation") == "communication"


def job(**kwargs):
    return SimpleNamespace(job_id="JOB-1", job_title="Support Specialist", description="", department="Support", location="", job_type=None,
        skills_requirements=kwargs.get("skills", "CRM software, Data Entry"),
        certifications_requirements=kwargs.get("certifications", ""), experience_requirements=kwargs.get("experience", ""), education_requirements="")


def test_all_requirements_asked_including_possible_related_matches():
    target = job(skills="Communication, Billing, Reporting, Research, Scheduling, CRM software, Data Entry", certifications="License A; License B", experience="Customer support; Invoicing")
    rows = evaluate_requirements({"skills": "Kustomer, Excel"}, target)
    questions = confirmation_questions(rows, target)
    assert sum(len(q["items"]) for q in questions) == 11
    assert all(q["type"] == "requirement_group" for q in questions)
    assert next(r for r in rows if r["requirement"] == "CRM software")["status"] == "Possible match"
    assert next(r for r in rows if r["requirement"] == "Data Entry")["status"] == "Possible match"
    assert not any(r["status"] == "Does not meet" for r in rows)


def test_weak_similarity_never_suppresses_question_and_map_is_configurable():
    rows = evaluate_requirements({"skills": "Data, CRM"}, job())
    assert len(confirmation_questions(rows, job())[0]["items"]) == 2
    rows = evaluate_requirements({"skills": "Custom Tool"}, job(), related_terms={"crm software": ["Custom Tool"]})
    assert rows[0]["status"] == "Possible match"


def score(resume, target):
    # Keep these tests deterministic and avoid model training or feedback writes.
    with patch("app.ml_engine.get_production_model", side_effect=RuntimeError("ML disabled in regression test")):
        return calculate_match_score(resume, target, matching_config={"weights": {}, "thresholds": {}}, log_prediction=False)


def test_confirmations_score_like_resume_and_no_is_the_only_failure():
    target = job()
    responses = [
        {"field": "skills", "requirement": "CRM software", "answer": "yes", "details": "Used Kustomer"},
        {"field": "skills", "requirement": "Data Entry", "answer": "some"},
    ]
    confirmed = score({"skills": "", "clarification_responses": responses}, target)
    extracted = score({"skills": "CRM software, Data Entry"}, target)
    assert confirmed["skills_score"] == extracted["skills_score"] == 100
    assert all(r["source"] == "Confirmed by applicant" for r in confirmed["requirement_evaluations"])
    unanswered = score({"skills": "Kustomer, Excel"}, target)
    assert unanswered["skills_status"] == "Not confirmed"
    assert unanswered["missing_skills"] == []
    assert len(unanswered["not_confirmed_skills"]) == 2
    responses[1]["answer"] = "no"
    denied = score({"skills": "", "clarification_responses": responses}, target)
    assert denied["missing_skills"] == ["Data Entry"]
    assert denied["skills_score"] == 50


def test_certification_and_experience_answers_reach_matching_inputs():
    target = job(certifications="License A", experience="Customer support")
    resume = {"clarification_responses": [
        {"field": "certifications", "requirement": "License A", "answer": "yes"},
        {"field": "experience", "requirement": "Customer support", "answer": "yes", "years": 3, "details": "Handled tickets"},
    ]}
    resolved = apply_confirmations(resume, evaluate_requirements(resume, target))
    assert resolved["certifications"] == "License A"
    assert "Handled tickets" in resolved["experience"]
    assert resolved["years_experience"] == 3


@pytest.mark.asyncio
async def test_confirmation_migration_is_idempotent_and_preserves_status():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    from migrations.add_requirement_confirmations import upgrade
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE job_applications (id INTEGER PRIMARY KEY, status TEXT)"))
            await conn.execute(text("INSERT INTO job_applications VALUES (1, 'SHORTLISTED')"))
            await upgrade(conn)
            await upgrade(conn)
            row = (await conn.execute(text("SELECT status, clarification_responses, requirement_evaluations FROM job_applications"))).first()
            assert tuple(row) == ("SHORTLISTED", None, None)
    finally:
        await engine.dispose()


def test_persisted_answers_survive_background_rescoring():
    from app.models.job_application import JobApplication
    from app.services.job_application_service import _resume_data_from_application, _apply_experience_gap_evaluation
    data = {"skills": [], "clarification_responses": [{"field": "skills", "requirement": "CRM software", "answer": "yes"}]}
    _apply_experience_gap_evaluation(data, job())
    application = JobApplication(candidate_name="Test", candidate_email="test@example.com", status="SHORTLISTED", **data)
    resume = _resume_data_from_application(application)
    result = score(resume, job())
    assert result["skills_score"] == 50
    assert result["requirement_evaluations"][0]["source"] == "Confirmed by applicant"
    assert application.status == "SHORTLISTED"
