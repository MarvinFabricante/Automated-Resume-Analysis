import pytest
from app.extractors.content.name_extractor import (
    extract_fullname,
    extract_all_name_candidates,
    _normalize_name,
    _invert_surname_first,
    is_valid_name
)
from app.extractors.content.content_extractor import extract_content


def test_standard_filipino_names():
    text1 = "JOHN PAUL T. BASAGRE\nFilipinas Avenue, Teresa, Rizal\n09602465936 | johnpaul@gmail.com"
    assert extract_fullname(text1) == "John Paul T. Basagre"

    text2 = "SEBASTIAN CURTIS LAVARIAS\nFull Stack Web Developer\nsebastian@gmail.com"
    assert extract_fullname(text2) == "Sebastian Curtis Lavarias"

    text3 = "Mary Grace P. Ramos\nEmail: marygrace@gmail.com"
    assert extract_fullname(text3) == "Mary Grace P. Ramos"


def test_surname_first_inversion():
    # Common Philippine government and school CV format: SURNAME, FIRST NAME MIDDLE
    text1 = "BASAGRE, JOHN PAUL T.\nDulumbayan, Teresa, Rizal\n09602465936"
    assert extract_fullname(text1) == "John Paul T. Basagre"

    text2 = "DELA CRUZ, JUAN M.\nQuezon City\n0917-123-4567"
    assert extract_fullname(text2) == "Juan M. Dela Cruz"

    text3 = "LAVARIAS, SEBASTIAN CURTIS\nManila"
    assert extract_fullname(text3) == "Sebastian Curtis Lavarias"

    text4 = "Santos, Maria Theresa G., CPA\nMakati City"
    assert extract_fullname(text4) == "Maria Theresa G. Santos, CPA"


def test_ma_maria_abbreviation():
    # In the Philippines, 'Ma.' is the standard abbreviation for Maria
    text1 = "Ma. Cristina G. Santos\nAccounting Associate\nmacristina@gmail.com"
    assert extract_fullname(text1) == "Ma. Cristina G. Santos"

    text2 = "MA. THERESA DELA CRUZ\nRegistered Nurse\n0918-123-4567"
    assert extract_fullname(text2) == "Ma. Theresa Dela Cruz"


def test_compound_filipino_surnames():
    # Dela Cruz, Del Rosario, Delos Santos, De Guzman, San Jose, Santa Maria
    text1 = "Juan Dela Cruz\nSoftware Engineer\njuan.delacruz@gmail.com"
    assert extract_fullname(text1) == "Juan Dela Cruz"

    text2 = "Maria Elena Del Rosario\nHR Specialist\n0917-888-9999"
    assert extract_fullname(text2) == "Maria Elena Del Rosario"

    text3 = "Mark Anthony Delos Santos\nWeb Developer\nmark@gmail.com"
    assert extract_fullname(text3) == "Mark Anthony Delos Santos"

    text4 = "Princess Joy De Guzman\nMarketing Manager"
    assert extract_fullname(text4) == "Princess Joy De Guzman"

    text5 = "Jan Paul San Jose\nCivil Engineer"
    assert extract_fullname(text5) == "Jan Paul San Jose"

    text6 = "Francis Santa Maria\nIT Specialist"
    assert extract_fullname(text6) == "Francis Santa Maria"


def test_prc_professional_licenses_and_suffixes():
    text1 = "Juan Dela Cruz, CPA\nSenior Auditor\n0917-123-4567"
    assert extract_fullname(text1) == "Juan Dela Cruz, CPA"

    text2 = "Maria Santos, RN\nStaff Nurse\n0918-234-5678"
    assert extract_fullname(text2) == "Maria Santos, RN"

    text3 = "Engr. Aris Mendoza, ECE\nTelecommunications Engineer"
    assert extract_fullname(text3) == "Aris Mendoza, ECE"

    text4 = "Ar. Kenneth Bautista, UAP\nArchitectural Designer"
    assert extract_fullname(text4) == "Kenneth Bautista, UAP"

    text5 = "Pedro Penduko, Jr.\nTechnician\n0997-123-4567"
    assert extract_fullname(text5) == "Pedro Penduko, Jr."

    text6 = "Antonio Luna III\nData Analyst"
    assert extract_fullname(text6) == "Antonio Luna III"


def test_biodata_and_tagalog_labels():
    text1 = "PANGALAN: Juan Dela Cruz\nTirahan: Manila\nMobile: 0917-123-4567"
    assert extract_fullname(text1) == "Juan Dela Cruz"

    text2 = "Full Name: Christian Dave M. Garcia\nEmail: cdave@gmail.com"
    assert extract_fullname(text2) == "Christian Dave M. Garcia"


def test_job_title_avoidance_and_email_correlation():
    text1 = """
    CURRICULUM VITAE
    FULL STACK DEVELOPER
    Sebastian Curtis Lavarias
    sebastiancurtislavarias@gmail.com
    """
    assert extract_fullname(text1) == "Sebastian Curtis Lavarias"

    text2 = """
    RESUME
    CUSTOMER SERVICE REPRESENTATIVE
    Quezon City, Metro Manila
    Jhesed Tacadena
    0917-111-2222 | jhesed@gmail.com
    """
    assert extract_fullname(text2) == "Jhesed Tacadena"


def test_content_extractor_fullname_integration():
    sample_resume = """
    BASAGRE, JOHN PAUL T.
    Bachelor of Science in Computer Science
    Filipinas Avenue, Teresa, Rizal
    0960-246-5936 | johnpaul6214@gmail.com

    EXPERIENCE
    Junior Web Developer | Tech Solutions
    2022 - Present

    SKILLS
    Python | JavaScript | React | FastAPI
    """
    data = extract_content(sample_resume)
    assert data["fullname"] == "John Paul T. Basagre"
    assert "John Paul T. Basagre" in data["names"]
    assert "John Paul T. Basagre" in data["all_names"]
    assert data["email"] == "johnpaul6214@gmail.com"
    assert data["phone"] == "0960-246-5936"
