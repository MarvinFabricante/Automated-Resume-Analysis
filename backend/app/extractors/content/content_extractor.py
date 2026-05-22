import re
from .name_extractor import extract_fullname
from .email_extractor import extract_email
from .phone_extractor import extract_phone
from .location_extractor import extract_location
from .experience_extractor import extract_experience, extract_years_experience
from .education_extractor import extract_education, extract_highest_degree
from .skills_extractor import extract_skills
from .certifications_extractor import extract_certifications
from .section_parser import split_into_sections
from ..nlp.nlp_engine import extract_all as nlp_extract_all


def _generate_summary(data: dict) -> str:
    """
    Generate a rich, professional summary from extracted resume data.
    Produces a 2-4 sentence summary highlighting key qualifications.
    This replaces the Gemini-generated summary with a comprehensive
    rule-based version that draws from all extracted fields.
    """
    parts = []

    name = data.get("fullname", "The candidate")
    years = data.get("years_experience", 0)
    degree = data.get("highest_degree", "")
    skills_raw = data.get("skills", "")
    experience_raw = data.get("experience", "")
    certifications_raw = data.get("certifications", "")
    education_raw = data.get("education", "")

    # ── Opening sentence: identity + experience level ─────────────────────────
    if years and years > 0 and degree:
        parts.append(
            f"{name} is a professional with {years} years of experience "
            f"and holds a {degree.title()} degree."
        )
    elif years and years > 0:
        parts.append(f"{name} is a professional with {years} years of experience.")
    elif degree:
        parts.append(f"{name} holds a {degree.title()} degree.")
    else:
        parts.append(f"{name} is a professional candidate.")

    # ── Skills highlight ──────────────────────────────────────────────────────
    if skills_raw:
        skill_list = [s.strip() for s in skills_raw.split('|') if s.strip()]
        if len(skill_list) >= 5:
            top_skills = ", ".join(skill_list[:6])
            parts.append(
                f"Key technical skills include {top_skills}, "
                f"among {len(skill_list)} total competencies."
            )
        elif len(skill_list) >= 2:
            parts.append(f"Skilled in {', '.join(skill_list)}.")
        elif skill_list:
            parts.append(f"Skilled in {skill_list[0]}.")

    # ── Experience highlight ──────────────────────────────────────────────────
    if experience_raw:
        exp_entries = [e.strip() for e in experience_raw.split('|') if e.strip()]
        if exp_entries:
            # Use the most recent role (first entry)
            latest_role = exp_entries[0]
            if len(exp_entries) > 1:
                parts.append(
                    f"Most recently served as {latest_role}, "
                    f"with {len(exp_entries)} roles in career history."
                )
            else:
                parts.append(f"Professional experience includes {latest_role}.")

    # ── Certifications highlight ──────────────────────────────────────────────
    if certifications_raw:
        cert_list = [c.strip() for c in certifications_raw.split('|') if c.strip()]
        if cert_list:
            if len(cert_list) == 1:
                parts.append(f"Holds certification: {cert_list[0]}.")
            elif len(cert_list) <= 3:
                parts.append(f"Certified in {', '.join(cert_list)}.")
            else:
                parts.append(
                    f"Holds {len(cert_list)} professional certifications including "
                    f"{', '.join(cert_list[:2])}, and more."
                )

    return " ".join(parts)


def _post_process(data: dict) -> dict:
    """
    Post-processing quality pass on extracted data.
    - Cleans up empty/whitespace-only fields
    - Ensures consistency
    - Validates extracted values
    """
    # Clean all string fields
    for key in ["fullname", "email", "phone", "location", "experience",
                "education", "highest_degree", "skills", "certifications", "summary"]:
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()
            # Remove redundant pipe separators
            data[key] = re.sub(r'\s*\|\s*\|\s*', ' | ', data[key])
            data[key] = data[key].strip(' |')

    # Validate email
    email = data.get("email", "")
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        data["email"] = ""

    # Validate years_experience
    years = data.get("years_experience", 0)
    if not isinstance(years, int) or years < 0:
        data["years_experience"] = 0
    elif years > 50:
        data["years_experience"] = 50  # sanity cap

    # Validate highest_degree
    valid_degrees = {
        "DOCTORATE", "MASTER", "BACHELOR", "ASSOCIATE",
        "DIPLOMA/VOCATIONAL", "SENIOR HIGH SCHOOL", ""
    }
    if data.get("highest_degree", "") not in valid_degrees:
        data["highest_degree"] = ""

    return data


def _cross_validate(data: dict, sections: dict) -> dict:
    """
    Cross-validate extracted data using section awareness.
    Uses parsed sections to fill gaps left by individual extractors.
    """
    # If skills are sparse, try extracting more from the TRAINING section
    skills_raw = data.get("skills", "")
    skill_count = len([s for s in skills_raw.split('|') if s.strip()]) if skills_raw else 0

    # If education is empty but we found section content, recheck
    if not data.get("education") and sections.get("EDUCATION"):
        edu_section = sections["EDUCATION"].strip()
        if edu_section and len(edu_section) > 5:
            data["education"] = edu_section[:300]

    # If experience is empty but section has content, use it
    if not data.get("experience") and sections.get("EXPERIENCE"):
        exp_section = sections["EXPERIENCE"].strip()
        if exp_section and len(exp_section) > 10:
            # Take first 3 non-empty lines as fallback entries
            lines = [l.strip() for l in exp_section.split('\n') if l.strip()]
            if lines:
                data["experience"] = " | ".join(lines[:5])

    # If certifications empty but training section exists, scan it
    if not data.get("certifications") and sections.get("TRAINING"):
        training = sections["TRAINING"].strip()
        if training and len(training) > 5:
            lines = [l.strip() for l in training.split('\n') if l.strip() and len(l.strip()) > 3]
            if lines:
                data["certifications"] = " | ".join(lines[:10])

    return data


def extract_content(text: str) -> dict:
    """
    Main content extraction pipeline.
    Extracts all structured data from resume text using:
      - Regex patterns
      - Rule-based extraction
      - Keyword matching
      - Structured section parsing

    No LLM/AI is used in this pipeline. Gemini is reserved
    exclusively for the downstream analysis/matching stage.
    """
    # Pre-parse sections for cross-validation
    sections = split_into_sections(text)

    data = {
        "fullname": extract_fullname(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": extract_location(text),
        "experience": extract_experience(text),
        "years_experience": extract_years_experience(text),
        "education": extract_education(text),
        "highest_degree": extract_highest_degree(text),
        "skills": extract_skills(text),
        "certifications": extract_certifications(text),
    }

    # ── Run unified NLP engine: preprocessing, NER, and rule-based matching ──
    try:
        nlp_out = nlp_extract_all(text)
        doc = nlp_out.get("doc")

        # Expose entities into data for downstream use
        ents = nlp_out.get("entities")
        if ents:
            data["nlp_entities"] = ents
    except Exception:
        # If NLP engine fails, keep rule-based outputs
        pass

    # Cross-validate using section boundaries
    data = _cross_validate(data, sections)

    # Generate summary from extracted data
    data["summary"] = _generate_summary(data)

    # Post-process for quality
    data = _post_process(data)

    return data
