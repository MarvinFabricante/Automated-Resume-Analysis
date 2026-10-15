import logging
import os
from .file.file_extractor import extract_file_content
from .content.content_extractor import extract_content, format_resume_display

logger = logging.getLogger(__name__)


def process_resume(file_path: str, file_extension: str) -> dict:
    """
    Main entry point for resume processing.

    Pipeline:
    1. Extract raw text from file (PDF/DOCX/TXT).
    2. Run newly engineered Philippine rule-based NLP extractors for comprehensive structured data:
       - Full Name (with post-nominal and prefix awareness)
       - Primary & Alternate Email addresses
       - Primary & Alternate Mobile numbers (+63 / 09xx / landlines)
       - Detailed Address & PSGC geographic breakdown (Barangay, City/Municipality, Province, Region)
       - Granular Work Experience entries, role, company, duration, and duties
       - Granular Educational Attainment entries, degree/course, school, status, and honors
       - Categorized Skills Inventory (Hard Skills, Tools, Soft Skills, Languages)
       - Licenses & Certifications (PRC, TESDA NC, DOLE-OSHC, Red Cross, LTO, IT)
       - Synthesized Executive Profile Summary
       - Formatted diagnostic report display
    3. Extract profile image if available (PDF/DOCX).

    NOTE: Resume extraction is entirely deterministic rule- and NLP-based (zero external LLM dependencies).
    """
    logger.info(f"Processing resume file at: {file_path}")
    text = extract_file_content(file_path, file_extension)
    if not text or not text.strip():
        logger.warning(f"extract_file_content returned empty text for: {file_path}")
        return {}

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
        f"Email='{email}', Phone='{phone}', Location='{extracted_data.get('location', '')}', "
        f"Skills={skills_count}, WorkExperiences={exp_count} ({extracted_data.get('total_experience_months', 0)} mos), "
        f"EducationEntries={edu_count} ({extracted_data.get('highest_educational_attainment', 'Unknown')}), "
        f"Certifications={certs_count}"
    )

    return extracted_data

