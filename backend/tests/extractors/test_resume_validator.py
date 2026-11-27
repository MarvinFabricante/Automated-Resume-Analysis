"""
Comprehensive tests for strict Resume-Only Document Gatekeeper (`resume_validator.py`)
and enforcement across ALL upload / parsing endpoints:
  - POST /candidate/parse-resume
  - POST /matching/match-resume
  - POST /resumes/upload
  - POST /hr/physical-resumes/upload
"""

import io
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import docx
import fitz
import pytest

from app.extractors.resume_processor import process_resume
from app.extractors.resume_validator import validate_resume_document, validate_resume_file_bytes
from app.services.ats_template_service import build_ats_friendly_resume_docx


REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_pdf_bytes(text: str, pages: int = 1, encrypt: bool = False) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        if text:
            chunk = text if i == 0 else f"Page {i + 1}\n{text}"
            page.insert_text((50, 50), chunk)
    if encrypt:
        pdf_bytes = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="secret123",
            owner_pw="owner123",
        )
    else:
        pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_docx_bytes(lines: list[str], page_breaks: int = 0) -> bytes:
    d = docx.Document()
    for ln in lines:
        d.add_paragraph(ln)
    for i in range(page_breaks):
        d.add_page_break()
        d.add_paragraph(f"Continuation page {i + 2}")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ─── 1. Real Non-Resume PDFs Present in Workspace (User Manuals) ─────────────

@pytest.mark.parametrize(
    "pdf_name",
    [
        "user manual.pdf",
        "Automated_Resume_Analysis_Short_User_Manual.pdf",
        "Automated_Resume_Analysis_User_Manual.pdf",
        "Mariwasa_AI_Screening_and_Job_Matching_User_Manual.pdf",
    ],
)
def test_workspace_user_manual_pdfs_are_rejected(pdf_name):
    pdf_path = REPO_ROOT / pdf_name
    if not pdf_path.is_file():
        pytest.skip(f"{pdf_name} not found in workspace root")
    parsed = process_resume(str(pdf_path), "pdf")
    assert parsed.get("is_valid_resume") is False, f"{pdf_name} must be rejected as non-resume: {parsed.get('resume_validation')}"
    val = parsed["resume_validation"]
    assert val["detected_document_type"] == "manual_or_guide"
    assert "resume" in val["message"].lower()


# ─── 2. Diverse Synthetic Non-Resume Documents MUST Be Rejected ──────────────

NON_RESUME_SAMPLES = [
    (
        "sales_invoice.pdf",
        """
        MARIWASA HARDWARE TRADING CORP.
        SALES INVOICE
        Invoice No.: INV-2026-00481
        VAT Reg. TIN: 001-234-567-000
        Bill To: ABC Construction Supply
        Date: November 12, 2026 | Payment Terms: Net 30 | Due Date: December 12, 2026
        Item Description | Qty | Unit Price | Amount
        Ceramic Floor Tiles 60x60cm | 100 | 450.00 | 45,000.00
        Tile Adhesive 25kg | 50 | 320.00 | 16,000.00
        Subtotal: 61,000.00
        VAT Amount (12%): 7,320.00
        Grand Total / Amount Due: PHP 68,320.00
        Cashier: Maria Reyes
        """,
        "financial_document",
    ),
    (
        "official_receipt.pdf",
        """
        OFFICIAL RECEIPT
        O.R. No. 987654
        Received from Juan Dela Cruz the sum of Five Thousand Pesos (PHP 5,000.00)
        as partial payment for tuition and miscellaneous fees.
        Vatable Sales: 4,464.29
        VAT Amount: 535.71
        Total Amount Due: 5,000.00
        Change Due: 0.00
        """,
        "financial_document",
    ),
    (
        "capstone_thesis.pdf",
        """
        AUTOMATED RESUME SCREENING AND JOB MATCHING PLATFORM
        A Capstone Project Documentation
        Submitted in Partial Fulfillment of the Requirements for the Degree
        Bachelor of Science in Information Technology

        ABSTRACT
        This study investigates natural language processing approaches for recruitment screening.

        CHAPTER 1
        INTRODUCTION
        Statement of the Problem
        Review of Related Literature
        Conceptual Framework
        Scope and Delimitation
        Significance of the Study

        Methodology
        Figure 1. System Architecture Diagram
        Table 1. Evaluation Metrics (Smith et al., 2024).

        References
        [1] Smith, J. et al. (2024). Journal of Applied Computing, vol. 12, pp. 44-59. doi: 10.1000/xyz
        """,
        "academic_paper",
    ),
    (
        "certificate_of_completion.pdf",
        """
        CERTIFICATE OF COMPLETION
        This is to certify that
        JUAN DELA CRUZ
        has successfully completed the 40-Hour Basic Occupational Safety and Health Seminar
        held on October 15-19, 2026 in Sto. Tomas, Batangas.
        Given this 19th day of October 2026.
        Signed: Training Director
        """,
        "certificate_or_official_record",
    ),
    (
        "barangay_clearance.pdf",
        """
        REPUBLIC OF THE PHILIPPINES
        Province of Batangas
        Municipality of Sto. Tomas
        BARANGAY CLEARANCE
        TO WHOM IT MAY CONCERN:
        This is to certify that JUAN DELA CRUZ, of legal age, Filipino, is a bonafide resident
        of Barangay San Antonio, Sto. Tomas, Batangas and has no derogatory record on file.
        Given this 20th day of November 2026 for employment purposes.
        Punong Barangay
        """,
        "certificate_or_official_record",
    ),
    (
        "transcript_of_records.pdf",
        """
        OFFICE OF THE REGISTRAR
        OFFICIAL TRANSCRIPT OF RECORDS
        Student Name: Maria Clara Santos | Program: BS Information Technology
        Course Code | Subject Description | Units Earned | Grade | Remarks
        IT101 | Introduction to Computing | 3 | 1.25 | Remarks: Passed
        IT102 | Computer Programming | 3 | 1.50 | Remarks: Passed
        General Weighted Average: 1.42
        Grading System: 1.00 Excellent, 3.00 Passing
        University Registrar
        """,
        "certificate_or_official_record",
    ),
    (
        "employment_contract.pdf",
        """
        MEMORANDUM OF AGREEMENT
        KNOW ALL MEN BY THESE PRESENTS:
        This Employment Contract and Non-Disclosure Agreement is entered into by and between
        Party of the First Part and Party of the Second Part.
        WITNESSETH:
        WHEREAS, the Company desires to engage the services of the Employee under the following
        Terms and Conditions. The parties hereby agree as follows:
        Section 1. Confidentiality and Indemnify and Hold Harmless.
        Section 2. Force Majeure.
        IN WITNESS WHEREOF, the parties have signed this agreement before a Notary Public.
        Doc. No. 14; Page No. 3; Book No. II; Series of 2026.
        """,
        "legal_or_correspondence",
    ),
    (
        "job_posting.pdf",
        """
        JOB DESCRIPTION
        We are hiring: Production Supervisor (Full-Time)
        About the Role
        We are looking for a detail-oriented Production Supervisor to join our team at our Sto. Tomas plant.
        You will be responsible for overseeing tile manufacturing lines and safety inspections.
        Reports to: Plant Operations Manager
        Minimum Qualifications
        - Bachelor's degree in Industrial or Mechanical Engineering
        - At least 3 years of experience in manufacturing and ISO 9001 quality control
        What We Offer
        - Competitive Salary Range and benefits and perks
        How to Apply: Send your resume to careers@company.com or Apply Now!
        Equal Opportunity Employer.
        """,
        "job_posting",
    ),
    (
        "standalone_cover_letter.pdf",
        """
        November 25, 2026

        Dear Hiring Manager,

        I am writing to express my strong interest in the Production Supervisor opening at your company.
        I have followed your organization's leadership in ceramic manufacturing and would be honored
        to contribute my dedication, reliability, and teamwork to your operations.
        Thank you very much for your time and consideration. I look forward to hearing from you soon.

        Sincerely yours,
        Juan Dela Cruz
        """,
        "legal_or_correspondence",
    ),
    (
        "course_syllabus.pdf",
        """
        COURSE SYLLABUS
        Course Title: Data Structures and Algorithms
        Credit Units: 3.0 | Pre-requisite: Computer Programming 2
        Course Description: This course introduces fundamental data structures.
        Learning Outcomes: Students will analyze algorithm complexity.
        Grading Criteria: Midterm Exam 30%, Final Exam 40%, Quizzes 30%.
        Class Schedule: Mon/Wed 9:00 AM - 10:30 AM.
        """,
        "misc_non_resume",
    ),
    (
        "recipe_and_story.pdf",
        """
        CLASSIC CHICKEN ADOBO RECIPE
        Ingredients:
        1 kg chicken thighs
        4 tablespoons soy sauce
        3 tablespoons vinegar
        1 teaspoon black peppercorn
        Preheat oven or simmer in a heavy pot for 35 minutes until tender.
        Nutrition Facts: 4 servings, 320 calories per serving.
        """,
        "misc_non_resume",
    ),
    (
        "business_card_only.pdf",
        """
        Juan Carlos Reyes
        juan.reyes@gmail.com
        +63 917 555 0199
        Makati City, Metro Manila, Philippines
        Call anytime for inquiries regarding our wholesale ceramic distribution catalog.
        """,
        "non_resume_document",
    ),
    (
        "random_essay.pdf",
        """
        The Importance of Renewable Energy in Modern Cities
        Urban centers around the world are transitioning toward solar and wind power to combat rising temperatures.
        Over the past decade, battery storage prices have fallen dramatically while grid efficiency has improved.
        Municipal governments are investing heavily in public transit electrification and green building codes.
        Researchers expect clean energy adoption to accelerate across Southeast Asia over the next twenty years.
        Citizens benefit from cleaner air, lower electricity costs, and stronger long-term climate resilience.
        """,
        "non_resume_document",
    ),
    (
        "blank_biodata_template.pdf",
        """
        PERSONAL DATA FORM
        Full Name: ___________________________
        Address: _____________________________
        Date of Birth: ________________________
        Civil Status: _________________________
        Telephone: ___________________________
        Education: ___________________________
        Signature Over Printed Name: __________
        For Office Use Only
        """,
        "misc_non_resume",
    ),
    (
        "wikipedia_biography.pdf",
        """
        From Wikipedia, the free encyclopedia
        Jose Protasio Rizal Mercado y Alonso Realonda was a Filipino nationalist, writer and polymath.
        Early life
        He studied at Ateneo Municipal de Manila and University of Santo Tomas before traveling to Europe.
        He completed his medical degree in Madrid and authored Noli Me Tangere and El Filibusterismo [citation needed].
        This page was last edited on 10 November 2026.
        """,
        "misc_non_resume",
    ),
]


@pytest.mark.parametrize("filename,content,expected_cat", NON_RESUME_SAMPLES)
def test_non_resume_documents_are_rejected(filename, content, expected_cat):
    pdf_bytes = _make_pdf_bytes(content)
    is_resume, result = validate_resume_file_bytes(pdf_bytes, filename)
    assert is_resume is False, f"Expected '{filename}' to be REJECTED, got: {result}"
    assert result["message"]


def test_blank_and_password_protected_pdfs_rejected():
    blank_pdf = _make_pdf_bytes("")
    is_resume_blank, res_blank = validate_resume_file_bytes(blank_pdf, "blank.pdf")
    assert is_resume_blank is False
    assert res_blank["reason_code"] == "unreadable_or_empty"

    short_pdf = _make_pdf_bytes("Hello world random test file")
    is_resume_short, res_short = validate_resume_file_bytes(short_pdf, "random.pdf")
    assert is_resume_short is False
    assert res_short["reason_code"] == "unreadable_or_empty"

    locked_pdf = _make_pdf_bytes("Juan Dela Cruz\nWORK EXPERIENCE\nEDUCATION\nSKILLS", encrypt=True)
    is_resume_locked, res_locked = validate_resume_file_bytes(locked_pdf, "locked.pdf")
    assert is_resume_locked is False
    assert res_locked["reason_code"] == "password_protected"


# ─── 3. Diverse Legitimate Resumes MUST All Be Accepted ──────────────────────

VALID_RESUME_SAMPLES = [
    (
        "engineering_resume.pdf",
        """
        Engr. Juanito Dela Cruz, RCE
        Makati City, Metro Manila | 09171234567 | jdelacruz.ce@gmail.com

        PROFESSIONAL EXPERIENCE
        Project Civil Engineer
        Megawide Construction Corp. - Makati City
        March 2021 - Present
        - Supervised reinforced concrete foundation works and structural compliance
        - Reviewed structural drawings using AutoCAD and Revit

        EDUCATION
        Bachelor of Science in Civil Engineering
        University of the Philippines Diliman
        2015 - 2019 | Cum Laude

        LICENSES AND ELIGIBILITY
        - PRC Registered Civil Engineer (License No. 0154321)
        - BOSH SO2 - DOLE-BWC Accredited

        TECHNICAL SKILLS
        AutoCAD, Revit, STAAD.Pro, Structural Analysis, Project Management
        """,
    ),
    (
        "blue_collar_worker.pdf",
        """
        ALEXANDER BAUTISTA
        Calamba City, Laguna | 09171234567 | alex.bautista@gmail.com

        WORK EXPERIENCE
        Service Crew / Kitchen Staff
        Jollibee Foods Corporation - Calamba Branch
        January 2022 - Present
        - Performed food preparation, counter service, and inventory stocking

        EDUCATION
        Vocational Course in Hospitality Services
        TESDA Calamba Training Center, 2020
        High School Graduate - Calamba National High School, 2019

        CERTIFICATIONS & LICENSES
        - TESDA Food and Beverage Services NC II
        - LTO Professional Driver's License

        SKILLS
        Customer Service, Food Preparation, Sanitation, Safe Driving
        """,
    ),
    (
        "fresh_grad_no_experience.pdf",
        """
        CARMINA FLORES SANTOS
        carmina.santos@gmail.com | +63 917 888 9999 | Makati City, Metro Manila

        OBJECTIVE
        Dedicated recent Accountancy graduate aiming to leverage analytical and financial skills.

        EDUCATION
        Bachelor of Science in Accountancy
        University of Santo Tomas, Manila
        2019 - 2023 | Magna Cum Laude

        SKILLS & COMPETENCIES
        Financial Accounting, QuickBooks, SAP Financial Accounting, Microsoft Excel

        CERTIFICATIONS & LICENSES
        Certified Public Accountant (CPA) - PRC Board Passer
        """,
    ),
    (
        "incomplete_no_education.pdf",
        """
        MARKO RODRIGUEZ
        marko.rodriguez@gmail.com | 0918-111-2222 | Pasig City

        WORK EXPERIENCE
        Senior Graphic Designer
        Creative Studio Inc., Pasig City
        March 2020 - Present
        - Created brand identity assets and UI graphics.

        SKILLS
        Adobe Photoshop, Illustrator, Figma, Typography
        """,
    ),
    (
        "incomplete_no_skills_section.pdf",
        """
        DIANA REYES
        diana.reyes@gmail.com | 0919-333-4444 | Quezon City

        EDUCATION
        BS Civil Engineering
        Polytechnic University of the Philippines
        2018 - 2022

        WORK EXPERIENCE
        Site Engineer
        Megawide Construction Corp.
        June 2022 - Present
        - Supervised rebar placement and concrete pouring.
        """,
    ),
    (
        "philippine_biodata.pdf",
        """
        BIO-DATA

        PERSONAL INFORMATION
        Full Name: Roberto M. Castillo
        Present Address: Brgy. San Rafael, Sto. Tomas, Batangas
        Date of Birth: May 14, 1998
        Place of Birth: Lipa City, Batangas
        Civil Status: Single
        Nationality: Filipino
        Religion: Roman Catholic
        Contact Number: 0927-444-8899

        EDUCATIONAL BACKGROUND
        Secondary: Sto. Tomas National High School (2011 - 2015)
        Vocational: TESDA Shielded Metal Arc Welding (SMAW) NC II (2016)

        EMPLOYMENT RECORD
        Production Helper - Batangas Packaging Corp. (2018 - 2023)
        - Assisted in machine loading, packing, and warehouse inventory checks.

        CHARACTER REFERENCES
        Engr. Pedro Santos - Plant Supervisor - 0917-222-3344
        """,
    ),
    (
        "filipino_tagalog_resume.pdf",
        """
        MARIA THERESA MENDOZA
        Calamba, Laguna | 0918-555-7788 | mtheresa.mendoza@gmail.com

        LAYUNIN SA TRABAHO
        Nais kong gamitin ang aking karanasan sa produksyon at quality control.

        KARANASAN SA TRABAHO
        Quality Control Inspector | Laguna Ceramics Inc. | 2021 - Present
        - Nag-inspeksyon ng mga produkto araw-araw at nagtala ng ulat ng kalidad.

        EDUKASYON
        Bachelor of Science in Industrial Technology
        Laguna State Polytechnic University | 2017 - 2021

        MGA KASANAYAN
        Quality Control, Machine Operation, Microsoft Excel, Safety Protocols
        """,
    ),
    (
        "headerless_minimal_resume.pdf",
        """
        Maria Elena Santos
        maria.santos@gmail.com | 0917-555-1234 | Calamba, Laguna
        Production Operator at Mariwasa Siam Ceramics (Jan 2021 - Present)
        - Operated ceramic press machines and conducted quality inspections.
        - Maintained production logs and ensured ISO 9001 safety compliance.
        BS Industrial Technology, Laguna State Polytechnic University, 2016 - 2020
        Proficient in Machine Operation, Quality Control, Preventive Maintenance, Microsoft Excel
        """,
    ),
    (
        "cover_letter_plus_resume_packet.pdf",
        """
        Dear Hiring Manager,
        I am excited to apply for the Maintenance Engineer position at Mariwasa Siam Ceramics.
        Sincerely yours,
        Carlo Mendoza

        CARLO MENDOZA
        carlo.mendoza@gmail.com | +63 917 222 1100 | Lipa City, Batangas

        WORK EXPERIENCE
        Maintenance Technician | Southern Luzon Plant Corp. | 2020 - Present
        - Performed preventive maintenance on hydraulic presses and PLC panels.

        EDUCATION
        BS Mechanical Engineering | Batangas State University | 2015 - 2019

        SKILLS
        Preventive Maintenance, PLC Troubleshooting, AutoCAD, Welding, Safety Compliance
        """,
    ),
]


@pytest.mark.parametrize("filename,content", VALID_RESUME_SAMPLES)
def test_valid_resumes_are_accepted(filename, content):
    pdf_bytes = _make_pdf_bytes(content)
    is_resume, result = validate_resume_file_bytes(pdf_bytes, filename)
    assert is_resume is True, f"Valid resume '{filename}' was wrongly rejected: {result}"
    assert result["detected_document_type"] == "resume"


def test_official_ats_docx_template_is_accepted():
    tpl_bytes = build_ats_friendly_resume_docx()
    is_resume, result = validate_resume_file_bytes(tpl_bytes, "ATS_Friendly_Resume_Guide_Template.docx")
    assert is_resume is True, f"Official ATS template should be accepted: {result}"


# ─── 4. End-to-End Enforcement Across All Upload HTTP Endpoints ──────────────

@pytest.mark.asyncio
async def test_all_resume_upload_endpoints_reject_random_pdf_and_accept_resume(client, db_session):
    random_pdf = _make_pdf_bytes(
        "MARIWASA ENTERPRISE USER MANUAL\n"
        "Quick Start Reference Guide & System Operations Manual\n"
        "Table of Contents\n"
        "Chapter 1: How to Log In and Navigate the System\n"
        "Click the Login button and enter your credentials.\n"
        "All rights reserved © 2026.\n"
    )
    valid_resume_pdf = _make_pdf_bytes(
        "ANA MARIE REYES\n"
        "ana.reyes@gmail.com | 0917-333-4455 | Santa Rosa, Laguna\n\n"
        "WORK EXPERIENCE\n"
        "Quality Assurance Analyst | Laguna Manufacturing Corp. | 2021 - Present\n"
        "- Inspected finished ceramic tiles for compliance with ISO 9001 standards.\n\n"
        "EDUCATION\n"
        "Bachelor of Science in Chemical Engineering\n"
        "University of the Philippines Los Banos | 2017 - 2021\n\n"
        "SKILLS\n"
        "Quality Control, ISO 9001, Root Cause Analysis, Microsoft Excel, Lab Testing\n"
    )

    fake_sb = AsyncMock(
        return_value={
            "public_url": "https://example.supabase.co/storage/v1/object/public/resume%20storage/resumes/mock.pdf",
            "storage_path": "resumes/mock.pdf",
            "filename": "mock.pdf",
        }
    )

    with patch("app.utils.supabase_storage.upload_resume", fake_sb):
        # 1. POST /candidate/parse-resume -> rejects random PDF without uploading to storage
        r_bad_parse = await client.post(
            "/candidate/parse-resume",
            files={"file": ("random_manual.pdf", random_pdf, "application/pdf")},
        )
        assert r_bad_parse.status_code == 400
        assert "resume" in r_bad_parse.json()["detail"].lower()
        assert fake_sb.await_count == 0, "Rejected non-resume must NOT be uploaded to Supabase"

        # 2. POST /matching/match-resume -> rejects random PDF
        r_bad_match = await client.post(
            "/matching/match-resume",
            files={"file": ("random_manual.pdf", random_pdf, "application/pdf")},
        )
        assert r_bad_match.status_code == 400
        assert "resume" in r_bad_match.json()["detail"].lower()
        assert fake_sb.await_count == 0

        # 3. POST /resumes/upload -> rejects random PDF
        r_bad_upload = await client.post(
            "/resumes/upload",
            files={"file": ("random_manual.pdf", random_pdf, "application/pdf")},
        )
        assert r_bad_upload.status_code == 400
        assert "resume" in r_bad_upload.json()["detail"].lower()
        assert fake_sb.await_count == 0

        # 4. POST /hr/physical-resumes/upload -> rejects random PDF
        r_bad_phys = await client.post(
            "/hr/physical-resumes/upload",
            data={"candidate_name": "Random Tester"},
            files={"file": ("random_manual.pdf", random_pdf, "application/pdf")},
        )
        assert r_bad_phys.status_code == 400
        assert "resume" in r_bad_phys.json()["detail"].lower()
        assert fake_sb.await_count == 0

        # 5. Thesis Manuscript (with CV Appendix, even renamed to resume.docx) rejected across ALL endpoints
        thesis_manuscript_docx = _make_docx_bytes([
            "REPUBLIC OF THE PHILIPPINES",
            "COMMISSION ON HIGHER EDUCATION",
            "BATANGAS STATE UNIVERSITY",
            "COLLEGE OF INFORMATICS AND COMPUTING SCIENCES",
            "DEPARTMENT OF INFORMATION TECHNOLOGY",
            "S.Y. 2025 - 2026",
            "SMART INVENTORY AND SALES FORECASTING PLATFORM FOR LOCAL RETAIL ENTERPRISES",
            "A Thesis Manuscript",
            "Presented to the Faculty of the College of Informatics and Computing Sciences",
            "In Partial Fulfillment of the Requirements for the Degree",
            "Bachelor of Science in Information Technology",
            "By: Mark Anthony Villanueva, Angela Mae Mendoza",
            "Adviser: Engr. Roberto D. Castillo, MIT",
            "CHAPTER 1: THE PROBLEM AND ITS BACKGROUND",
            "Background of the Study: Local retail stores struggle with inventory tracking.",
            "Objectives of the Study: To automate stock monitoring and demand forecasting.",
            "Scope and Limitations: Covers retail stores in Batangas.",
            "CHAPTER 2: REVIEW OF RELATED LITERATURE",
            "According to Santos (2023), computerized systems reduce shrinkage by 35%.",
            "CHAPTER 3: METHODOLOGY",
            "Research Design: Developmental research design with 45 respondents.",
            "CHAPTER 4: RESULTS AND DISCUSSION",
            "Table 1. Weighted Mean of System Acceptability",
            "APPENDIX A: CURRICULUM VITAE OF THE RESEARCHERS",
            "CURRICULUM VITAE",
            "MARK ANTHONY VILLANUEVA",
            "mark.villanueva@gmail.com | 0917-888-1122 | Batangas City",
            "EDUCATION",
            "Bachelor of Science in Information Technology, Batangas State University (2022 - 2026)",
            "WORK EXPERIENCE",
            "IT Intern | ABC Retail Corp. | June 2025 - August 2025",
            "- Assisted with database maintenance and POS troubleshooting.",
            "SKILLS",
            "Python, FastAPI, React, PostgreSQL, Git",
        ])
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        for ep, extra_data in [
            ("/candidate/parse-resume", None),
            ("/matching/match-resume", None),
            ("/resumes/upload", None),
            ("/hr/physical-resumes/upload", {"candidate_name": "Panelist Upload"}),
        ]:
            kwargs = {"files": {"file": ("Juan_Dela_Cruz_Resume.docx", thesis_manuscript_docx, docx_mime)}}
            if extra_data:
                kwargs["data"] = extra_data
            r_thesis = await client.post(ep, **kwargs)
            assert r_thesis.status_code == 400, f"Endpoint {ep} must reject Thesis Manuscript DOCX, got {r_thesis.status_code}"
            detail_low = r_thesis.json()["detail"].lower()
            assert "resume" in detail_low and ("thesis" in detail_low or "manuscript" in detail_low or "academic" in detail_low)
            assert fake_sb.await_count == 0, f"Rejected thesis manuscript on {ep} must NOT be uploaded to Supabase"

        # 6. Valid resume succeeds on /candidate/parse-resume and /resumes/upload
        r_ok_parse = await client.post(
            "/candidate/parse-resume",
            files={"file": ("ana_reyes_resume.pdf", valid_resume_pdf, "application/pdf")},
        )
        assert r_ok_parse.status_code == 200
        assert r_ok_parse.json()["is_valid_resume"] is True
        assert "Ana Marie Reyes" in r_ok_parse.json()["fullname"]

        r_ok_upload = await client.post(
            "/resumes/upload",
            files={"file": ("ana_reyes_resume.pdf", valid_resume_pdf, "application/pdf")},
        )
        assert r_ok_upload.status_code == 200
        assert "public_url" in r_ok_upload.json()


# ─── 5. Hardened Thesis Manuscript Variants & Tricky Legitimate Resumes ──────

THESIS_AND_EXTRA_NON_RESUME_SAMPLES = [
    (
        "Juan_Dela_Cruz_Resume.pdf",  # Disguised filename: Thesis Manuscript with CV Appendix
        """
        REPUBLIC OF THE PHILIPPINES
        COMMISSION ON HIGHER EDUCATION
        REGION IV-A CALABARZON
        BATANGAS STATE UNIVERSITY
        THE NATIONAL ENGINEERING UNIVERSITY
        ARASOF-NASUGBU CAMPUS
        COLLEGE OF INFORMATICS AND COMPUTING SCIENCES
        DEPARTMENT OF INFORMATION TECHNOLOGY
        S.Y. 2025 - 2026

        SMART INVENTORY AND SALES FORECASTING PLATFORM
        FOR LOCAL RETAIL ENTERPRISES

        A Thesis Manuscript
        Presented to the Faculty of the
        College of Informatics and Computing Sciences
        Batangas State University

        In Partial Fulfillment of the Requirements for the Degree
        Bachelor of Science in Information Technology

        By:
        Mark Anthony Villanueva
        Angela Mae Mendoza
        Carlo Joseph Bautista

        Adviser: Engr. Roberto D. Castillo, MIT

        CHAPTER 1: THE PROBLEM AND ITS BACKGROUND
        Background of the Study
        Small retail businesses in Batangas struggle with manual stock tracking.
        Objectives of the Study
        - Developed a centralized inventory database using PostgreSQL and FastAPI.
        - Implemented demand forecasting algorithms using Python and Scikit-learn.
        Scope and Limitations
        This study covers point-of-sale and inventory modules for retail stores in Batangas.

        CHAPTER 2: REVIEW OF RELATED LITERATURE
        According to Santos (2023), computerized inventory systems reduce shrinkage by 35%.

        CHAPTER 3: METHODOLOGY
        Research Design: The researchers used developmental research design and Agile Scrum methodology.
        Respondents of the Study: 45 store managers and staff participated in the evaluation survey.

        CHAPTER 4: RESULTS AND DISCUSSION
        Table 1. Weighted Mean of System Acceptability
        Figure 2. Forecasting Accuracy Comparison

        CHAPTER 5: SUMMARY, CONCLUSION AND RECOMMENDATIONS
        Based on the findings, the system is highly acceptable.

        APPENDIX A: CURRICULUM VITAE OF THE RESEARCHERS
        CURRICULUM VITAE
        MARK ANTHONY VILLANUEVA
        mark.villanueva@gmail.com | 0917-888-1122 | Batangas City
        PERSONAL INFORMATION
        Date of Birth: March 10, 2003
        Place of Birth: Batangas City
        Civil Status: Single
        Nationality: Filipino
        EDUCATION
        Bachelor of Science in Information Technology
        Batangas State University (2022 - 2026)
        WORK EXPERIENCE
        IT Intern | ABC Retail Corp. | June 2025 - August 2025
        - Assisted in database maintenance and POS troubleshooting.
        SKILLS
        Python, FastAPI, React, PostgreSQL, Git, Microsoft Excel
        """,
    ),
    (
        "candidate_cv.pdf",  # Disguised filename: Thesis Proposal Chapters I-III (no CV appendix)
        """
        BATANGAS STATE UNIVERSITY
        College of Computer Studies

        THESIS MANUSCRIPT
        WEB-BASED CLINIC APPOINTMENT AND PATIENT RECORDS MANAGEMENT SYSTEM

        Submitted by:
        Kevin Paul Reyes (kevin.reyes@gmail.com, 0918-444-5566)
        Sarah Jane Lim

        CHAPTER I: INTRODUCTION
        Background of the Study
        Medical clinics rely heavily on paper logbooks for scheduling and storing patient charts.
        Objectives of the Study
        1. To design an online booking portal for patients and clinic staff.
        2. To implement automated SMS reminders for scheduled visits.
        3. To evaluate the system based on ISO 25010 software quality characteristics.

        CHAPTER II: REVIEW OF RELATED STUDIES
        Prior studies by Dela Cruz (2022) and Reyes (2023) demonstrate that digital health records cut waiting time by half.

        CHAPTER III: RESEARCH METHODOLOGY
        Software Development Life Cycle (SDLC)
        The team followed the Iterative Waterfall model from August 2025 - February 2026.
        - Designed entity-relationship diagrams and system wireframes using Figma.
        - Developed backend REST APIs in Python, Django, and MySQL.
        - Conducted Alpha and Beta testing with clinic nurses and administrative staff at St. Luke Medical Clinic Inc.
        """,
    ),
    (
        "resume.pdf",  # Disguised filename: IMRaD Thesis Manuscript
        """
        DESIGN AND DEVELOPMENT OF AN IOT-BASED GREENHOUSE MONITORING SYSTEM
        Juan Dela Cruz, Maria Clara Santos, Pedro Reyes
        College of Engineering and Architecture, Batangas State University
        juan.delacruz@g.batstate-u.edu.ph | 0917-555-1234

        Abstract
        This study presents the design and implementation of an IoT-based greenhouse monitoring system for smallholder farmers in Batangas.
        Keywords: Internet of Things, Greenhouse, Agriculture, Sensor Network, Python

        1. Introduction
        Agriculture remains a vital pillar of the Philippine economy. Farmers face unpredictable weather conditions.

        2. Methodology
        The researchers utilized agile software development and hardware prototyping from January 2025 - November 2025.
        - Developed sensor nodes using ESP32 and DHT22 modules.
        - Built a web dashboard using React, FastAPI, and PostgreSQL.

        3. Results and Discussion
        Table 1. Usability and Functionality Evaluation Summary
        Figure 1. System Architecture of the Greenhouse Monitoring Platform

        4. Conclusion and Recommendations
        The IoT-based system effectively automates greenhouse monitoring.

        References
        [1] Garcia, M., & Cruz, L. (2024). Smart Agriculture Systems. Journal of Engineering, vol. 8, pp. 12-20.
        """,
    ),
    (
        "ieee_paper.pdf",
        """
        Deep Learning Approaches for Ceramic Tile Surface Defect Detection
        Miguel Angelo Torres, Patricia Ann Cruz
        Department of Computer Engineering, Mapua University, Manila, Philippines
        matorres@mapua.edu.ph

        Abstract—Automated visual inspection is critical in ceramic tile manufacturing. We propose a convolutional neural network trained on 12,000 labeled tile images achieving 98.4% accuracy.
        Index Terms—Computer Vision, Ceramic Tiles, Deep Learning, Defect Detection, PyTorch.

        I. INTRODUCTION
        Manual quality inspection in ceramic factories suffers from human fatigue and inconsistent defect classification.

        II. RELATED WORK
        Previous approaches used hand-crafted texture features (Lee et al., 2021) and support vector machines.

        III. PROPOSED METHODOLOGY
        We trained ResNet-50 and YOLOv8 models using Python, PyTorch, OpenCV, and Docker on an NVIDIA GPU cluster.

        IV. EXPERIMENTAL RESULTS
        Table I shows precision and recall metrics across five defect classes. Fig. 1 illustrates the confusion matrix.

        V. CONCLUSION
        Our automated defect inspection model significantly outperforms manual screening in speed and consistency.

        REFERENCES
        [1] K. Lee et al., "Tile defect detection," IEEE Trans. Ind. Electron., vol. 68, pp. 102-110, 2021.
        """,
    ),
    (
        "tagalog_thesis.pdf",
        """
        KABANATA 1: ANG SULIRANIN AT KALIGIRAN NITO
        Kaligiran ng Pag-aaral
        Ang pananaliksik na ito ay naglalayong suriin ang epekto ng makabagong teknolohiya sa mga mag-aaral.
        Paglalahad ng Suliranin
        1. Ano ang antas ng kahusayan ng mga mag-aaral sa paggamit ng digital learning tools?
        Saklaw at Limitasyon
        Ang pag-aaral na ito ay nakatuon sa mga mag-aaral sa kolehiyo sa Batangas.
        Kahalagahan ng Pag-aaral
        Makakatulong ito sa mga guro at tagapamahala ng paaralan.

        KABANATA 2: MGA KAUGNAY NA LITERATURA AT PAG-AARAL
        Ayon kay Cruz (2023), malaki ang naitutulong ng teknolohiya sa edukasyon.

        KABANATA 3: DISENYO NG PANANALIKSIK
        Ginamit ng mga mananaliksik ang deskriptibong disenyo ng pananaliksik.
        Buod, Konklusyon at Rekomendasyon
        """,
    ),
    (
        "chapter_2_rrl_only.pdf",
        """
        CHAPTER 2: REVIEW OF RELATED LITERATURE AND STUDIES
        This chapter presents the conceptual framework, theoretical framework, and related literature and studies
        that guided the researchers in designing the system architecture.
        According to Reyes et al. (2023), automated document classification improves precision by 31%.
        Figure 2.1: Conceptual Framework (Input-Process-Output Model)
        Table 2.1: Summary of Related Studies Reviewed
        """,
    ),
    (
        "ojt_narrative_report.pdf",
        """
        OJT NARRATIVE REPORT
        Submitted by: Paolo Santos (paolo.santos@gmail.com, 0917-222-3333)
        Bachelor of Science in Information Technology
        Batangas State University

        CHAPTER 1: COMPANY PROFILE
        Mariwasa Siam Ceramics Inc. is a leading ceramic tile manufacturer in the Philippines.
        CHAPTER 2: WEEKLY ACCOMPLISHMENT REPORT
        Week 1: Assisted IT department with network cable crimping and inventory.
        CHAPTER 3: CONCLUSION AND RECOMMENDATIONS
        Based on the findings, the internship provided valuable industry exposure.
        """,
    ),
    (
        "srs_specification.pdf",
        """
        SOFTWARE REQUIREMENTS SPECIFICATION
        Automated Recruitment Tracking System v2.0
        Prepared by: Engineering Team (eng.lead@gmail.com, 0917-111-2222)
        Table of Contents
        1. Introduction
        2. Overall Description
        3. System Features and Functional Requirements
        4. Non-Functional Requirements
        Figure 1. Context Diagram
        """,
    ),
    (
        "midterm_exam.pdf",
        """
        MIDTERM EXAMINATION PAPER
        Name: _____________________ Score: _______
        Directions: Choose the letter of the best answer. Multiple Choice.
        1. Which protocol operates at the transport layer?
           a) HTTP  b) TCP  c) DNS  d) ARP
        2. What does SQL stand for?
           a) Structured Query Language  b) Simple Query Language
        """,
    ),
]


@pytest.mark.parametrize("filename,content", THESIS_AND_EXTRA_NON_RESUME_SAMPLES)
def test_thesis_manuscripts_and_extra_non_resumes_rejected(filename, content):
    pdf_bytes = _make_pdf_bytes(content)
    is_resume, result = validate_resume_file_bytes(pdf_bytes, filename)
    assert is_resume is False, f"Expected non-resume '{filename}' to be REJECTED, got: {result}"
    assert result["message"]


def test_oversized_pdf_and_docx_manuscripts_rejected_fast():
    # 20-page image/empty-text PDF (e.g. scanned thesis manuscript) rejected immediately without OCR hang
    scanned_20p = _make_pdf_bytes("", pages=20)
    ok_scan, res_scan = validate_resume_file_bytes(scanned_20p, "scanned_manuscript.pdf")
    assert ok_scan is False
    assert res_scan["reason_code"] == "document_too_long"

    # 16-page DOCX with explicit page breaks rejected as document_too_long
    long_docx = _make_docx_bytes(
        ["Generic industrial report discussing tile manufacturing operations across facilities."] * 25,
        page_breaks=15,
    )
    ok_docx, res_docx = validate_resume_file_bytes(long_docx, "long_report.docx")
    assert ok_docx is False
    assert res_docx["reason_code"] in ("document_too_long", "insufficient_resume_evidence")

    # Source code file disguised as .txt rejected
    code_bytes = (
        b"import os\nimport sys\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n"
        b"def parse_doc(text):\n    result = {}\n    return result\n\n"
        b"class DocumentScanner:\n    def run(self):\n        return True\n"
    )
    ok_code, res_code = validate_resume_file_bytes(code_bytes, "script.txt")
    assert ok_code is False


TRICKY_VALID_RESUMES = [
    (
        "fresh_grad_with_thesis_project.pdf",
        """
        MARVIN FABRICANTE
        marvin.fabricante@gmail.com | 0917-555-0123 | Sto. Tomas, Batangas

        OBJECTIVE
        Motivated BS Information Technology graduate seeking a junior full-stack developer role.

        EDUCATION
        Bachelor of Science in Information Technology
        Batangas State University | 2022 - 2026 | Cum Laude
        Thesis: Automated Resume Analysis and Job Matching System

        PROJECTS
        Automated Resume Analysis System (Capstone Project, 2025 - 2026)
        - Developed a FastAPI backend and React TypeScript frontend for automated resume parsing.
        - Implemented deterministic NLP extraction for skills, education, and work history.

        SKILLS
        Python, FastAPI, React, TypeScript, PostgreSQL, Docker, Git
        """,
    ),
    (
        "academic_cv_with_publications.pdf",
        """
        CURRICULUM VITAE
        DR. MARIA ELENA SANTOS, PhD
        maria.santos@up.edu.ph | 0917-999-8888 | Quezon City, Metro Manila

        EDUCATION
        Ph.D. in Materials Science and Engineering, University of the Philippines Diliman (2018 - 2022)
        M.S. in Chemical Engineering, University of the Philippines Diliman (2015 - 2017)

        RESEARCH EXPERIENCE
        Senior Research Scientist | Ceramics R&D Lab Corp. | 2022 - Present
        - Led ceramic glaze formulation experiments and thermal shock testing.
        - Managed analytical lab instruments and mentored junior researchers.

        PUBLICATIONS
        1. Santos, M. E., et al. (2023). Thermal stability of ceramic glazes. Journal of Materials, vol. 14, pp. 101-115. doi: 10.1000/abc
        2. Santos, M. E., & Reyes, J. (2022). High-strength clay composites. Proceedings of ASEAN Ceramics, pp. 45-52.

        SKILLS
        Materials Characterization, XRD, SEM, Statistical Analysis, Python, MATLAB
        """,
    ),
    (
        "resume_with_clearances_and_certs.pdf",
        """
        JOSELITO RAMOS
        joselito.ramos@gmail.com | 0919-555-7777 | Calamba, Laguna

        WORK EXPERIENCE
        Warehouse Staff | Southern Logistics Inc. | Jan 2021 - Present
        - Handled incoming shipments, palletizing, and daily inventory audits.
        - Operated electric forklift safely in compliance with warehouse SOPs.

        EDUCATION
        High School Graduate | Calamba National High School | 2014 - 2018

        CERTIFICATIONS & LICENSES
        - Certificate of Completion: Basic Occupational Safety and Health (BOSH)
        - TESDA Forklift Operation NC II
        - Valid NBI Clearance and Barangay Clearance

        SKILLS
        Inventory Management, Forklift Operation, Packing, Safety Compliance
        """,
    ),
]


@pytest.mark.parametrize("filename,content", TRICKY_VALID_RESUMES)
def test_tricky_legitimate_resumes_are_still_accepted(filename, content):
    pdf_bytes = _make_pdf_bytes(content)
    is_resume, result = validate_resume_file_bytes(pdf_bytes, filename)
    assert is_resume is True, f"Legitimate resume '{filename}' was wrongly rejected: {result}"
    assert result["detected_document_type"] == "resume"
