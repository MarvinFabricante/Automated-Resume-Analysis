import pytest
from app.extractors.content.experience_extractor import (
    extract_structured_experience,
    extract_experience_entries,
    extract_experience,
    extract_years_experience,
    extract_experience_years_float,
    extract_job_title,
    extract_company,
    extract_relevance,
    _parse_date_and_duration,
    _detect_employment_type,
    _split_company_and_location
)
from app.extractors.content.content_extractor import extract_content


TEMPLATE_1 = """
WORK EXPERIENCE
Service Crew (Kitchen / Grill)
Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna
June 2023 - December 2023 (End of Contract)
- Assigned in kitchen area as fryman and grill station crew.
- Maintained cleanliness of the station and washed dishes/utensils during closing.

Utility Personnel / Janitor
Robinsons Place Antipolo (via Manpower Agency)
January 2022 - May 2023
- Responsible for floor maintenance, trash collection, and restroom sanitation.
"""

TEMPLATE_2 = """
EMPLOYMENT HISTORY
Cashier / Counter Crew | Chowking - SM City Taytay | March 2021 to August 2022
Duties: Handled POS transactions, assisted customers at the front counter, and performed daily cash balancing.
Dishwasher / Kitchen Helper | Gerry's Grill - Robinsons Galleria | Oct 2020 - Feb 2021
Duties: Washed plates, glassware, and kitchen cookware during peak dining hours.
"""

TEMPLATE_3 = """
PROFESSIONAL EXPERIENCE
Junior Backend Developer
Accenture Philippines | BGC, Taguig City
August 2025 - Present
- Developed and maintained RESTful APIs using Node.js, NestJS, and PostgreSQL.
- Collaborated with frontend developers and QA engineers in an Agile Scrum environment.

Site Civil Engineer
DMCI Homes - Quezon City Project Site
March 2024 - July 2025
- Supervised daily site construction activities, rebar installation, and concrete pouring.
- Prepared daily accomplishment reports and monitored sub-contractor manpower.

ON-THE-JOB TRAINING (OJT)
Software Developer Intern (OJT)
XYZ Tech Solutions Inc., Makati City
January 2024 - April 2024 (486 Hours)
- Assisted in debugging C# and Java modules and performing manual regression testing.
"""


def test_template_1_service_blue_collar():
    result = extract_structured_experience(TEMPLATE_1)
    
    assert "total_experience_months" in result
    assert "work_experiences" in result
    assert len(result["work_experiences"]) == 2
    
    # First role: Jollibee Service Crew
    role1 = result["work_experiences"][0]
    assert "Service Crew" in role1["job_title"]
    assert "Jollibee" in role1["company_name"]
    assert "Calamba" in (role1["location"] or "") or "Crossing" in (role1["location"] or "")
    assert role1["employment_type"] == "Contractual"
    assert role1["start_date"] == "2023-06"
    assert role1["end_date"] == "2023-12"
    assert role1["duration_months"] == 7
    assert len(role1["responsibilities"]) >= 2
    assert any("kitchen" in r.lower() for r in role1["responsibilities"])
    
    # Second role: Janitor / Utility
    role2 = result["work_experiences"][1]
    assert any(term in role2["job_title"].lower() for term in ["janitor", "utility"])
    assert "Robinsons" in role2["company_name"]
    assert role2["employment_type"] == "Contractual"
    assert role2["start_date"] == "2022-01"
    assert role2["end_date"] == "2023-05"
    assert role2["duration_months"] == 17
    assert len(role2["responsibilities"]) >= 1


def test_template_2_inline_tabular():
    result = extract_structured_experience(TEMPLATE_2)
    
    assert len(result["work_experiences"]) == 2
    
    # Chowking Cashier
    role1 = result["work_experiences"][0]
    assert "Cashier" in role1["job_title"]
    assert "Chowking" in role1["company_name"]
    assert role1["start_date"] == "2021-03"
    assert role1["end_date"] == "2022-08"
    assert role1["duration_months"] == 18
    assert len(role1["responsibilities"]) >= 1
    assert any("pos" in r.lower() or "counter" in r.lower() for r in role1["responsibilities"])
    
    # Gerry's Grill Dishwasher
    role2 = result["work_experiences"][1]
    assert "Dishwasher" in role2["job_title"]
    assert "Gerry's Grill" in role2["company_name"] or "Gerry" in role2["company_name"]
    assert role2["start_date"] == "2020-10"
    assert role2["end_date"] == "2021-02"
    assert role2["duration_months"] == 5
    assert len(role2["responsibilities"]) >= 1


def test_template_3_technical_engineering_and_ojt():
    result = extract_structured_experience(TEMPLATE_3)
    
    assert len(result["work_experiences"]) == 3
    
    # Role 1: Junior Backend Developer
    role1 = result["work_experiences"][0]
    assert "Developer" in role1["job_title"] or "Backend" in role1["job_title"]
    assert "Accenture" in role1["company_name"]
    assert role1["start_date"] == "2025-08"
    assert role1["end_date"] == "Present"
    assert len(role1["responsibilities"]) >= 2
    
    # Role 2: Site Civil Engineer
    role2 = result["work_experiences"][1]
    assert "Civil Engineer" in role2["job_title"] or "Engineer" in role2["job_title"]
    assert "DMCI" in role2["company_name"]
    assert role2["start_date"] == "2024-03"
    assert role2["end_date"] == "2025-07"
    assert role2["duration_months"] == 17
    assert len(role2["responsibilities"]) >= 2
    
    # Role 3: OJT Intern
    role3 = result["work_experiences"][2]
    assert "Intern" in role3["job_title"] or "Developer" in role3["job_title"]
    assert role3["employment_type"] == "OJT"
    assert "XYZ Tech" in role3["company_name"]
    assert role3["start_date"] == "2024-01"
    assert role3["end_date"] == "2024-04"
    assert role3["duration_months"] == 4
    assert len(role3["responsibilities"]) >= 1


def test_date_and_duration_parsing_units():
    # Standard format
    s, e, dur, _ = _parse_date_and_duration("June 2023 - December 2023")
    assert s == "2023-06"
    assert e == "2023-12"
    assert dur == 7

    # Present format
    s, e, dur, _ = _parse_date_and_duration("March 2023 up to present")
    assert s == "2023-03"
    assert e == "Present"
    assert dur is not None and dur > 0

    # Hours format
    s, e, dur, _ = _parse_date_and_duration("January 2024 - April 2024 (486 Hours)")
    assert s == "2024-01"
    assert e == "2024-04"
    assert dur == 4

    # Year only format
    s, e, dur, _ = _parse_date_and_duration("2021 - 2023")
    assert s == "2021-01"
    assert e == "2023-12"
    assert dur == 36


def test_employment_type_detection():
    assert _detect_employment_type("Software Engineer Intern") == "OJT"
    assert _detect_employment_type("Practicum Student - 300 hrs") == "OJT"
    assert _detect_employment_type("Service Crew (End of Contract / ENDO)") == "Contractual"
    assert _detect_employment_type("Robinsons Janitor (via Manpower Agency)") == "Contractual"
    assert _detect_employment_type("Holiday Reliever Cashier") == "Seasonal"
    assert _detect_employment_type("Part-Time ESL Tutor") == "Part-time"
    assert _detect_employment_type("Permanent Regular Staff") == "Full-time"


def test_company_and_location_splitting():
    comp, loc = _split_company_and_location("Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna")
    assert "Jollibee" in comp
    assert "Calamba" in (loc or "") or "Crossing" in (loc or "")

    comp2, loc2 = _split_company_and_location("Accenture Philippines | BGC, Taguig City")
    assert "Accenture" in comp2
    assert "Taguig" in (loc2 or "") or "BGC" in (loc2 or "")


def test_backward_compatibility():
    years = extract_years_experience(TEMPLATE_1)
    assert years is not None
    assert isinstance(years, (int, float))
    assert years >= 1.0

    entries = extract_experience_entries(TEMPLATE_1)
    assert len(entries) >= 2
    assert "title" in entries[0]
    assert "company" in entries[0]

    job_title = extract_job_title(TEMPLATE_3)
    assert job_title != ""

    company = extract_company(TEMPLATE_3)
    assert company != ""

    relevance = extract_relevance(TEMPLATE_3)
    assert isinstance(relevance, str) and len(relevance) > 0


def test_content_extractor_structured_experience():
    parsed = extract_content(TEMPLATE_3)
    assert "work_experiences" in parsed
    assert "total_experience_months" in parsed
    assert isinstance(parsed["work_experiences"], list)
    assert len(parsed["work_experiences"]) == 3
    assert parsed["total_experience_months"] > 0


def test_r1_production_operator_experience_and_institution():
    """
    Validates R1 (4 yrs Production Operator): job title, employer, dates,
    computed years (4 years / 48 months), and clean institution extraction.
    """
    r1_text = """
JUAN DELA CRUZ
juan.delacruz@gmail.com | 09171234567 | Laguna, Philippines

WORK EXPERIENCE
Production Operator
Luzon Plastics Industries Inc. - Laguna
2020 - 2024 (4 years)
Machine setup, routine preventive maintenance, and line clearance.

EDUCATION
Technical-Vocational Track (Electronics)
TESDA Institute
2018 - 2020

SKILLS
ISO 9001 Quality Standards, Preventive Maintenance, Machine Maintenance, Safety Training
"""
    parsed = extract_content(r1_text)
    assert parsed["job_title"] == "Production Operator"
    assert parsed["company"] == "Luzon Plastics Industries Inc."
    assert parsed["years_experience"] == 4
    assert parsed["total_experience_months"] == 48
    assert len(parsed["work_experiences"]) == 1
    exp = parsed["work_experiences"][0]
    assert exp["start_date"] == "2020-01"
    assert exp["end_date"] == "2024-12"
    assert exp["duration_months"] == 48
    assert parsed["institution"] == "TESDA Institute"
    assert parsed["college"] == "TESDA Institute"
    assert parsed["is_incomplete"] is False
    assert parsed["needs_clarification"] is False
    assert parsed["is_vague"] is False
    assert parsed["clarification_questions"] == []


def test_vague_r4_triggers_clarification_questions():
    """
    Validates vague resume handling (R4):
    - Undated / vague manufacturing or work descriptions trigger clarification
    - Includes follow-up question asking years of manufacturing experience
    """
    r4_vague_mfg = """
ROBERTO SANTOS
roberto.santos@gmail.com | 09181234567

WORK EXPERIENCE
Worked in manufacturing
Handled production tasks and assembly work

EDUCATION
High School

SKILLS
Teamwork
"""
    res1 = extract_content(r4_vague_mfg)
    assert res1["needs_clarification"] is True
    assert res1["is_vague"] is True
    questions1 = res1["clarification_questions"]
    assert len(questions1) >= 1
    assert any(
        q["field"] == "years_experience"
        and "years of manufacturing experience" in q["question"].lower()
        for q in questions1
    )

    r4_sparse = """
R4 APPLICANT
r4@gmail.com | 09179998888

SUMMARY
Some experience in factory work. Willing to learn and hardworking.
"""
    res2 = extract_content(r4_sparse)
    assert res2["needs_clarification"] is True
    assert res2["is_vague"] is True
    questions2 = res2["clarification_questions"]
    assert any(
        q["field"] == "years_experience"
        and "years of manufacturing experience" in q["question"].lower()
        for q in questions2
    )
    assert len(questions2) >= 2


def test_explicit_single_year_experience_label():
    assert extract_years_experience("Experience: 1 yr\nProduction Operator at Plant A") == 1


def test_two_work_experiences_not_collapsed_to_one():
    """
    Regression tests ensuring resumes with 2 work experiences extract BOTH entries
    across mixed layouts, 'Associate'/'Master' titles, same-year month ranges,
    and bullet prefixes like 'Training:' or 'Projects:'.
    """
    # 1. Multi-line role 1 + inline role 2
    mixed_multiline_then_inline = """
WORK EXPERIENCE
Production Supervisor
Mariwasa Siam Ceramics Inc.
January 2022 - Present
• Managed kiln shift teams and daily production output.
Training: Conducted operator safety onboarding for new hires.

Quality Control Inspector at Rizal Packaging Corp. (March 2019 - December 2021)
• Inspected finished tile batches and logged defect reports.
"""
    res1 = extract_structured_experience(mixed_multiline_then_inline)
    assert len(res1["work_experiences"]) == 2
    assert "Supervisor" in res1["work_experiences"][0]["job_title"]
    assert "Quality Control" in res1["work_experiences"][1]["job_title"]

    # 2. Inline role 1 + multi-line role 2 (including >15 char title)
    mixed_inline_then_multiline = """
WORK EXPERIENCE
Software Developer | Tech Corp | Jan 2022 - Present
- Built FastAPI REST services.

Senior Quality Assurance Engineer
Acme Manufacturing Inc.
January 2020 - December 2021
- Automated regression test suites.
"""
    res2 = extract_structured_experience(mixed_inline_then_multiline)
    assert len(res2["work_experiences"]) == 2
    assert "Developer" in res2["work_experiences"][0]["job_title"]
    assert "Quality Assurance" in res2["work_experiences"][1]["job_title"]

    # 3. Roles with 'Associate' or 'Master' in title + same-year month range
    associate_and_same_year = """
WORK EXPERIENCE
Sales Associate
SM Retail Inc.
June 2023 - August 2024
- Assisted customers and handled POS checkout.

Marketing Intern
ABC Media Group
January - May 2023
- Assisted with social media campaign scheduling.
"""
    res3 = extract_structured_experience(associate_and_same_year)
    assert len(res3["work_experiences"]) == 2
    assert "Sales Associate" in res3["work_experiences"][0]["job_title"]
    assert "Intern" in res3["work_experiences"][1]["job_title"]
    assert res3["work_experiences"][1]["start_date"] == "2023-01"
    assert res3["work_experiences"][1]["end_date"] == "2023-05"
    assert res3["work_experiences"][1]["duration_months"] == 5

    # 4. Multi-line role 1 + date-first role 2
    multiline_then_date_first = """
WORK EXPERIENCE
Cashier
Puregold Supermarket
2022 - 2024
- Processed customer payments and balanced daily register.

2020 - 2021
Service Crew
Jollibee Foods Corporation
- Prepared food orders and maintained counter cleanliness.
"""
    res4 = extract_structured_experience(multiline_then_date_first)
    assert len(res4["work_experiences"]) == 2
    assert "Cashier" in res4["work_experiences"][0]["job_title"]
    assert "Service Crew" in res4["work_experiences"][1]["job_title"]

    # 5. Title (Date) + Company on next line + OJT Role 2 with hours/duration only
    title_date_and_ojt_hours = """
WORK EXPERIENCE
Software Developer (Jan 2023 - Present)
Acme Tech Corp - Makati City
• Built backend APIs.

ON-THE-JOB TRAINING (OJT)
IT Support Intern
Barangay Hall Laguna
486 Hours
• Assisted with workstation setup and network troubleshooting.
"""
    res5 = extract_structured_experience(title_date_and_ojt_hours)
    assert len(res5["work_experiences"]) == 2
    assert "Developer" in res5["work_experiences"][0]["job_title"]
    assert "Acme Tech Corp" in res5["work_experiences"][0]["company_name"]
    assert "Intern" in res5["work_experiences"][1]["job_title"]
    assert res5["work_experiences"][1]["duration_months"] == 3


def test_extended_date_and_duration_formats():
    # DD Month YYYY
    s, e, dur, _ = _parse_date_and_duration("15 June 2020 - 20 August 2023")
    assert s == "2020-06"
    assert e == "2023-08"
    assert dur == 39

    # DD/MM/YYYY consistent disambiguation
    s, e, dur, _ = _parse_date_and_duration("01/06/2020 - 20/12/2023")
    assert s == "2020-06"
    assert e == "2023-12"
    assert dur == 43

    # YYYY/MM and MM.YYYY
    s, e, dur, _ = _parse_date_and_duration("2020/06 - 2023/12")
    assert (s, e, dur) == ("2020-06", "2023-12", 43)
    s, e, dur, _ = _parse_date_and_duration("06.2020 - 12.2023")
    assert (s, e, dur) == ("2020-06", "2023-12", 43)

    # Apostrophe short years and Quarters
    s, e, dur, _ = _parse_date_and_duration("Jan '20 - Dec '23")
    assert (s, e, dur) == ("2020-01", "2023-12", 48)
    s, e, dur, _ = _parse_date_and_duration("Q1 2021 - Q4 2023")
    assert (s, e, dur) == ("2021-01", "2023-12", 36)

    # Combined years + months duration
    s, e, dur, _ = _parse_date_and_duration("2 yrs 6 mos")
    assert dur == 30

    # Open-ended 'Since' and 'Currently'
    s, e, dur, _ = _parse_date_and_duration("Since June 2023")
    assert s == "2023-06"
    assert e == "Present"
    assert dur >= 1
    s, e, dur, _ = _parse_date_and_duration("Jan 2022 - Currently")
    assert s == "2022-01"
    assert e == "Present"
    assert dur >= 1

    # Misspelled months
    s, e, dur, _ = _parse_date_and_duration("Febuary 2020 - Septmber 2022")
    assert (s, e, dur) == ("2020-02", "2022-09", 32)


def test_overlapping_jobs_interval_merging():
    resume_text = """
    WORK EXPERIENCE
    Senior Developer | Alpha Tech | Jan 2022 - Dec 2024
    - Led backend platform.

    Freelance Consultant | Beta Studio | Jan 2023 - Dec 2023
    - Advised on architecture.

    Junior Developer | Gamma Corp | Jan 2020 - Dec 2021
    - Developed REST APIs.
    """
    res = extract_structured_experience(resume_text)
    assert len(res["work_experiences"]) == 3
    # Union of 2020-01..2021-12 (24m) and 2022-01..2024-12 (36m) with concurrent 2023-01..2023-12 inside = 60 months (5 years)
    assert res["total_experience_months"] == 60
    assert extract_years_experience(resume_text) == 5


def test_diverse_cv_layouts_and_groupings():
    # 1. LinkedIn grouped parent company + standalone summary duration
    linkedin_text = """
    WORK EXPERIENCE
    Accenture Philippines
    4 yrs 2 mos
    Senior Developer
    Jan 2022 - Dec 2024
    - Built microservices
    Junior Developer
    Jan 2020 - Dec 2021
    - Wrote APIs
    """
    res_li = extract_structured_experience(linkedin_text)
    assert len(res_li["work_experiences"]) == 2
    assert res_li["work_experiences"][0]["company_name"] == "Accenture Philippines"
    assert res_li["work_experiences"][1]["company_name"] == "Accenture Philippines"
    assert res_li["total_experience_months"] == 60

    # 2. Company -> Date -> Title ordering
    comp_first = """
    WORK EXPERIENCE
    Jollibee Foods Corporation
    June 2022 - December 2023
    Service Crew
    - Served customers
    """
    res_cf = extract_structured_experience(comp_first)
    assert len(res_cf["work_experiences"]) == 1
    assert res_cf["work_experiences"][0]["job_title"] == "Service Crew"
    assert "Jollibee" in res_cf["work_experiences"][0]["company_name"]
    assert res_cf["total_experience_months"] == 19

    # 3. Inline bullet separator, inline duration, prose entry, and modifier + engineering company
    mixed_layouts = """
    WORKING EXPERIENCE
    Service Crew • Jollibee Foods Corp. • Jun 2022 - Dec 2023
    Production Operator at ABC Corp (2 years)
    Worked as Quality Control Inspector at Mariwasa Siam Ceramics Inc. from January 2019 to December 2020.
    Site Civil Engineer (Jan 2021 - Dec 2021)
    ABC Engineering Services Inc.
    """
    res_mix = extract_structured_experience(mixed_layouts)
    assert len(res_mix["work_experiences"]) == 4
    titles = [r["job_title"] for r in res_mix["work_experiences"]]
    assert "Service Crew" in titles
    assert "Production Operator" in titles
    assert "Quality Control Inspector" in titles
    assert "Site Civil Engineer" in titles
    site_role = next(r for r in res_mix["work_experiences"] if r["job_title"] == "Site Civil Engineer")
    assert site_role["company_name"] == "ABC Engineering Services Inc."
    assert res_mix["total_experience_months"] == 79


def test_explicit_years_accuracy_and_false_positive_rejection():
    # Decimals must not parse fractional digit (2.5 -> 2.5f / 3 int, NOT 5!)
    dec_cv = "SUMMARY\nSoftware Developer with 2.5 years of experience in Python."
    assert extract_experience_years_float(dec_cv) == 2.5
    assert extract_years_experience(dec_cv) == 3

    # Word numbers
    word_cv = "SUMMARY\nAccountant with five years of professional experience."
    assert extract_years_experience(word_cv) == 5

    # Months-only explicit statement
    mo_cv = "SUMMARY\nQA Tester with 18 months of work experience."
    assert extract_experience_years_float(mo_cv) == 1.5
    assert extract_years_experience(mo_cv) == 2

    # Explicit label formats
    assert extract_years_experience("Years of Experience: 5\nEXPERIENCE\nCashier at Puregold") == 5
    assert extract_years_experience("Total Work Experience: 3 yrs 6 mos") == 4

    # False positives must be rejected (age, academic duration, company heritage, mentoring juniors)
    fp_cv = """
    OBJECTIVE
    Hardworking applicant, 22 years old, seeking an entry-level role.
    Mentored interns with 2 years of experience during capstone.
    Our school has over 50 years of heritage in engineering.
    EDUCATION
    BS Computer Science (4 years)
    University of Manila, 2020 - 2024
    SKILLS
    Python, SQL
    """
    assert extract_years_experience(fp_cv) == 0
    assert extract_experience_years_float(fp_cv) == 0.0



