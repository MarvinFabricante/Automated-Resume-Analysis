import logging
import os
from .file.file_extractor import extract_file_content
from .content.content_extractor import extract_content, format_resume_display
from .readability_checker import evaluate_resume_readability, inspect_file_readability_signals

logger = logging.getLogger(__name__)


def process_resume(file_path: str, file_extension: str) -> dict:
    """
    Main entry point for resume processing.

    Pipeline:
    1. Inspect file readability signals (non-blocking: encryption, text layer, layout).
    2. Extract raw text from file (PDF/DOCX/TXT).
    3. Run Philippine rule-based NLP extractors for comprehensive structured data.
    4. Attach non-blocking applicant readability check (never stored as a penalty).
    5. Extract profile image if available (PDF/DOCX).

    NOTE: Resume extraction is entirely deterministic rule- and NLP-based (zero external LLM dependencies).
    """
    logger.info(f"Processing resume file at: {file_path}")
    file_signals = inspect_file_readability_signals(file_path, file_extension)

    if file_signals.get("password_protected"):
        logger.warning(f"Resume file appears password-protected: {file_path}")
        readability = evaluate_resume_readability(
            file_path=file_path,
            file_extension=file_extension,
            raw_text="",
            extracted_data={},
            file_signals=file_signals,
        )
        return {
            "fullname": "",
            "name": "",
            "candidate_name": "",
            "email": "",
            "candidate_email": "",
            "phone": "",
            "candidate_phone": "",
            "location": "",
            "skills": [],
            "skills_list": [],
            "skills_array": [],
            "work_experiences": [],
            "education_entries": [],
            "certifications": "",
            "certifications_list": [],
            "raw_text": "",
            "is_incomplete": True,
            "is_complete": False,
            "completeness_status": "Incomplete",
            "readability_check": readability,
        }

    text = extract_file_content(file_path, file_extension)
    if not text or not text.strip():
        logger.warning(f"extract_file_content returned empty text for: {file_path}")
        readability = evaluate_resume_readability(
            file_path=file_path,
            file_extension=file_extension,
            raw_text="",
            extracted_data={},
            file_signals=file_signals,
        )
        return {
            "fullname": "",
            "name": "",
            "candidate_name": "",
            "email": "",
            "candidate_email": "",
            "phone": "",
            "candidate_phone": "",
            "location": "",
            "skills": [],
            "skills_list": [],
            "skills_array": [],
            "work_experiences": [],
            "education_entries": [],
            "certifications": "",
            "certifications_list": [],
            "raw_text": "",
            "is_incomplete": True,
            "is_complete": False,
            "completeness_status": "Incomplete",
            "readability_check": readability,
        }

    logger.info(f"Successfully extracted {len(text)} characters of text from {file_path}")

    # ── Step 2: Comprehensive rule-based NLP extraction ──────────────────────
    extracted_data = extract_content(text)

    # Attach raw text and formatted display report
    extracted_data["raw_text"] = text
    extracted_data["formatted_display"] = format_resume_display(extracted_data)

    # Standardize cross-system aliases for database models and frontend views
    fullname = extracted_data.get("fullname", "")
    extracted_data["name"] = fullname
    extracted_data["candidate_name"] = fullname

    email = extracted_data.get("email", "")
    extracted_data["candidate_email"] = email

    phone = extracted_data.get("phone", "")
    extracted_data["candidate_phone"] = phone

    degree = extracted_data.get("degree", "")
    extracted_data["candidate_degree"] = degree

    certifications = extracted_data.get("certifications", "")
    extracted_data["candidate_certifications"] = certifications

    summary = extracted_data.get("summary", "")
    extracted_data["ai_summary"] = summary

    company = extracted_data.get("company", "")
    extracted_data["candidate_company"] = company

    job_title = extracted_data.get("job_title", "")
    extracted_data["candidate_job_title"] = job_title

    # Propagate completeness evaluation to top-level (TC-RES-013 / REQ006)
    is_incomplete = extracted_data.get("is_incomplete", False)
    extracted_data["is_incomplete"] = is_incomplete
    extracted_data["is_complete"] = extracted_data.get("is_complete", not is_incomplete)
    extracted_data["completeness_status"] = extracted_data.get("completeness_status", "Incomplete" if is_incomplete else "Complete")
    extracted_data["missing_sections"] = extracted_data.get("missing_sections", [])
    extracted_data["missing_fields"] = extracted_data.get("missing_fields", [])
    extracted_data["completeness_flags"] = extracted_data.get("completeness_flags", {})
    extracted_data["completeness_score"] = extracted_data.get("completeness_score", 100.0 if not is_incomplete else 0.0)
    extracted_data["is_vague"] = extracted_data.get("is_vague", False)
    extracted_data["needs_clarification"] = extracted_data.get("needs_clarification", False)
    extracted_data["clarification_reasons"] = extracted_data.get("clarification_reasons", [])
    extracted_data["clarification_questions"] = extracted_data.get("clarification_questions", [])
    extracted_data["followup_questions"] = extracted_data.get("followup_questions", extracted_data["clarification_questions"])

    # Ensure list representations for array consumers
    if "skills_list" in extracted_data and not isinstance(extracted_data.get("skills"), list):
        # Keep string for string consumers, but ensure array is accessible
        extracted_data["skills_array"] = extracted_data["skills_list"]

    # ── Step 3: Extract profile image if PDF or DOCX ──────────────────────────
    ext = file_extension.lower().strip('.')
    image_path = None
    if ext == 'pdf':
        try:
            from .file.pdf_extractor import extract_image_from_pdf
            image_path = extract_image_from_pdf(file_path)
        except Exception as e:
            logger.warning(f"Error extracting image from PDF: {e}")
    elif ext in ('docx', 'doc'):
        try:
            from .file.docx_extractor import extract_image_from_docx
            image_path = extract_image_from_docx(file_path)
        except Exception as e:
            logger.warning(f"Error extracting image from DOCX: {e}")

    if image_path:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            extracted_data['profile_image_url'] = image_path
        else:
            extracted_data['profile_image_url'] = f"/{image_path.lstrip('/')}"

    # Detailed diagnostics logging
    skills_count = len(extracted_data.get("skills_list", []))
    exp_count = len(extracted_data.get("work_experiences", []))
    edu_count = len(extracted_data.get("education_entries", []))
    certs_count = len(extracted_data.get("certifications_list", []))

    logger.info(
        f"Resume extraction complete for [{fullname or 'Unknown'}]: "
        f"Status={extracted_data.get('completeness_status')}, Incomplete={is_incomplete}, "
        f"MissingSections={extracted_data.get('missing_sections')}, "
        f"Email='{email}', Phone='{phone}', Location='{extracted_data.get('location', '')}', "
        f"Skills={skills_count}, WorkExperiences={exp_count} ({extracted_data.get('total_experience_months', 0)} mos), "
        f"EducationEntries={edu_count} ({extracted_data.get('highest_educational_attainment', 'Unknown')}), "
        f"Certifications={certs_count}"
    )

    # Attach non-blocking applicant readability check (ephemeral guidance only; never stored as a penalty)
    extracted_data["readability_check"] = evaluate_resume_readability(
        file_path=file_path,
        file_extension=file_extension,
        raw_text=text,
        extracted_data=extracted_data,
        file_signals=file_signals,
    )

    return extracted_data

