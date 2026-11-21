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


def test_skill_synonym_matching_ml_and_qc():
    res = job_matching_service.calculate_skills_match("ML, QC", "Machine Learning, Quality")
    assert res["score"] == 1.0
    assert res["missing"] == []
    res_rev = job_matching_service.calculate_skills_match("Machine Learning, Quality Control", "ML, QC")
    assert res_rev["score"] == 1.0
    assert res_rev["missing"] == []


def test_job_specific_followup_questions_differ_for_j1_and_j3():
    same_resume = {
        "fullname": "Juan Dela Cruz",
        "skills": "Quality Control, Documentation",
        "experience": "General Staff",
        "relevance": "",
        "years_experience": 0,
        "education": "High School Diploma",
        "highest_degree": "High School",
        "certifications": [],
        "location": "Laguna",
    }
    j1 = {
        "job_id": "J1",
        "job_title": "Production Supervisor",
        "department": "Manufacturing",
        "description": "Oversee kiln operations, tile manufacturing lines, and safety compliance.",
        "skills_requirements": "Production Planning, Lean Manufacturing, Six Sigma",
        "experience_requirements": "3+ years in manufacturing supervision",
        "education_requirements": "Bachelor's Degree in Industrial Engineering",
        "certifications_requirements": "COSH Safety Officer",
    }
    j3 = {
        "job_id": "J3",
        "job_title": "HR Generalist",
        "department": "Human Resources",
        "description": "Manage talent acquisition, payroll processing, and DOLE labor compliance.",
        "skills_requirements": "Recruitment, Payroll, HRIS, Onboarding",
        "experience_requirements": "2+ years in human resources",
        "education_requirements": "Bachelor's Degree in Psychology or HRDM",
        "certifications_requirements": "CHRP",
    }
    cfg = {"weights": {}, "thresholds": {}}

    res_j1 = job_matching_service.calculate_match_score(same_resume, j1, matching_config=cfg)
    res_j3 = job_matching_service.calculate_match_score(same_resume, j3, matching_config=cfg)

    q_j1 = res_j1.get("followup_questions") or []
    q_j3 = res_j3.get("followup_questions") or []
    assert len(q_j1) >= 2
    assert len(q_j3) >= 2
    assert q_j1 == res_j1.get("clarification_questions")
    assert q_j3 == res_j3.get("clarification_questions")

    texts_j1 = [q["question"] for q in q_j1]
    texts_j3 = [q["question"] for q in q_j3]
    ids_j1 = {q["id"] for q in q_j1}
    ids_j3 = {q["id"] for q in q_j3}

    assert texts_j1 != texts_j3
    assert ids_j1.isdisjoint(ids_j3)
    assert any("Production Supervisor" in t or "manufacturing" in t.lower() for t in texts_j1)
    assert any("HR Generalist" in t or "hr" in t.lower() or "recruitment" in t.lower() for t in texts_j3)
    assert all(q.get("job_id") == "J1" for q in q_j1)
    assert all(q.get("job_id") == "J3" for q in q_j3)


def test_insufficient_experience_1yr_vs_3yr_reports_gap():
    exp_short = job_matching_service.calculate_experience_match(
        resume_years=1,
        job_description="Production Operator",
        experience_req="3yrs",
    )
    assert exp_short["required_years"] == 3
    assert exp_short["candidate_years"] == 1
    assert exp_short["below_minimum"] is True
    assert exp_short["gap_years"] == 2
    assert "experience below minimum" in exp_short["reason"].lower()

    # Range strings such as "3-5 years" must resolve minimum bound 3 (never 35)
    exp_range = job_matching_service.calculate_experience_match(
        resume_years=1,
        job_description="Production Supervisor",
        experience_req="3-5 years supervisory experience in a manufacturing plant",
    )
    assert exp_range["required_years"] == 3
    assert exp_range["below_minimum"] is True
    assert exp_range["gap_years"] == 2

    j1 = {
        "job_id": "J1",
        "job_title": "Production Operator (Manufacturing)",
        "department": "Manufacturing",
        "description": "Operates tile production equipment and enforces quality checks.",
        "skills_requirements": "Production Planning, Quality Control, Machine Operation",
        "experience_requirements": "3yrs",
    }
    applicant_1yr = {
        "fullname": "Applicant 1yr",
        "skills": "Production Planning, Quality Control, Machine Operation",
        "experience": "Production Operator at ABC Mfg (1 year)",
        "years_experience": 1,
        "education": "High School Diploma",
    }
    cfg = {"weights": {}, "thresholds": {}}
    res = job_matching_service.calculate_match_score(applicant_1yr, j1, matching_config=cfg)

    assert res["experience_below_minimum"] is True
    assert res["experience_gap_years"] == 2
    assert "experience below minimum" in (res.get("experience_gaps") or "").lower()
    assert "experience below minimum" in (res.get("experience_reason") or "").lower()
    assert any("experience below minimum" in w.lower() for w in (res.get("weaknesses") or []))
    assert res["requirement_gaps"]
    assert res["experience_score"] < 50.0

    applicant_4yr = {**applicant_1yr, "years_experience": 4, "experience": "Production Operator at ABC Mfg (4 years)"}
    res_ok = job_matching_service.calculate_match_score(applicant_4yr, j1, matching_config=cfg)
    assert res_ok["experience_below_minimum"] is False
    assert res_ok["experience_gap_years"] == 0
    assert res_ok["experience_gaps"] is None
    assert res_ok["requirement_gaps"] == []


def test_followup_questions_skip_criteria_already_covered_in_resume():
    job = {
        "job_id": "J_PROD",
        "job_title": "Production Operator (Manufacturing)",
        "department": "Manufacturing",
        "description": "Operate CNC and injection molding machinery, conduct in-process quality checks, and perform preventive maintenance.",
        "skills_requirements": "CNC Operation, Injection Molding, Quality Control, Preventive Maintenance",
        "experience_requirements": "3+ years",
        "certifications_requirements": "None",
    }
    resume_covered = {
        "fullname": "Juan Dela Cruz",
        "skills": "CNC Operation, Injection Molding, Quality Control, Preventive Maintenance, Calipers",
        "experience": (
            "Senior Production Operator — Laguna Auto Parts Manufacturing Corp. June 2024 – Present (2 years) "
            "Operated automated CNC and injection molding machinery to meet daily quota of 1,500+ units. "
            "Conducted hourly in-process quality checks using calipers and micrometers. "
            "Performed preventive maintenance, tooling changeovers, and troubleshooting. "
            "Production Operator — Rizal Packaging & Industrial Solutions Inc. June 2022 – June 2024 (2 years)"
        ),
        "years_experience": 4,
        "education": "Technical Vocational Graduate",
    }
    cfg = {"weights": {}, "thresholds": {}}
    res_covered = job_matching_service.calculate_match_score(resume_covered, job, matching_config=cfg)
    fields_covered = {q["field"] for q in res_covered.get("clarification_questions", [])}

    assert "years_experience" not in fields_covered
    assert "skills" not in fields_covered
    assert "relevance" not in fields_covered

    # Even if structured years_experience=0 is passed when dated experience text/entries exist, do not ask for years
    resume_dated_text_only = {
        **resume_covered,
        "years_experience": 0,
        "work_experiences": [
            {
                "job_title": "Senior Production Operator",
                "company_name": "Laguna Auto Parts Manufacturing Corp.",
                "start_date": "June 2024",
                "is_current": True,
                "responsibilities": "Operated CNC machinery and conducted quality checks.",
            }
        ],
    }
    res_dated = job_matching_service.calculate_match_score(resume_dated_text_only, job, matching_config=cfg)
    fields_dated = {q["field"] for q in res_dated.get("clarification_questions", [])}
    assert "years_experience" not in fields_dated

    # Resume missing years, missing required skills, and lacking relevant experience should still get follow-ups
    resume_missing = {
        "fullname": "New Applicant",
        "skills": "Customer Service",
        "experience": "",
        "years_experience": 0,
        "education": "High School",
    }
    res_missing = job_matching_service.calculate_match_score(resume_missing, job, matching_config=cfg)
    fields_missing = {q["field"] for q in res_missing.get("clarification_questions", [])}
    assert "years_experience" in fields_missing
    assert "skills" in fields_missing
    assert "relevance" in fields_missing


def test_irrelevant_work_experience_not_counted_as_directly_relevant():
    """
    Regression test: having a work experience entry (with transferable soft skills or
    common words like 'maintained', 'inquiries', 'retail', 'three', 'posts') must NOT
    automatically count as '1 work experience(s) are directly relevant' when the role
    is unrelated to the target position.
    """
    unrelated_cases = [
        (
            "Cashier at Jollibee (2022 - 2024) - Responsibilities: Handled customer payments, operated POS, maintained cleanliness",
            "Cashier, Customer Service",
            {
                "job_id": "J_CHEM",
                "job_title": "R&D Chemist",
                "department": "R&D",
                "description": "Creates new mixtures for ceramic tiles and tests materials in the laboratory.",
                "skills_requirements": "Chemical analysis, Material testing, Formulation, Data Analysis",
                "experience_requirements": "2 years",
            },
        ),
        (
            "OJT Intern at Barangay Hall (2023) - Responsibilities: Filed documents, encoded resident records, answered inquiries",
            "MS Word, Filing",
            {
                "job_id": "J_DES",
                "job_title": "Graphic Designer",
                "department": "Marketing",
                "description": "Designs advertising materials and layouts for social media and print.",
                "skills_requirements": "Adobe Creative Suite, Layout design, Typography, Creativity",
                "experience_requirements": "2 years",
            },
        ),
        (
            "Sales Clerk at SM Store (2022 - 2024) - Responsibilities: Assisted shoppers, arranged retail display, processed returns",
            "Sales, Retail, Customer Handling",
            {
                "job_id": "J_DATA",
                "job_title": "Data Analyst",
                "department": "Strategy and Planning",
                "description": "Looks at our sales and the market to help company leaders make smart choices.",
                "skills_requirements": "SQL, Python, Tableau, Statistical Analysis",
                "experience_requirements": "2 years",
            },
        ),
        (
            "Service Crew at McDonalds (2021 - 2023) - Responsibilities: Prepared food orders, assisted customers, maintained kitchen",
            "Food Service, Teamwork, Communication",
            {
                "job_id": "J_DEV",
                "job_title": "Software Developer",
                "department": "IT",
                "description": "Builds and fixes backend APIs and web applications for three internal teams.",
                "skills_requirements": "Python, React, SQL, API Development",
                "experience_requirements": "2 years",
            },
        ),
    ]

    cfg = {"weights": {}, "thresholds": {}}
    for exp_text, skills_text, job in unrelated_cases:
        rel = job_matching_service.calculate_experience_relevance(
            exp_text, skills_text, job["job_title"], job["description"] + " " + job["skills_requirements"]
        )
        assert rel["relevant_count"] == 0, f"Expected 0 relevant for {exp_text} vs {job['job_title']}, got: {rel}"
        assert rel["highly_relevant_count"] == 0
        assert rel["relevance_score"] == 0.0
        assert rel["relevance_level"] == "Irrelevant"

        match_res = job_matching_service.calculate_match_score(
            {
                "fullname": "Applicant",
                "skills": skills_text,
                "experience": exp_text,
                "years_experience": 2,
                "education": "Bachelor's Degree",
            },
            job,
            matching_config=cfg,
        )
        strengths_text = " ".join(match_res.get("strengths") or []).lower()
        assert "directly relevant" not in strengths_text, f"False 'directly relevant' strength for {job['job_title']}: {match_res['strengths']}"
        assert any("none of the work experience entries are relevant" in w.lower() for w in (match_res.get("weaknesses") or []))
        assert "none of the 1 work experience(s) are relevant" in (match_res.get("experience_reason") or "").lower()
        assert match_res["experience_score"] <= 10.0


def test_directly_and_partially_relevant_work_experience_distinction():
    cfg = {"weights": {}, "thresholds": {}}

    # Directly relevant experience must still be detected as directly relevant
    dev_job = {
        "job_id": "J_SWE",
        "job_title": "Software Developer",
        "department": "IT",
        "description": "Builds and maintains web applications and REST APIs.",
        "skills_requirements": "Python, FastAPI, React, SQL",
        "experience_requirements": "2 years",
    }
    dev_resume = {
        "fullname": "Dev Candidate",
        "skills": "Python, FastAPI, React, SQL",
        "experience": "",
        "work_experiences": [
            {
                "job_title": "Backend Software Developer",
                "company_name": "Tech Corp",
                "responsibilities": ["Built Python FastAPI microservices and SQL database schemas."],
            }
        ],
        "years_experience": 3,
        "education": "Bachelor of Science in Computer Science",
    }
    res_direct = job_matching_service.calculate_match_score(dev_resume, dev_job, matching_config=cfg)
    assert any("1 work experience(s) are directly relevant" in s.lower() for s in (res_direct.get("strengths") or []))
    assert res_direct["experience_score"] >= 70.0

    # Partially relevant experience (related domain overlap, not direct) must not claim "directly relevant"
    mkt_job = {
        "job_id": "J_MKT",
        "job_title": "Marketing Associate",
        "department": "Marketing",
        "description": "Runs ad campaigns, plans events, and posts on social media pages.",
        "skills_requirements": "Copywriting, Social Media Management, Event Coordination, Creativity",
        "experience_requirements": "1 year",
    }
    designer_resume = {
        "fullname": "Designer Candidate",
        "skills": "Adobe Photoshop, Canva, Social Media",
        "experience": "Freelance Graphic Designer (2021 - 2024) - Responsibilities: Created logos and social media posters using Adobe Photoshop",
        "years_experience": 3,
        "education": "Bachelor of Fine Arts",
    }
    res_partial = job_matching_service.calculate_match_score(designer_resume, mkt_job, matching_config=cfg)
    strengths_lower = " ".join(res_partial.get("strengths") or []).lower()
    assert "directly relevant" not in strengths_lower
    assert "partially relevant" in strengths_lower

    # Placeholder experience values must evaluate as 0 entries
    rel_placeholder = job_matching_service.calculate_experience_relevance(
        "None | N/A | Fresh Graduate", "", dev_job["job_title"], dev_job["description"]
    )
    assert rel_placeholder["total_entries"] == 0
    assert rel_placeholder["relevant_count"] == 0


def test_unrelated_years_experience_not_shown_as_strength():
    """
    Regression test: 3 years of experience on an unrelated ('other') job on the
    resume must NOT appear as a strength (e.g. 'Meets or exceeds the experience
    requirement with 3 years.') for the job applied.
    """
    cfg = {"weights": {}, "thresholds": {}}
    target_job = {
        "job_id": "J_DEV_3YR",
        "job_title": "Software Developer",
        "department": "IT",
        "description": "Builds and maintains backend APIs and web applications.",
        "skills_requirements": "Python, FastAPI, PostgreSQL, React",
        "experience_requirements": "3 years",
    }
    target_job_no_req = {
        "job_id": "J_DEV_NOREQ",
        "job_title": "Software Developer",
        "department": "IT",
        "description": "Builds and maintains backend APIs and web applications.",
        "skills_requirements": "Python, FastAPI, PostgreSQL, React",
        "experience_requirements": "",
    }

    # 1. Purely unrelated 3-year job (with and without explicit years requirement)
    unrelated_resume = {
        "fullname": "Other Job Applicant",
        "skills": "Cash Handling, POS Operation, Customer Service",
        "experience": "Cashier at SM Supermarket (Jan 2021 - Jan 2024) - Responsibilities: Operated POS register, processed payments, assisted shoppers",
        "work_experiences": [
            {
                "job_title": "Cashier",
                "company_name": "SM Supermarket",
                "duration_months": 36,
                "responsibilities": ["Operated POS register", "Processed payments", "Assisted shoppers"],
            }
        ],
        "years_experience": 3,
        "education": "High School Diploma",
    }

    for job in (target_job, target_job_no_req):
        res = job_matching_service.calculate_match_score(unrelated_resume, job, matching_config=cfg)
        strengths_lower = " ".join(res.get("strengths") or []).lower()
        assert "meets or exceeds" not in strengths_lower, f"False experience strength for {job['job_id']}: {res['strengths']}"
        assert "3 years" not in strengths_lower, f"Unrelated 3 years shown as strength: {res['strengths']}"
        assert "relevant work experience" not in strengths_lower
        assert res["experience_score"] <= 10.0

    res_req = job_matching_service.calculate_match_score(unrelated_resume, target_job, matching_config=cfg)
    assert res_req["experience_below_minimum"] is True
    assert res_req["experience_gap_years"] == 3

    # 2. Mixed resume: 3 years unrelated + 1 year relevant for a 3-year requirement
    mixed_short_resume = {
        "fullname": "Mixed Short Applicant",
        "skills": "Python, FastAPI, PostgreSQL, React",
        "experience": "",
        "work_experiences": [
            {
                "job_title": "Cashier",
                "company_name": "SM Supermarket",
                "duration_months": 36,
                "responsibilities": ["Operated POS register and processed customer payments."],
            },
            {
                "job_title": "Junior Software Developer",
                "company_name": "Startup Inc",
                "duration_months": 12,
                "responsibilities": ["Built Python FastAPI endpoints and PostgreSQL queries."],
            },
        ],
        "years_experience": 4,
        "education": "Bachelor of Science in Computer Science",
    }
    res_mixed_short = job_matching_service.calculate_match_score(mixed_short_resume, target_job, matching_config=cfg)
    mixed_short_strengths = " ".join(res_mixed_short.get("strengths") or []).lower()
    assert "meets or exceeds" not in mixed_short_strengths
    assert "4 years" not in mixed_short_strengths
    assert res_mixed_short["experience_below_minimum"] is True
    assert res_mixed_short["experience_gap_years"] == 2

    # 3. Mixed resume: 3 years unrelated + 3 years relevant -> only the 3 relevant years count
    mixed_ok_resume = {
        **mixed_short_resume,
        "work_experiences": [
            mixed_short_resume["work_experiences"][0],
            {
                "job_title": "Software Developer",
                "company_name": "Tech Corp",
                "duration_months": 36,
                "responsibilities": ["Built Python FastAPI microservices and React UIs."],
            },
        ],
        "years_experience": 6,
    }
    res_mixed_ok = job_matching_service.calculate_match_score(mixed_ok_resume, target_job, matching_config=cfg)
    mixed_ok_strengths = " ".join(res_mixed_ok.get("strengths") or []).lower()
    assert "meets or exceeds the experience requirement with 3 years of relevant experience" in mixed_ok_strengths
    assert "6 years" not in mixed_ok_strengths
    assert res_mixed_ok["experience_below_minimum"] is False


def test_unrelated_certification_not_perfect_score_or_strength():
    """
    Regression test: detecting ANY certification on a resume (when the job either
    has no certification requirement, mentions generic 'certification', or requires
    a different certification) must NOT automatically yield a 100% certification
    score or add 'Relevant certifications...' to strengths.
    """
    cfg = {"weights": {}, "thresholds": {}}

    # 1. Job has no certification requirement (empty and "None required") + unrelated cert on resume
    for cert_req in ("", "None", "None required"):
        job_no_cert_req = {
            "job_id": "J_DEV_CERT",
            "job_title": "Software Developer",
            "department": "IT",
            "description": "Builds backend REST APIs and web applications.",
            "skills_requirements": "Python, FastAPI, PostgreSQL, React",
            "experience_requirements": "2 years",
            "education_requirements": "Bachelor's Degree in Computer Science",
            "certifications_requirements": cert_req,
        }
        resume_unrelated_cert = {
            "fullname": "Chef Applicant",
            "skills": "Python, FastAPI, PostgreSQL, React",
            "experience": "Software Developer at Acme (2022 - 2024)",
            "years_experience": 2,
            "education": "Bachelor of Science in Computer Science",
            "certifications": "Food Safety Certificate | TESDA NC II Cookery",
        }
        res = job_matching_service.calculate_match_score(resume_unrelated_cert, job_no_cert_req, matching_config=cfg)
        strengths_lower = " ".join(res.get("strengths") or []).lower()
        assert res["certifications_score"] == 0.0, f"Unrelated cert got non-zero score for req={cert_req!r}: {res}"
        assert "certification" not in strengths_lower, f"False cert strength for req={cert_req!r}: {res['strengths']}"
        assert res["required_certifications"] == "None"
        assert not any("required certifications are missing" in w.lower() for w in (res.get("weaknesses") or []))

    # 2. Job description mentions generic "certification" -> must not fuzzy-match "<X> Certification"
    job_generic_cert = {
        "job_id": "J_DEV_GENERIC",
        "job_title": "Software Developer",
        "department": "IT",
        "description": "Builds backend APIs. Relevant certification is an advantage.",
        "skills_requirements": "Python, FastAPI, PostgreSQL",
        "experience_requirements": "2 years",
        "certifications_requirements": "",
    }
    resume_event_cert = {
        "fullname": "Event Cert Applicant",
        "skills": "Python, FastAPI",
        "experience": "Software Developer (2 years)",
        "years_experience": 2,
        "education": "BS Computer Science",
        "certifications": "Event Certification | Barista Training Certificate",
    }
    res_generic = job_matching_service.calculate_match_score(resume_event_cert, job_generic_cert, matching_config=cfg)
    assert res_generic["certifications_score"] == 0.0
    assert "certification" not in " ".join(res_generic.get("strengths") or []).lower()

    # 3. Job has explicit certification requirement -> unrelated cert (even sharing generic word 'safety'/'training') must score 0
    job_prod = {
        "job_id": "J_PROD_CERT",
        "job_title": "Production Operator",
        "department": "Manufacturing",
        "description": "Operates tile kilns and follows plant safety procedures.",
        "skills_requirements": "kiln operation, machine handling, safety compliance",
        "experience_requirements": "3 years",
        "certifications_requirements": "safety training (OSHA or BOSH)",
    }
    resume_food_safety = {
        "fullname": "Food Safety Applicant",
        "skills": "kiln operation, machine handling",
        "experience": "Production Operator at Factory (3 years)",
        "years_experience": 3,
        "certifications": "Food Safety Certificate | Customer Service Training",
    }
    res_prod_unrelated = job_matching_service.calculate_match_score(resume_food_safety, job_prod, matching_config=cfg)
    assert res_prod_unrelated["certifications_score"] == 0.0
    assert "certification" not in " ".join(res_prod_unrelated.get("strengths") or []).lower()
    assert any("required certifications" in w.lower() for w in (res_prod_unrelated.get("weaknesses") or []))

    # 4. Skills alone must never masquerade as certifications when certifications field is empty
    job_iso = {
        "job_id": "J_QA_ISO",
        "job_title": "QA Inspector",
        "department": "Manufacturing",
        "description": "Inspects tiles against ISO quality standards.",
        "skills_requirements": "quality control, ISO 9001",
        "certifications_requirements": "ISO 9001",
    }
    resume_skills_only = {
        "fullname": "No Cert Applicant",
        "skills": "quality control, ISO 9001",
        "experience": "QA Inspector (2 years)",
        "years_experience": 2,
        "certifications": "",
    }
    res_no_cert = job_matching_service.calculate_match_score(resume_skills_only, job_iso, matching_config=cfg)
    assert res_no_cert["certifications_score"] == 0.0
    assert res_no_cert["candidate_certifications"] == "None"
    assert "certification" not in " ".join(res_no_cert.get("strengths") or []).lower()


def test_relevant_certification_scores_and_appears_as_strength():
    """
    Verify genuinely relevant certifications (explicitly required or domain-aligned)
    still receive credit and appear in strengths.
    """
    cfg = {"weights": {}, "thresholds": {}}

    # 1. Explicit requirement match (OSHA/BOSH alternative)
    job_prod = {
        "job_id": "J_PROD_OK",
        "job_title": "Production Operator",
        "department": "Manufacturing",
        "description": "Operates tile production equipment and enforces plant safety.",
        "skills_requirements": "kiln operation, safety compliance",
        "certifications_requirements": "safety training (OSHA or BOSH)",
    }
    resume_bosh = {
        "fullname": "Safety Certified Operator",
        "skills": "kiln operation, safety compliance",
        "experience": "Production Operator (3 years)",
        "years_experience": 3,
        "certifications": "DOLE BOSH Safety Officer 2",
    }
    res_bosh = job_matching_service.calculate_match_score(resume_bosh, job_prod, matching_config=cfg)
    assert res_bosh["certifications_score"] == 100.0
    assert any("relevant certifications meet the job requirements" in s.lower() for s in (res_bosh.get("strengths") or []))

    # 2. Job lists "None required", candidate holds genuinely domain-relevant certification (CPA for Accounting)
    job_acct = {
        "job_id": "J_ACCT",
        "job_title": "Accounting Assistant",
        "department": "Finance",
        "description": "Encodes invoices, reconciles bank accounts, prepares financial reports.",
        "skills_requirements": "SAP, bookkeeping, Excel, reconciliation",
        "certifications_requirements": "None required",
    }
    resume_cpa = {
        "fullname": "CPA Candidate",
        "skills": "SAP, bookkeeping, Excel, reconciliation",
        "experience": "Accounting Staff (2 years)",
        "years_experience": 2,
        "certifications": "Certified Public Accountant (CPA)",
    }
    res_cpa = job_matching_service.calculate_match_score(resume_cpa, job_acct, matching_config=cfg)
    assert res_cpa["certifications_score"] == 100.0
    assert any("relevant certifications" in s.lower() for s in (res_cpa.get("strengths") or []))





