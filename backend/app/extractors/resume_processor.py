import logging
import os
from .file.file_extractor import extract_file_content
from .content.content_extractor import extract_content, format_resume_display
from .readability_checker import evaluate_resume_readability, inspect_file_readability_signals
from .resume_validator import fast_precheck_non_resume, validate_resume_document

logger = logging.getLogger(__name__)


def _apply_gemini_verification_and_enrichment(
    raw_text: str,
    extracted_data: dict,
    validation: dict,
    file_signals: dict,
    file_path: str,
) -> dict:
    """
    Quota-efficient Gemini verification + semantic extraction enhancement.
    - Obvious non-resumes (hard vetoes) are skipped locally with 0 API calls.
    - Repeat uploads / Step 1 -> Step 4 HR imports hit SHA-256 cache with 0 API calls.
    - Uses 1 single combined Flash-Lite call (thinking_budget=0) to verify is_resume AND
      enrich ai_summary, inferred_skills, career_domain, seniority_level, and missing fields.
    - Gracefully preserves local deterministic results whenever Gemini is disabled, budgeted out,
      or temporarily unavailable.
    """
    try:
        from app.services.gemini_service import (
            gemini_verify_and_enhance_resume,
            should_invoke_gemini_for_resume,
        )
        from .resume_validator import _build_rejection_message
    except Exception:
        return validation

    should_call, decision_reason = should_invoke_gemini_for_resume(validation, extracted_data)
    validation["verified_by"] = "local_deterministic"
    validation["gemini_decision"] = decision_reason

    if not should_call:
        return validation

    gemini_res = gemini_verify_and_enhance_resume(
        raw_text=raw_text,
        local_validation=validation,
        extracted_data=extracted_data,
        page_count=file_signals.get("page_count"),
        filename=os.path.basename(file_path),
    )
    if not gemini_res:
        validation["gemini_decision"] = "fallback_local_unavailable"
        return validation

    g_is_resume = bool(gemini_res.get("is_resume"))
    g_conf = float(gemini_res.get("confidence") or 0.0)
    g_doc_type = str(gemini_res.get("document_type") or "misc_non_resume")
    g_reason = str(gemini_res.get("reason") or "").strip()

    # Map Gemini document_type onto canonical local rejection labels
    type_map = {
        "thesis_manuscript": ("academic_paper", "detected_thesis_manuscript"),
        "academic_paper": ("academic_paper", "detected_academic_paper"),
        "manual_or_guide": ("manual_or_guide", "detected_manual_or_guide"),
        "financial_document": ("financial_document", "detected_financial_document"),
        "certificate_or_official_record": ("certificate_or_official_record", "detected_certificate_or_official_record"),
        "legal_or_correspondence": ("legal_or_correspondence", "detected_legal_or_correspondence"),
        "cover_letter": ("cover_letter", "detected_cover_letter"),
        "presentation_or_slides": ("presentation_or_slides", "detected_presentation_or_slides"),
        "school_or_course_document": ("school_or_course_document", "detected_school_or_course_document"),
        "job_posting": ("job_posting", "detected_job_posting"),
        "misc_non_resume": ("misc_non_resume", "detected_misc_non_resume"),
    }

    local_conf = float(validation.get("confidence") or 0.0)
    local_neg = float(validation.get("negative_score") or 0.0)
    local_core_headings = (validation.get("metrics") or {}).get("core_headings") or []
    reject_conf_threshold = 0.60 if (local_conf < 0.78 or local_neg >= 2.0 or len(local_core_headings) < 2) else 0.70

    # Case 1: Gemini rejects a disguised/tricky non-resume that slipped past local heuristics
    if not g_is_resume and g_conf >= reject_conf_threshold:
        mapped_type, mapped_reason = type_map.get(g_doc_type, ("misc_non_resume", "gemini_rejected_non_resume"))
        validation["is_resume"] = False
        validation["verified_by"] = "gemini"
        validation["gemini_cached"] = bool(gemini_res.get("cached"))
        validation["gemini_model"] = gemini_res.get("gemini_model")
        validation["detected_document_type"] = mapped_type
        validation["reason_code"] = mapped_reason
        validation["confidence"] = round(max(local_conf, g_conf), 2)
        base_msg = _build_rejection_message(
            mapped_type,
            mapped_reason,
            ai_reason=g_reason,
            verified_by="AI",
        )
        validation["message"] = base_msg
        validation["gemini_reason"] = g_reason
        neg_sigs = list(validation.get("negative_signals") or [])
        neg_sigs.append(f"gemini_rejected:{g_doc_type}(conf={g_conf:.2f})")
        validation["negative_signals"] = neg_sigs
        return validation

    # Case 2: Local rejected only softly (low-confidence insufficient evidence) & Gemini strongly confirms valid resume
    local_is_resume = bool(validation.get("is_resume"))
    if (
        not local_is_resume
        and g_is_resume
        and g_conf >= 0.85
        and validation.get("reason_code") == "insufficient_resume_evidence"
        and float(validation.get("negative_score") or 0.0) < 3.0
    ):
        validation["is_resume"] = True
        validation["verified_by"] = "gemini_rescue"
        validation["gemini_cached"] = bool(gemini_res.get("cached"))
        validation["gemini_model"] = gemini_res.get("gemini_model")
        validation["detected_document_type"] = "resume"
        validation["reason_code"] = "gemini_verified_resume"
        validation["confidence"] = round(g_conf, 2)
        validation["message"] = "Valid resume document verified."
        pos_sigs = list(validation.get("positive_signals") or [])
        pos_sigs.append(f"gemini_verified:{g_doc_type}(conf={g_conf:.2f})")
        validation["positive_signals"] = pos_sigs

    # Case 3: Document is a confirmed resume -> merge Gemini semantic enhancements
    if validation.get("is_resume"):
        if validation.get("verified_by") == "local_deterministic":
            validation["verified_by"] = "local+gemini"
        validation["gemini_cached"] = bool(gemini_res.get("cached"))
        validation["gemini_model"] = gemini_res.get("gemini_model")

        extracted_data["ai_extraction_enhanced"] = True
        extracted_data["ai_gemini_model"] = gemini_res.get("gemini_model")
        extracted_data["ai_extraction_cached"] = bool(gemini_res.get("cached"))

        if gemini_res.get("career_domain"):
            extracted_data["career_domain"] = gemini_res["career_domain"]
        if gemini_res.get("seniority_level"):
            extracted_data["seniority_level"] = gemini_res["seniority_level"]

        if gemini_res.get("ai_summary"):
            extracted_data["ai_summary"] = gemini_res["ai_summary"]
            if not (extracted_data.get("summary") or "").strip():
                extracted_data["summary"] = gemini_res["ai_summary"]

        # Merge inferred skills without duplicating existing extracted skills
        inferred_skills = gemini_res.get("inferred_skills") or []
        extracted_data["ai_inferred_skills"] = list(inferred_skills)
        if inferred_skills:
            existing_list = list(extracted_data.get("skills_list") or [])
            seen_lower = {str(s).strip().lower() for s in existing_list if str(s).strip()}
            added_skills = []
            for sk in inferred_skills:
                clean_sk = str(sk).strip()
                if clean_sk and clean_sk.lower() not in seen_lower:
                    seen_lower.add(clean_sk.lower())
                    existing_list.append(clean_sk)
                    added_skills.append(clean_sk)
            if added_skills:
                extracted_data["skills_list"] = existing_list
                extracted_data["skills_array"] = existing_list
                if isinstance(extracted_data.get("skills"), list):
                    extracted_data["skills"] = existing_list
                else:
                    extracted_data["skills"] = " | ".join(existing_list)

        # Gap-fill ONLY missing core fields (never overwrite valid local extractions)
        if not (extracted_data.get("fullname") or "").strip() and gemini_res.get("corrected_fullname"):
            corr_name = gemini_res["corrected_fullname"]
            extracted_data["fullname"] = corr_name
            extracted_data["name"] = corr_name
            extracted_data["candidate_name"] = corr_name

        if not (extracted_data.get("job_title") or "").strip() and gemini_res.get("corrected_job_title"):
            corr_title = gemini_res["corrected_job_title"]
            extracted_data["job_title"] = corr_title
            extracted_data["candidate_job_title"] = corr_title

        if not (extracted_data.get("degree") or "").strip() and gemini_res.get("corrected_degree"):
            corr_deg = gemini_res["corrected_degree"]
            extracted_data["degree"] = corr_deg
            extracted_data["candidate_degree"] = corr_deg
            if not (extracted_data.get("highest_degree") or "").strip():
                extracted_data["highest_degree"] = corr_deg

    return validation


def process_resume(file_path: str, file_extension: str) -> dict:
    """
    Main entry point for resume processing.

    Pipeline:
    1. Reject disguised executable binaries immediately.
    2. Inspect file readability signals (encryption, page count, text layer, layout).
    3. Extract raw text from file (PDF/DOCX/TXT).
    4. Run Philippine rule-based NLP extractors for comprehensive structured data.
    5. Run strict resume-vs-non-resume document gatekeeper (`validate_resume_document`).
    6. Attach non-blocking applicant readability check (never stored as a penalty).
    7. Extract profile image if available (PDF/DOCX) ONLY for validated resumes.

    NOTE: Resume extraction is entirely deterministic rule- and NLP-based (zero external LLM dependencies).
    """
    logger.info(f"Processing resume file at: {file_path}")

    # Security gate: reject disguised executables before any extraction
    try:
        from app.utils.file_validator import is_executable_binary
        with open(file_path, "rb") as _f:
            _hdr = _f.read(64)
        is_exe, _ = is_executable_binary(_hdr)
        if is_exe:
            logger.warning(f"Executable binary rejected in process_resume: {file_path}")
            return {}
    except Exception:
        pass

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
        validation = validate_resume_document(
            raw_text="",
            extracted_data={},
            file_signals=file_signals,
            page_count=file_signals.get("page_count"),
            filename=os.path.basename(file_path),
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
            "is_valid_resume": validation["is_resume"],
            "resume_validation": validation,
        }

    # ── Ultra-fast pre-extraction gate (runs BEFORE expensive dual-engine PDF/OCR extraction) ──
    # Immediately rejects huge thesis manuscripts, manuals, books, or unmistakable cover-page non-resumes
    # in milliseconds so they never get scanned by pdfminer.six, 250-DPI OCR, or spaCy NER.
    pre_sample_text = (file_signals.get("fast_sample_text") or "").strip()
    pre_page_count = file_signals.get("page_count")
    if pre_sample_text or (isinstance(pre_page_count, int) and pre_page_count >= 15):
        early_rejection = fast_precheck_non_resume(
            raw_text=pre_sample_text,
            file_signals=file_signals,
            page_count=pre_page_count,
            filename=os.path.basename(file_path),
            is_partial_sample=True,
        )
        if early_rejection is not None:
            early_rejection["verified_by"] = "local_fast_prefilter"
            early_rejection["gemini_decision"] = "skipped_local_fast_prefilter"
            try:
                from app.services.gemini_service import record_local_prefilter_skip
                record_local_prefilter_skip()
            except Exception:
                pass
            logger.warning(
                f"Pre-extraction fast-rejected non-resume document ({early_rejection['detected_document_type']}, "
                f"reason={early_rejection['reason_code']}, pages={pre_page_count}, score={early_rejection['score']}): {file_path}"
            )
            readability = evaluate_resume_readability(
                file_path=file_path,
                file_extension=file_extension,
                raw_text=pre_sample_text,
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
                "raw_text": pre_sample_text,
                "is_incomplete": True,
                "is_complete": False,
                "completeness_status": "Incomplete",
                "readability_check": readability,
                "is_valid_resume": False,
                "resume_validation": early_rejection,
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
        validation = validate_resume_document(
            raw_text="",
            extracted_data={},
            file_signals=file_signals,
            page_count=file_signals.get("page_count"),
            filename=os.path.basename(file_path),
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
            "is_valid_resume": validation["is_resume"],
            "resume_validation": validation,
        }

    logger.info(f"Successfully extracted {len(text)} characters of text from {file_path}")

    # ── Fast pre-screen: immediately reject unmistakable non-resumes (e.g. 20-page manuals, invoices, theses)
    #    before spending time on heavy spaCy NER / structured extraction.
    fast_rejection = fast_precheck_non_resume(
        raw_text=text,
        file_signals=file_signals,
        page_count=file_signals.get("page_count"),
        filename=os.path.basename(file_path),
    )
    if fast_rejection is not None:
        fast_rejection["verified_by"] = "local_fast_prefilter"
        fast_rejection["gemini_decision"] = "skipped_local_fast_prefilter"
        try:
            from app.services.gemini_service import record_local_prefilter_skip
            record_local_prefilter_skip()
        except Exception:
            pass
        logger.warning(
            f"Fast-rejected non-resume document ({fast_rejection['detected_document_type']}, "
            f"reason={fast_rejection['reason_code']}, score={fast_rejection['score']}): {file_path}"
        )
        readability = evaluate_resume_readability(
            file_path=file_path,
            file_extension=file_extension,
            raw_text=text,
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
            "raw_text": text,
            "is_incomplete": True,
            "is_complete": False,
            "completeness_status": "Incomplete",
            "readability_check": readability,
            "is_valid_resume": False,
            "resume_validation": fast_rejection,
        }

    # ── Step 2: Comprehensive rule-based NLP extraction ──────────────────────
    extracted_data = extract_content(text)

    # Attach raw text, multi-page metadata, and formatted display report
    detected_pages = file_signals.get("page_count")
    if not isinstance(detected_pages, int) or detected_pages < 1:
        detected_pages = 1
    extracted_data["page_count"] = detected_pages
    extracted_data["pages_parsed"] = detected_pages
    extracted_data["is_multi_page"] = detected_pages > 1
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

    # ── Step 2.5: Strict Resume-Only Document Gatekeeper (Local + Quota-Gated Gemini) ──
    validation = validate_resume_document(
        raw_text=text,
        extracted_data=extracted_data,
        file_signals=file_signals,
        page_count=file_signals.get("page_count"),
        filename=os.path.basename(file_path),
    )
    validation = _apply_gemini_verification_and_enrichment(
        raw_text=text,
        extracted_data=extracted_data,
        validation=validation,
        file_signals=file_signals,
        file_path=file_path,
    )
    extracted_data["is_valid_resume"] = validation["is_resume"]
    extracted_data["resume_validation"] = validation
    # Refresh local display alias in case Gemini gap-filled fullname
    fullname = extracted_data.get("fullname", "")

    if not validation["is_resume"]:
        logger.warning(
            f"Document rejected as non-resume ({validation['detected_document_type']}, "
            f"reason={validation['reason_code']}, verified_by={validation.get('verified_by', 'local')}, "
            f"score={validation['score']}, pos={validation['positive_score']}, neg={validation['negative_score']}): {file_path}"
        )

    # ── Step 3: Extract profile image ONLY for validated resumes ─────────────
    ext = file_extension.lower().strip('.')
    image_path = None
    if validation["is_resume"]:
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

