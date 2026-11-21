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


def test_expanded_explicit_years_phrases_and_false_positives():
    # Domain-qualified, hyphenated, apostrophe, YoE, reversed, decade, compound words, fractions, multi-line, Tagalog
    assert extract_years_experience("SUMMARY\nEngineer with 5-year experience in manufacturing.") == 5
    assert extract_years_experience("SUMMARY\n4 years of manufacturing experience and 3 years of quality control experience.") == 4
    assert extract_years_experience("PROFILE\nSenior Backend Developer (6+ YoE) with 6 years' experience in Python.") == 6
    assert extract_years_experience("SUMMARY\nDedicated accountant with experience of 7 years in corporate finance.") == 7
    assert extract_years_experience("SUMMARY\nOver a decade of experience in hospitality management.") == 10
    assert extract_experience_years_float("SUMMARY\nOne and a half years of customer service experience.") == 1.5
    assert extract_experience_years_float("SUMMARY\n2½ years of experience in retail operations.") == 2.5
    assert extract_experience_years_float("SUMMARY\nTwenty-two months in resort operations.") == 1.8
    assert extract_years_experience("PERSONAL INFORMATION\nTotal Work Experience\n5 years 6 months") == 6
    assert extract_experience_years_float("PERSONAL INFORMATION\nTotal Work Experience\n5 years 6 months") == 5.5
    assert extract_experience_years_float("SUMMARY\nExperienced software developer with 4.5+ years of backend development experience.") == 4.5
    assert extract_years_experience("SUMMARY\n5 taong karanasan sa trabaho bilang driver.") == 5
    assert extract_years_experience("SUMMARY\nWorking as a Software Engineer since January 2022.") >= 4

    # Qualifications summary explicit years preserved in extract_content
    qual_cv = """
    MARIO REYES
    mario@gmail.com | 09171234567
    SUMMARY OF QUALIFICATIONS
    • Over 8 years of progressive experience in industrial plant maintenance
    • Licensed Mechanical Engineer
    EDUCATION
    BS Mechanical Engineering
    SKILLS
    Maintenance
    """
    parsed_qual = extract_content(qual_cv)
    assert parsed_qual["years_experience"] == 8
    assert parsed_qual["total_experience_months"] == 96
    assert parsed_qual["years_experience_float"] == 8.0

    # Strict false positive rejections
    fp_extended = """
    SUMMARY
    24 years old, graduated more than 2 years ago, lived in Cebu for over 10 years,
    managed project with over 5 years of historical logs.
    EDUCATION
    BS Computer Science, 2018 - 2022
    SKILLS
    Python
    """
    assert extract_years_experience(fp_extended) == 0
    assert extract_experience_years_float(fp_extended) == 0.0

    # Sectionless resume must reject degree & certifications as jobs
    sectionless_cv = """
    JUAN DELA CRUZ
    juan@gmail.com | 09171234567
    BS Computer Science
    PUP Manila
    2016 - 2020
    Software Developer
    Accenture Philippines
    Jan 2021 - Dec 2023
    AWS Certified Developer (2021 - 2024)
    """
    res_sec = extract_structured_experience(sectionless_cv)
    assert len(res_sec["work_experiences"]) == 1
    assert res_sec["work_experiences"][0]["job_title"] == "Software Developer"
    assert res_sec["work_experiences"][0]["company_name"] == "Accenture Philippines"
    assert res_sec["total_experience_months"] == 36


def test_expanded_date_formats_and_future_clamping():
    from datetime import datetime

    # Wrapped multi-line date range
    wrapped_cv = """
    WORK EXPERIENCE
    Software Engineer
    Acme Tech Inc.
    Jan 2021 -
    Dec 2023
    - Built APIs
    """
    res_w = extract_structured_experience(wrapped_cv)
    assert len(res_w["work_experiences"]) == 1
    assert res_w["work_experiences"][0]["start_date"] == "2021-01"
    assert res_w["work_experiences"][0]["end_date"] == "2023-12"
    assert res_w["work_experiences"][0]["duration_months"] == 36

    # YYYY - YY
    s, e, dur, _ = _parse_date_and_duration("2019 - 22")
    assert (s, e, dur) == ("2019-01", "2022-12", 48)

    # Dotted month + day + year
    s, e, dur, _ = _parse_date_and_duration("Sept. 15, 2020 - Dec. 20, 2023")
    assert (s, e, dur) == ("2020-09", "2023-12", 40)

    # DD-Mon-YYYY
    s, e, dur, _ = _parse_date_and_duration("01-Jun-2021 to 30-Nov-2023")
    assert (s, e, dur) == ("2021-06", "2023-11", 30)

    # Spaces around slash & dot short year
    s, e, dur, _ = _parse_date_and_duration("06 / 2020 - 12 / 2023")
    assert (s, e, dur) == ("2020-06", "2023-12", 43)
    s, e, dur, _ = _parse_date_and_duration("06.20 - 12.23")
    assert (s, e, dur) == ("2020-06", "2023-12", 43)

    # Seasons (standalone & range)
    s, e, dur, _ = _parse_date_and_duration("Summer 2022")
    assert (s, e, dur) == ("2022-06", "2022-08", 3)
    s, e, dur, _ = _parse_date_and_duration("Fall 2021 - Spring 2022")
    assert (s, e, dur) == ("2021-09", "2022-05", 9)

    # Between X and Y, - to present, Tagalog months
    s, e, dur, _ = _parse_date_and_duration("Between January 2020 and December 2023")
    assert (s, e, dur) == ("2020-01", "2023-12", 48)
    s, e, dur, _ = _parse_date_and_duration("March 2021 - to present")
    assert s == "2021-03" and e == "Present" and dur > 0
    s, e, dur, _ = _parse_date_and_duration("Enero 2020 - Disyembre 2023")
    assert (s, e, dur) == ("2020-01", "2023-12", 48)

    # Future end-date clamping to current month/year
    now = datetime.now()
    s, e, dur, _ = _parse_date_and_duration("Jan 2024 - Dec 2030")
    expected_clamped = (now.year - 2024) * 12 + (now.month - 1) + 1
    assert s == "2024-01"
    assert e == f"{now.year:04d}-{now.month:02d}"
    assert dur == expected_clamped

    # Bare single-year stamp without explicit duration must not fabricate 12 months
    single_year_cv = "WORK EXPERIENCE\nFreelance Photographer | Studio X (2022)"
    res_sy = extract_structured_experience(single_year_cv)
    assert len(res_sy["work_experiences"]) == 1
    assert res_sy["work_experiences"][0]["duration_months"] == 0
    assert res_sy["total_experience_months"] == 0


def test_diverse_layouts_linkedin_biodata_pds_and_headers():
    # 1. Lowercase & iOS Developer + Company, City
    lower_cv = """
    work experience
    iOS Developer
    apple solutions inc.
    jan 2021 - dec 2023
    - built apps

    service crew
    jollibee, calamba
    jun 2019 - dec 2020
    - served customers
    """
    res_l = extract_structured_experience(lower_cv)
    assert len(res_l["work_experiences"]) == 2
    assert res_l["work_experiences"][0]["job_title"] == "iOS Developer"
    assert res_l["work_experiences"][1]["job_title"] == "Service Crew"
    assert "Jollibee" in res_l["work_experiences"][1]["company_name"]
    assert res_l["total_experience_months"] == 55

    # 2. LinkedIn middle-dot metadata + unrecognized org
    li_dot_cv = """
    EXPERIENCE
    PixelCraft Digital
    3 yrs 2 mos
    Senior Product Designer · Full-time
    Jan 2022 - Dec 2023 · 2 yrs
    Makati, Metro Manila · Hybrid
    - Designed UX flows
    Product Designer · Full-time
    Nov 2020 - Dec 2021 · 1 yr 2 mos
    - Wireframing
    """
    res_dot = extract_structured_experience(li_dot_cv)
    assert len(res_dot["work_experiences"]) == 2
    assert res_dot["work_experiences"][0]["job_title"] == "Senior Product Designer"
    assert res_dot["work_experiences"][0]["company_name"] == "PixelCraft Digital"
    assert res_dot["work_experiences"][0]["location"] == "Makati, Metro Manila"
    assert res_dot["work_experiences"][1]["company_name"] == "PixelCraft Digital"
    assert res_dot["total_experience_months"] == 38

    # 3. Bullet sub-roles under company (Kestrel Digital) + Company then 2 roles without total
    bullet_sub_cv = """
    WORK EXPERIENCE
    Kestrel Digital (2019 - 2024)
    • Senior Software Engineer (2022 - 2024)
    • Software Engineer (2020 - 2022)
    • Associate Software Engineer (2019 - 2020)
    """
    res_bs = extract_structured_experience(bullet_sub_cv)
    assert len(res_bs["work_experiences"]) == 3
    assert all(e["company_name"] == "Kestrel Digital" for e in res_bs["work_experiences"])
    assert res_bs["total_experience_months"] == 72

    comp_2_roles = """
    WORK EXPERIENCE
    Accenture Philippines - Taguig City
    Senior Software Engineer (Jan 2023 - Dec 2024)
    - Led team
    Software Engineer (Jan 2021 - Dec 2022)
    - Built APIs
    """
    res_c2 = extract_structured_experience(comp_2_roles)
    assert len(res_c2["work_experiences"]) == 2
    assert all(e["company_name"] == "Accenture Philippines" for e in res_c2["work_experiences"])
    assert res_c2["total_experience_months"] == 48

    # 4. Pipe with employment type + Biodata KV + Government PDS + Semicolon + Single date+dur + Dash duration
    combo_cv = """
    WORK EXPERIENCE
    Software Engineer | Jan 2021 - Dec 2023 | Full-time
    Accenture Philippines, Taguig City
    - Built microservices
    """
    res_pipe = extract_structured_experience(combo_cv)
    assert res_pipe["work_experiences"][0]["company_name"] == "Accenture Philippines"
    assert res_pipe["work_experiences"][0]["employment_type"] == "Full-time"

    biodata_cv = """
    EMPLOYMENT RECORD
    Company Name: Jollibee Foods Corp.
    Job Title: Service Crew
    Period: June 2021 - May 2023
    Location: Calamba, Laguna
    """
    res_bio = extract_structured_experience(biodata_cv)
    assert len(res_bio["work_experiences"]) == 1
    assert res_bio["work_experiences"][0]["job_title"] == "Service Crew"
    assert res_bio["work_experiences"][0]["company_name"] == "Jollibee Foods Corp."
    assert res_bio["work_experiences"][0]["location"] == "Calamba, Laguna"
    assert res_bio["total_experience_months"] == 24

    pds_cv = """
    WORK EXPERIENCE
    01/15/2020 - 12/31/2023 | Administrative Aide IV | Department of Education | Permanent
    06/01/2018 - 12/31/2019 | Data Encoder | Municipality of Taytay | Job Order
    """
    res_pds = extract_structured_experience(pds_cv)
    assert len(res_pds["work_experiences"]) == 2
    assert res_pds["work_experiences"][0]["job_title"] == "Administrative Aide IV"
    assert res_pds["work_experiences"][1]["company_name"] == "Municipality of Taytay"
    assert res_pds["work_experiences"][1]["employment_type"] == "Contractual"
    assert res_pds["total_experience_months"] == 67

    semi_cv = """
    WORK EXPERIENCE
    Barista at Starbucks (2022 - 2024); Cashier at 7-Eleven (2020 - 2022)
    """
    res_semi = extract_structured_experience(semi_cv)
    assert len(res_semi["work_experiences"]) == 2
    assert res_semi["total_experience_months"] == 60

    single_date_dur_cv = """
    WORK EXPERIENCE
    Cashier | SM Supermarket | 2022 (6 months)
    Intern | ABC Corp | June 2023 (486 hours)
    """
    res_sdd = extract_structured_experience(single_date_dur_cv)
    assert len(res_sdd["work_experiences"]) == 2
    assert res_sdd["work_experiences"][0]["start_date"] == "2022-01"
    assert res_sdd["work_experiences"][0]["end_date"] == "2022-06"
    assert res_sdd["work_experiences"][1]["duration_months"] == 3
    assert res_sdd["total_experience_months"] == 9

    dash_dur_cv = """
    WORK EXPERIENCE
    Welder - ABC Fabrication - 3 years
    Helper - XYZ Hardware - 1 year 6 months
    """
    res_dd = extract_structured_experience(dash_dur_cv)
    assert len(res_dd["work_experiences"]) == 2
    assert res_dd["total_experience_months"] == 54

    # 5. Unconventional headers (CAREER PROGRESSION, SEA SERVICE, RESEARCH EXPERIENCE, KARANASAN SA TRABAHO)
    for hdr, role_ln, comp_ln in [
        ("CAREER PROGRESSION", "Operations Manager", "San Miguel Corp."),
        ("SEA SERVICE / WORK EXPERIENCE", "Able Seaman", "Maersk Filipinas Crewing Inc."),
        ("RESEARCH EXPERIENCE", "Graduate Research Assistant", "University of the Philippines Diliman"),
        ("KARANASAN SA TRABAHO", "Driver", "LBC Express"),
    ]:
        h_cv = f"{hdr}\n{role_ln}\n{comp_ln}\nJan 2020 - Dec 2023\n- Handled duties\nEDUCATION\nBS Degree\nSKILLS\nOperations"
        res_h = extract_structured_experience(h_cv)
        assert len(res_h["work_experiences"]) == 1, f"Failed for header {hdr}"
        assert res_h["work_experiences"][0]["company_name"] == comp_ln
        assert res_h["total_experience_months"] == 48

    # 6. Mixed explicit + undated role reconciliation in extract_content
    mixed_reconcile_cv = """
    JUAN CRUZ
    juan@gmail.com | 09171234567

    PROFESSIONAL SUMMARY
    Seasoned Electrical Engineer with 8 years of electrical engineering experience.

    WORK EXPERIENCE
    Electrical Engineer
    Meralco
    - Maintained substations

    EDUCATION
    BS Electrical Engineering
    UP Diliman

    SKILLS
    AutoCAD, Power Systems
    """
    parsed_mix = extract_content(mixed_reconcile_cv)
    assert parsed_mix["years_experience"] == 8
    assert parsed_mix["total_experience_months"] == 96
    assert parsed_mix["years_experience_float"] == 8.0


def test_pdf_timeline_gutter_and_two_col_footer_layout():
    import fitz
    from app.extractors.file.pdf_extractor import extract_text_from_pdf

    # 1. Timeline / Date-gutter PDF (left gutter = dates, right = roles/companies/bullets)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((40, 50), "MARIA CLARA SANTOS", fontsize=16)
    page.insert_text((40, 70), "maria.clara@gmail.com | 09171234567", fontsize=10)
    page.insert_text((180, 120), "WORK EXPERIENCE", fontsize=12)
    page.insert_text((40, 150), "Jan 2022 -\nDec 2024", fontsize=10)
    page.insert_text((180, 150), "Senior Quality Engineer\nMariwasa Siam Ceramics Inc.\n• Led ISO 9001 quality audits\n• Supervised 12 QC inspectors", fontsize=10)
    page.insert_text((40, 230), "Jun 2019 -\nDec 2021", fontsize=10)
    page.insert_text((180, 230), "Quality Control Inspector\nLuzon Ceramics Corp.\n• Inspected kiln output batches\n• Logged defect rates daily", fontsize=10)
    page.insert_text((40, 310), "Jan 2017 -\nMay 2019", fontsize=10)
    page.insert_text((180, 310), "Production Operator\nSan Miguel Packaging\n• Operated automated press machines", fontsize=10)
    page.insert_text((180, 390), "EDUCATION", fontsize=12)
    page.insert_text((40, 415), "2013 - 2017", fontsize=10)
    page.insert_text((180, 415), "BS Industrial Engineering\nBatangas State University", fontsize=10)
    pdf_txt = extract_text_from_pdf(doc.tobytes())
    doc.close()

    parsed_tl = extract_content(pdf_txt)
    assert len(parsed_tl["work_experiences"]) == 3
    assert parsed_tl["total_experience_months"] == 96
    assert parsed_tl["years_experience"] == 8

    # 2. Two-column sidebar PDF with bottom crossing footer ("Page 1 of 1")
    doc2 = fitz.open()
    page2 = doc2.new_page(width=595, height=842)
    page2.insert_text((40, 50), "PEDRO PENDUKO", fontsize=16)
    page2.insert_text((40, 70), "pedro.penduko@gmail.com | 09175551234", fontsize=10)
    page2.insert_text((40, 150), "SKILLS\nPython\nFastAPI\nDocker\nPostgreSQL\nReact", fontsize=10)
    page2.insert_text((40, 320), "EDUCATION\nBS Computer Science\nPUP Manila\n2015 - 2019", fontsize=10)
    page2.insert_text((240, 150), "WORK EXPERIENCE\nBackend Developer\nTechCorp Philippines\nJan 2020 - Dec 2023\n• Built REST APIs\n• Optimized SQL queries", fontsize=10)
    page2.insert_text((220, 800), "Page 1 of 1 - Confidential Resume", fontsize=9)
    pdf_txt2 = extract_text_from_pdf(doc2.tobytes())
    doc2.close()

    parsed_2c = extract_content(pdf_txt2)
    assert len(parsed_2c["work_experiences"]) == 1
    assert parsed_2c["work_experiences"][0]["job_title"] == "Backend Developer"
    assert parsed_2c["total_experience_months"] == 48
    assert parsed_2c["years_experience"] == 4


def test_harvard_overleaf_all_four_header_layouts():
    # (a) Company | Location + Role | Dates
    cv_a = """
    WORK EXPERIENCE
    Pointwest Technologies | Quezon City, Metro Manila
    Senior QA Engineer | Jan 2020 - Dec 2022
    • Automated API and regression test suites
    """
    res_a = extract_structured_experience(cv_a)
    assert len(res_a["work_experiences"]) == 1
    e_a = res_a["work_experiences"][0]
    assert "Qa Engineer" in e_a["job_title"] or "QA Engineer" in e_a["job_title"]
    assert "Pointwest" in e_a["company_name"]
    assert "Quezon City" in (e_a["location"] or "")
    assert e_a["duration_months"] == 36

    # (b) Company | Dates + Role | Location
    cv_b = """
    WORK EXPERIENCE
    Pointwest Technologies | Jan 2020 - Dec 2022
    Senior QA Engineer | Quezon City, Metro Manila
    • Led release verification
    """
    res_b = extract_structured_experience(cv_b)
    assert len(res_b["work_experiences"]) == 1
    e_b = res_b["work_experiences"][0]
    assert "QA Engineer" in e_b["job_title"]
    assert "Pointwest" in e_b["company_name"]
    assert "Quezon City" in (e_b["location"] or "")
    assert e_b["duration_months"] == 36

    # (c) Role | Dates + Company | Location
    cv_c = """
    WORK EXPERIENCE
    Senior QA Engineer | Jan 2020 - Dec 2022
    Pointwest Technologies | Quezon City, Metro Manila
    • Designed test automation frameworks
    """
    res_c = extract_structured_experience(cv_c)
    assert len(res_c["work_experiences"]) == 1
    e_c = res_c["work_experiences"][0]
    assert "QA Engineer" in e_c["job_title"]
    assert "Pointwest" in e_c["company_name"]
    assert "Quezon City" in (e_c["location"] or "")
    assert e_c["duration_months"] == 36

    # (d) Title + Company + Location + Dates on 4 lines
    cv_d = """
    WORK EXPERIENCE
    Senior QA Engineer
    Pointwest Technologies
    Quezon City, Metro Manila
    Jan 2020 - Dec 2022
    • Maintained CI test pipelines
    """
    res_d = extract_structured_experience(cv_d)
    assert len(res_d["work_experiences"]) == 1
    e_d = res_d["work_experiences"][0]
    assert "QA Engineer" in e_d["job_title"]
    assert "Pointwest" in e_d["company_name"]
    assert "Quezon City" in (e_d["location"] or "")
    assert e_d["duration_months"] == 36


def test_linkedin_international_grouped_and_metadata_layouts():
    # International grouped roles under parent company with total duration + full-time/hybrid metadata
    cv_grouped_dur = """
    EXPERIENCE
    Stripe Pte. Ltd.
    2 yrs 6 mos
    Senior Backend Engineer
    Jan 2023 - Dec 2023 · 1 yr · Full-time · Hybrid
    • Built idempotent payment webhook handlers

    Backend Engineer
    Jul 2021 - Dec 2022 · 1 yr 6 mos · Full-time
    • Maintained settlement microservices
    """
    res1 = extract_structured_experience(cv_grouped_dur)
    assert len(res1["work_experiences"]) == 2
    assert all("Stripe" in w["company_name"] for w in res1["work_experiences"])
    assert res1["work_experiences"][0]["employment_type"] == "Full-time"
    assert res1["total_experience_months"] == 30

    # Grouped roles WITHOUT parent duration line (company + location only)
    cv_grouped_no_dur = """
    EXPERIENCE
    Shopee Philippines
    Makati City
    Senior Product Manager
    Jan 2023 - Dec 2024
    • Owned checkout conversion roadmap

    Associate Product Manager
    Jan 2021 - Dec 2022
    • Launched seller analytics dashboards
    """
    res2 = extract_structured_experience(cv_grouped_no_dur)
    assert len(res2["work_experiences"]) == 2
    assert all("Shopee" in w["company_name"] for w in res2["work_experiences"])
    assert all("Makati" in (w["location"] or "") for w in res2["work_experiences"])
    assert res2["total_experience_months"] == 48

    # Parent company with location line BEFORE duration + inline metadata stripping
    cv_loc_before_dur = """
    EXPERIENCE
    Globe Telecom
    BGC, Taguig City
    3 yrs
    Cloud Solutions Architect
    Jan 2022 - Dec 2023 · Full-time · Hybrid · 2 yrs
    • Architected multi-region Kubernetes clusters

    Systems Engineer
    Jan 2021 - Dec 2021 · 1 yr
    • Automated server provisioning with Ansible
    """
    res3 = extract_structured_experience(cv_loc_before_dur)
    assert len(res3["work_experiences"]) == 2
    assert all("Globe Telecom" in w["company_name"] for w in res3["work_experiences"])
    assert all("Taguig" in (w["location"] or "") or "BGC" in (w["location"] or "") for w in res3["work_experiences"])
    assert "Hybrid" not in res3["work_experiences"][0]["company_name"]
    assert res3["total_experience_months"] == 36


def test_csc_pds_and_biodata_kv_layouts():
    # CSC Form 212 PDS table row with separate From | To dates + salary/SG/Y/N noise
    cv_pds = """
    WORK EXPERIENCE
    01/15/2020 | 12/31/2023 | Administrative Officer II | Department of Education | ₱27,000.00 | SG 11-1 | Permanent | Y
    """
    res_pds = extract_structured_experience(cv_pds)
    assert len(res_pds["work_experiences"]) == 1
    e_pds = res_pds["work_experiences"][0]
    assert "Administrative Officer II" in e_pds["job_title"]
    assert "Department of Education" in e_pds["company_name"]
    assert "27,000" not in e_pds["company_name"]
    assert "SG" not in e_pds["company_name"]
    assert e_pds["start_date"] == "2020-01"
    assert e_pds["end_date"] == "2023-12"
    assert e_pds["duration_months"] == 48

    # Biodata multi-line KV layout with From: / To:
    cv_bio = """
    EMPLOYMENT RECORD
    Position: Warehouse Supervisor
    Company: San Miguel Logistics Corp.
    Location: Cabuyao, Laguna
    From: March 2020
    To: August 2023
    • Managed cold-chain inventory and dispatch schedules
    """
    res_bio = extract_structured_experience(cv_bio)
    assert len(res_bio["work_experiences"]) == 1
    e_bio = res_bio["work_experiences"][0]
    assert e_bio["job_title"] == "Warehouse Supervisor"
    assert "San Miguel Logistics" in e_bio["company_name"]
    assert "Cabuyao" in (e_bio["location"] or "")
    assert e_bio["start_date"] == "2020-03"
    assert e_bio["end_date"] == "2023-08"
    assert e_bio["duration_months"] == 42


def test_bullet_dates_preserved_and_nested_subheadings():
    cv_bullets = """
    WORK EXPERIENCE
    Senior Internal Auditor
    SGV & Co.
    Jan 2020 - Dec 2024
    • Audited 2020 - 2023 financial records and tax compliance filings across 14 business units
    • Led statutory audit teams and prepared executive remediation briefings
      for quarterly board committee reviews
    Key Achievements
    • Reduced closing cycle reconciliation bottlenecks by 30%
    Selected Projects
    • Implemented automated SOX sampling workbook

    EDUCATION
    BS Accountancy
    """
    res_b = extract_structured_experience(cv_bullets)
    assert len(res_b["work_experiences"]) == 1
    e = res_b["work_experiences"][0]
    assert e["job_title"] == "Senior Internal Auditor"
    assert any("Audited 2020 - 2023 financial records" in r for r in e["responsibilities"])
    assert any("for quarterly board committee reviews" in r for r in e["responsibilities"])
    assert any("Reduced closing cycle reconciliation" in r for r in e["responsibilities"])
    assert any("SOX sampling workbook" in r for r in e["responsibilities"])

    # Kestrel Digital bullet sub-roles must STILL split cleanly
    cv_kestrel = """
    WORK EXPERIENCE
    Kestrel Digital
    • Senior Software Engineer (2022 - 2024)
    - Architected microservices platform
    • Software Engineer (2020 - 2021)
    - Developed REST endpoints
    """
    res_k = extract_structured_experience(cv_kestrel)
    assert len(res_k["work_experiences"]) == 2
    assert all("Kestrel Digital" in w["company_name"] for w in res_k["work_experiences"])


def test_substring_and_header_prefix_traps():
    cv_traps = """
    WORK EXPERIENCE
    Training Officer | Concrete Corp | Jan 2022 - Dec 2023
    Education Coordinator | Davao Medical Mission Foundation | Jan 2020 - Dec 2021
    Salesman | Nuvali Retail Depot | Jan 2019 - Dec 2019
    Draftsman | Tech Innovations Inc. | Jan 2018 - Dec 2018
    Project Management Specialist | Ayala Land Inc. | Jan 2017 - Dec 2017
    Software Development Lead | Pointwest Technologies | Jan 2016 - Dec 2016
    """
    res = extract_structured_experience(cv_traps)
    assert len(res["work_experiences"]) == 6
    titles = [w["job_title"] for w in res["work_experiences"]]
    companies = [w["company_name"] for w in res["work_experiences"]]
    assert titles[0] == "Training Officer" and "Concrete Corp" in companies[0]
    assert titles[1] == "Education Coordinator" and "Davao" in companies[1]
    assert titles[2] == "Salesman" and "Nuvali" in companies[2]
    assert titles[3] == "Draftsman" and "Tech Innovations Inc." in companies[3]
    assert "Project Management Specialist" in titles[4] and "Ayala Land" in companies[4]
    assert "Software Development Lead" in titles[5] and "Pointwest" in companies[5]


def test_expanded_dates_ocr_repair_and_acronym_title_case():
    # Expanded date formats + OCR repair
    assert _parse_date_and_duration("Jan2020 - Dec2022")[:3] == ("2020-01", "2022-12", 36)
    assert _parse_date_and_duration("15 Jan - 30 May 2024")[:3] == ("2024-01", "2024-05", 5)
    assert _parse_date_and_duration("01/06/20 - 31/12/23")[:3] == ("2020-06", "2023-12", 43)
    assert _parse_date_and_duration("Jan 20 - Dec 23")[:3] == ("2020-01", "2023-12", 48)
    s_jp, e_jp, d_jp, _ = _parse_date_and_duration("Jun 21 - Present")
    assert s_jp == "2021-06" and e_jp == "Present" and d_jp >= 48
    assert _parse_date_and_duration("Jan 2020 - 23")[:3] == ("2020-01", "2023-12", 48)
    assert _parse_date_and_duration("Early 2021 - Late 2023")[:3] == ("2021-02", "2023-10", 33)
    assert _parse_date_and_duration("VI/2020 - XII/2023")[:3] == ("2020-06", "2023-12", 43)
    assert _parse_date_and_duration("Q1 2022 - Q4 2023")[:3] == ("2022-01", "2023-12", 24)
    s_pr, e_pr, _, _ = _parse_date_and_duration("Jan 2024 - Pres.")
    assert s_pr == "2024-01" and e_pr == "Present"
    s_og, e_og, _, _ = _parse_date_and_duration("Jan 2024 - On-going")
    assert s_og == "2024-01" and e_og == "Present"
    assert _parse_date_and_duration("3y 4m")[2] == 40
    assert _parse_date_and_duration("6+ months")[2] == 6

    # Day-range guard: Jan 15 - Jan 20 must NOT be parsed as 2015-2020
    assert _parse_date_and_duration("Jan 15 - Jan 20")[2] == 0
    assert _parse_date_and_duration("June 15 - August 20, 2023")[:3] == ("2023-06", "2023-08", 3)

    # OCR repair & acronym-preserving Title Case
    cv_ocr = """
    WORK EXPERIENCE
    UI/UX DESIGNER & QA/QC LEAD | Jan 2O2O - Dec 2O23
    Accenture Philippines
    IT HR SPECIALIST | 0ct 2021 - Pr3sent
    Makati Development Corp.
    BOSH SAFETY OFFICER / CNC OPERATOR | Jan 2019 - Dec 2020
    San Miguel Packaging
    CI/CD IOS DEVELOPER | Jan 2018 - Dec 2018
    Pointwest Technologies
    """
    res_ocr = extract_structured_experience(cv_ocr)
    assert len(res_ocr["work_experiences"]) == 4
    assert res_ocr["work_experiences"][0]["start_date"] == "2020-01"
    assert res_ocr["work_experiences"][0]["end_date"] == "2023-12"
    assert res_ocr["work_experiences"][1]["start_date"] == "2021-10"
    assert res_ocr["work_experiences"][1]["end_date"] == "Present"
    t0 = res_ocr["work_experiences"][0]["job_title"]
    t1 = res_ocr["work_experiences"][1]["job_title"]
    t2 = res_ocr["work_experiences"][2]["job_title"]
    t3 = res_ocr["work_experiences"][3]["job_title"]
    assert "UI / UX" in t0 and "QA / QC" in t0
    assert "IT" in t1 and "HR" in t1
    assert "BOSH" in t2 and "CNC" in t2
    assert "CI / CD" in t3 and "iOS" in t3


def test_recency_inline_header_rescue_and_mixed_dated_undated():
    # Oldest-first chronological CV must still return most recent role & company
    cv_oldest_first = """
    WORK EXPERIENCE
    Junior Developer
    Startup Alpha Inc.
    Jan 2018 - Dec 2019

    Senior Software Architect
    Enterprise Beta Corp.
    Jan 2023 - Dec 2025
    """
    assert extract_job_title(cv_oldest_first) == "Senior Software Architect"
    assert extract_company(cv_oldest_first) == "Enterprise Beta Corp."

    # Inline single-line header
    cv_inline = """
    Work Experience: Senior Accountant | SGV & Co. | 2020 - 2024
    EDUCATION
    BS Accountancy
    """
    res_inline = extract_structured_experience(cv_inline)
    assert len(res_inline["work_experiences"]) == 1
    assert res_inline["work_experiences"][0]["job_title"] == "Senior Accountant"
    assert "SGV" in res_inline["work_experiences"][0]["company_name"]
    assert res_inline["total_experience_months"] == 60

    # Creative heading ("WHERE I'VE WORKED") and unlabeled rescue vs TC-RES-013 incomplete guard
    cv_creative = """
    WHERE I'VE WORKED
    Data Engineer
    Globe Telecom
    Jan 2021 - Dec 2023
    • Built ETL streaming pipelines
    """
    res_creative = extract_structured_experience(cv_creative)
    assert len(res_creative["work_experiences"]) == 1
    assert res_creative["work_experiences"][0]["job_title"] == "Data Engineer"

    cv_unlabeled = """
    JUAN DELA CRUZ
    juan@gmail.com | 09171234567

    Backend Developer
    Stratpoint Technologies
    Jan 2021 - Dec 2023
    • Built microservices APIs

    EDUCATION
    BS Computer Science
    UP Diliman
    2016 - 2020

    SKILLS
    Python, FastAPI
    """
    res_unl = extract_structured_experience(cv_unlabeled)
    assert len(res_unl["work_experiences"]) == 1
    assert res_unl["work_experiences"][0]["job_title"] == "Backend Developer"

    cv_incomplete = """
    JANE DOE
    jane@gmail.com | 09171234567
    EDUCATION
    BS Information Technology
    STI College
    2020 - 2024
    SKILLS
    Python, SQL
    CERTIFICATIONS
    AWS Cloud Practitioner
    """
    parsed_inc = extract_content(cv_incomplete)
    assert parsed_inc["work_experiences"] == []
    assert parsed_inc["is_incomplete"] is True

    # Mixed dated + undated roles inside EXPLICIT EXPERIENCE section
    cv_mixed = """
    WORK EXPERIENCE
    Senior QA Engineer
    Pointwest Technologies
    Jan 2022 - Dec 2024
    • Led test automation

    Freelance Web Developer
    Independent Consultant
    • Built landing pages for SMEs
    """
    res_mix = extract_structured_experience(cv_mixed)
    assert len(res_mix["work_experiences"]) == 2
    assert any("Freelance" in w["job_title"] or "Web Developer" in w["job_title"] for w in res_mix["work_experiences"])


def test_pdf_and_docx_layout_integrations():
    import os
    import tempfile
    import docx
    import fitz
    from app.extractors.file.docx_extractor import extract_text_from_docx
    from app.extractors.file.pdf_extractor import extract_text_from_pdf

    # 1. Tab-separated DOCX paragraph + date-gutter table + CSC PDS From|To table
    d = docx.Document()
    d.add_paragraph("WORK EXPERIENCE")
    d.add_paragraph("Full Stack Engineer\tInnovatech Corp\tJan 2022 - Dec 2023")

    t_gutter = d.add_table(rows=1, cols=2)
    t_gutter.cell(0, 0).text = "Jan 2020 -\nDec 2021"
    t_gutter.cell(0, 1).text = "Software Developer\nBeta Systems Inc.\n• Built REST APIs\n• Wrote unit tests\n• Deployed containers"

    t_pds = d.add_table(rows=2, cols=6)
    for idx, hdr in enumerate(["From", "To", "Position Title", "Department / Agency / Office / Company", "Monthly Salary", "Gov't Service (Y/N)"]):
        t_pds.cell(0, idx).text = hdr
    for idx, val in enumerate(["01/01/2018", "12/31/2019", "IT Officer I", "DICT Philippines", "35,000.00", "Y"]):
        t_pds.cell(1, idx).text = val

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        docx_path = tf.name
    try:
        d.save(docx_path)
        docx_txt = extract_text_from_docx(docx_path)
    finally:
        if os.path.exists(docx_path):
            os.remove(docx_path)

    parsed_docx = extract_structured_experience(docx_txt)
    assert len(parsed_docx["work_experiences"]) == 3
    assert parsed_docx["total_experience_months"] == 72

    # 2. PDF: Full-width summary above 2-col body + right-aligned dates + 2-page 2-col continuation
    pdf_doc = fitz.open()
    p1 = pdf_doc.new_page(width=595, height=842)
    p1.insert_text((40, 45), "CARLOS MENDOZA", fontsize=16)
    p1.insert_text((40, 62), "carlos.mendoza@gmail.com | 09175559999", fontsize=10)
    p1.insert_text((40, 88), "SUMMARY\nExperienced backend engineer specializing in distributed APIs and cloud databases across enterprise teams.", fontsize=10)
    # 2-column body below y=130 (x<210 sidebar, x>=230 main with right-aligned dates at x=430)
    p1.insert_text((40, 145), "SKILLS\nPython\nFastAPI\nPostgreSQL\nDocker\nRedis\nAWS", fontsize=10)
    p1.insert_text((40, 290), "EDUCATION\nBS Computer Science\nUP Diliman\n2014 - 2018", fontsize=10)
    p1.insert_text((230, 145), "WORK EXPERIENCE", fontsize=12)
    p1.insert_text((230, 170), "Lead Backend Engineer", fontsize=10)
    p1.insert_text((430, 170), "Jan 2022 - Dec 2024", fontsize=10)
    p1.insert_text((230, 185), "Accenture Philippines\n• Led backend platform migration\n• Mentored 8 engineers\n• Improved API latency", fontsize=10)

    # Page 2 continues WORK EXPERIENCE directly on right column while left column shows certifications
    p2 = pdf_doc.new_page(width=595, height=842)
    p2.insert_text((40, 60), "CERTIFICATIONS\nAWS Solutions Architect\nGCP Data Engineer\nScrum Master\nITIL Foundation", fontsize=10)
    p2.insert_text((230, 60), "Software Engineer", fontsize=10)
    p2.insert_text((430, 60), "Jan 2019 - Dec 2021", fontsize=10)
    p2.insert_text((230, 75), "Stratpoint Technologies\n• Built GraphQL services\n• Automated CI pipelines\n• Tuned SQL queries", fontsize=10)

    pdf_txt = extract_text_from_pdf(pdf_doc.tobytes())
    pdf_doc.close()

    parsed_pdf = extract_content(pdf_txt)
    assert len(parsed_pdf["work_experiences"]) == 2
    assert parsed_pdf["total_experience_months"] == 72
    assert parsed_pdf["years_experience"] == 6


def test_expanded_explicit_years_and_strict_rejections():
    assert extract_years_experience("Experience: 6+ years | Skills: Python, SQL") == 6
    assert extract_years_experience("Logistics Experience: 5 years") == 5
    assert extract_years_experience("SUMMARY\nEngineer with 7 years of hands-on, enterprise-scale software engineering experience.") == 7
    assert extract_years_experience("SUMMARY\nSoftware Engineer since 2020 building APIs.") >= 5
    assert extract_years_experience("SUMMARY\nCareer spanning 2018 - Present across fintech platforms.") >= 7
    assert extract_years_experience("SUMMARY\nOver five (5)+ years of experience in retail management.") == 5
    assert extract_experience_years_float("SUMMARY\nCandidate has a year and 6 months of accounting experience.") == 1.5
    assert extract_experience_years_float("SUMMARY\n3 taon at 6 buwan karanasan bilang warehouse staff.") == 3.5
    assert extract_years_experience("SUMMARY\nMay 8 na buwang karanasan sa pagiging kahera.") == 1
    assert extract_years_experience("SUMMARY\nWorked for a retail company for 4 years in Metro Manila.") == 4

    # Strict rejections
    assert extract_years_experience("CERTIFICATIONS\nPRC License valid for 5 years.") == 0
    assert extract_years_experience("CERTIFICATIONS\nCertification with validity of 3 years.") == 0
    assert extract_years_experience("CERTIFICATIONS\n2 years remaining before renewal.") == 0
    assert extract_years_experience("EDUCATION\nCompleted 4 years of coursework in civil engineering.") == 0





