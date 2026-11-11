import re
from typing import Optional, List, Dict, Any
from .name_extractor import extract_fullname, extract_all_name_candidates, _normalize_name, is_valid_name
from .email_extractor import extract_email, extract_all_emails, _clean_email, is_valid_email
from .phone_extractor import extract_phone, extract_all_phones, _clean_phone, is_valid_phone
from .location_extractor import extract_location, extract_applicant_address
from .experience_extractor import (
    extract_experience, extract_years_experience, extract_experience_entries,
    extract_job_title, extract_company, extract_relevance, extract_structured_experience
)
from .education_extractor import (
    extract_education, extract_highest_degree, extract_education_entries,
    extract_degree_title, extract_institution, extract_structured_education
)
from .skills_extractor import extract_skills, extract_skills_list, extract_structured_skills
from .certifications_extractor import extract_certifications, extract_structured_certifications
from .section_parser import split_into_sections
from ..nlp.nlp_engine import extract_all as nlp_extract_all


def _generate_summary(data: dict) -> str:
    """
    Generate a rich, professional executive summary from extracted resume data.
    Synthesizes name, location, role, experience, education, skills, and certifications.
    """
    parts = []

    name = data.get("fullname", "The candidate")
    years = data.get("years_experience", 0)
    job_title = data.get("job_title", "")
    company = data.get("company", "")
    location = data.get("location", "")
    highest_attainment = data.get("highest_educational_attainment", "")
    degree = data.get("degree") or data.get("highest_degree", "")
    institution = data.get("institution") or data.get("college", "")
    skills_raw = data.get("skills", "")
    certifications_raw = data.get("certifications", "")

    # 1. Identity, target title, location & experience
    loc_clause = f" based in {location}" if location and location != "Philippines" else ""
    valid_title = job_title and job_title.lower() not in {"experience", "work experience", "professional experience", "employment history", "work history"}
    if valid_title and years and years > 0:
        parts.append(
            f"{name} is an experienced {job_title}{loc_clause} with over {years} years of professional experience."
        )
    elif valid_title:
        parts.append(f"{name} is a dedicated {job_title}{loc_clause}.")
    elif years and years > 0 and degree:
        parts.append(
            f"{name} is a qualified professional{loc_clause} with {years} years of experience and background in {degree}."
        )
    elif years and years > 0:
        parts.append(f"{name} is a qualified professional{loc_clause} with {years} years of industry experience.")
    elif degree:
        parts.append(f"{name} is an applicant{loc_clause} with educational credentials in {degree}.")
    else:
        parts.append(f"{name} is a qualified candidate{loc_clause}.")

    # 2. Education highlight
    if degree and institution:
        parts.append(f"Holds a degree in {degree} from {institution}.")
    elif degree:
        parts.append(f"Holds a degree in {degree}.")
    elif highest_attainment and highest_attainment != "Unknown":
        parts.append(f"Highest educational attainment is {highest_attainment}.")

    # 3. Employment & Experience highlight
    if company and valid_title:
        parts.append(f"Most recently served as {job_title} at {company}.")
    elif data.get("work_experiences"):
        top_exp = data["work_experiences"][0]
        r = top_exp.get("job_title") or top_exp.get("role", "")
        c = top_exp.get("company_name") or top_exp.get("company", "")
        if r and c:
            parts.append(f"Career highlights include serving as {r} at {c}.")
        elif r:
            parts.append(f"Career highlights include serving as {r}.")

    # 4. Skills highlight (uses skills_details if available)
    skills_details = data.get("skills_details", {})
    if isinstance(skills_details, dict) and skills_details.get("skills"):
        all_skills = [s["skill_name"] for s in skills_details["skills"]]
        hard_skills = [s["skill_name"] for s in skills_details["skills"] if s.get("category") == "Hard Skills"]
        tools = [s["skill_name"] for s in skills_details["skills"] if s.get("category") == "Tools & Machinery"]
        
        featured = hard_skills[:4] + tools[:2]
        if not featured:
            featured = all_skills[:6]
        parts.append(f"Core competencies include {', '.join(featured)}, among {len(all_skills)} verified proficiencies.")
    elif skills_raw:
        skill_list = [s.strip() for s in skills_raw.split('|') if s.strip()]
        if len(skill_list) >= 4:
            parts.append(f"Core competencies include {', '.join(skill_list[:5])}, among {len(skill_list)} recorded proficiencies.")
        elif skill_list:
            parts.append(f"Proficient in {', '.join(skill_list)}.")

    # 5. Certifications & Licenses highlight
    cert_details = data.get("certifications_details", {})
    if isinstance(cert_details, dict) and cert_details.get("certifications"):
        certs = cert_details["certifications"]
        prc_gov = [c["canonical_name"] for c in certs if c.get("category") == "PRC / Government License"]
        tesda = [c["canonical_name"] for c in certs if c.get("category") == "TESDA National Certificate"]
        safety = [c["canonical_name"] for c in certs if c.get("category") == "Safety & Compliance"]
        it_prof = [c["canonical_name"] for c in certs if c.get("category") == "IT & Professional Certification"]
        
        notable = prc_gov + tesda + safety + it_prof
        if notable:
            parts.append(f"Credentials and certifications include {', '.join(notable[:3])}.")
        else:
            names = [c["canonical_name"] for c in certs[:3]]
            parts.append(f"Credentials include {', '.join(names)}.")
    elif certifications_raw:
        cert_list = [c.strip() for c in certifications_raw.split('|') if c.strip()]
        if cert_list:
            parts.append(f"Credentials include {', '.join(cert_list[:3])}.")

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
    if email:
        cleaned_em = _clean_email(email)
        if not cleaned_em or not is_valid_email(cleaned_em):
            data["email"] = ""
        else:
            data["email"] = cleaned_em

    if not data.get("email") and data.get("emails"):
        for alt in data["emails"]:
            cleaned_alt = _clean_email(alt)
            if cleaned_alt and is_valid_email(cleaned_alt):
                data["email"] = cleaned_alt
                break

    # Validate phone
    phone = data.get("phone", "")
    if phone:
        cleaned_ph = _clean_phone(phone)
        if not cleaned_ph or not is_valid_phone(cleaned_ph):
            data["phone"] = ""
        else:
            data["phone"] = cleaned_ph

    if not data.get("phone") and data.get("phones"):
        for alt in data["phones"]:
            cleaned_alt = _clean_phone(alt)
            if cleaned_alt and is_valid_phone(cleaned_alt):
                data["phone"] = cleaned_alt
                break

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
    # If education is empty but section has actual academic content, recheck
    if not data.get("education") and sections.get("EDUCATION"):
        edu_section = sections["EDUCATION"].strip()
        if edu_section and len(edu_section) > 5 and re.search(
            r'\b(?:bachelor|master|doctor|associate|diploma|vocational|technical\s+course|'
            r'university|college|school|institute|academy|polytechnic|tesda|bs|ba|shs|stem|abm|humss|tvl)\b',
            edu_section,
            re.I,
        ):
            data["education"] = edu_section[:300]

    # If experience is empty but section has content, fallback
    if not data.get("experience") and sections.get("EXPERIENCE"):
        exp_section = sections["EXPERIENCE"].strip()
        if exp_section and len(exp_section) > 10:
            lines = [l.strip() for l in exp_section.split('\n') if l.strip()]
            if lines:
                data["experience"] = " | ".join(lines[:5])

    # If certifications empty but certifications/training/awards section exists, scan it
    if not data.get("certifications"):
        cert_sec = (
            sections.get("CERTIFICATIONS")
            or sections.get("TRAINING")
            or sections.get("AWARDS")
            or ""
        ).strip()
        if cert_sec and len(cert_sec) > 3:
            fallback_items = [
                re.sub(r'^(?:[•\-–—▪►✓*]|\(?\d{1,2}[\.\)])\s*', '', l.strip()).strip()
                for l in cert_sec.split('\n')
            ]
            fallback_items = [
                item for item in fallback_items
                if len(item) >= 3
                and not re.match(r'^(?:none|n/?a|not\s+applicable|(?:19|20)\d{2})$', item, re.I)
            ]
            if fallback_items:
                data["certifications"] = " | ".join(fallback_items[:25])
                if not data.get("certifications_list"):
                    data["certifications_list"] = fallback_items[:25]

    # If email is empty, re-scan PERSONAL/CONTACT section
    if not data.get("email") and sections.get("PERSONAL"):
        personal_section = sections["PERSONAL"].strip()
        fallback_email = extract_email(personal_section, candidate_name=data.get("fullname", ""))
        if fallback_email:
            data["email"] = fallback_email
            emails_list = data.setdefault("emails", [])
            if fallback_email not in emails_list:
                emails_list.insert(0, fallback_email)
            data["all_emails"] = emails_list

    # If phone is empty, re-scan PERSONAL/CONTACT section
    if not data.get("phone") and sections.get("PERSONAL"):
        personal_section = sections["PERSONAL"].strip()
        fallback_phone = extract_phone(personal_section)
        if fallback_phone:
            data["phone"] = fallback_phone
            phones_list = data.setdefault("phones", [])
            if fallback_phone not in phones_list:
                phones_list.insert(0, fallback_phone)
    # If fullname is empty, re-scan PERSONAL/CONTACT section
    if not data.get("fullname") and sections.get("PERSONAL"):
        personal_section = sections["PERSONAL"].strip()
        fallback_name = extract_fullname(personal_section)
        if fallback_name:
            data["fullname"] = fallback_name
            names_list = data.setdefault("names", [])
            if fallback_name not in names_list:
                names_list.insert(0, fallback_name)
            data["all_names"] = names_list

    # If company is empty, check work_experiences / experience_details / EXPERIENCE section
    if not data.get("company"):
        for exp in data.get("work_experiences", []):
            c = exp.get("company_name") or exp.get("company")
            if c and len(c) > 2:
                data["company"] = c
                break
        if not data.get("company"):
            for exp in data.get("experience_details", []):
                c = exp.get("company_name") or exp.get("company")
                if c and len(c) > 2:
                    data["company"] = c
                    break
        if not data.get("company") and sections.get("EXPERIENCE"):
            c = extract_company(sections["EXPERIENCE"])
            if c:
                data["company"] = c

    # If degree is empty, check education_entries / education_details / EDUCATION section
    if not data.get("degree"):
        for edu in data.get("education_entries", []):
            d = edu.get("degree_or_course") or edu.get("degree") or edu.get("raw_degree_or_course")
            if d and len(d) > 3:
                data["degree"] = d
                break
        if not data.get("degree"):
            for edu in data.get("education_details", []):
                d = edu.get("degree")
                if d and len(d) > 3:
                    data["degree"] = d
                    break
        if not data.get("degree") and sections.get("EDUCATION"):
            d = extract_degree_title(sections["EDUCATION"])
            if d:
                data["degree"] = d

    return data


def _has_explicit_skill_list(full_text: str, extracted_items: list[dict]) -> bool:
    """
    Detect whether the resume contains an explicit skill list or competency
    statement even if section headers were missing or mis-segmented.
    """
    if not full_text or not extracted_items:
        return False

    if re.search(
        r'\b(?:proficient\s+in|skilled\s+in|knowledgeable\s+in|expertise\s+in|'
        r'specializing\s+in|well[\s\-]versed\s+in|tech\s+stack\s*:|'
        r'(?:technical\s+|core\s+|key\s+)?skills\s*(?:used|include|list)?\s*:)\b',
        full_text,
        re.I,
    ):
        return True

    raw_mentions = {
        s["raw_mention"].lower()
        for s in extracted_items
        if s.get("raw_mention") and len(s["raw_mention"].strip()) >= 2
    }
    if len(raw_mentions) < 3:
        return False

    _EXP_VERB_START = re.compile(
        r'^(?:[•\-*▪►✓]\s*)?(?:developed|built|managed|supervised|performed|'
        r'assisted|handled|conducted|prepared|designed|created|led|worked|'
        r'maintained|operated|implemented|executed|engineered|monitored)\b',
        re.I,
    )
    for line in full_text.split('\n'):
        stripped = line.strip()
        if not stripped or (',' not in stripped and '|' not in stripped and '/' not in stripped):
            continue
        if _EXP_VERB_START.match(stripped):
            continue
        line_lower = stripped.lower()
        hits = 0
        for mention in raw_mentions:
            if len(mention) <= 2:
                if re.search(rf'(?<![A-Za-z0-9]){re.escape(mention)}(?![A-Za-z0-9])', line_lower):
                    hits += 1
            elif mention in line_lower:
                hits += 1
        if hits >= 3:
            return True

    return False


def _supplement_skills_from_section(skills_section_text: str, skills_details: dict, skills_list: list[str]) -> list[str]:
    """
    Capture any skills explicitly listed in the SKILLS section that were not
    already matched by the taxonomy engine (e.g. niche tools or domain terms),
    without duplicating already-covered canonical skills.
    """
    if not skills_section_text or not skills_section_text.strip():
        return skills_list

    extracted_items = skills_details.get("extracted_skills", []) if isinstance(skills_details, dict) else []
    covered_terms = set()
    for item in extracted_items:
        if item.get("canonical_skill"):
            covered_terms.add(item["canonical_skill"].lower())
        if item.get("raw_mention"):
            covered_terms.add(item["raw_mention"].lower())

    ignore_labels = {
        "skills", "technical skills", "competencies", "core competencies",
        "soft skills", "hard skills", "tools", "technologies", "languages",
        "frameworks", "frameworks & libraries", "databases", "databases & cloud",
        "tools & testing", "software", "none", "n/a", "na", "not applicable",
    }
    category_prefix_re = re.compile(
        r'^(?:languages|frameworks(?:\s*(?:&|and)\s*libraries)?|'
        r'databases(?:\s*(?:&|and)\s*cloud)?|tools(?:\s*(?:&|and)\s*testing)?|'
        r'technologies|software|platforms|cloud|testing|other|others|'
        r'hard\s+skills|soft\s+skills|technical\s+skills|core\s+skills)\s*:\s*(.+)$',
        re.I,
    )

    added_items: list[str] = []
    existing_lower = {s.lower() for s in skills_list}

    for raw_line in skills_section_text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue
        m_cat = category_prefix_re.match(line)
        if m_cat:
            line = m_cat.group(1).strip()

        # Split on delimiters outside parentheses and on spaced slashes (" / ")
        parts = re.split(r'(?:[,|•*▪►✓\t;]+(?![^()]*\))|\s+/\s+)', line)
        for part in parts:
            item_clean = part.strip(' -•*▪►✓.:')
            if not item_clean or len(item_clean) < 2 or len(item_clean) > 55:
                continue
            if len(item_clean.split()) > 5:
                continue
            item_lower = item_clean.lower()
            if item_lower in ignore_labels or item_lower in existing_lower:
                continue

            # Skip if already covered by an extracted canonical skill or raw mention
            is_covered = item_lower in covered_terms
            if not is_covered:
                for term in covered_terms:
                    if len(term) >= 3:
                        if re.search(rf'(?<![A-Za-z0-9+#.]){re.escape(term)}(?![A-Za-z0-9+#.])', item_lower):
                            is_covered = True
                            break
                        if re.search(rf'(?<![A-Za-z0-9+#.]){re.escape(item_lower)}(?![A-Za-z0-9+#.])', term):
                            is_covered = True
                            break
            if is_covered:
                continue

            formatted = item_clean.title() if item_clean.islower() else item_clean
            if formatted.lower() not in existing_lower:
                existing_lower.add(formatted.lower())
                skills_list.append(formatted)
                added_items.append(formatted)

    if added_items and isinstance(skills_details, dict):
        for sk in added_items:
            entry = {
                "canonical_skill": sk,
                "raw_mention": sk,
                "skill_type": "Hard Skill",
                "domain_category": "Listed Skills Section",
                "source_section": "Skills",
                "extraction_method": "Gazetteer_Exact",
                "confidence_score": 0.90,
            }
            skills_details.setdefault("extracted_skills", []).append(entry)
            skills_details.setdefault("skills", []).append({
                **entry,
                "skill_name": sk,
                "category": "Hard Skill",
            })
            cat_view = skills_details.setdefault("categorized_view", {})
            cat_view.setdefault("hard_skills", []).append(sk)

        total = len(skills_details.get("extracted_skills", []))
        skills_details["total_unique_skills"] = total
        skills_details["total_skills_count"] = total
        if isinstance(skills_details.get("skill_summary_by_type"), dict):
            skills_details["skill_summary_by_type"]["hard_skills_count"] = (
                skills_details["skill_summary_by_type"].get("hard_skills_count", 0) + len(added_items)
            )
        if isinstance(skills_details.get("summary_by_category"), dict):
            skills_details["summary_by_category"]["hard_skills"] = (
                skills_details["summary_by_category"].get("hard_skills", 0) + len(added_items)
            )

    return skills_list


def assess_resume_completeness(data: dict, sections: Optional[dict] = None, raw_text: Optional[str] = None) -> dict:
    """
    Evaluates whether the resume contains all essential core sections:
      1. Personal & Contact Information (Candidate Name + Email or Phone)
      2. Work Experience (Prior employment, roles, or relevant history)
      3. Education (Academic degrees, vocational courses, or schooling)
      4. Skills (Technical, soft, or functional competencies)

    If any core section is missing (TC-RES-013 / REQ006):
      - Marks is_incomplete = True, is_complete = False, completeness_status = "Incomplete"
      - Enforces that missing section fields remain cleanly empty (no bleeding or hallucinated placeholders)
      - Records missing section names in `missing_sections` (e.g. ["Work Experience"])
      - Records granular missing fields in `missing_fields`
      - Calculates a completeness_score (0.0 - 100.0)
    """
    missing_sections: list[str] = []
    missing_fields: list[str] = []
    notes: list[str] = []

    # ── 1. Personal & Contact Information Assessment ─────────────────────────
    fullname = (data.get("fullname") or data.get("name") or data.get("candidate_name") or "").strip()
    email = (data.get("email") or data.get("candidate_email") or "").strip()
    phone = (data.get("phone") or data.get("candidate_phone") or "").strip()

    has_name = bool(fullname and len(fullname) >= 3)
    has_contact = bool(email or phone)
    has_personal = has_name and has_contact

    if not has_personal:
        missing_sections.append("Contact Information" if has_name else "Personal Information")
        if not has_name:
            missing_fields.append("fullname")
            notes.append("Missing candidate name")
        if not email:
            missing_fields.append("email")
            notes.append("Missing contact email")
        if not phone:
            missing_fields.append("phone")
            notes.append("Missing contact phone number")

    # ── 2. Work Experience Assessment ─────────────────────────────────────────
    work_exps = data.get("work_experiences") or []
    exp_details = data.get("experience_details") or []
    job_title = (data.get("job_title") or "").strip()
    company = (data.get("company") or "").strip()
    exp_section = sections.get("EXPERIENCE", "").strip() if sections else ""

    # Check for empty / placeholder sections like "N/A", "None", "Fresh Graduate with no experience"
    placeholder_exp = bool(re.search(r'^(?:none|n/?a|not\s+applicable|no\s+experience|fresh\s+graduate\s+with\s+no\s+work\s+experience)$', exp_section, re.I))
    has_other_headers_for_exp = bool(sections and any(k in sections for k in ("EDUCATION", "SKILLS", "CERTIFICATIONS")))
    if has_other_headers_for_exp and not exp_section:
        has_work_experience = False
    else:
        has_work_experience = (
            bool(work_exps or exp_details or (job_title and company))
            and not placeholder_exp
            and (bool(work_exps) or bool(exp_details) or (bool(exp_section) and len(exp_section) > 15))
        )

    if not has_work_experience:
        missing_sections.append("Work Experience")
        missing_fields.extend(["work_experiences", "job_title", "company", "experience"])
        notes.append("Missing Work Experience section: no prior employment or work history entries found.")
        # Ensure missing section fields are cleanly empty
        data["work_experiences"] = []
        data["experience_details"] = []
        data["job_title"] = ""
        data["company"] = ""
        data["experience"] = ""
        data["years_experience"] = 0
        data["total_experience_months"] = 0
        data["relevance"] = ""

    # ── 3. Education Assessment ───────────────────────────────────────────────
    edu_entries = data.get("education_entries") or []
    edu_details = data.get("education_details") or []
    degree = (data.get("degree") or data.get("candidate_degree") or "").strip()
    institution = (data.get("institution") or data.get("college") or "").strip()
    education_str = (data.get("education") or "").strip()
    edu_section = sections.get("EDUCATION", "").strip() if sections else ""

    placeholder_edu = bool(re.search(r'^(?:none|n/?a|not\s+applicable)$', edu_section, re.I))
    has_other_headers_for_edu = bool(sections and any(k in sections for k in ("EXPERIENCE", "SKILLS", "CERTIFICATIONS")))
    if has_other_headers_for_edu and not edu_section:
        has_education = False
    else:
        has_education = (
            bool(edu_entries or edu_details or degree or institution or education_str)
            and not placeholder_edu
            and (bool(edu_entries) or bool(edu_details) or (bool(edu_section) and len(edu_section) > 10) or bool(degree and institution))
        )

    if not has_education:
        missing_sections.append("Education")
        missing_fields.extend(["education_entries", "degree", "institution", "education"])
        notes.append("Missing Education section: no academic qualifications or schooling records found.")
        # Ensure missing section fields are cleanly empty
        data["education_entries"] = []
        data["education_details"] = []
        data["degree"] = ""
        data["highest_degree"] = ""
        data["institution"] = ""
        data["college"] = ""
        data["education"] = ""
        data["highest_educational_attainment"] = ""

    # ── 4. Skills Assessment ──────────────────────────────────────────────────
    skills_list = data.get("skills_list") or []
    skills_str = (data.get("skills") or "").strip()
    skills_details = data.get("skills_details") or {}
    skills_section_present = bool(sections and "SKILLS" in sections)
    skills_section = sections.get("SKILLS", "").strip() if sections else ""
    has_extracted_skills = bool(skills_list or (skills_str and len(skills_str) > 2))

    placeholder_skills = bool(re.search(r'^(?:none|n/?a|not\s+applicable)\.?$', skills_section, re.I))
    has_other_headers_for_skills = bool(sections and any(k in sections for k in ("EXPERIENCE", "EDUCATION", "CERTIFICATIONS")))

    if placeholder_skills:
        has_skills = False
    elif skills_section:
        has_skills = has_extracted_skills or len(re.sub(r'[^a-zA-Z0-9]', '', skills_section)) >= 2
    elif has_other_headers_for_skills:
        extracted_items = skills_details.get("extracted_skills", []) if isinstance(skills_details, dict) else []
        from_skills_sec = any(s.get("source_section") == "Skills" for s in extracted_items)
        non_exp_skills = [
            s for s in extracted_items
            if s.get("source_section") in ("Skills", "Summary", "Projects", "Languages", "General")
        ]
        full_text_for_check = raw_text or ("\n".join(sections.values()) if sections else "")
        has_explicit_skill_list = _has_explicit_skill_list(full_text_for_check, extracted_items)
        has_skills = has_extracted_skills and (
            skills_section_present
            or from_skills_sec
            or len(non_exp_skills) >= 2
            or has_explicit_skill_list
        )
    else:
        has_skills = has_extracted_skills

    if not has_skills:
        missing_sections.append("Skills")
        missing_fields.extend(["skills_list", "skills"])
        notes.append("Missing Skills section: no skills or competencies identified.")
        # Ensure missing section fields are cleanly empty
        data["skills_list"] = []
        data["skills"] = ""
        data["skills_details"] = {}
        data["skills_array"] = []

    # ── Completeness calculation ──────────────────────────────────────────────
    core_flags = {
        "personal_info": has_personal,
        "work_experience": has_work_experience,
        "education": has_education,
        "skills": has_skills,
    }

    total_core = len(core_flags)
    present_core = sum(1 for v in core_flags.values() if v)
    completeness_score = round((present_core / float(total_core)) * 100.0, 1)

    is_incomplete = len(missing_sections) > 0
    is_complete = not is_incomplete
    completeness_status = "Incomplete" if is_incomplete else "Complete"

    data["is_incomplete"] = is_incomplete
    data["is_complete"] = is_complete
    data["completeness_status"] = completeness_status
    data["missing_sections"] = missing_sections
    data["missing_fields"] = list(dict.fromkeys(missing_fields))
    data["completeness_flags"] = core_flags
    data["completeness_score"] = completeness_score
    data["completeness_notes"] = notes

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
    from ..file.file_extractor import clean_raw_text
    text = clean_raw_text(text)
    sections = split_into_sections(text)

    # Structured entries
    structured_exp = extract_structured_experience(text)
    work_experiences = structured_exp.get("work_experiences", [])
    total_experience_months = structured_exp.get("total_experience_months", 0)
    exp_entries = extract_experience_entries(text)

    structured_edu = extract_structured_education(text)
    education_entries = structured_edu.get("education_entries", [])
    highest_educational_attainment = structured_edu.get("highest_educational_attainment", "Unknown")
    edu_entries = extract_education_entries(text)

    # Core extractions
    fullname = extract_fullname(text)
    all_names = extract_all_name_candidates(text)
    email = extract_email(text, candidate_name=fullname)
    all_emails = extract_all_emails(text, candidate_name=fullname)
    phone = extract_phone(text)
    all_phones = extract_all_phones(text)
    location_details = extract_applicant_address(text)
    if location_details.get("normalized_location") and location_details["normalized_location"] != "Philippines":
        location = location_details["normalized_location"]
    else:
        location = extract_location(text)

    job_title = extract_job_title(text, exp_entries)
    company = extract_company(text, exp_entries)
    experience_str = extract_experience(text)
    years_experience = extract_years_experience(text)

    skills_details = extract_structured_skills(text)
    skills_list = [s["canonical_skill"] for s in skills_details.get("extracted_skills", [])]
    if sections.get("SKILLS"):
        skills_list = _supplement_skills_from_section(sections["SKILLS"], skills_details, skills_list)
    skills_str = " | ".join(skills_list[:50]) if skills_list else ""

    relevance = extract_relevance(text, years_experience, job_title, skills_str)

    degree_title = extract_degree_title(text, edu_entries)
    highest_degree = extract_highest_degree(text)
    institution = extract_institution(text, edu_entries)
    education_str = extract_education(text)
    certifications_details = extract_structured_certifications(text)
    certifications_list = [c["canonical_name"] for c in certifications_details.get("certifications", [])]
    certifications_str = " | ".join(certifications_list[:25]) if certifications_list else extract_certifications(text)

    data = {
        # Personal Information
        "fullname": fullname,
        "names": all_names,
        "all_names": all_names,
        "email": email,
        "emails": all_emails,
        "all_emails": all_emails,
        "phone": phone,
        "phones": all_phones,
        "all_phones": all_phones,
        "location": location,
        "location_details": location_details,

        # Job & Experience Details
        "job_title": job_title,
        "company": company,
        "experience": experience_str,
        "experience_details": exp_entries,
        "work_experiences": work_experiences,
        "total_experience_months": total_experience_months,
        "years_experience": years_experience,
        "relevance": relevance,

        # Education Details
        "degree": degree_title,
        "highest_degree": highest_degree,
        "institution": institution,
        "college": institution,  # alias for frontend/DB compatibility
        "education": education_str,
        "education_details": edu_entries,
        "education_entries": education_entries,
        "highest_educational_attainment": highest_educational_attainment,

        # Skills & Certifications
        "skills": skills_str,
        "skills_list": skills_list,
        "skills_details": skills_details,
        "certifications": certifications_str,
        "certifications_list": certifications_list,
        "certifications_details": certifications_details,
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

    # Post-process for cleanliness and validation
    data = _post_process(data)

    # Assess completeness against core resume sections (TC-RES-013 / REQ006)
    data = assess_resume_completeness(data, sections, raw_text=text)

    # Generate summary from validated/finalized extracted data
    data["summary"] = _generate_summary(data).strip()

    return data


def format_resume_display(data: dict) -> str:
    """
    Renders an exhaustive, beautifully formatted text display of all resume data
    extracted by the newly engineered specialized extractors.
    """
    lines = []
    bar = "=" * 80

    lines.append(bar)
    lines.append("                  PHILIPPINE RESUME CONTENT EXTRACTION REPORT")
    lines.append(bar)

    # 1. Personal & Contact Information
    lines.append("\n[1. PERSONAL & CONTACT INFORMATION]")
    lines.append(f"  • Full Name:       {data.get('fullname') or 'Not detected'}")
    if data.get("names") and len(data["names"]) > 1:
        alt_names = [n for n in data["names"] if n != data.get("fullname")]
        if alt_names:
            lines.append(f"  • Alternate Names: {', '.join(alt_names)}")
    lines.append(f"  • Primary Email:   {data.get('email') or 'Not detected'}")
    if data.get("emails") and len(data["emails"]) > 1:
        alt_emails = [e for e in data["emails"] if e != data.get("email")]
        if alt_emails:
            lines.append(f"  • Alternate Emails:{', '.join(alt_emails)}")
    lines.append(f"  • Primary Phone:   {data.get('phone') or 'Not detected'}")
    if data.get("phones") and len(data["phones"]) > 1:
        alt_phones = [p for p in data["phones"] if p != data.get("phone")]
        if alt_phones:
            lines.append(f"  • Alternate Phones:{', '.join(alt_phones)}")

    loc_det = data.get("location_details", {})
    lines.append(f"  • Primary Location:{data.get('location') or 'Not detected'}")
    if isinstance(loc_det, dict) and loc_det.get("city_or_municipality"):
        details_str = f"City: {loc_det.get('city_or_municipality')}"
        if loc_det.get("barangay"):
            details_str += f" | Brgy: {loc_det.get('barangay')}"
        if loc_det.get("province"):
            details_str += f" | Province: {loc_det.get('province')}"
        if loc_det.get("region"):
            details_str += f" | Region: {loc_det.get('region')}"
        lines.append(f"  • Location Detail: {details_str}")

    # 2. Professional Experience
    lines.append("\n[2. WORK EXPERIENCE & CAREER HISTORY]")
    lines.append(f"  • Target / Role:   {data.get('job_title') or 'Not detected'}")
    lines.append(f"  • Employer:        {data.get('company') or 'Not detected'}")
    lines.append(f"  • Experience:      {data.get('years_experience', 0)} years ({data.get('total_experience_months', 0)} months)")

    work_exps = data.get("work_experiences", [])
    if work_exps:
        lines.append("  • Granular Positions:")
        for idx, exp in enumerate(work_exps, 1):
            role = exp.get("job_title") or exp.get("role") or "Role not specified"
            comp = exp.get("company_name") or exp.get("company") or "Company not specified"
            loc = f" ({exp.get('location')})" if exp.get("location") else ""
            dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}".strip(" -")
            dur = f" ({exp.get('duration_months')} mos)" if exp.get("duration_months") else ""
            emp_type = f" [{exp.get('employment_type')}]" if exp.get("employment_type") else ""
            lines.append(f"    {idx}. {role} at {comp}{loc}{emp_type}")
            if dates:
                lines.append(f"       Period: {dates}{dur}")
            resps = exp.get("responsibilities") or exp.get("highlights") or []
            if resps:
                for h in resps[:2]:
                    lines.append(f"       - {h}")
    elif data.get("experience"):
        lines.append(f"  • Summary of Roles: {data.get('experience')}")

    # 3. Educational Attainment
    lines.append("\n[3. EDUCATIONAL BACKGROUND]")
    lines.append(f"  • Attainment Level:{data.get('highest_educational_attainment') or data.get('highest_degree') or 'Not detected'}")
    lines.append(f"  • Degree / Program:{data.get('degree') or 'Not detected'}")
    lines.append(f"  • Institution:     {data.get('institution') or data.get('college') or 'Not detected'}")

    edu_entries = data.get("education_entries", [])
    if edu_entries:
        lines.append("  • Granular Education History:")
        for idx, edu in enumerate(edu_entries, 1):
            deg = edu.get("degree_or_course") or edu.get("degree") or "Program not specified"
            inst = edu.get("institution_name") or edu.get("institution") or "School not specified"
            yr_val = edu.get("year") or f"{edu.get('start_year', '')} - {edu.get('end_year', '')}".strip(" -")
            yr = f" ({yr_val})" if yr_val else ""
            honors_val = edu.get("honors") or (", ".join(edu.get("honors_and_awards", [])) if edu.get("honors_and_awards") else "")
            hon = f" - Honors: {honors_val}" if honors_val else ""
            lines.append(f"    {idx}. {deg} — {inst}{yr}{hon}")

    # 4. Skills Inventory
    lines.append("\n[4. SKILLS & COMPETENCIES INVENTORY]")
    skills_det = data.get("skills_details", {})
    if isinstance(skills_det, dict) and skills_det.get("summary_by_category"):
        lines.append(f"  • Total Verified Skills: {skills_det.get('total_skills_count', 0)}")
        cat_summary = skills_det.get("summary_by_category", {})
        cat_view = skills_det.get("categorized_view", {})
        for cat_k, cat_v in cat_summary.items():
            cat_skills = cat_view.get(cat_k)
            if not cat_skills and cat_k == "certifications_and_licenses":
                cat_skills = cat_view.get("certifications_and_eligibility", [])
            if not cat_skills:
                cat_skills = [
                    s.get("canonical_skill") or s.get("skill_name")
                    for s in skills_det.get("skills", [])
                    if cat_k in s.get("category", "").lower().replace(" ", "_")
                ]

            label = cat_k.replace("_", " ").title()
            skill_sample = ", ".join(cat_skills[:8]) if cat_skills else "None detected"
            lines.append(f"    - {label:<24} ({cat_v} items): {skill_sample}")
    elif data.get("skills_list"):
        lines.append(f"  • Extracted Skills ({len(data['skills_list'])} items): {', '.join(data['skills_list'][:15])}")
    elif data.get("skills"):
        lines.append(f"  • Extracted Skills: {data.get('skills')}")

    # 5. Certifications & Licenses
    lines.append("\n[5. LICENSES, ELIGIBILITY & CERTIFICATIONS]")
    certs_det = data.get("certifications_details", {})
    if isinstance(certs_det, dict) and certs_det.get("certifications"):
        lines.append(f"  • Total Credentials:   {certs_det.get('total_certifications_count', len(certs_det['certifications']))}")
        for idx, c in enumerate(certs_det["certifications"], 1):
            c_name = c.get("canonical_name")
            cat = c.get("category")
            iss = c.get("issuing_organization")
            status = f" | Status: {c.get('expiration_or_status')}" if c.get("expiration_or_status") else ""
            dt = f" | Date: {c.get('issue_date')}" if c.get("issue_date") else ""
            details = f" | Details: {c.get('credential_id_or_details')}" if c.get("credential_id_or_details") else ""
            method = f" [{c.get('extraction_method')}]" if c.get("extraction_method") else ""
            lines.append(f"    {idx}. [{cat}] {c_name}{method}")
            lines.append(f"       Issuer: {iss}{status}{dt}{details}")
    elif data.get("certifications_list"):
        lines.append(f"  • Credentials ({len(data['certifications_list'])} items): {', '.join(data['certifications_list'])}")
    elif data.get("certifications"):
        lines.append(f"  • Credentials: {data.get('certifications')}")

    # 6. Executive Summary
    lines.append("\n[6. SYNTHESIZED EXECUTIVE SUMMARY]")
    lines.append(f"  {data.get('summary', 'No summary generated.')}")

    # 7. Completeness Assessment
    lines.append("\n[7. COMPLETENESS ASSESSMENT]")
    lines.append(f"  • Completeness Status: {data.get('completeness_status', 'Complete')}")
    lines.append(f"  • Completeness Score:  {data.get('completeness_score', 100.0)}%")
    lines.append(f"  • Flagged Incomplete:  {'Yes' if data.get('is_incomplete') else 'No'}")
    if data.get("missing_sections"):
        lines.append(f"  • Missing Sections:    {', '.join(data['missing_sections'])}")
    if data.get("missing_fields"):
        lines.append(f"  • Missing Fields:      {', '.join(data['missing_fields'])}")
    lines.append(bar)

    return "\n".join(lines)


def display_extracted_content(data: dict) -> None:
    """Prints the structured resume content display report to stdout."""
    print(format_resume_display(data))


if __name__ == "__main__":
    import json

    resume_1_engineering = """
Engr. Juanito Dela Cruz, RCE, RMP
Makati City, Metro Manila | 09171234567 | jdelacruz.ce@gmail.com

PROFESSIONAL EXPERIENCE
Project Civil Engineer
Megawide Construction Corp. - Makati City
March 2021 - Present
- Supervised reinforced concrete foundation works and structural compliance
- Reviewed structural drawings and architectural plans using AutoCAD and Revit

Site Engineer
DMCI Holdings - Pasay City
June 2019 - February 2021
- Performed site inspections and material quantity surveying

EDUCATION
Bachelor of Science in Civil Engineering
University of the Philippines Diliman
2015 - 2019 | Cum Laude

LICENSES AND ELIGIBILITY
- PRC Registered Civil Engineer (Rating: 85.60%, PRC License No. 0154321)
- PRC Registered Master Plumber (Reg. No. 008921)
- Basic Occupational Safety and Health for SO2 (BOSH SO2) - DOLE-BWC Accredited (40 Hours, 2023)

TECHNICAL SKILLS
AutoCAD, Revit, STAAD.Pro, Structural Analysis, Quantity Surveying, Project Management, English, Tagalog
"""

    resume_2_blue_collar = """
ALEXANDER BAUTISTA
Calamba City, Laguna | 09171234567 | alex.bautista@gmail.com

WORK EXPERIENCE
Service Crew / Kitchen Staff
Jollibee Foods Corporation - Calamba Branch
January 2022 - Present
- Food preparation, counter service, inventory stocking, food safety

Housekeeping Attendant
Seda Hotel Nuvali - Santa Rosa, Laguna
June 2020 - December 2021
- Guest room cleaning, sanitation, linen maintenance

EDUCATION
Vocational / Technical Course in Hospitality Services
TESDA Calamba Training Center, 2020
High School Graduate - Calamba National High School, 2019

CERTIFICATIONS & LICENSES
- TESDA Food and Beverage Services NC II & Bread and Pastry Production NC II (Issued: June 2022)
- Housekeeping NC II - TESDA (Cert No. 22040102001, Issued: 2021)
- LTO Professional Driver's License (Restriction 1, 2, 3 / DL Code A, B) - Valid until 2028
- Standard First Aid and Basic Life Support (BLS) - Philippine Red Cross (24 Hours, 2023)

SKILLS
Customer Service, Food Preparation, Sanitation, Housekeeping, Cashiering, Safe Driving, Tagalog
"""

    resumes = [
        ("Candidate Profile 1: Civil Engineering & Construction Professional", resume_1_engineering),
        ("Candidate Profile 2: Blue-Collar & Service Worker (TESDA / Hospitality)", resume_2_blue_collar)
    ]

    for title, text in resumes:
        print(f"\nProcessing: {title}")
        extracted = extract_content(text)
        display_extracted_content(extracted)

