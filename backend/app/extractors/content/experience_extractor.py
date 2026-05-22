import re
from datetime import datetime


# ─── Section Headers ─────────────────────────────────────────────────────────

_EXPERIENCE_HEADERS = [
    "EXPERIENCE", "WORK HISTORY", "EMPLOYMENT", "PROFESSIONAL BACKGROUND",
    "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY",
    "RELEVANT EXPERIENCE", "EMPLOYMENT HISTORY", "JOB EXPERIENCE",
    "CAREER SUMMARY", "PROFESSIONAL SUMMARY", "CAREER EXPERIENCE",
    "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
]

_STOP_HEADERS = [
    "EDUCATION", "SKILLS", "CERTIFICATIONS", "PROJECTS", "QUALIFICATIONS",
    "ACHIEVEMENTS", "AFFILIATIONS", "REFERENCES", "INTERESTS",
    "AWARDS", "PUBLICATIONS", "HOBBIES", "VOLUNTEER", "PERSONAL",
    "TRAINING", "SEMINARS", "ACTIVITIES", "TOOLS", "TECHNOLOGIES",
    "TECHNICAL SKILLS", "CORE COMPETENCIES", "LANGUAGES",
]

# ─── Date Patterns ───────────────────────────────────────────────────────────

_MONTHS_RE = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
)
_YEAR_RE = r'(?:19|20)\d{2}'
_PRESENT_RE = r'(?:Present|Current|Now|To\s+Date|Ongoing|Today)'

# Full date range patterns
_DATE_RANGE_PATTERNS = [
    # Month Year - Month Year / Present
    rf'({_MONTHS_RE}\s*\.?\s*{_YEAR_RE})\s*[-–—to]+\s*({_MONTHS_RE}\s*\.?\s*{_YEAR_RE}|{_PRESENT_RE})',
    # Year - Year / Present
    rf'({_YEAR_RE})\s*[-–—to]+\s*({_YEAR_RE}|{_PRESENT_RE})',
    # Month/Year - Month/Year (MM/YYYY)
    rf'(\d{{1,2}}/\d{{4}})\s*[-–—to]+\s*(\d{{1,2}}/\d{{4}}|{_PRESENT_RE})',
]

# Common job title keywords that help identify experience entries
_ROLE_INDICATORS = [
    r'(?:Senior|Junior|Lead|Principal|Staff|Chief|Head|Associate|Assistant)\s+',
    r'(?:Software|Web|Frontend|Backend|Full[\s-]?Stack|Mobile|Cloud|Data|DevOps|QA|UI/?UX)\s+',
    r'(?:Engineer|Developer|Designer|Manager|Analyst|Specialist|Consultant|Director|'
    r'Administrator|Coordinator|Architect|Scientist|Intern|Trainee|Officer|Executive|'
    r'Supervisor|Technician|Programmer|Tester|Support)',
]


def _is_header_line(line: str, keywords: list[str]) -> bool:
    """Check if a line matches a section header."""
    clean = line.strip().upper()
    if not clean or len(clean.split()) >= 6:
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


def _extract_role_entry(lines: list[str], start_idx: int) -> dict:
    """
    Attempt to extract a structured role entry starting at given index.
    Returns a dict with role, company, dates, and description.
    """
    role = ""
    company = ""
    dates = ""
    descriptions = []

    line = lines[start_idx].strip()

    # Try to extract dates from this line
    date_match = None
    for pattern in _DATE_RANGE_PATTERNS:
        date_match = re.search(pattern, line, re.IGNORECASE)
        if date_match:
            dates = date_match.group(0).strip()
            # Remove the date from the line to get role/company
            line = line[:date_match.start()].strip().rstrip('|,–—-').strip()
            break

    # Try to split "Role at Company" or "Role - Company" or "Role, Company"
    separators = [r'\s+at\s+', r'\s*[–—]\s*', r'\s*\|\s*', r'\s*,\s+(?=[A-Z])']
    split = False
    for sep in separators:
        parts = re.split(sep, line, maxsplit=1)
        if len(parts) == 2 and len(parts[0]) > 2 and len(parts[1]) > 2:
            role = parts[0].strip()
            company = parts[1].strip()
            split = True
            break

    if not split:
        # Check next line for company name
        if _has_role_indicator(line):
            role = line
            if start_idx + 1 < len(lines):
                next_line = lines[start_idx + 1].strip()
                if next_line and not _has_date_range(next_line) and len(next_line) < 80:
                    if not _is_header_line(next_line, _STOP_HEADERS + _EXPERIENCE_HEADERS):
                        company = next_line
        else:
            role = line

    # Collect description bullets (up to 5 lines)
    for j in range(start_idx + 1, min(start_idx + 8, len(lines))):
        desc_line = lines[j].strip()
        if not desc_line:
            continue
        if _has_date_range(desc_line) and _has_role_indicator(desc_line):
            break  # Next role entry
        if _is_header_line(desc_line, _STOP_HEADERS):
            break
        # Skip if it's the company we already captured
        if desc_line == company:
            continue
        # Description lines are typically longer or start with bullets
        if len(desc_line) > 20 or desc_line.startswith(('•', '-', '–', '▪', '►', '✓', '*')):
            descriptions.append(desc_line.lstrip('•-–▪►✓* ').strip())
            if len(descriptions) >= 4:
                break

    return {
        "role": role,
        "company": company,
        "dates": dates,
        "descriptions": descriptions,
    }


def extract_experience(text: str) -> str:
    """
    Extracts work experience from resume text with structured parsing.
    
    Returns pipe-separated entries in format: "Role at Company (Dates)"
    Each entry is a single line of a job held.
    """
    lines = text.split('\n')
    found_section = False
    section_start = -1
    section_lines = []

    # ── Step 1: Find the experience section ───────────────────────────────────
    for i, line in enumerate(lines):
        clean_line = line.strip()
        if not clean_line:
            continue

        if _is_header_line(clean_line, _EXPERIENCE_HEADERS):
            found_section = True
            section_start = i + 1
            continue

        if found_section:
            if _is_header_line(clean_line, _STOP_HEADERS):
                break
            section_lines.append(clean_line)

    # ── Step 2: Parse structured entries from the section ─────────────────────
    entries = []

    if section_lines:
        i = 0
        while i < len(section_lines):
            line = section_lines[i]

            # Look for lines that indicate a new role entry
            is_entry = _has_date_range(line) or _has_role_indicator(line)

            if is_entry:
                entry = _extract_role_entry(section_lines, i)
                if entry["role"]:
                    formatted = entry["role"]
                    if entry["company"]:
                        formatted += f" at {entry['company']}"
                    if entry["dates"]:
                        formatted += f" ({entry['dates']})"
                    entries.append(formatted)
            i += 1
    
    # ── Step 3: Fallback — scan full document for date-range lines ────────────
    if not entries:
        for i, line in enumerate(lines):
            clean = line.strip()
            if not clean:
                continue
            if _has_date_range(clean):
                # Check if this or adjacent line has a role indicator
                context = clean
                if i > 0:
                    context = lines[i-1].strip() + " " + context
                if i + 1 < len(lines):
                    context += " " + lines[i+1].strip()

                if _has_role_indicator(context) or len(clean) > 15:
                    entries.append(clean)
                    if len(entries) >= 10:
                        break

    # Deduplicate while preserving order
    seen = set()
    unique_entries = []
    for entry in entries:
        key = entry.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    return " | ".join(unique_entries[:12]) if unique_entries else ""


def extract_years_experience(text: str) -> int:
    """
    Calculates total years of experience by:
    1. Finding explicit mentions like "X years experience"
    2. Summing date ranges found in the resume
    3. Returns the higher of the two values
    """
    if not text:
        return 0

    # ── Explicit mentions ─────────────────────────────────────────────────────
    explicit_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|exp|work)',
        r'(?:over|more\s+than|at\s+least)\s+(\d+)\s*years?',
        r'(\d+)\+?\s*years?\s+(?:in\s+(?:the\s+)?(?:industry|field|practice|IT|tech))',
    ]
    explicit_years = 0
    for pattern in explicit_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for m in matches:
                try:
                    val = int(m)
                    if val < 50:  # sanity check
                        explicit_years = max(explicit_years, val)
                except ValueError:
                    continue

    # ── Calculate from date ranges ────────────────────────────────────────────
    range_pattern = (
        rf'({_MONTHS_RE}\s*\.?\s*)?({_YEAR_RE})\s*[-–—to]+\s*'
        rf'(?:({_MONTHS_RE}\s*\.?\s*)?({_YEAR_RE})|({_PRESENT_RE}))'
    )
    ranges = re.findall(range_pattern, text, re.IGNORECASE)

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
            if 0 < diff < 600:  # sanity: max 50 years
                total_months += diff
        except (ValueError, TypeError):
            continue

    calculated_years = round(total_months / 12) if total_months > 0 else 0

    return max(explicit_years, calculated_years)


def _month_to_num(month_str: str) -> int:
    """Convert a month string to a number."""
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
    for key, val in month_map.items():
        if key in m:
            return val
    return 1