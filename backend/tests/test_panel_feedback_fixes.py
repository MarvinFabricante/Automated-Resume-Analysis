"""
Comprehensive verification tests for the thesis-defense panel findings:
1. AI / local wrong-document prediction & clear rejection messaging.
2. Blocking applications below accepted requirements (scoring + server-side gate).
3. Non-redundant email notification content + duplicate send suppression.
4. Multi-page resume NLP reading (4-page PDF + 3-page DOCX with running headers/footers).
"""
import os
import re
from datetime import datetime
from unittest.mock import patch, MagicMock
import fitz
import docx
import pytest

from app.extractors.resume_validator import validate_resume_document
from app.extractors.resume_processor import process_resume
from app.services.job_matching_service import calculate_match_score
from app.services import email_service
from app.models.job_description import JobDescription, JobType


# ═════════════════════════════════════════════════════════════════════════════
# 1. WRONG DOCUMENT PREDICTION
# ═════════════════════════════════════════════════════════════════════════════

def test_wrong_document_predictions_cover_panel_doc_types():
    thesis_text = """
    AUTOMATED RESUME ANALYSIS AND JOB MATCHING SYSTEM
    A Thesis Manuscript Presented to the Faculty of the College of Information Technology
    In Partial Fulfillment of the Requirements for the Degree
    Bachelor of Science in Information Technology

    CHAPTER 1: THE PROBLEM AND ITS BACKGROUND
    Statement of the Problem
    Scope and Delimitation
    CHAPTER 2: REVIEW OF RELATED LITERATURE
    CHAPTER 3: RESEARCH METHODOLOGY
    """
    res_thesis = validate_resume_document(thesis_text, filename="Final_Thesis_Manuscript.pdf")
    assert res_thesis["is_resume"] is False
    assert "Wrong document detected" in res_thesis["message"]
    assert "Thesis" in res_thesis["message"]

    slides_text = """
    SLIDE 1: PROJECT OVERVIEW
    Presentation Outline
    • Problem Statement
    • System Architecture
    SLIDE 2: OBJECTIVES
    • Improve screening accuracy
    SLIDE 3: DEMO & RESULTS
    THANK YOU FOR LISTENING
    Questions & Answers
    """
    res_slides = validate_resume_document(slides_text, filename="Defense_Deck.pdf")
    assert res_slides["is_resume"] is False
    assert "Wrong document detected" in res_slides["message"]
    assert res_slides["detected_document_type"] == "presentation_or_slides"
    assert "Presentation / Slide Deck" in res_slides["message"]

    syllabus_text = """
    COURSE SYLLABUS
    Course Code: IT 312 - Natural Language Processing
    Course Description: Introduces text mining and syntactic parsing.
    Learning Outcomes:
    1. Build tokenizers and named entity pipelines.
    Grading System: Midterm Exam 30%, Final Exam 40%, Assignments 30%.
    Week 1: Introduction to NLP
    Week 2: Regular Expressions and Tokenization
    """
    res_syllabus = validate_resume_document(syllabus_text, filename="IT312_Syllabus.pdf")
    assert res_syllabus["is_resume"] is False
    assert "Wrong document detected" in res_syllabus["message"]
    assert res_syllabus["detected_document_type"] == "school_or_course_document"
    assert "School / Course Document" in res_syllabus["message"]

    invoice_text = """
    OFFICIAL RECEIPT / SALES INVOICE
    Invoice No.: INV-2026-00921
    TIN: 123-456-789-000
    Bill To: Sample Client Corp.
    Item Description | Qty | Unit Price | Amount
    Ceramic Floor Tiles 60x60 | 100 | 450.00 | 45,000.00
    VAT (12%): 5,400.00
    Grand Total Due: PHP 50,400.00
    """
    res_inv = validate_resume_document(invoice_text, filename="receipt.pdf")
    assert res_inv["is_resume"] is False
    assert "Wrong document detected" in res_inv["message"]
    assert "Invoice / Receipt" in res_inv["message"]


def test_gemini_ai_rejection_surfaces_ai_predicted_label_and_reason(tmp_path):
    """When Gemini identifies a disguised non-resume, the error message shows AI Predicted + Reason."""
    tricky_doc = tmp_path / "ambiguous_profile.txt"
    tricky_doc.write_text(
        "Juan Dela Cruz\n"
        "juan.delacruz@gmail.com | +63 917 555 1234\n\n"
        "SUMMARY\n"
        "Dedicated professional writing a brief personal bio and motivation note for an event.\n"
        "EDUCATION\n"
        "Batangas State University - 2022\n",
        encoding="utf-8",
    )

    mock_gemini_resp = {
        "is_resume": False,
        "confidence": 0.91,
        "document_type": "cover_letter",
        "reason": "Document is a short personal motivation note rather than a structured resume or CV.",
        "cached": False,
        "gemini_model": "gemini-2.5-flash-lite",
    }

    with patch("app.services.gemini_service.should_invoke_gemini_for_resume", return_value=(True, "verify")), \
         patch("app.services.gemini_service.gemini_verify_and_enhance_resume", return_value=mock_gemini_resp):
        result = process_resume(str(tricky_doc), "txt")

    assert result["is_valid_resume"] is False
    val = result["resume_validation"]
    assert val["verified_by"] == "gemini"
    assert "Wrong document detected (AI Predicted: Standalone Cover / Application Letter)" in val["message"]
    assert "Reason:" in val["message"]


# ═════════════════════════════════════════════════════════════════════════════
# 2. BLOCKING APPLICATIONS BELOW ACCEPTED REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════════

def test_match_score_flags_below_accepted_requirements():
    job = JobDescription(
        job_id="JOB-GATE-01",
        job_title="Senior Ceramic Process Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Manage kiln firing processes, glaze formulation, and ISO 9001 quality control.",
        skills_requirements="Ceramic Processing, Glaze Formulation, ISO 9001, Quality Control",
        experience_requirements="3+ years",
        education_requirements="Bachelor's Degree in Chemical Engineering",
        is_active=True,
    )

    unqualified = calculate_match_score(
        {
            "skills_list": ["Photoshop", "Video Editing"],
            "skills": "Photoshop, Video Editing",
            "experience": "Fresh graduate",
            "education": "High School Diploma",
            "degree": "High School Diploma",
            "years_experience": 0,
        },
        job,
        matching_config={"minimum_match_score": 40.0},
        log_prediction=False,
    )
    assert unqualified["eligible_to_apply"] is False
    assert unqualified["meets_threshold"] is False
    assert len(unqualified["eligibility_reasons"]) >= 1

    qualified = calculate_match_score(
        {
            "skills_list": ["Ceramic Processing", "Glaze Formulation", "ISO 9001", "Quality Control"],
            "skills": "Ceramic Processing, Glaze Formulation, ISO 9001, Quality Control",
            "experience": "4 years Ceramic Process Engineer at Mariwasa Plant",
            "education": "Bachelor of Science in Chemical Engineering - Batangas State University",
            "degree": "Bachelor of Science in Chemical Engineering",
            "years_experience": 4,
        },
        job,
        matching_config={"minimum_match_score": 40.0},
        log_prediction=False,
    )
    assert qualified["eligible_to_apply"] is True
    assert qualified["meets_threshold"] is True
    assert qualified["eligibility_reasons"] == []


@pytest.mark.asyncio
async def test_application_endpoint_blocks_below_requirements_and_allows_qualified(client, db_session):
    job = JobDescription(
        job_id="JOB-GATE-API",
        job_title="Plant Quality Assurance Engineer",
        department="Quality Assurance",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Lead ISO 9001 audits, quality control inspections, and Six Sigma projects.",
        skills_requirements="Quality Control, ISO 9001, Six Sigma, Root Cause Analysis",
        experience_requirements="2 years",
        education_requirements="Bachelor's Degree",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    with patch("app.tasks.analyze_application_task.delay"):
        # 1. Online applicant well below accepted requirements -> BLOCKED (400)
        blocked_res = await client.post(
            "/applications/",
            json={
                "job_id": "JOB-GATE-API",
                "candidate_name": "Unqualified Applicant",
                "candidate_email": "unqualified@example.com",
                "skills": ["Cooking", "Baking"],
                "years_experience": 0,
                "degree": "High School Diploma",
            },
        )
        assert blocked_res.status_code == 400
        assert "below accepted requirements" in blocked_res.json()["detail"].lower()

        # 2. Qualified online applicant -> ACCEPTED (201)
        ok_res = await client.post(
            "/applications/",
            json={
                "job_id": "JOB-GATE-API",
                "candidate_name": "Qualified Engineer",
                "candidate_email": "qualified.qa@example.com",
                "skills": ["Quality Control", "ISO 9001", "Six Sigma"],
                "years_experience": 3,
                "degree": "Bachelor of Science in Industrial Engineering",
            },
        )
        assert ok_res.status_code == 201, ok_res.text

        # 3. HR Imported physical/walk-in resume -> ALLOWED (201) so HR can still archive/redirect
        hr_res = await client.post(
            "/applications/",
            json={
                "job_id": "JOB-GATE-API",
                "source": "Imported",
                "candidate_name": "Walk-in Applicant",
                "candidate_email": "walkin@example.com",
                "skills": ["Cooking"],
                "years_experience": 0,
            },
        )
        assert hr_res.status_code == 201, hr_res.text


# ═════════════════════════════════════════════════════════════════════════════
# 3. NON-REDUNDANT EMAIL CONTENT & DUPLICATE SUPPRESSION
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_email_notifications_are_concise_and_non_redundant():
    sent = []

    def capture_smtp(to_email, subject, html_body, attachments=None):
        sent.append({"to": to_email, "subject": subject, "body": html_body})
        return True

    with patch("app.services.email_service._send_smtp_sync", side_effect=capture_smtp):
        for status_val in ("REVIEWED", "ACCEPTED", "REJECTED", "TECHNICAL INTERVIEW"):
            await email_service.send_application_status_update_email(
                to_email="applicant@example.com",
                candidate_name="Juan Dela Cruz",
                job_title="Process Engineer",
                new_status=status_val,
                notes="Strong technical background.",
            )

        await email_service.send_interview_invitation_email(
            to_email="applicant@example.com",
            candidate_name="Juan Dela Cruz",
            job_title="Process Engineer",
            interview_title="Initial Interview - Process Engineer",
            start_time=datetime(2026, 12, 5, 10, 0),
            end_time=datetime(2026, 12, 5, 11, 0),
            meeting_link="https://meet.google.com/abc-defg-hij",
            interviewer_name="HR Panel",
        )

    assert len(sent) == 5
    for idx in range(4):
        body = sent[idx]["body"]
        # Company name shouldn't be spammed redundantly 4+ times inside a single status email
        assert body.count("Mariwasa Siam Ceramics") <= 2
        # No redundant empty body_content blocks or bloated multi-paragraph walls of text
        visible_text = re.sub(r"<[^>]+>", " ", body)
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        assert len(visible_text) < 1200, f"Email {idx} still verbose ({len(visible_text)} chars)"

    # Online interview invite should include the meeting link in CTA button only (no duplicate raw URL row)
    invite_body = sent[4]["body"]
    assert invite_body.count("https://meet.google.com/abc-defg-hij") == 1


def test_recent_duplicate_email_guard_suppresses_immediate_repeat():
    email_service._RECENT_EMAIL_DEDUP.clear()
    first = email_service._is_duplicate_recent_email(
        "dup@example.com", "Interview Invitation: Engineer", "<html>same body</html>"
    )
    second = email_service._is_duplicate_recent_email(
        "dup@example.com", "Interview Invitation: Engineer", "<html>same body</html>"
    )
    different = email_service._is_duplicate_recent_email(
        "dup@example.com", "Interview Rescheduled: Engineer", "<html>new body</html>"
    )
    assert first is False
    assert second is True
    assert different is False


# ═════════════════════════════════════════════════════════════════════════════
# 4. MULTI-PAGE RESUME NLP READING (PDF + DOCX)
# ═════════════════════════════════════════════════════════════════════════════

def test_multipage_4page_pdf_resume_reads_all_pages(tmp_path):
    """Build a real 4-page PDF resume with running headers/footers and verify NLP extracts all 4 pages."""
    pdf_path = tmp_path / "maria_clara_4page_resume.pdf"
    doc = fitz.open()

    pages_content = [
        # Page 1: Personal Info + Summary + Start of Work Experience
        [
            "MARIA CLARA SANTOS",
            "Sto. Tomas, Batangas, Philippines",
            "maria.santos@gmail.com | +63 917 888 4521",
            "",
            "PROFESSIONAL SUMMARY",
            "Results-driven Industrial & Software Systems Engineer with 6+ years of experience",
            "leading ceramic manufacturing automation, quality assurance, and ERP integrations.",
            "",
            "WORK EXPERIENCE",
            "Senior Process Automation Engineer | Mariwasa Ceramics Plant",
            "Jan 2022 - Present",
            "• Led ISO 9001 quality control workflow digitization across 4 kiln production lines.",
            "• Built Python FastAPI telemetry dashboards monitoring kiln temperature profiles.",
            "• Reduced tile defect rate by 18% through statistical process control and root cause analysis.",
        ],
        # Page 2: Repeated running header + continued experience
        [
            "MARIA CLARA SANTOS | Page 2 of 4",
            "",
            "WORK EXPERIENCE (CONT'D)",
            "Quality Assurance Engineer | Laguna Precision Manufacturing Corp.",
            "Jun 2019 - Dec 2021",
            "• Managed Lean Manufacturing and Six Sigma process improvement audits.",
            "• Developed PostgreSQL reporting tools and automated defect inspection logs.",
            "",
            "Junior Industrial Engineer | Calamba Industrial Systems Inc.",
            "May 2018 - May 2019",
            "• Supported preventive maintenance scheduling and AutoCAD plant layout optimization.",
            "",
            "Page 2 of 4",
        ],
        # Page 3: Repeated running header + Technical Skills & Projects
        [
            "MARIA CLARA SANTOS | Page 3 of 4",
            "",
            "TECHNICAL SKILLS",
            "Programming & Data: Python, FastAPI, PostgreSQL, SQL, Docker, Power BI, SAP ERP",
            "Manufacturing & Quality: Quality Control, ISO 9001, Lean Manufacturing, Six Sigma, AutoCAD",
            "",
            "KEY PROJECTS",
            "Automated Defect Classification Pipeline (2023)",
            "• Deployed Dockerized FastAPI backend integrated with factory floor sensors.",
            "",
            "Page 3 of 4",
        ],
        # Page 4: Repeated running header + Education + Licenses & Certifications
        [
            "MARIA CLARA SANTOS | Page 4 of 4",
            "",
            "EDUCATION",
            "Bachelor of Science in Industrial Engineering",
            "Batangas State University (2014 - 2018)",
            "Magna Cum Laude",
            "",
            "LICENSES AND CERTIFICATIONS",
            "• ISO 9001 Internal Auditor Certification (2023)",
            "• Lean Six Sigma Green Belt (2022)",
            "• DOLE-BOSH Safety Officer 2 Certification (2021)",
            "",
            "Page 4 of 4",
        ],
    ]

    for p_lines in pages_content:
        page = doc.new_page(width=595, height=842)
        y = 50
        for line in p_lines:
            if line:
                page.insert_text((50, y), line, fontsize=11)
            y += 18
    doc.save(str(pdf_path))
    doc.close()

    result = process_resume(str(pdf_path), "pdf")

    assert result["is_valid_resume"] is True, result.get("resume_validation")
    assert result["page_count"] == 4
    assert result["pages_parsed"] == 4
    assert result["is_multi_page"] is True

    # Page 1 personal details
    assert "maria" in (result.get("fullname") or "").lower()
    assert result.get("email") == "maria.santos@gmail.com"

    # Page 1 + Page 2 work experiences preserved across page break
    exp_joined = (result.get("experience") or "").lower()
    raw_lower = (result.get("raw_text") or "").lower()
    assert "laguna precision" in raw_lower
    assert "calamba industrial" in raw_lower
    assert "page 2 of 4" not in raw_lower
    assert "page 4 of 4" not in raw_lower
    assert len(result.get("work_experiences") or []) >= 2 or "laguna precision" in exp_joined

    # Page 3 skills extracted
    skills_lower = {s.lower() for s in (result.get("skills_list") or [])}
    assert "python" in skills_lower
    assert "docker" in skills_lower or "postgresql" in skills_lower

    # Page 4 education & certifications extracted
    edu_joined = " ".join([
        result.get("degree") or "",
        result.get("education") or "",
        result.get("institution") or "",
    ]).lower()
    assert "industrial engineering" in edu_joined
    assert "batangas state university" in edu_joined
    certs_joined = (result.get("certifications") or "").lower()
    assert "iso 9001" in certs_joined or "six sigma" in certs_joined or "bosh" in certs_joined


def test_multipage_3page_docx_resume_reads_all_pages(tmp_path):
    """Build a real 3-page DOCX resume with page breaks & footers and verify NLP reads all 3 pages."""
    docx_path = tmp_path / "carlos_3page_resume.docx"
    d = docx.Document()

    # Add footer with page marker to make sure it is stripped cleanly
    d.sections[0].footer.paragraphs[0].text = "Page 1 of 3"

    # Page 1: Personal + Summary
    d.add_paragraph("CARLOS MIGUEL REYES")
    d.add_paragraph("Calamba City, Laguna | carlos.reyes@gmail.com | +63 918 222 7788")
    d.add_paragraph("SUMMARY")
    d.add_paragraph("Experienced Electrical & Maintenance Technician with 5 years in manufacturing plants.")
    d.add_page_break()

    # Page 2: Experience
    d.add_paragraph("WORK EXPERIENCE")
    d.add_paragraph("Senior Electrical Technician - Southern Luzon Ceramics Inc. (2021 - Present)")
    d.add_paragraph("• Performed PLC programming, preventive maintenance, and motor control troubleshooting.")
    d.add_paragraph("Maintenance Technician - Sta. Rosa Industrial Plant (2019 - 2021)")
    d.add_paragraph("• Maintained pneumatic systems, calibration instruments, and electrical panels.")
    d.add_page_break()

    # Page 3: Skills + Education + Certifications
    d.add_paragraph("TECHNICAL SKILLS")
    d.add_paragraph("PLC Programming, Preventive Maintenance, Electrical Systems, Troubleshooting, AutoCAD")
    d.add_paragraph("EDUCATION")
    d.add_paragraph("Bachelor of Science in Electrical Engineering - University of Batangas (2014 - 2019)")
    d.add_paragraph("CERTIFICATIONS")
    d.add_paragraph("• PRC Registered Electrical Engineer (REE)")
    d.add_paragraph("• TESDA Electrical Installation and Maintenance NC II")
    d.save(str(docx_path))

    result = process_resume(str(docx_path), "docx")

    assert result["is_valid_resume"] is True, result.get("resume_validation")
    assert result["page_count"] >= 3
    assert result["is_multi_page"] is True
    assert result.get("email") == "carlos.reyes@gmail.com"
    assert "page 1 of 3" not in (result.get("raw_text") or "").lower()

    raw_lower = (result.get("raw_text") or "").lower()
    assert "southern luzon ceramics" in raw_lower
    assert "university of batangas" in raw_lower

    skills_lower = " ".join(result.get("skills_list") or []).lower()
    assert "plc" in skills_lower or "preventive maintenance" in skills_lower or "autocad" in skills_lower
    edu_joined = " ".join([
        result.get("degree") or "",
        result.get("education") or "",
        result.get("institution") or "",
    ]).lower()
    assert "electrical engineering" in edu_joined
    certs_joined = (result.get("certifications") or "").lower()
    assert "electrical engineer" in certs_joined or "tesda" in certs_joined
