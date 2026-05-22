import re

# ─── Section Headers ─────────────────────────────────────────────────────────

_EDUCATION_HEADERS = [
    "EDUCATION", "ACADEMIC", "QUALIFICATIONS", "SCHOLASTIC",
    "EDUCATIONAL ATTAINMENT", "EDUCATIONAL BACKGROUND", "ACADEMIC BACKGROUND",
    "STUDIES", "SCHOOLING", "ACADEMIC QUALIFICATIONS", "ACADEMIC RECORD",
    "EDUCATIONAL HISTORY", "ACADEMIC HISTORY", "DEGREES",
]

_STOP_HEADERS = [
    "EXPERIENCE", "SKILLS", "CERTIFICATIONS", "PROJECTS", "WORK",
    "EMPLOYMENT", "TRAININGS", "SEMINARS", "AFFILIATIONS", "REFERENCES",
    "ACHIEVEMENTS", "AWARDS", "INTERESTS", "HOBBIES", "VOLUNTEER",
    "TOOLS", "TECHNOLOGIES", "TECHNICAL SKILLS", "CORE COMPETENCIES",
    "PUBLICATIONS", "LANGUAGES", "PERSONAL", "ACTIVITIES",
]

# ─── Degree Patterns (ordered highest to lowest) ─────────────────────────────

_DEGREE_HIERARCHY = [
    ("DOCTORATE", [
        r"PH\.?D\.?", r"DOCTORATE", r"DOCTOR\s+OF", r"JURIS\s+DOCTOR",
        r"DOCTOR\s+OF\s+MEDICINE", r"\bMD\b", r"\bJ\.?D\.?\b",
        r"ED\.?D\.?", r"DOCTOR\s+OF\s+PHILOSOPHY",
    ]),
    ("MASTER", [
        r"MASTER(?:'?S)?", r"\bMSC?\b", r"M\.SC\.?", r"\bMA\b", r"M\.A\.?",
        r"\bMBA\b", r"M\.B\.A\.?", r"\bMPA\b", r"M\.P\.A\.?",
        r"\bMENG\b", r"M\.ENG\.?", r"\bMED\b", r"M\.ED\.?",
        r"GRADUATE\s+STUDIES", r"GRADUATE\s+DEGREE", r"\bMFIN\b",
        r"\bMIT\b(?=\s)", r"MASTER\s+IN", r"\bMIS\b",
    ]),
    ("BACHELOR", [
        r"BACHELOR(?:'?S)?", r"\bBSC?\b", r"B\.SC\.?", r"\bBA\b", r"B\.A\.?",
        r"\bAB\b", r"A\.B\.?", r"\bBSE\b", r"B\.S\.E\.?", r"\bBFA\b",
        r"\bBBM\b", r"\bBBA\b", r"B\.B\.A\.?", r"\bBCOM\b", r"B\.COM\.?",
        r"\bBENG\b", r"B\.ENG\.?", r"\bBIT\b", r"B\.I\.T\.?",
        r"\bBSIT\b", r"\bBSCS\b", r"\bBSCE\b", r"\bBSN\b",
        r"BACHELOR\s+OF", r"UNDERGRADUATE\s+DEGREE",
    ]),
    ("ASSOCIATE", [
        r"ASSOCIATE(?:'?S)?", r"\bAS\b(?=\s+(?:IN|OF))", r"A\.S\.?",
        r"\bAA\b(?=\s+(?:IN|OF))", r"A\.A\.?",
        r"2[\s-]?YEAR\s+DEGREE",
    ]),
    ("DIPLOMA/VOCATIONAL", [
        r"DIPLOMA", r"VOCATIONAL", r"\bTESDA\b",
        r"\bNC\s?I\b", r"\bNC\s?II\b", r"\bNC\s?III\b", r"\bNC\s?IV\b",
        r"NATIONAL\s+CERTIFICATE", r"CERTIFICATE\s+(?:IN|OF)\s+\w+",
        r"TECHNICAL\s+EDUCATION",
    ]),
    ("SENIOR HIGH SCHOOL", [
        r"SENIOR\s+HIGH", r"S\.?H\.?S\.?", r"\bSHS\b",
        r"K[\s-]?12", r"GRADE\s+12", r"12TH\s+GRADE",
    ]),
]

# University / Institution indicators
_INSTITUTION_PATTERNS = [
    r"University", r"College", r"Institute", r"Polytechnic", r"School",
    r"Academy", r"Lyceum", r"Lycée",
    # Philippine universities
    r"\bUP\s", r"\bPUP\b", r"\bUST\b", r"\bDLSU\b", r"\bADMU\b",
    r"\bFEU\b", r"\bUE\b", r"\bNU\b", r"\bAUF\b", r"\bTIP\b",
    r"\bMAPUA\b", r"\bATENEO\b", r"\bLA\s+SALLE\b", r"\bSAN\s+BEDA\b",
    r"\bSILLIMAN\b", r"\bADAMSON\b", r"\bLETRAN\b",
    r"\bSTO\.?\s+TOMAS\b", r"\bSANTO\s+TOMAS\b",
    # International
    r"\bMIT\b", r"\bSTANFORD\b", r"\bHARVARD\b", r"\bOXFORD\b",
    r"\bCAMBRIDGE\b", r"\bYALE\b", r"\bPRINCETON\b",
]


def _is_header(line: str, keywords: list[str]) -> bool:
    """Check if a line is a section header."""
    clean = line.strip().upper()
    if not clean or len(clean.split()) >= 6:
        return False
    stripped = re.sub(r'^[\s\-–—=_*#•►:]+', '', clean)
    stripped = re.sub(r'[\s\-–—=_*#•►:]+$', '', stripped)
    for kw in keywords:
        if stripped == kw or stripped.startswith(kw + ":") or clean == kw:
            return True
    return False


def _has_degree_mention(line: str) -> bool:
    """Check if a line contains a degree mention."""
    for _, patterns in _DEGREE_HIERARCHY:
        for p in patterns:
            if re.search(r'\b' + p, line, re.IGNORECASE):
                return True
    return False


def _has_institution_mention(line: str) -> bool:
    """Check if a line mentions an educational institution."""
    for p in _INSTITUTION_PATTERNS:
        if re.search(p, line, re.IGNORECASE):
            return True
    return False


def extract_education(text: str) -> str:
    """
    Extracts education details from resume text.
    
    Returns pipe-separated education entries with degree, institution, and year.
    Prioritizes the education section, then falls back to pattern scanning.
    """
    if not text:
        return ""

    lines = text.split('\n')
    found_section = False
    education_lines = []

    # ── Step 1: Extract from the education section ────────────────────────────
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if _is_header(clean_line, _EDUCATION_HEADERS):
            found_section = True
            continue

        if found_section:
            if _is_header(clean_line, _STOP_HEADERS):
                break
            education_lines.append(clean_line)

    # ── Step 2: Parse structured education entries ────────────────────────────
    entries = []

    if education_lines:
        entries = _parse_education_entries(education_lines)

    # ── Step 3: Fallback — scan entire document ───────────────────────────────
    if not entries:
        for line in lines:
            clean_line = line.strip()
            if not clean_line or len(clean_line) > 150:
                continue
            if _has_degree_mention(clean_line) or _has_institution_mention(clean_line):
                if clean_line not in entries:
                    entries.append(clean_line)
                    if len(entries) >= 6:
                        break

    # Deduplicate
    seen = set()
    unique = []
    for entry in entries:
        key = entry.lower().strip()
        if key not in seen and len(key) > 3:
            seen.add(key)
            unique.append(entry)

    return " | ".join(unique[:6]) if unique else ""


def _parse_education_entries(lines: list[str]) -> list[str]:
    """Parse raw education section lines into structured entries."""
    entries = []
    current_entry_parts = []

    for line in lines:
        # Check if this line starts a new entry (has degree or institution)
        if _has_degree_mention(line) or _has_institution_mention(line):
            # Save previous entry
            if current_entry_parts:
                entries.append(_format_education_entry(current_entry_parts))
            current_entry_parts = [line]
        elif current_entry_parts:
            # Continue building current entry (dates, GPA, etc.)
            current_entry_parts.append(line)
        else:
            # Orphan line at the start — could be a year or detail
            current_entry_parts.append(line)

    # Don't forget the last entry
    if current_entry_parts:
        entries.append(_format_education_entry(current_entry_parts))

    return entries


def _format_education_entry(parts: list[str]) -> str:
    """Format education entry parts into a single readable string."""
    if not parts:
        return ""

    # Join parts that are meaningful
    meaningful = []
    for part in parts:
        cleaned = part.strip()
        if cleaned and len(cleaned) > 2:
            # Skip lines that are just bullets or decorations
            if re.match(r'^[\s\-–—•]+$', cleaned):
                continue
            meaningful.append(cleaned)

    return " - ".join(meaningful[:3]) if meaningful else ""


def extract_highest_degree(text: str) -> str:
    """
    Identifies the highest degree mentioned in the resume.
    
    Returns one of: DOCTORATE, MASTER, BACHELOR, ASSOCIATE, 
    DIPLOMA/VOCATIONAL, SENIOR HIGH SCHOOL, or empty string.
    """
    if not text:
        return ""

    # Check from highest to lowest degree level
    for degree_label, patterns in _DEGREE_HIERARCHY:
        for pattern in patterns:
            if re.search(r'\b' + pattern, text, re.IGNORECASE):
                return degree_label

    return ""