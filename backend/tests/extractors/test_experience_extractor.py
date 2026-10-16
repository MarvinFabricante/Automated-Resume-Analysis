import pytest
from app.extractors.content.experience_extractor import (
    extract_structured_experience,
    extract_experience_entries,
    extract_experience,
    extract_years_experience,
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
