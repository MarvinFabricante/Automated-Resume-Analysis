import re
from .name_extractor import extract_fullname
from .email_extractor import extract_email
from .phone_extractor import extract_phone
from .location_extractor import extract_location
from .experience_extractor import (
    extract_experience, extract_years_experience, extract_experience_entries,
    extract_job_title, extract_company, extract_relevance
)
from .education_extractor import (
    extract_education, extract_highest_degree, extract_education_entries,
    extract_degree_title, extract_institution
)
from .skills_extractor import extract_skills, extract_skills_list
from .certifications_extractor import extract_certifications
from .section_parser import split_into_sections
from ..nlp.nlp_engine import extract_all as nlp_extract_all


def _generate_summary(data: dict) -> str:
    """
    Generate a rich, professional summary from extracted resume data.
    Produces a 2-4 sentence summary highlighting key qualifications.
    """
    parts = []

    name = data.get("fullname", "The candidate")
    years = data.get("years_experience", 0)
    job_title = data.get("job_title", "")
    company = data.get("company", "")
    degree = data.get("degree") or data.get("highest_degree", "")
    skills_raw = data.get("skills", "")
    experience_raw = data.get("experience", "")
    certifications_raw = data.get("certifications", "")

    # ── Opening sentence: identity + title + experience level ────────────────
    if job_title and years and years > 0:
        parts.append(
            f"{name} is an experienced {job_title} with over {years} years of professional experience."
        )
    elif job_title:
        parts.append(f"{name} is a professional {job_title}.")
    elif years and years > 0 and degree:
        parts.append(
            f"{name} is a professional with {years} years of experience and holds a {degree} degree."
        )
    elif years and years > 0:
        parts.append(f"{name} is a professional with {years} years of experience.")
    elif degree:
        parts.append(f"{name} holds a degree in {degree}.")
    else:
        parts.append(f"{name} is a qualified professional candidate.")

    # ── Skills highlight ──────────────────────────────────────────────────────
    if skills_raw:
        skill_list = [s.strip() for s in skills_raw.split('|') if s.strip()]
        if len(skill_list) >= 5:
            top_skills = ", ".join(skill_list[:6])
            parts.append(
                f"Core competencies and technical skills include {top_skills}, "
                f"among {len(skill_list)} total proficiencies."
            )
        elif len(skill_list) >= 2:
            parts.append(f"Proficient in {', '.join(skill_list)}.")
        elif skill_list:
            parts.append(f"Proficient in {skill_list[0]}.")

    # ── Experience highlight ──────────────────────────────────────────────────
    if company and job_title:
        parts.append(f"Most recently served as {job_title} at {company}.")
    elif experience_raw:
        exp_entries = [e.strip() for e in experience_raw.split('|') if e.strip()]
        if exp_entries:
            latest_role = exp_entries[0]
            if len(exp_entries) > 1:
                parts.append(
                    f"Career history includes {latest_role}, with {len(exp_entries)} recorded positions."
                )
            else:
                parts.append(f"Professional background includes {latest_role}.")

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
                    f"Holds {len(cert_list)} certifications including "
                    f"{', '.join(cert_list[:2])}, and others."
                )

    return " ".join(parts)


def _post_process(data: dict) -> dict:
    """
    Post-processing quality pass on extracted data.
    - Cleans up empty/whitespace-only fields
    - Ensures consistency and validates values
    """
    string_fields = [
        "fullname", "email", "phone", "location", "job_title", "company",
        "relevance", "experience", "education", "degree", "highest_degree",
        "institution", "college", "skills", "certifications", "summary"
    ]
    for key in string_fields:
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()
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
        data["years_experience"] = 50

    # Validate highest_degree
    valid_degrees = {
        "DOCTORATE", "MASTER", "BACHELOR", "ASSOCIATE",
        "DIPLOMA/VOCATIONAL", "SENIOR HIGH SCHOOL", ""
    }
    if data.get("highest_degree", "") not in valid_degrees:
        data["highest_degree"] = ""

    # Ensure institution and college match
    if not data.get("college") and data.get("institution"):
        data["college"] = data["institution"]
    elif not data.get("institution") and data.get("college"):
        data["institution"] = data["college"]

    return data


def _cross_validate(data: dict, sections: dict) -> dict:
    """
    Cross-validate extracted data using section awareness.
    Uses parsed sections to fill gaps left by individual extractors.
    """
    # If education is empty but section has content, recheck
    if not data.get("education") and sections.get("EDUCATION"):
        edu_section = sections["EDUCATION"].strip()
        if edu_section and len(edu_section) > 5:
            data["education"] = edu_section[:300]

    # If experience is empty but section has content, fallback
    if not data.get("experience") and sections.get("EXPERIENCE"):
        exp_section = sections["EXPERIENCE"].strip()
        if exp_section and len(exp_section) > 10:
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
    Extracts all structured details from resume text:
      - full name
      - email address
      - phone number
      - location
      - job title
      - company
      - experience & relevance
      - education/degree
      - institution / college
      - skills (string & list)
      - certifications

    No external LLM is required; runs high-speed rule-based + spaCy NLP pipelines.
    """
    sections = split_into_sections(text)

    # Structured entries
    exp_entries = extract_experience_entries(text)
    edu_entries = extract_education_entries(text)

    # Core extractions
    fullname = extract_fullname(text)
    email = extract_email(text)
    phone = extract_phone(text)
    location = extract_location(text)

    job_title = extract_job_title(text, exp_entries)
    company = extract_company(text, exp_entries)
    experience_str = extract_experience(text)
    years_experience = extract_years_experience(text)

    skills_str = extract_skills(text)
    skills_list = extract_skills_list(text)
    relevance = extract_relevance(text, years_experience, job_title, skills_str)

    degree_title = extract_degree_title(text, edu_entries)
    highest_degree = extract_highest_degree(text)
    institution = extract_institution(text, edu_entries)
    education_str = extract_education(text)
    certifications_str = extract_certifications(text)

    data = {
        # Personal Information
        "fullname": fullname,
        "email": email,
        "phone": phone,
        "location": location,

        # Job & Experience Details
        "job_title": job_title,
        "company": company,
        "experience": experience_str,
        "experience_details": exp_entries,
        "years_experience": years_experience,
        "relevance": relevance,

        # Education Details
        "degree": degree_title,
        "highest_degree": highest_degree,
        "institution": institution,
        "college": institution,  # alias for frontend/DB compatibility
        "education": education_str,
        "education_details": edu_entries,

        # Skills & Certifications
        "skills": skills_str,
        "skills_list": skills_list,
        "certifications": certifications_str,
    }

    # Run unified NLP engine for NER entities
    try:
        nlp_out = nlp_extract_all(text)
        ents = nlp_out.get("entities")
        if ents:
            data["nlp_entities"] = ents
    except Exception:
        pass

    # Cross-validate using section boundaries
    data = _cross_validate(data, sections)

    # Generate summary from extracted data
    data["summary"] = _generate_summary(data)

    # Post-process for cleanliness and validation
    data = _post_process(data)

    return data
