import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.extractors.nlp.nlp_engine import get_doc, extract_advanced_experience
from app.extractors.content.section_parser import split_into_sections


# ─── Section Headers ─────────────────────────────────────────────────────────

_EXPERIENCE_HEADERS = [
    "EXPERIENCE", "WORK HISTORY", "EMPLOYMENT", "PROFESSIONAL BACKGROUND",
    "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY",
    "RELEVANT EXPERIENCE", "EMPLOYMENT HISTORY", "JOB EXPERIENCE",
    "CAREER SUMMARY", "CAREER EXPERIENCE",
    "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
    "PROFESSIONAL HISTORY",
]

_STOP_HEADERS = [
    "EDUCATION", "SKILLS", "CERTIFICATIONS", "PROJECTS", "QUALIFICATIONS",
    "ACHIEVEMENTS", "AFFILIATIONS", "REFERENCES", "INTERESTS",
    "AWARDS", "PUBLICATIONS", "HOBBIES", "VOLUNTEER", "PERSONAL",
    "TRAINING", "SEMINARS", "ACTIVITIES", "TOOLS", "TECHNOLOGIES",
    "TECHNICAL SKILLS", "CORE COMPETENCIES", "LANGUAGES", "SUMMARY",
    "CONTACT", "CONTACT INFORMATION", "CONTACT DETAILS",
    "PERSONAL INFORMATION", "WORK PROJECTS",
]

# ─── Date Patterns ───────────────────────────────────────────────────────────

_MONTHS_RE = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
)
_YEAR_RE = r'(?:19|20)\d{2}'
_PRESENT_RE = r'(?:Present|Current|Now|To\s+Date|Ongoing|Today)'

_DATE_RANGE_PATTERNS = [
    # Month Year - Month Year / Present
    rf'({_MONTHS_RE}\s*\.?\s*{_YEAR_RE})\s*[-–—to]+\s*({_MONTHS_RE}\s*\.?\s*{_YEAR_RE}|{_PRESENT_RE})',
    # Year - Year / Present
    rf'({_YEAR_RE})\s*[-–—to]+\s*({_YEAR_RE}|{_PRESENT_RE})',
    # Month/Year - Month/Year (MM/YYYY)
    rf'(\d{{1,2}}/\d{{4}})\s*[-–—to]+\s*(\d{{1,2}}/\d{{4}}|{_PRESENT_RE})',
]

_ROLE_INDICATORS = [
    r'\b(?:Senior|Junior|Lead|Principal|Staff|Chief|Head|Associate|Assistant)\b',
    r'\b(?:Software|Web|Frontend|Backend|Full[\s-]?Stack|Mobile|Cloud|Data|DevOps|QA|UI/?UX)\b',
    r'\b(?:Engineer|Developer|Designer|Manager|Analyst|Specialist|Consultant|Director|'
    r'Administrator|Coordinator|Architect|Scientist|Intern|Trainee|Officer|Executive|'
    r'Supervisor|Technician|Programmer|Tester|Support|Accountant|Representative|Product\s+Manager|Project\s+Manager)\b',
    # Operations / Logistics / Manufacturing (Crucial for Mariwasa & standard PH applicants)
    r'\b(?:Rider|Delivery\s+Rider|Driver|Courier|Crew|Service\s+Crew|Cashier|Barista)\b',
    r'\b(?:Operator|Machine\s+Operator|Production\s+Operator|Line\s+Leader|Factory\s+Worker|Laborer)\b',
    r'\b(?:Warehouse\s+Staff|Warehouseman|Inventory\s+Clerk|Logistics\s+Assistant|Forklift\s+Operator)\b',
    r'\b(?:Quality\s+Control|Quality\s+Inspector|QC|Maintenance\s+Technician|Electrician|Mechanic)\b',
    # Administrative & Customer Service
    r'\b(?:CSR|Customer\s+Service\s+Representative|Call\s+Center\s+Agent|TSR|Technical\s+Support)\b',
    r'\b(?:Virtual\s+Assistant|Office\s+Staff|Administrative\s+Assistant|Office\s+Clerk|Data\s+Entry)\b',
    r'\b(?:Accounting\s+Staff|Bookkeeper|Sales\s+Associate|Sales\s+Representative|HR\s+Assistant)\b',
]

_BRAND_ROLE_RE = re.compile(
    r'^(Food\s*Panda|Foodpanda|Grab|Lalamove|Angkas|Shopee|Lazada|Jollibee|McDonald\'?s|SM|Puregold)\s+(.+)$',
    re.IGNORECASE
)


def _is_header_line(line: str, keywords: list[str]) -> bool:
    """Check if a line matches a section header."""
    clean = line.strip().upper()
    if not clean or len(clean.split()) >= 7:
        return False

    stripped = re.sub(r'^[\s\-–—=_*#•►:]+', '', clean)
    stripped = re.sub(r'[\s\-–—=_*#•►:]+$', '', stripped)

    for kw in keywords:
        if stripped == kw or stripped.startswith(kw + ":") or clean == kw:
            return True
    return False


def _has_date_range(line: str) -> bool:
    """Check if a line contains a date range."""
    for pattern in _DATE_RANGE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _has_role_indicator(line: str) -> bool:
    """Check if a line contains a job role keyword."""
    for pattern in _ROLE_INDICATORS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _clean_company_name(comp: str) -> str:
    """Clean company name by removing trailing locations and delimiters."""
    if not comp:
        return ""
    # Strip bullet or pipe
    parts = re.split(r'\s*[|•]\s*', comp)
    comp = parts[0].strip()
    # Strip trailing dash location
    if ' - ' in comp:
        cparts = comp.split(' - ')
        if len(cparts) == 2 and any(loc in cparts[1].lower() for loc in ['philippines', 'norway', 'manila', 'usa', 'remote']):
            comp = cparts[0].strip()
    if ',' in comp:
        cparts = comp.split(',')
        if len(cparts) == 2 and any(loc in cparts[1].lower() for loc in ['philippines', 'norway', 'manila', 'usa', 'remote', 'drøbak', 'bgc']):
            comp = cparts[0].strip()
    comp = re.sub(r'^(?:at|for|with)\s+', '', comp, flags=re.IGNORECASE).strip()
    return comp.strip(' ,-–—|•()')


def _is_valid_company_name(comp: str) -> bool:
    """Validate that candidate string is an actual company name and not noise."""
    if not comp or len(comp) < 2 or len(comp) > 60:
        return False
    lower = comp.lower().strip()
    if lower in {"present", "current", "ongoing", "none", "n/a", "contract", "full-time", "part-time"}:
        return False
    if lower.startswith(('•', '-', '*', 'responsibilit', 'dutie', 'assist', 'manag', 'handle', 'maintain', 'deliver')):
        return False
    return True


def _clean_description_line(desc: str) -> str:
    """Strip leading bullets, responsibility labels, and whitespace."""
    cleaned = desc.strip().lstrip('•-–—▪►✓* ').strip()
    cleaned = re.sub(r'^(?:Responsibilities|Duties|Key\s+Achievements|Key\s+Responsibilities|Tasks)\s*[:.\-]\s*', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _parse_entry_at(lines: list[str], start_idx: int) -> tuple[Optional[dict], int]:
    """
    Parse a structured role entry starting at start_idx across a 3-4 line window.
    Returns (entry_dict, lines_consumed).
    """
    line0 = lines[start_idx].strip()

    # Skip redundant duplicate titles or pure bullets
    if start_idx + 1 < len(lines):
        line1 = lines[start_idx + 1].strip()
        if _has_role_indicator(line0) and _has_role_indicator(line1):
            if start_idx + 2 < len(lines) and (_has_date_range(lines[start_idx + 2]) or '|' in lines[start_idx + 2]):
                return None, 1

    # Look at window of up to 4 lines
    window = lines[start_idx:min(start_idx + 4, len(lines))]

    date_idx = -1
    dates = ""
    for idx, w in enumerate(window):
        if _has_date_range(w):
            date_idx = idx
            for pattern in _DATE_RANGE_PATTERNS:
                m = re.search(pattern, w, re.IGNORECASE)
                if m:
                    dates = m.group(0).strip()
                    break
            break

    non_date_lines = [w.strip() for idx, w in enumerate(window) if idx != date_idx and not w.strip().startswith(('•', '-', '*'))]
    if not non_date_lines:
        return None, 1

    role = ""
    company = ""

    # Case 1: Brand + Role (e.g. Food Panda Delivery Rider)
    brand_m = _BRAND_ROLE_RE.match(non_date_lines[0])
    if brand_m:
        company = brand_m.group(1).title()
        role = brand_m.group(2).strip()
    # Case 2: Role at Company
    elif re.search(r'\s+at\s+', non_date_lines[0], re.IGNORECASE):
        parts = re.split(r'\s+at\s+', non_date_lines[0], flags=re.IGNORECASE, maxsplit=1)
        role = parts[0].strip()
        company = _clean_company_name(parts[1].strip())
    # Case 3: Line 0 has Role, Line 1 has Company
    elif _has_role_indicator(non_date_lines[0]):
        role = non_date_lines[0]
        if len(non_date_lines) > 1 and not _has_role_indicator(non_date_lines[1]):
            company = _clean_company_name(non_date_lines[1])
    # Case 4: Line 0 has Company, Line 1 has Role
    elif len(non_date_lines) > 1 and _has_role_indicator(non_date_lines[1]):
        company = _clean_company_name(non_date_lines[0])
        role = non_date_lines[1]
    else:
        role = non_date_lines[0]

    role = re.sub(r'^(?:Senior|Junior|Lead)\s*$', '', role).strip(' ,-–—|•()')
    if not role or len(role) < 3 or any(role.lower().startswith(p) for p in ["experienced", "passionate", "seeking", "dedicated"]):
        return None, 1

    # Lines consumed for header
    header_count = 1
    if date_idx != -1:
        header_count = max(header_count, date_idx + 1)
    if company and len(non_date_lines) > 1:
        header_count = max(header_count, 2)

    consumed = header_count

    # Collect descriptions
    descriptions = []
    desc_start = start_idx + consumed
    for j in range(desc_start, min(desc_start + 8, len(lines))):
        dl = lines[j].strip()
        if not dl:
            continue
        if _has_date_range(dl) or (_has_role_indicator(dl) and not dl.startswith(('•', '-', '*'))):
            break
        cleaned = _clean_description_line(dl)
        if cleaned and len(cleaned) > 8:
            descriptions.append(cleaned)
            consumed += 1

    return {
        "role": role.title() if role.isupper() else role,
        "company": company,
        "dates": dates,
        "descriptions": descriptions
    }, consumed


def extract_experience_entries(text: str) -> list[dict]:
    """
    Parses full structured experience entries from resume text.
    Returns list of dicts: [{"role": str, "company": str, "dates": str, "descriptions": list[str]}]
    """
    sections = split_into_sections(text)
    exp_text = sections.get("EXPERIENCE", "")

    lines = [l.strip() for l in exp_text.split('\n') if l.strip()] if exp_text else [l.strip() for l in text.split('\n') if l.strip()]
    entries = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line or _is_header_line(line, _EXPERIENCE_HEADERS + _STOP_HEADERS):
            i += 1
            continue

        if line.startswith(('•', '-', '–', '▪', '►', '✓', '*')) and not _has_date_range(line):
            i += 1
            continue

        entry, consumed = _parse_entry_at(lines, i)
        if entry and entry.get("role"):
            entries.append(entry)
            i += max(1, consumed)
        else:
            i += 1

    # ── Parse WORK PROJECTS / PROJECTS section for richer descriptions ─────────
    proj_text = sections.get("PROJECTS", "")
    if proj_text:
        project_entries = _parse_project_entries(proj_text)

        # Back-fill descriptions from projects into experience entries that lack them
        for entry in entries:
            if entry.get("descriptions"):
                continue  # Already has descriptions
            entry_role = entry.get("role", "").lower().strip()
            entry_company = entry.get("company", "").lower().strip()

            for proj in project_entries:
                proj_role = proj.get("role", "").lower().strip()
                proj_company = proj.get("company", "").lower().strip()
                # Match by role similarity or company mention in project name
                if (proj_role and entry_role and
                    (proj_role in entry_role or entry_role in proj_role or
                     _roles_similar(entry_role, proj_role))) or \
                   (proj_company and entry_company and
                    (proj_company in entry_company or entry_company in proj_company)):
                    entry["descriptions"] = proj.get("descriptions", [])
                    if proj.get("technologies"):
                        entry["technologies"] = proj["technologies"]
                    break

        # Add project roles not already in experience entries
        if len(entries) < 2:
            for proj in project_entries:
                proj_role = proj.get("role", "")
                if proj_role and not any(
                    e.get("role", "").lower().strip() == proj_role.lower().strip()
                    for e in entries
                ):
                    entries.append({
                        "role": proj_role,
                        "company": proj.get("company", ""),
                        "dates": "",
                        "descriptions": proj.get("descriptions", [])
                    })

    return entries


def _roles_similar(role1: str, role2: str) -> bool:
    """Check if two role strings are similar (e.g. 'full-stack web developer' vs 'full stack web developer')."""
    # Normalize
    r1 = re.sub(r'[\s\-]+', ' ', role1.lower()).strip()
    r2 = re.sub(r'[\s\-]+', ' ', role2.lower()).strip()
    if r1 == r2:
        return True
    # Check core words overlap
    words1 = set(r1.split())
    words2 = set(r2.split())
    common = words1 & words2
    # If at least 2 meaningful words match (e.g. "developer" + "web")
    meaningful = common - {"a", "an", "the", "of", "in", "at", "and", "or", "for"}
    return len(meaningful) >= 2


def _parse_project_entries(proj_text: str) -> list[dict]:
    """
    Parse WORK PROJECTS / PROJECTS section into structured entries.
    Each project typically has: name, description, Role:, Technologies: lines.
    """
    lines = [l.strip() for l in proj_text.split('\n')]
    projects = []
    current_project = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            continue

        # Check for Role: line
        role_match = re.match(r'^Role\s*:\s*(.+)', line, re.IGNORECASE)
        if role_match:
            if current_project is not None:
                current_project["role"] = role_match.group(1).strip()
            continue

        # Check for Technologies: line
        tech_match = re.match(r'^Technologies?\s*:\s*(.+)', line, re.IGNORECASE)
        if tech_match:
            if current_project is not None:
                current_project["technologies"] = tech_match.group(1).strip()
            continue

        # Check if this is a new project name (short, title-like, not a bullet point)
        is_bullet = line.startswith(('•', '-', '–', '▪', '►', '✓', '*'))
        is_short = len(line) < 60
        has_no_period = '.' not in line or line.endswith('.')

        if is_short and not is_bullet and not line.startswith(('Role', 'Technologies', 'Tech')):
            # Looks like a new project name
            if current_project is not None:
                projects.append(current_project)
            current_project = {
                "name": line,
                "company": line,
                "role": "",
                "descriptions": [],
                "technologies": ""
            }
        elif current_project is not None:
            # This is a description line
            desc = line.lstrip('•-–—▪►✓* ').strip()
            if desc and len(desc) > 10:
                current_project["descriptions"].append(desc)

    if current_project is not None:
        projects.append(current_project)

    return projects


def extract_job_title(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's primary/target job title from resume.
    1. Header inspection: title directly below the candidate's name.
    2. Most recent work experience entry role.
    3. Student / Objective target role.
    4. spaCy Matcher fallback.
    """
    if not text:
        return ""

    if entries is None:
        entries = extract_experience_entries(text)

    # Strategy 1: Header line right below candidate name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[1:6]:
        if len(line) > 60:
            continue
        if _has_role_indicator(line) and not re.search(r'@|\d{3,}|http', line):
            clean_title = re.sub(r'^[|•\-–—*#\s]+|[|•\-–—*#\s]+$', '', line).strip()
            if 3 < len(clean_title) < 50:
                return clean_title.title() if clean_title.isupper() else clean_title

    # Strategy 2: First entry's role
    if entries and entries[0].get("role"):
        role = entries[0]["role"]
        role = re.sub(r'^\d+\+?\s*years?\s+(?:of\s+)?(?:experience\s+)?(?:as\s+(?:a\s+|an\s+)?)?', '', role, flags=re.IGNORECASE).strip()
        if role and len(role) > 2:
            return role

    # Strategy 3: Check objective for student / career title
    obj_match = re.search(r'(?:seeking\s+an?\s+(?:opportunity\s+as\s+an?|internship\s+as\s+an?|position\s+as\s+an?)|hardworking|motivated)\s+([A-Za-z0-9\s]+?(?:Student|Graduate|Developer|Engineer|Technician|Rider|Associate))', text[:1200], re.I)
    if obj_match:
        obj_cand = obj_match.group(1).strip()
        if 3 < len(obj_cand) < 45:
            return obj_cand.title()

    # Strategy 4: spaCy matcher
    try:
        doc = get_doc(text[:1500])
        from app.extractors.nlp.nlp_engine import get_job_title_matcher
        matcher = get_job_title_matcher()
        matches = matcher(doc)
        if matches:
            match_id, start, end = matches[0]
            cand = doc[start:end].text.strip()
            if 3 < len(cand) < 50:
                return cand.title()
    except Exception:
        pass

    return ""


def extract_company(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's most recent company name.
    1. Most recent experience entry company.
    2. spaCy ORG entity in first experience entry with validation.
    """
    if entries is None:
        entries = extract_experience_entries(text)

    if entries:
        for e in entries:
            comp = e.get("company", "").strip()
            if _is_valid_company_name(comp):
                return comp

    # spaCy ORG entity fallback in experience section with strict validation
    try:
        sections = split_into_sections(text)
        exp_text = sections.get("EXPERIENCE", "")
        if exp_text:
            doc = get_doc(exp_text[:1000])
            for ent in doc.ents:
                clean_org = ent.text.strip().lstrip('•-–* ')
                if ent.label_ == "ORG" and _is_valid_company_name(clean_org):
                    return clean_org
    except Exception:
        pass

    return ""


def extract_relevance(text: str, years: int = 0, job_title: str = "", skills: str = "") -> str:
    """
    Generates a concise, informative relevance statement highlighting candidate qualifications.
    """
    parts = []
    if years and years > 0:
        if job_title:
            parts.append(f"{years}+ years of experience as {job_title}")
        else:
            parts.append(f"{years}+ years of professional experience")
    elif job_title:
        parts.append(f"Experienced {job_title}")

    # Top skills mention
    if skills:
        top_skills = [s.strip() for s in skills.split('|') if s.strip()][:3]
        if top_skills:
            parts.append(f"specializing in {', '.join(top_skills)}")

    if parts:
        return " ".join(parts)
    return "Professional career history with relevant industry experience"


def extract_experience(text: str) -> str:
    """
    Extracts work experience from resume text with structured parsing.
    Returns pipe-separated entries in format: "Role at Company (Dates) - Responsibilities: ..."
    """
    entries = extract_experience_entries(text)
    formatted_entries = []

    for entry in entries:
        role = entry.get("role", "").strip()
        if not role:
            continue
        company = entry.get("company", "").strip()
        dates = entry.get("dates", "").strip()
        descriptions = entry.get("descriptions", [])

        parts = [role]
        if company:
            parts.append(f"at {company}")
        if dates:
            parts.append(f"({dates})")
        if descriptions:
            parts.append("- Responsibilities: " + "; ".join(descriptions[:3]))

        formatted = " ".join(parts).strip()
        if formatted and formatted not in formatted_entries:
            formatted_entries.append(formatted)

    # spaCy-based fallback if no section entries parsed
    if not formatted_entries:
        try:
            doc = get_doc(text)
            nlp_entries = extract_advanced_experience(doc)
            for nlp_entry in nlp_entries:
                if nlp_entry and nlp_entry not in formatted_entries:
                    formatted_entries.append(nlp_entry)
        except Exception:
            pass

    return " | ".join(formatted_entries[:10]) if formatted_entries else ""


def extract_years_experience(text: str) -> int:
    """
    Calculates total years of experience by:
    1. Finding explicit mentions like "X years experience" (prioritized).
    2. Summing non-overlapping date ranges found in the EXPERIENCE section.
    """
    if not text:
        return 0

    # ── Strategy 1: Explicit mentions (e.g., "6+ years of experience") ────────
    explicit_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|exp|work|expertise)',
        r'(?:over|more\s+than|at\s+least)\s+(\d+)\s*years?',
        r'(\d+)\+?\s*years?\s+(?:in\s+(?:the\s+)?(?:industry|field|practice|IT|tech|software))',
        r'(\d+)\+?\s*years?\s+(?:as\s+(?:a\s+|an\s+)?)',
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional|related|relevant)\s+(?:experience|work)',
    ]
    explicit_years = 0
    for pattern in explicit_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for m in matches:
                try:
                    val = int(m)
                    if 0 < val < 50:
                        explicit_years = max(explicit_years, val)
                except ValueError:
                    continue

    # If explicit mention found, it is almost always the candidate's exact stated tenure!
    if explicit_years > 0:
        return explicit_years

    # ── Strategy 2: Calculate from date ranges ONLY in the EXPERIENCE section ─
    sections = split_into_sections(text)
    exp_text = sections.get("EXPERIENCE", "")

    # If no designated experience section, search lines that have role indicators
    search_text = exp_text if exp_text else text

    range_pattern = (
        rf'({_MONTHS_RE}\s*\.?\s*)?({_YEAR_RE})\s*[-–—to]+\s*'
        rf'(?:({_MONTHS_RE}\s*\.?\s*)?({_YEAR_RE})|({_PRESENT_RE}))'
    )
    ranges = re.findall(range_pattern, search_text, re.IGNORECASE)

    current_year = datetime.now().year
    current_month = datetime.now().month
    total_months = 0

    for start_m, start_y, end_m, end_y, present in ranges:
        try:
            s_y = int(start_y)
            s_m = _month_to_num(start_m) if start_m else 1

            if present:
                e_y = current_year
                e_m = current_month
            else:
                e_y = int(end_y)
                e_m = _month_to_num(end_m) if end_m else 12

            diff = (e_y - s_y) * 12 + (e_m - s_m)
            if 0 < diff < 600:
                total_months += diff
        except (ValueError, TypeError):
            continue

    calculated_years = round(total_months / 12) if total_months > 0 else 0
    return min(calculated_years, 50)


def _month_to_num(month_str: str) -> int:
    """Convert month name to 1-indexed number."""
    if not month_str:
        return 1
    m = month_str.strip().lower().rstrip('.')
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    return month_map.get(m, 1)