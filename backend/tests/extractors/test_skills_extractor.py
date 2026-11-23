"""
Tests for Philippine Resume Skills Extraction Engine
===================================================
Validates multi-pass extraction across blue-collar, BPO/admin, and technical
workforce archetypes, schema compliance, fuzzy normalization, and backward compatibility.
"""

import os
import tempfile
import pytest

from app.extractors.content.skills_extractor import (
    PhilippineSkillsExtractor,
    extract_structured_skills,
    extract_skills,
    extract_skills_list,
    load_external_skill_datasets,
    COMMON_SKILLS,
    _format_skill,
)
from app.extractors.content.content_extractor import extract_content


# ─── Archetype Resume Templates ───────────────────────────────────────────────

RESUME_BLUE_COLLAR = """
OBJECTIVE
Seeking a Service Crew or Janitor position where I can utilize my skills in food preparation,
kitchen sanitation, and customer service. Willing to learn and work under pressure.

WORK EXPERIENCE
Service Crew
Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna
June 2023 - December 2023
- Food preparation and kitchen sanitation in frying and grill stations.
- Handled POS cashiering, cash handling, and customer order taking.
- Performed dining area table bussing, tray cleaning, and dishwashing.

Utility Personnel / Janitor
Robinsons Place Antipolo
January 2022 - May 2023
- Floor buffing and housekeeping using heavy-duty rotary floor polisher.
- Restroom sanitation, trash segregation, and chemical handling.

Delivery Rider
Lalamove Philippines / Self-Employed
2021 - 2022
- Single motorcycle driving with Professional Driver's License Restriction 1, 2.
- Defensive driving and mobile GPS navigation across Metro Manila and Rizal.

SKILLS & TRAITS
- Fast learner and willing to be trained
- Can work under pressure and willing to render overtime
- Team player with good interpersonal skills
- Fluent in Tagalog and basic English
"""

RESUME_BPO_ADMIN = """
CAREER SUMMARY
Dedicated Customer Service Representative with 2+ years of BPO experience handling inbound technical support and customer care accounts.

CORE COMPETENCIES & SKILLS
- Customer service & active listening
- Conflict de-escalation & complaint resolution
- 45 WPM typing speed
- Inbound call handling & email correspondence
- Ticketing systems: Zendesk, Freshdesk, Jira Service Desk
- CRM & VoIP tools: Salesforce, Avaya One-X, Cisco IP Phone
- Proficient in Microsoft Office (Excel VLOOKUP & Pivot Tables, Word, PowerPoint)
- 201 file management and data encoding
- Amenable to shifting schedules, night shift, and holiday overtime
- Languages: Fluent in English and Filipino / Tagalog

WORK EXPERIENCE
Technical Support Representative (TSR)
Concentrix Philippines - Bridgetowne, Pasig City
March 2022 - Present
- Handled 50+ inbound customer inquiries daily regarding internet connectivity and account billing.
- Utilized Zendesk and Avaya for real-time call logging and customer de-escalation.
"""

RESUME_SOFTWARE_DEV = """
SOFTWARE ENGINEER
Makati City, Metro Manila | 09171234567 | dev@gmail.com

TECHNICAL SKILLS
Languages: Java, C#, TypeScript, JavaScript, Python, SQL, HTML5, CSS3
Frameworks & Libraries: Spring Boot, NestJS, Node.js, Express.js, React.js, Next.js, Tailwind CSS
Databases & Cloud: PostgreSQL, Supabase, MongoDB Atlas, Redis, Docker, AWS (S3, EC2)
Tools & Testing: Git, GitHub Actions, Postman, Jest, Cypress, CI/CD, Linux

PROFESSIONAL EXPERIENCE
Full Stack Software Developer
Accenture Philippines | BGC, Taguig City
August 2023 - Present
- Developed scalable RESTful APIs using NestJS and PostgreSQL with Supabase.
- Built responsive UI components using React and Tailwind CSS.
- Performed manual regression testing and automated API testing using Postman.
- Collaborated in an Agile Scrum environment with daily standups and sprint planning.
"""

RESUME_CIVIL_WELDER = """
REGISTERED CIVIL ENGINEER / SITE ENGINEER
Binangonan, Rizal | 09181234567 | civil_eng@gmail.com

LICENSES & CERTIFICATIONS
- PRC Registered Civil Engineer (Civil Engineering Board Exam Passer)
- BOSH SO2 Certified (Basic Occupational Safety and Health)
- TESDA Shielded Metal Arc Welding (SMAW) NC II Certified
- COSH Certified (Construction Occupational Safety and Health)

TECHNICAL & ENGINEERING SKILLS
- AutoCAD (2D & 3D), STAAD.Pro, ETABS, Revit, SketchUp, MS Project
- Structural analysis and design
- Site supervision and construction management
- Concrete pouring and rebar inspection
- Quantity surveying, cost estimation, and Bill of Quantities (BOQ) preparation
- Blueprint reading and architectural plan interpretation
- TIG/MIG welding and metal fabrication

WORK EXPERIENCE
Project Site Engineer
DMCI Homes - Quezon City
March 2023 - Present
- Conducted daily site supervision and reinforced concrete quality inspection.
- Prepared daily accomplishment reports and monitored subcontractor manpower.
- Ensured strict compliance with construction safety and ISO 9001 quality standards.
"""


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_blue_collar_service_worker_extraction():
    """Validates extraction on Jollibee crew, janitor, and motorcycle delivery rider."""
    out = extract_structured_skills(RESUME_BLUE_COLLAR)

    assert out["total_unique_skills"] >= 15
    summary = out["skill_summary_by_type"]
    assert summary["hard_skills_count"] >= 10
    assert summary["soft_skills_count"] >= 4
    assert summary["certifications_and_licenses_count"] >= 1
    assert summary["languages_count"] >= 2

    # Check canonical skills in categorized view
    cats = out["categorized_view"]
    assert "Food Preparation" in cats["hard_skills"]
    assert "Kitchen Sanitation" in cats["hard_skills"]
    assert "Dining Table Bussing" in cats["hard_skills"]
    assert "Dishwashing & Stewarding" in cats["hard_skills"]
    assert "Defensive Driving" in cats["hard_skills"]
    assert "Restroom Sanitation" in cats["hard_skills"]
    assert "Waste Segregation" in cats["hard_skills"]
    assert "Chemical Handling & Dilution" in cats["hard_skills"]

    # Tools
    assert "POS Cashiering" in cats["tools_and_technologies"]
    assert "Floor Polishing & Buffing" in cats["tools_and_technologies"]

    # Soft skills & Filipino traits
    assert "Stress Tolerance (Can Work Under Pressure)" in cats["soft_skills"]
    assert "Overtime & Shifting Flexibility" in cats["soft_skills"]
    assert "Fast Learner & Willing to be Trained" in cats["soft_skills"]
    assert "Teamwork & Collaboration" in cats["soft_skills"]
    assert "Interpersonal Skills" in cats["soft_skills"]

    # License & Languages
    assert "Professional Driver's License (LTO)" in cats["certifications_and_eligibility"]
    assert "Tagalog / Filipino" in cats["languages"]
    assert "English" in cats["languages"]


def test_bpo_admin_extraction():
    """Validates extraction on BPO CSR, TSR, and administrative assistant."""
    out = extract_structured_skills(RESUME_BPO_ADMIN)

    assert out["total_unique_skills"] >= 15
    cats = out["categorized_view"]

    # Hard skills & metrics
    assert "Customer Service" in cats["hard_skills"]
    assert "Technical Support" in cats["hard_skills"]
    assert "Typing Speed (WPM)" in cats["hard_skills"]
    assert "Inbound & Outbound Calling" in cats["hard_skills"]
    assert "201 File Management" in cats["hard_skills"]
    assert "Data Encoding & Entry" in cats["hard_skills"]

    # Tools
    assert "Zendesk" in cats["tools_and_technologies"]
    assert "Freshdesk" in cats["tools_and_technologies"]
    assert "Salesforce CRM" in cats["tools_and_technologies"]
    assert "Avaya VoIP" in cats["tools_and_technologies"]
    assert "Microsoft Office Suite" in cats["tools_and_technologies"]
    assert "Advanced Excel (VLOOKUP & Pivot Tables)" in cats["tools_and_technologies"]

    # Soft skills
    assert "Active Listening" in cats["soft_skills"]
    assert "Conflict De-escalation" in cats["soft_skills"]
    assert "Overtime & Shifting Flexibility" in cats["soft_skills"]


def test_software_developer_extraction():
    """Validates extraction on full-stack software engineer stack."""
    out = extract_structured_skills(RESUME_SOFTWARE_DEV)

    assert out["total_unique_skills"] >= 20
    tools = out["categorized_view"]["tools_and_technologies"]

    assert "Java" in tools
    assert "C#" in tools
    assert "TypeScript" in tools
    assert "Python" in tools
    assert "SQL" in tools
    assert "Spring Boot" in tools
    assert "NestJS" in tools
    assert "Node.js" in tools
    assert "React.js" in tools
    assert "Next.js" in tools
    assert "Tailwind CSS" in tools
    assert "PostgreSQL" in tools
    assert "Supabase" in tools
    assert "Docker" in tools
    assert "Amazon Web Services (AWS)" in tools
    assert "Git & Version Control" in tools
    assert "Postman" in tools
    assert "Jest & Cypress" in tools

    assert "Agile Scrum" in out["categorized_view"]["hard_skills"]
    assert "Regression Testing" in out["categorized_view"]["hard_skills"]


def test_civil_engineer_and_welder_extraction():
    """Validates extraction on PRC civil engineer and TESDA certified welder."""
    out = extract_structured_skills(RESUME_CIVIL_WELDER)

    assert out["total_unique_skills"] >= 15
    cats = out["categorized_view"]

    # Licensure & certifications
    certs = cats["certifications_and_eligibility"]
    assert "PRC Registered Civil Engineer" in certs
    assert "Basic Occupational Safety and Health (BOSH)" in certs
    assert "Construction Occupational Safety and Health (COSH)" in certs
    assert "TESDA National Certificate (NC II)" in certs

    # Engineering tools
    tools = cats["tools_and_technologies"]
    assert "AutoCAD (2D & 3D)" in tools
    assert "STAAD.Pro" in tools
    assert "ETABS" in tools
    assert "Revit Architecture & BIM" in tools
    assert "SketchUp" in tools
    assert "Primavera P6 & MS Project" in tools
    assert "Shielded Metal Arc Welding (SMAW)" in tools
    assert "TIG & MIG Welding" in tools

    # Domain hard skills
    hard = cats["hard_skills"]
    assert "Structural Analysis & Design" in hard
    assert "Site Supervision & Construction Management" in hard
    assert "Concrete Pouring & Rebar Inspection" in hard
    assert "Quantity Surveying & Cost Estimation" in hard
    assert "Bill of Quantities (BOQ)" in hard
    assert "Blueprint Reading & Plan Interpretation" in hard
    assert "ISO 9001 Quality Standards" in hard


def test_json_output_schema_structure():
    """Ensures exact conformance to the expected JSON output schema."""
    text = "Proficient in Python, React, and Customer Service. Can work under pressure. Speaks Tagalog."
    res = extract_structured_skills(text)

    # Root fields
    assert "total_unique_skills" in res
    assert isinstance(res["total_unique_skills"], int)
    assert "skill_summary_by_type" in res
    assert "extracted_skills" in res
    assert "categorized_view" in res

    # Summary by type
    summary = res["skill_summary_by_type"]
    assert "hard_skills_count" in summary
    assert "soft_skills_count" in summary
    assert "certifications_and_licenses_count" in summary
    assert "languages_count" in summary

    # Extracted skill item schema
    assert len(res["extracted_skills"]) == res["total_unique_skills"]
    for item in res["extracted_skills"]:
        assert "canonical_skill" in item
        assert "raw_mention" in item
        assert "skill_type" in item
        assert item["skill_type"] in {"Hard Skill", "Soft Skill", "Certification / License", "Language"}
        assert "domain_category" in item
        assert "source_section" in item
        assert "extraction_method" in item
        assert item["extraction_method"] in {"Gazetteer_Exact", "Regex_Pattern", "Syntactic_Dependency", "Fuzzy_Normalized"}
        assert "confidence_score" in item
        assert 0.0 <= item["confidence_score"] <= 1.0

    # Categorized view
    cats = res["categorized_view"]
    assert "hard_skills" in cats
    assert "soft_skills" in cats
    assert "tools_and_technologies" in cats
    assert "certifications_and_eligibility" in cats
    assert "languages" in cats


def test_fuzzy_normalization_and_typos():
    """Validates that minor variations and abbreviations map to canonical skills."""
    text = """
SKILLS
- Cust. Service
- MS Word/Excel/Powerpoint
- SMAW NCII Certified
- BOSH SO2
"""
    out = extract_structured_skills(text)
    canonicals = [s["canonical_skill"] for s in out["extracted_skills"]]

    assert "Customer Service" in canonicals
    assert "Microsoft Office Suite" in canonicals
    assert "Shielded Metal Arc Welding (SMAW)" in canonicals
    assert "Basic Occupational Safety and Health (BOSH)" in canonicals


def test_external_dataset_ingestion_hook():
    """Validates runtime ingestion of external ESCO / O*NET / TESDA datasets."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Quantum Computing Qiskit\t15-1252.00\tTechnology\n")
        f.flush()
        onet_path = f.name

    try:
        added = load_external_skill_datasets(onet_txt_path=onet_path)
        assert added >= 1

        test_text = "Experienced in Quantum Computing Qiskit and cloud workflows."
        out = extract_structured_skills(test_text)
        extracted_names = [s["canonical_skill"] for s in out["extracted_skills"]]
        assert "Quantum Computing Qiskit" in extracted_names
    finally:
        if os.path.exists(onet_path):
            os.remove(onet_path)


def test_backward_compatibility():
    """Validates backward-compatible helper functions and symbols."""
    text = "Java, Python, Docker, Customer Service"

    skills_str = extract_skills(text)
    assert isinstance(skills_str, str)
    assert "Java" in skills_str
    assert "Python" in skills_str

    skills_list = extract_skills_list(text)
    assert isinstance(skills_list, list)
    assert "Docker" in skills_list

    # COMMON_SKILLS and _format_skill
    assert "PYTHON" in COMMON_SKILLS
    assert "JAVA" in COMMON_SKILLS
    assert _format_skill("node.js") == "Node.js"
    assert _format_skill("html5") == "HTML5"


def test_content_extractor_integration():
    """Validates that extract_content populates skills_details correctly."""
    resume_text = """
Maria Santos
maria.santos@gmail.com | 09171234567
Pasig City, Metro Manila

CORE SKILLS
- Customer Service & Active Listening
- Zendesk & Salesforce
- 45 WPM typing speed
"""
    content = extract_content(resume_text)

    assert "skills" in content
    assert "skills_list" in content
    assert "skills_details" in content

    details = content["skills_details"]
    assert details["total_unique_skills"] >= 4
    assert details["skill_summary_by_type"]["hard_skills_count"] >= 2
    assert details["skill_summary_by_type"]["soft_skills_count"] >= 1


def test_skills_extraction_known_list_not_flagged_incomplete():
    """
    Validates that resumes with a known skill list across inline headers,
    alternate/numbered headers, Summary declarations, or 2-column layouts
    capture all listed skills without falsely flagging Skills as missing.
    """
    # 1. Inline Skills: with >= 7 words
    inline_resume = """
JUAN DELA CRUZ
juan@gmail.com | 09171234567 | Makati City

WORK EXPERIENCE
Software Engineer | Tech Corp | 2021 - Present
- Built enterprise APIs.

EDUCATION
BS Computer Science | UP Diliman | 2017 - 2021

Skills: Python, FastAPI, React, TypeScript, PostgreSQL, Docker, Git, AWS
"""
    res_inline = extract_content(inline_resume)
    assert res_inline["is_incomplete"] is False
    assert "Skills" not in res_inline["missing_sections"]
    assert len(res_inline["skills_list"]) >= 8
    assert "Python" in res_inline["skills_list"]
    assert "FastAPI" in res_inline["skills_list"]
    assert "Docker" in res_inline["skills_list"]

    # 2. Numbered / parenthesized / alternate Skills header
    alt_header_resume = """
MARIA SANTOS
maria@gmail.com | 09181234567 | Pasig City

WORK EXPERIENCE
Accountant | SGV & Co | 2020 - Present
- Prepared tax returns and audits.

EDUCATION
BS Accountancy | University of Santo Tomas | 2016 - 2020

IV. SKILLS & QUALIFICATIONS (TECHNICAL)
QuickBooks, SAP, Philippine Taxation, Microsoft Excel, Financial Accounting
"""
    res_alt = extract_content(alt_header_resume)
    assert res_alt["is_incomplete"] is False
    assert "Skills" not in res_alt["missing_sections"]
    assert "Financial Accounting" in res_alt["skills_list"]
    assert "Philippine Taxation" in res_alt["skills_list"]

    # 3. Skills declared in Summary ("Proficient in ...") without standalone SKILLS header
    summary_skills_resume = """
PEDRO REYES
pedro@gmail.com | 09191234567 | Quezon City

SUMMARY
Full stack engineer proficient in Python, FastAPI, React, Docker, PostgreSQL, and Git.

WORK EXPERIENCE
Developer | Accenture | 2021 - Present
- Built microservices.

EDUCATION
BS Information Technology | PUP | 2017 - 2021
"""
    res_summary = extract_content(summary_skills_resume)
    assert res_summary["is_incomplete"] is False
    assert "Skills" not in res_summary["missing_sections"]
    assert len(res_summary["skills_list"]) >= 6

    # 4. Placeholder Skills ("N/A") must still flag Skills as missing and not leak into summary
    placeholder_resume = """
DIANA REYES
diana.reyes@gmail.com | 0919-333-4444 | Quezon City

EDUCATION
BS Civil Engineering | PUP | 2018 - 2022

WORK EXPERIENCE
Site Engineer | Megawide | 2022 - Present
- Supervised concrete pouring.

SKILLS
N/A
"""
    res_na = extract_content(placeholder_resume)
    assert res_na["is_incomplete"] is True
    assert "Skills" in res_na["missing_sections"]
    assert res_na["skills_list"] == []
    assert res_na["skills"] == ""
    assert "Core competencies include" not in res_na["summary"]


def test_skills_section_captures_custom_and_taxonomy_skills():
    """
    Ensures all listed skills in the SKILLS section (including custom/domain
    skills alongside taxonomy-matched skills) are captured in skills and skills_list.
    """
    r1_text = """
JUAN DELA CRUZ
juan.delacruz@gmail.com | 09171234567 | Laguna

WORK EXPERIENCE
QA Lead | Mariwasa Ceramics | 2020 - Present
- Supervised ceramic tile inspection and quality adherence.

EDUCATION
BS Materials Engineering | Mapua University | 2016 - 2020

SKILLS
Quality Control, ISO 9001, Six Sigma, Tile Inspection, Ceramic Glazing, Kiln Operation, Minitab
"""
    res = extract_content(r1_text)
    assert res["is_incomplete"] is False
    assert res["missing_sections"] == []
    captured = res["skills_list"]
    for expected in [
        "ISO 9001 Quality Standards",
        "Six Sigma Quality Management",
        "Quality Control",
        "Tile Inspection",
        "Ceramic Glazing",
        "Kiln Operation",
        "Minitab",
    ]:
        assert expected in captured, f"Expected '{expected}' in captured skills: {captured}"
        assert expected in res["skills"]


def test_r5_synonym_recognition_ml_and_qc():
    """
    Validates Synonym recognition for R5 ('ML', 'QC'):
    - 'ML' maps to 'Machine Learning'
    - 'QC' maps to 'Quality Control' (without hijacking Quezon City addresses or '500 ml')
    """
    r5_text = """
ALEXANDER REYES
alex.reyes@gmail.com | 09171234567

WORK EXPERIENCE
Data & Quality Analyst | Metro Systems Inc.
2021 - 2024
- Built predictive pipelines using ML and performed daily QC checks.

EDUCATION
BS Computer Science | UP Diliman | 2017 - 2021

SKILLS
ML, QC
"""
    res = extract_content(r5_text)
    assert res["is_incomplete"] is False
    assert "Machine Learning" in res["skills_list"]
    assert "Quality Control" in res["skills_list"]
    assert "ML" not in res["skills_list"]
    assert "QC" not in res["skills_list"]
    assert res["location"] == "Philippines"

    # Inline skills header without full resume headers
    res_inline = extract_content("Skills: ML, QC")
    assert "Machine Learning" in res_inline["skills_list"]
    assert "Quality Control" in res_inline["skills_list"]

    # QC in Quezon City address header must stay a location, not Quality Control skill
    addr_only = """
PEDRO SANTOS
pedro@gmail.com | 09191234567 | Diliman, QC

SKILLS
Python, FastAPI
"""
    res_addr = extract_content(addr_only)
    assert res_addr["location"] == "Quezon City, Metro Manila"
    assert "Quality Control" not in res_addr["skills_list"]

    # Milliliter units must not map to Machine Learning
    ml_unit = """
MARIA REYES
maria@gmail.com | 09191234567

SKILLS
Baking, 500 ml measuring
"""
    res_unit = extract_content(ml_unit)
    assert "Machine Learning" not in res_unit["skills_list"]


def test_two_column_mern_pdf_no_false_positive_or_garbled_skills():
    """
    Regression test for two-column resumes (sidebar EDUCATION + SKILLS alongside
    WORK PROJECTS with justified paragraphs, 'Bicol University', 'data integrity',
    '• Technologies: React JS', and 'Role: Full Stack Developer').
    Ensures clean skill analysis without geographic/homonym false positives,
    column interleaving, or split justified-text fragments.
    """
    import fitz
    from app.extractors.file.pdf_extractor import extract_text_from_pdf

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Top contact (left) + summary mentioning Bicol University (right)
    page.insert_text((30, 55), "JERICHO MARALIT", fontsize=16)
    page.insert_text((30, 78), "maralit25jericho@gmail.com", fontsize=9)
    page.insert_text((30, 95), "Mahaba , Ligao City ,Albay", fontsize=9)
    page.insert_textbox(
        fitz.Rect(210, 45, 565, 125),
        "Information Technology graduate from Bicol University Polangui with strong skills in "
        "web development using the MERN stack (MongoDB, Express.js, React, Node.js). Good at "
        "problem-solving, coding, and teamwork. Looking to use my technical skills to help a "
        "forward-thinking team create great web solutions.",
        fontsize=9,
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )

    # Left column: EDUCATION + SKILLS
    page.insert_text((30, 150), "EDUCATION", fontsize=10)
    page.insert_text(
        (30, 170),
        "Bicol University (BU)- Polangui Campus\nBS in Information Technology (IT)\n"
        "Graduated - Cum Laude\n2019 - 2024",
        fontsize=8.5,
    )
    page.insert_text((30, 232), "Ligao National High School\n2013 - 2019", fontsize=8.5)
    page.insert_text((30, 272), "St. Mary's Academy of Ligao\n2007 - 2013", fontsize=8.5)
    page.insert_text((30, 340), "SKILLS", fontsize=10)
    page.insert_text((30, 365), "- HTML & CSS", fontsize=9)
    page.insert_text((30, 390), "-React", fontsize=9)
    page.insert_text((30, 415), "-Node JS", fontsize=9)
    page.insert_text((30, 440), "-Express", fontsize=9)
    page.insert_text((30, 465), "-MONGO DB", fontsize=9)
    page.insert_text((30, 490), "-Tailwind CSS", fontsize=9)

    # Right column: WORK PROJECTS (letter-spaced header + justified paragraphs)
    page.insert_text((280, 150), "W O R K   P R O J E C T S", fontsize=10)
    page.insert_textbox(
        fitz.Rect(210, 165, 565, 255),
        "RETIRO PARES\nfocusing on creating a seamless and efficient user experience. "
        "Implemented receipt printing functionality directly from the web application, "
        "ensuring smooth transaction processing.\n"
        "• Role: Frontend\n• Technologies: React JS",
        fontsize=8.5,
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )
    page.insert_textbox(
        fitz.Rect(210, 265, 565, 365),
        "Sisco Thrift\nImplemented user authentication, product management, and shopping cart features. "
        "Designed a responsive and user-friendly interface to enhance customer experience. "
        "Managed database operations, ensuring data integrity and security.\n"
        "Role: Full Stack Developer\nTechnologies: MongoDB, Express.js, React.js, Node.js",
        fontsize=8.5,
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )
    page.insert_textbox(
        fitz.Rect(210, 375, 565, 495),
        "Barangay Mahaba Management System\nThe Barangay Management System is a MERN stack-based project "
        "designed to streamline barangay administration and official document issuance within the barangay.\n"
        "• Role: Full Stack Developer\n• Technologies: MongoDB, Express.js, React.js, Node.js",
        fontsize=8.5,
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )
    page.insert_textbox(
        fitz.Rect(210, 505, 565, 645),
        "iCrown Booking Dental System\nThe Dental Booking System is a MERN stack-based application "
        "designed to streamline appointment scheduling and management for dental clinics. "
        "This system allows patients to book, reschedule, and cancel appointments online, "
        "while providing clinic staff with tools to manage their schedules efficiently through a "
        "comprehensive dashboard.\n"
        "• Role: Full Stack Developer\n• Technologies: MongoDB, Express.js, React.js, Node.js",
        fontsize=8.5,
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )

    pdf_bytes = doc.tobytes()
    doc.close()

    extracted_txt = extract_text_from_pdf(pdf_bytes)
    res = extract_content(extracted_txt)
    skills = res["skills_list"]

    # Expected real skills from the resume
    for expected in [
        "HTML5 & CSS3",
        "React.js",
        "Node.js",
        "Express.js",
        "MongoDB",
        "Tailwind CSS",
        "Problem Solving",
        "Teamwork & Collaboration",
    ]:
        assert expected in skills, f"Expected '{expected}' in extracted skills: {skills}"

    # Must NOT include geographic/homonym false positives or non-skill prose/school/project entries
    for forbidden in [
        "Bicolano / Bikol",
        "Honesty & Integrity",
        "TypeScript",
        "St. Mary's Academy of Ligao",
        "Sisco Thrift",
        "Implemented user authentication",
        "Full Stack Developer",
        "Barangay Mahaba Management System",
        "MONGO DB within the barangay",
    ]:
        assert forbidden not in skills, f"Unexpected false positive '{forbidden}' in skills: {skills}"

    # Education should be properly parsed (not empty)
    assert "Information Technology" in res["degree"]
    assert "Bicol University" in res["college"]


def test_defense_in_depth_against_interleaved_and_broken_pdf_skills():
    """
    Even if a severely malformed PDF interleaves columns, injects '|'-split
    justified prose fragments, or breaks words like 'patien ts' / 'reschedul e',
    skills extraction must reject all noise and homonym false positives.
    """
    corrupted_text = """
JERICHO MARALIT
maralit25jericho@gmail.com | Mahaba, Ligao City, Albay
Information Technology graduate from Bicol University Polangui.

EDUCATION
Bicol University (BU)- Polangui Campus
BS in Information Technology (IT)
• Technologies: React JS
St. Mary's Academy of Ligao
2007 - 2013
Sisco Thrift
Implemented user authentication, product management, and shopping cart features.
Managed database operations, ensuring data integrity and security.
Role: Full Stack Developer

SKILLS
- HTML & CSS
-React
-Node JS
-Express
-MONGO DB
within the barangay.
-Tailwind CSS
Barangay Mahaba Management System
This system allows patien ts to book, reschedul e, and cancel appointmen ts online, while providing clinic staff with to | ols | to man | age th | eir schedu | les efficien | tly thro | ugh a comprehensive dashboard.
"""
    res = extract_content(corrupted_text)
    skills = res["skills_list"]

    for expected in ["HTML5 & CSS3", "React.js", "Node.js", "Express.js", "MongoDB", "Tailwind CSS"]:
        assert expected in skills, f"Expected '{expected}' in {skills}"

    for forbidden in [
        "Bicolano / Bikol",
        "Honesty & Integrity",
        "TypeScript",
        "St. Mary's Academy of Ligao",
        "Sisco Thrift",
        "Implemented user authentication",
        "Full Stack Developer",
        "Barangay Mahaba Management System",
        "MONGO DB within the barangay",
        "Reschedul E",
        "Ols",
        "To Man",
        "Age Th",
        "Eir Schedu",
        "Les Efficien",
        "Tly Thro",
        "Ugh A Comprehensive Dashboard",
    ]:
        assert forbidden not in skills, f"Garbage/false-positive '{forbidden}' leaked into skills: {skills}"


def test_contextual_homonym_guards_and_justified_row_merging():
    """
    Verifies contextual guards on ambiguous keywords (Express, Next, Spring, Integrity,
    Bicol, Filipino citizenship, Setter, TS) and verifies justified/kerning row merging
    in PDF extraction never splits words or injects pipes into prose.
    """
    from app.extractors.file.pdf_extractor import _extract_region_lines_paired

    # 1. Ambiguous homonyms outside tech/language contexts must NOT trigger false skills
    homonym_resume = """
JUAN SANTOS
juan@gmail.com | 09171234567
Citizenship: Filipino
Address: Legazpi City, Bicol Region

SUMMARY
Looking forward to the next step in my career. Built reliable systems and ensured data integrity.

WORK EXPERIENCE
Delivery Rider | LBC Express | Spring 2022 - Present
- Worked as a tile setter before joining courier delivery.
"""
    res = extract_content(homonym_resume)
    for fp in [
        "Honesty & Integrity",
        "Bicolano / Bikol",
        "Tagalog / Filipino",
        "Express.js",
        "Next.js",
        "Spring Boot",
        "Appointment Setting",
        "TypeScript",
    ]:
        assert fp not in res["skills_list"], f"False positive '{fp}' triggered on non-skill homonym: {res['skills_list']}"

    # 2. Genuine mentions in proper contexts MUST still be extracted
    genuine_resume = """
MARIA CRUZ
maria@gmail.com | 09181234567

SKILLS
TypeScript, JS/TS, Next.js, Express, Spring Boot, Honesty & Integrity, Fluent in Bicolano and Tagalog
"""
    res_gen = extract_content(genuine_resume)
    for expected in [
        "TypeScript",
        "JavaScript",
        "Next.js",
        "Express.js",
        "Spring Boot",
        "Honesty & Integrity",
        "Bicolano / Bikol",
        "Tagalog / Filipino",
    ]:
        assert expected in res_gen["skills_list"], f"Legitimate skill '{expected}' missed: {res_gen['skills_list']}"

    # 3. _extract_region_lines_paired: intra-word split merges without space, justified prose merges with spaces (no '|')
    dict_blocks = [
        {
            "type": 0,
            "lines": [
                {"bbox": [210.0, 500.0, 250.0, 510.0], "spans": [{"text": "reschedul"}]},
                {"bbox": [250.4, 500.0, 256.0, 510.0], "spans": [{"text": "e,"}]},
                {"bbox": [210.0, 520.0, 232.0, 530.0], "spans": [{"text": "tools"}]},
                {"bbox": [244.0, 520.0, 254.0, 530.0], "spans": [{"text": "to"}]},
                {"bbox": [266.0, 520.0, 298.0, 530.0], "spans": [{"text": "manage"}]},
                {"bbox": [310.0, 520.0, 330.0, 530.0], "spans": [{"text": "their"}]},
                {"bbox": [342.0, 520.0, 384.0, 530.0], "spans": [{"text": "schedules"}]},
                {"bbox": [396.0, 520.0, 440.0, 530.0], "spans": [{"text": "efficiently"}]},
            ],
        }
    ]
    blocks = [(210.0, 500.0, 440.0, 530.0, "reschedul e,\ntools to manage their schedules efficiently")]
    lines = _extract_region_lines_paired(blocks, dict_blocks)
    assert lines[0] == "reschedule,", f"Expected kerning-joined 'reschedule,', got: {lines[0]}"
    assert lines[1] == "tools to manage their schedules efficiently", f"Expected clean prose line without pipes, got: {lines[1]}"
    assert "|" not in lines[1]

