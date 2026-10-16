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
