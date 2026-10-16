import pytest
from app.extractors.content.email_extractor import (
    extract_email,
    extract_all_emails,
    _clean_email,
    is_valid_email
)
from app.extractors.content.content_extractor import extract_content


def test_standard_email_extraction():
    text = "Candidate Name\nSoftware Developer\njohn.doe@gmail.com\nPhone: +1 555 123 4567"
    assert extract_email(text) == "john.doe@gmail.com"
    assert "john.doe@gmail.com" in extract_all_emails(text)


def test_labeled_email_extraction():
    text = "Applicant: Jane Smith\nE-mail: jane.smith@company.org\nContact: 0917-123-4567"
    assert extract_email(text) == "jane.smith@company.org"


def test_icon_and_emoji_email_extraction():
    text = "Marvin Fabricante\n✉️ marvin.fabricante@gmail.com\n📞 09123456789"
    assert extract_email(text) == "marvin.fabricante@gmail.com"

    text2 = "Alex Santos\n📧 alex.santos@outlook.com"
    assert extract_email(text2) == "alex.santos@outlook.com"


def test_mailto_extraction():
    text = "Portfolio: https://candidate.dev\nmailto:developer@proton.me?subject=Inquiry"
    assert extract_email(text) == "developer@proton.me"


def test_spaced_and_wrapped_email_extraction():
    # Spaced email resulting from multi-column text extraction
    text = "Contact: juan . dela . cruz @ gmail . com\nMetro Manila"
    assert extract_email(text) == "juan.dela.cruz@gmail.com"

    # Linebreak within email
    text2 = "Reach out at maria.santos@\ngmail.com or call me."
    assert extract_email(text2) == "maria.santos@gmail.com"


def test_obfuscated_email_extraction():
    text = "Security Engineer: alice [at] security [dot] io"
    assert extract_email(text) == "alice@security.io"

    text2 = "Contact: bob (at) research (dot) up (dot) edu (dot) ph"
    assert extract_email(text2) == "bob@research.up.edu.ph"


def test_multi_part_and_modern_tlds():
    text1 = "Engr. Reyes\nreyes@coe.upd.edu.ph\nCollege of Engineering"
    assert extract_email(text1) == "reyes@coe.upd.edu.ph"

    text2 = "Cloud Architect: lead@cloudnative.engineering"
    assert extract_email(text2) == "lead@cloudnative.engineering"


def test_placeholder_filtering():
    text = """
    Resume Template
    your.email@example.com
    Candidate: Arthur Dent
    arthur.dent@galaxy.org
    """
    assert extract_email(text) == "arthur.dent@galaxy.org"
    all_emails = extract_all_emails(text)
    assert "your.email@example.com" not in all_emails


def test_disambiguation_with_candidate_name():
    text = """
    Sebastian Curtis Lavarias
    Full Stack Developer
    sebastiancurtislavarias@gmail.com | 09171234567

    Work Experience:
    Company XYZ - contact info@companyxyz.com or hr@companyxyz.com

    References:
    Prof. Carlos D. Gomez
    Email: cgomez@university.edu.ph
    """
    primary = extract_email(text, candidate_name="Sebastian Curtis Lavarias")
    assert primary == "sebastiancurtislavarias@gmail.com"

    all_emails = extract_all_emails(text, candidate_name="Sebastian Curtis Lavarias")
    assert all_emails[0] == "sebastiancurtislavarias@gmail.com"
    assert "cgomez@university.edu.ph" in all_emails


def test_content_extractor_integration():
    sample_resume = """
    Maria Clara Dela Cruz
    Full Stack Software Engineer
    mariaclara.delacruz@gmail.com | +63 917 123 4567 | Quezon City, Philippines

    EXPERIENCE
    Senior Web Developer | TechCorp Solutions
    2021 - Present
    - Developed scalable web applications

    EDUCATION
    Bachelor of Science in Information Technology | University of the Philippines
    2017 - 2021

    SKILLS
    Python | JavaScript | React | FastAPI | Docker | PostgreSQL
    """
    data = extract_content(sample_resume)
    assert data["email"] == "mariaclara.delacruz@gmail.com"
    assert "mariaclara.delacruz@gmail.com" in data["emails"]
    assert "mariaclara.delacruz@gmail.com" in data["all_emails"]
