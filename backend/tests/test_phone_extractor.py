import pytest
from app.extractors.content.phone_extractor import (
    extract_phone,
    extract_all_phones,
    _clean_phone,
    is_valid_phone
)
from app.extractors.content.content_extractor import extract_content


def test_standard_ph_mobile_extraction():
    # 09XX-XXX-XXXX format
    text1 = "Juan Dela Cruz\nMobile: 0917-123-4567\nManila, Philippines"
    assert extract_phone(text1) == "0917-123-4567"
    assert "0917-123-4567" in extract_all_phones(text1)

    # 09XX XXX XXXX format
    text2 = "Maria Santos\nContact No.: 0918 234 5678\nQuezon City"
    assert extract_phone(text2) == "0918-234-5678"

    # Raw 11 digits: 09XXXXXXXXX
    text3 = "Pedro Penduko\n09972217704 | pedro@gmail.com"
    assert extract_phone(text3) == "0997-221-7704"

    # Dot-separated: 09XX.XXX.XXXX
    text4 = "Alex Lee\nPhone: 0922.345.6789\nMakati"
    assert extract_phone(text4) == "0922-345-6789"


def test_international_ph_mobile_extraction():
    # +63 9XX XXX XXXX
    text1 = "Ana Reyes\n+63 917 123 4567\nTaguig City"
    assert extract_phone(text1) == "+63 917 123 4567"

    # +63-9XX-XXX-XXXX
    text2 = "Mark Cruz\n+63-920-987-6543\nPasig"
    assert extract_phone(text2) == "+63 920 987 6543"

    # Compact +639XXXXXXXXX
    text3 = "Carlos Tan\n+639171234567\nMandaluyong"
    assert extract_phone(text3) == "+63 917 123 4567"

    # With trunk zero: +63 (0) 917 123 4567
    text4 = "Elena Bautista\n+63 (0) 917 123 4567\nCebu City"
    assert extract_phone(text4) == "+63 917 123 4567"

    # Parens around country code: (+63) 917 123 4567
    text5 = "Teresa Ramos\n(+63) 917 123 4567\nIloilo"
    assert extract_phone(text5) == "+63 917 123 4567"

    # Without plus: 639171234567
    text6 = "Lito Gomez\nContact: 639171234567"
    assert extract_phone(text6) == "+63 917 123 4567"


def test_ph_landline_extraction():
    # Metro Manila 8-digit landline: (02) 8XXX-XXXX
    text1 = "Office Landline: (02) 8123-4567\nBGC, Taguig"
    assert extract_phone(text1) == "(02) 8123-4567"

    # Metro Manila landline international: +63 2 8XXX-XXXX
    text2 = "Direct Line: +63 2 8123 4567\nMakati"
    assert extract_phone(text2) == "+63 2 8123 4567"

    # Provincial landline: (049) 545-1234
    text3 = "Laguna Residence: (049) 545-1234\nCalamba, Laguna"
    assert extract_phone(text3) == "(049) 545-1234"


def test_icon_and_emoji_phone_extraction():
    text1 = "John Doe\n📱 0917-123-4567\n✉️ john@gmail.com"
    assert extract_phone(text1) == "0917-123-4567"

    text2 = "Jane Doe\n📞 +63 928 123 4567"
    assert extract_phone(text2) == "+63 928 123 4567"


def test_date_and_tin_exclusion():
    text = """
    Work History
    2018 - 2022 Senior Developer
    TIN: 123-456-789-000
    Mobile: 0917-555-1234
    """
    assert extract_phone(text) == "0917-555-1234"
    all_phones = extract_all_phones(text)
    assert len(all_phones) == 1
    assert all_phones[0] == "0917-555-1234"


def test_references_section_disambiguation():
    text = """
    Sebastian Curtis Lavarias
    09972217704 | sebastian@gmail.com

    WORK EXPERIENCE
    Company XYZ (2020 - 2023)

    REFERENCES
    Prof. Carlos Gomez
    Contact: 0918-999-8888
    """
    assert extract_phone(text) == "0997-221-7704"
    all_phones = extract_all_phones(text)
    assert all_phones[0] == "0997-221-7704"
    assert "0918-999-8888" in all_phones


def test_multiple_phones_extraction():
    text = "Candidate Contact: 0917-111-2222 / 0920-333-4444"
    assert extract_phone(text) == "0917-111-2222"
    all_p = extract_all_phones(text)
    assert len(all_p) >= 2
    assert "0917-111-2222" in all_p
    assert "0920-333-4444" in all_p


def test_content_extractor_phone_integration():
    sample_resume = """
    Maria Clara Dela Cruz
    Full Stack Software Engineer
    mariaclara.delacruz@gmail.com | 0917-888-9999 | Quezon City, Philippines

    EXPERIENCE
    Senior Web Developer | TechCorp Solutions
    2021 - Present
    - Developed scalable web applications

    EDUCATION
    Bachelor of Science in Information Technology | University of the Philippines
    2017 - 2021

    SKILLS
    Python | JavaScript | React | FastAPI
    """
    data = extract_content(sample_resume)
    assert data["phone"] == "0917-888-9999"
    assert "0917-888-9999" in data["phones"]
    assert "0917-888-9999" in data["all_phones"]
