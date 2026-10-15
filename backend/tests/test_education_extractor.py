import pytest
from app.extractors.content.education_extractor import (
    extract_structured_education,
    extract_education_entries,
    extract_education,
    extract_highest_degree,
    extract_degree_title,
    extract_institution,
    _resolve_highest_attainment,
    _normalize_degree_or_strand,
    _extract_honors_and_awards,
    _detect_completion_status,
    _parse_academic_years,
    _split_school_and_location
)
from app.extractors.content.content_extractor import extract_content


TEMPLATE_1 = """
EDUCATIONAL BACKGROUND
Tertiary:
Bachelor of Science in Information Technology (BSIT)
STI College - Ortigas-Cainta Campus
A.Y. 2022 - 2026
- Cum Laude, Best in Capstone Project

Senior High School:
Technical-Vocational-Livelihood (TVL) - Information and Communications Technology (ICT)
Antipolo National High School, Antipolo City, Rizal
S.Y. 2020 - 2022
- With High Honors

Junior High School:
Teresa National High School, Teresa, Rizal
S.Y. 2016 - 2020

Primary:
Teresa Elementary School
2010 - 2016
"""

TEMPLATE_2 = """
EDUCATIONAL ATTAINMENT
College Level (2nd Year irregular) - BS in Hotel and Restaurant Management (BSHRM)
ICCT Colleges Foundation Inc. - Cainta Main Campus (2019 - 2021)

Vocational / Technical:
Food and Beverage Services (FBS) NC II & Bread and Pastry Production NC II
TESDA Provincial Training Center - Rizal (2022)

Secondary:
Alternative Learning System (ALS) Completer - DepEd Rizal (2018)
"""

TEMPLATE_3 = """
EDUCATION
BS Civil Engineering | Polytechnic University of the Philippines (PUP) - Sta. Mesa, Manila | 2018 - 2022 | Dean's Lister
STEM Strand (Senior High School) | Rizal National Science High School, Binangonan, Rizal | 2016 - 2018 | With Honors
"""


def test_template_1_multi_tier():
    result = extract_structured_education(TEMPLATE_1)
    
    assert result["highest_educational_attainment"] == "Tertiary / College"
    entries = result["education_entries"]
    assert len(entries) >= 4

    # Tertiary
    tertiary = next(e for e in entries if e["education_level"] == "Tertiary / College")
    assert "Information Technology" in tertiary["degree_or_course"]
    assert "STI College" in tertiary["institution_name"]
    assert tertiary["start_year"] == "2022"
    assert tertiary["end_year"] == "2026"
    assert any("Cum Laude" in h for h in tertiary["honors_and_awards"])
    assert any("Best in Capstone Project" in h for h in tertiary["honors_and_awards"])

    # Senior High School
    shs = next(e for e in entries if e["education_level"] == "Senior High School (SHS)")
    assert "TVL" in (shs["degree_or_course"] or "") or "Technical-Vocational-Livelihood" in (shs["degree_or_course"] or "")
    assert "Antipolo National High School" in shs["institution_name"]
    assert shs["start_year"] == "2020"
    assert shs["end_year"] == "2022"
    assert any("With High Honors" in h for h in shs["honors_and_awards"])

    # Junior High School
    jhs = next(e for e in entries if e["education_level"] == "Secondary / High School")
    assert "Teresa National High School" in jhs["institution_name"]
    assert jhs["start_year"] == "2016"
    assert jhs["end_year"] == "2020"

    # Primary
    elem = next(e for e in entries if e["education_level"] == "Primary / Elementary")
    assert "Teresa Elementary School" in elem["institution_name"]
    assert elem["start_year"] == "2010"
    assert elem["end_year"] == "2016"


def test_template_2_undergrad_and_tesda():
    result = extract_structured_education(TEMPLATE_2)

    # Highest attainment: TESDA is completed, while College is undergraduate level
    assert result["highest_educational_attainment"] == "Vocational / Technical (TESDA)"
    entries = result["education_entries"]
    assert len(entries) >= 3

    # College entry
    college = next(e for e in entries if e["education_level"] == "Tertiary / College")
    assert college["status"] == "Undergraduate / College Level"
    assert "Hospitality Management" in college["degree_or_course"] or "Hotel and Restaurant" in college["degree_or_course"]
    assert "ICCT Colleges" in college["institution_name"]
    assert college["start_year"] == "2019"
    assert college["end_year"] == "2021"

    # TESDA entry
    tesda_entries = [e for e in entries if e["education_level"] == "Vocational / Technical (TESDA)"]
    assert len(tesda_entries) >= 1
    t_entry = tesda_entries[0]
    assert "NC II" in (t_entry["degree_or_course"] or "")
    assert "TESDA" in t_entry["institution_name"] or "Training Center" in t_entry["institution_name"]
    assert t_entry["status"] == "Completed"
    assert t_entry["end_year"] == "2022"

    # Secondary ALS entry
    als = next(e for e in entries if e["education_level"] == "Secondary / High School")
    assert "ALS" in (als["degree_or_course"] or "") or "Alternative Learning System" in (als["degree_or_course"] or "")
    assert als["status"] == "Completed"
    assert als["end_year"] == "2018"


def test_template_3_compact_engineering():
    result = extract_structured_education(TEMPLATE_3)

    assert result["highest_educational_attainment"] == "Tertiary / College"
    entries = result["education_entries"]
    assert len(entries) >= 2

    # College entry
    pup_entry = next(e for e in entries if e["education_level"] == "Tertiary / College")
    assert "Civil Engineering" in pup_entry["degree_or_course"]
    assert "Polytechnic University of the Philippines" in pup_entry["institution_name"]
    assert pup_entry["start_year"] == "2018"
    assert pup_entry["end_year"] == "2022"
    assert any("Dean's Lister" in h for h in pup_entry["honors_and_awards"])

    # SHS entry
    shs_entry = next(e for e in entries if e["education_level"] == "Senior High School (SHS)")
    assert "STEM" in shs_entry["degree_or_course"]
    assert "Rizal National Science High School" in shs_entry["institution_name"]
    assert shs_entry["start_year"] == "2016"
    assert shs_entry["end_year"] == "2018"
    assert any("With Honors" in h for h in shs_entry["honors_and_awards"])


def test_degree_normalization():
    # Philippine Bachelor abbreviations
    assert _normalize_degree_or_strand("BSIT") == "Bachelor of Science in Information Technology"
    assert _normalize_degree_or_strand("BSCS") == "Bachelor of Science in Computer Science"
    assert _normalize_degree_or_strand("BSCE") == "Bachelor of Science in Civil Engineering"
    assert _normalize_degree_or_strand("BSA") == "Bachelor of Science in Accountancy"
    assert _normalize_degree_or_strand("BSBA-FM") == "Bachelor of Science in Business Administration Major in Financial Management"
    assert _normalize_degree_or_strand("BSN") == "Bachelor of Science in Nursing"
    assert _normalize_degree_or_strand("BSCrim") == "Bachelor of Science in Criminology"

    # Senior High School strands
    assert "STEM" in _normalize_degree_or_strand("STEM")
    assert "ABM" in _normalize_degree_or_strand("ABM")
    assert "HUMSS" in _normalize_degree_or_strand("HUMSS")
    assert "TVL" in _normalize_degree_or_strand("TVL")


def test_academic_honors_extraction():
    text1 = "Graduated Cum Laude and Dean's Lister, Batch 2023"
    honors1 = _extract_honors_and_awards(text1)
    assert "Cum Laude" in honors1
    assert "Dean's Lister" in honors1

    text2 = "Valedictorian with Highest Honors and Best in Capstone Project"
    honors2 = _extract_honors_and_awards(text2)
    assert "Valedictorian" in honors2
    assert "With Highest Honors" in honors2
    assert "Best in Capstone Project" in honors2


def test_status_detection():
    assert _detect_completion_status("2nd Year College Level irregular") == "Undergraduate / College Level"
    assert _detect_completion_status("Completed 3rd Year College Undergrad") == "Undergraduate / College Level"
    assert _detect_completion_status("Currently Enrolled in BSIT 4th year") == "Ongoing"
    assert _detect_completion_status("Alternative Learning System (ALS) Completer") == "Completed"
    assert _detect_completion_status("TESDA NC II Holder") == "Completed"
    assert _detect_completion_status("Graduated Magna Cum Laude") == "Graduated"


def test_hierarchy_resolver():
    # Completed college graduates higher than college undergrad
    entries_grad = [
        {"education_level": "Tertiary / College", "status": "Graduated"},
        {"education_level": "Senior High School (SHS)", "status": "Graduated"}
    ]
    assert _resolve_highest_attainment(entries_grad) == "Tertiary / College"

    # TESDA completed is higher than College Undergrad
    entries_tesda = [
        {"education_level": "Tertiary / College", "status": "Undergraduate / College Level"},
        {"education_level": "Vocational / Technical (TESDA)", "status": "Completed"}
    ]
    assert _resolve_highest_attainment(entries_tesda) == "Vocational / Technical (TESDA)"

    # Postgraduate beats all
    entries_postgrad = [
        {"education_level": "Postgraduate", "status": "Graduated"},
        {"education_level": "Tertiary / College", "status": "Graduated"}
    ]
    assert _resolve_highest_attainment(entries_postgrad) == "Postgraduate"


def test_backward_compatibility():
    # extract_highest_degree
    assert extract_highest_degree(TEMPLATE_1) == "BACHELOR"
    # extract_degree_title
    assert "Civil Engineering" in extract_degree_title(TEMPLATE_3) or "BS" in extract_degree_title(TEMPLATE_3)
    # extract_institution
    assert "STI College" in extract_institution(TEMPLATE_1)
    # extract_education
    edu_text = extract_education(TEMPLATE_1)
    assert "STI College" in edu_text or "Information Technology" in edu_text
    # extract_education_entries
    entries = extract_education_entries(TEMPLATE_1)
    assert len(entries) >= 4


def test_content_extractor_integration():
    resume_text = f"""
MARVIN FABRICANTE
Senior Software Engineer
09171234567 | marvin@gmail.com | Antipolo City, Rizal

{TEMPLATE_1}

WORK EXPERIENCE
Senior Full Stack Engineer
ABC Software Solutions Inc. - Makati City
2023 - Present
- Built enterprise applications using Python and React.
"""
    extracted = extract_content(resume_text)
    assert "education_entries" in extracted
    assert "highest_educational_attainment" in extracted
    assert extracted["highest_educational_attainment"] == "Tertiary / College"
    assert len(extracted["education_entries"]) >= 4
