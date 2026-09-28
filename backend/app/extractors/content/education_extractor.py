import re
from typing import Optional, List, Dict, Any
from app.extractors.nlp.nlp_engine import get_doc, extract_advanced_education
from app.extractors.content.section_parser import split_into_sections

# ─── Section Headers ─────────────────────────────────────────────────────────

_EDUCATION_HEADERS = [
    "EDUCATION", "ACADEMIC", "QUALIFICATIONS", "SCHOLASTIC",
    "EDUCATIONAL ATTAINMENT", "EDUCATIONAL BACKGROUND", "ACADEMIC BACKGROUND",
    "STUDIES", "SCHOOLING", "ACADEMIC QUALIFICATIONS", "ACADEMIC RECORD",
    "EDUCATIONAL HISTORY", "ACADEMIC HISTORY", "DEGREES",
    "EDUCATIONAL QUALIFICATIONS",
]

_STOP_HEADERS = [
    "EXPERIENCE", "SKILLS", "CERTIFICATIONS", "PROJECTS", "WORK",
    "EMPLOYMENT", "TRAININGS", "SEMINARS", "AFFILIATIONS", "REFERENCES",
    "ACHIEVEMENTS", "AWARDS", "INTERESTS", "HOBBIES", "VOLUNTEER",
    "TOOLS", "TECHNOLOGIES", "TECHNICAL SKILLS", "CORE COMPETENCIES",
    "PUBLICATIONS", "LANGUAGES", "PERSONAL", "ACTIVITIES", "SUMMARY",
]

# ─── Degree Patterns (ordered highest to lowest) ─────────────────────────────

_DEGREE_HIERARCHY = [
    ("DOCTORATE", [
        r"PH\.?D\.?", r"DOCTORATE", r"DOCTOR\s+OF\s+PHILOSOPHY", r"JURIS\s+DOCTOR",
        r"DOCTOR\s+OF\s+MEDICINE", r"\bMD\b", r"\bJ\.?D\.?\b",
        r"ED\.?D\.?", r"DOCTOR\s+OF\s+\w+",
    ]),
    ("MASTER", [
        r"MASTER(?:'?S)?\s+OF\s+BUSINESS\s+ADMINISTRATION", r"\bMBA\b", r"M\.B\.A\.?",
        r"MASTER(?:'?S)?\s+OF\s+SCIENCE", r"\bMSC?\b", r"M\.SC\.?",
        r"MASTER(?:'?S)?\s+OF\s+ARTS", r"\bMA\b", r"M\.A\.?",
        r"MASTER(?:'?S)?\s+OF\s+ENGINEERING", r"\bMENG\b", r"M\.ENG\.?",
        r"MASTER(?:'?S)?\s+IN\s+INFORMATION\s+TECHNOLOGY", r"\bMIT\b(?=\s)",
        r"MASTER(?:'?S)?\s+OF\s+PUBLIC\s+ADMINISTRATION", r"\bMPA\b",
        r"MASTER(?:'?S)?\s+IN\s+\w+", r"MASTER(?:'?S)?\s+OF\s+\w+",
        r"GRADUATE\s+STUDIES", r"GRADUATE\s+DEGREE", r"MASTER(?:'?S)?\b",
    ]),
    ("BACHELOR", [
        r"BACHELOR(?:'?S)?\s+OF\s+SCIENCE\s+IN\s+COMPUTER\s+SCIENCE", r"\bBSCS\b", r"B\.S\.C\.S\.?",
        r"BACHELOR(?:'?S)?\s+OF\s+SCIENCE\s+IN\s+INFORMATION\s+TECHNOLOGY", r"\bBSIT\b", r"B\.S\.I\.T\.?",
        r"BACHELOR(?:'?S)?\s+OF\s+SCIENCE\s+IN\s+COMPUTER\s+ENGINEERING", r"\bBSCPE\b", r"B\.S\.C\.P\.E\.?", r"\bBSCE\b",
        r"BACHELOR(?:'?S)?\s+OF\s+SCIENCE\s+IN\s+INFORMATION\s+SYSTEMS", r"\bBSIS\b", r"B\.S\.I\.S\.?",
        r"\bBS\s+INFORMATION\s+TECHNOLOGY\b", r"\bBS\s+COMPUTER\s+SCIENCE\b",
        r"\bBS\s+COMPUTER\s+ENGINEERING\b", r"\bBS\s+INFORMATION\s+SYSTEMS\b",
        r"\bBS\s+BUSINESS\s+ADMINISTRATION\b", r"\bBS\s+ACCOUNTANCY\b",
        r"BACHELOR(?:'?S)?\s+OF\s+SCIENCE\s+IN\s+\w+(?:\s+\w+)?", r"BACHELOR(?:'?S)?\s+OF\s+ARTS\s+IN\s+\w+",
        r"BACHELOR(?:'?S)?\s+OF\s+ENGINEERING", r"BACHELOR(?:'?S)?\s+OF\s+BUSINESS(?:\s+ADMINISTRATION)?",
        r"\bBBA\b", r"\bBCOM\b", r"\bBFA\b", r"\bBSE\b", r"\bBSN\b",
        r"BACHELOR(?:'?S)?\s+OF\s+\w+", r"BACHELOR(?:'?S)?\s+DEGREE",
        r"\bBS\s+[A-Z]\w+(?:\s+[A-Z]\w+)*", r"\bB\.S\.\s+[A-Z]\w+(?:\s+[A-Z]\w+)*",
        r"\bBA\s+[A-Z]\w+(?:\s+[A-Z]\w+)*", r"\bB\.A\.\s+[A-Z]\w+(?:\s+[A-Z]\w+)*",
        r"BACHELOR(?:'?S)?\b", r"UNDERGRADUATE\s+DEGREE",
    ]),
    ("ASSOCIATE", [
        r"ASSOCIATE\s+IN\s+COMPUTER\s+TECHNOLOGY", r"\bACT\b(?=\s)",
        r"ASSOCIATE(?:'?S)?\s+OF\s+SCIENCE", r"ASSOCIATE(?:'?S)?\s+OF\s+ARTS",
        r"ASSOCIATE(?:'?S)?\s+DEGREE", r"ASSOCIATE\s+(?:IN|OF)\s+\w+",
        r"2[\s-]?YEAR\s+DEGREE", r"ASSOCIATE(?:'?S)?\b",
    ]),
    ("DIPLOMA/VOCATIONAL", [
        r"DIPLOMA\s+IN\s+\w+", r"DIPLOMA", r"VOCATIONAL", r"\bTESDA\b",
        r"\bNC\s?I\b", r"\bNC\s?II\b", r"\bNC\s?III\b", r"\bNC\s?IV\b",
        r"NATIONAL\s+CERTIFICATE", r"CERTIFICATE\s+(?:IN|OF)\s+\w+",
        r"TECHNICAL\s+EDUCATION",
    ]),
    ("SENIOR HIGH SCHOOL", [
        r"SENIOR\s+HIGH\s+SCHOOL", r"SENIOR\s+HIGH", r"S\.?H\.?S\.?", r"\bSHS\b",
        r"K[\s-]?12", r"GRADE\s+12", r"12TH\s+GRADE",
        r"\bSTEM(?:\s+STRAND)?\b", r"\bABM(?:\s+STRAND)?\b",
        r"\bHUMSS(?:\s+STRAND)?\b", r"\bGAS(?:\s+STRAND)?\b", r"\bTVL(?:\s+STRAND)?\b",
        r"HIGH\s+SCHOOL\s+DIPLOMA",
    ]),
]

# University / Institution indicators
_INSTITUTION_PATTERNS = [
    # Explicit Philippine Universities & Colleges
    r"\b(?:UP\s+Diliman|U\.P\.\s+Diliman|University of the Philippines\s+Diliman)\b",
    r"\b(?:University of the Philippines)(?:\s+Diliman|\s+Manila|\s+Los Baños|\s+Visayas)?\b",
    r"\b(?:DLSU|De La Salle University|De La Salle)(?:\s+Manila|\s+Dasmariñas|\s+Canlubang)?\b",
    r"\b(?:PUP|Polytechnic University of the Philippines)\b",
    r"\b(?:ADMU|Ateneo de Manila University|Ateneo)(?:\s+de\s+Manila)?\b",
    r"\b(?:FEU Tech|FEU Institute of Technology|Far Eastern University|FEU)\b",
    r"\b(?:UST|University of Santo Tomas|University of St\. Tomas)\b",
    r"\b(?:MAPUA|Mapúa University|Mapua Institute of Technology)\b",
    r"\b(?:UE|University of the East)\b",
    r"\b(?:NU|National University)\b",
    r"\b(?:TIP|Technological Institute of the Philippines)\b",
    r"\b(?:TUP|Technological University of the Philippines)\b",
    r"\b(?:PLM|Pamantasan ng Lungsod ng Maynila)\b",
    r"\b(?:UDM|Universidad [Dd]e Manila)\b",
    r"\b(?:STI\s+Colleges?)(?:[ \t]+[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)*\b",
    r"\b(?:AMA\s+(?:University|Computer\s+College|College))\b",
    r"\b(?:Adamson University|Adamson)\b",
    r"\b(?:San Beda University|San Beda College|San Beda)\b",
    r"\b(?:Silliman University|Silliman)\b",
    r"\b(?:Letran|Colegio de San Juan de Letran)\b",
    r"\b(?:University of San Carlos|USC)\b",
    r"\b(?:Lyceum of the Philippines University|LPU)\b",
    r"\b(?:Centro Escolar University|CEU)\b",
    r"\b(?:Trinity University of Asia)\b",
    r"\b(?:Rizal Technological University|RTU)\b",
    r"\b(?:Bulacan State University|BulSU)\b",
    r"\b(?:Batangas State University|BatStateU)\b",
    r"\b(?:Cavite State University|CvSU)\b",
    r"\b(?:Laguna State Polytechnic University|LSPU)\b",

    # Global / International Universities
    r"\b(?:Harvard|Stanford|MIT|Oxford|Cambridge|Yale|Princeton|Columbia|Cornell|Berkeley)\b(?:\s+University)?",

    # Spanish / Filipino University / College Prefixes
    r"\b(?:Universidad|Colegio|Pamantasan)\s+(?:[Dd]e|[Nn]g)\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+)?\b",

    # Generic Institution Phrases
    r"\b(?:University|College|Colleges|Institute|Polytechnic)\s+of\s+(?:the\s+)?[A-Z][a-zA-Z0-9.'-]+(?:\s+[A-Z][a-zA-Z0-9.'-]+)?\b",
    r"\b(?:[A-Z][a-zA-Z0-9.'-]+\s+){1,4}(?:State\s+)?(?:University|College|Colleges|Institute|Polytechnic|Academy|Lyceum)(?:[ \t]+[-–—][ \t]+[A-Za-z0-9-]+)?\b",

    # High Schools & Secondary
    r"\b(?:[A-Z][a-zA-Z0-9.'-]+\s+){1,3}(?:High\s+School|Senior\s+High|Junior\s+High|National\s+High\s+School)\b",

    # Elementary Schools
    r"\b(?:[A-Z][a-zA-Z0-9.'-]+\s+){1,4}(?:Elementary\s+School|Elementary)\b",

    # Short-named vocational/technical schools (MMC-CAST, AMA, TESDA, etc.)
    r"\b(?:MMC[-\s]?CAST|TESDA|CIIT|iACADEMY|ICCT|ACLC|PHINMA|INFORMATICS)\b",
]


def _normalize_education_text(text: str) -> str:
    """Normalize degrees, strands, and school names in text without duplicate expansions."""
    normalized = text

    # Standardize specific Philippine degrees & SHS strands
    degree_replacements = [
        (r'\b(?:BS\s+Information\s+Technology|B\.S\.\s+Information\s+Technology|B\.S\.I\.T\.|BSIT)\b(?!\s*\([^)]*Information Technology[^)]*\))', "Bachelor of Science in Information Technology"),
        (r'\b(?:BS\s+Computer\s+Science|B\.S\.\s+Computer\s+Science|B\.S\.C\.S\.|BSCS)\b(?!\s*\([^)]*Computer Science[^)]*\))', "Bachelor of Science in Computer Science"),
        (r'\b(?:BS\s+Computer\s+Engineering|B\.S\.\s+Computer\s+Engineering|B\.S\.C\.P\.E\.|BSCpE|BSCE)\b(?!\s*\([^)]*Computer Engineering[^)]*\))', "Bachelor of Science in Computer Engineering"),
        (r'\b(?:BS\s+Information\s+Systems|B\.S\.\s+Information\s+Systems|B\.S\.I\.S\.|BSIS)\b(?!\s*\([^)]*Information Systems[^)]*\))', "Bachelor of Science in Information Systems"),
        (r'\b(?:ACT|Associate in Computer Tech(?:nology)?)\b', "Associate in Computer Technology"),
        (r'\bMBA\b(?!\s*\([^)]*Business Administration[^)]*\))', "Master of Business Administration"),
        (r'\bSTEM(?:\s+Strand)?\b', "STEM Strand"),
        (r'\bABM(?:\s+Strand)?\b', "ABM Strand"),
        (r'\bHUMSS(?:\s+Strand)?\b', "HUMSS Strand"),
        (r'\bGAS(?:\s+Strand)?\b', "GAS Strand"),
        (r'\bTVL(?:\s+Strand)?\b', "TVL Strand"),
    ]
    for pat, rep in degree_replacements:
        normalized = re.sub(pat, rep, normalized, flags=re.IGNORECASE)

    # Clean redundant duplicate acronym expansions
    normalized = re.sub(r'(\b[A-Za-z\s]+)\s*\(\1\)', r'\1', normalized)
    normalized = re.sub(r'\((?:BSCS|BSIT|BSCPE|BSIS|MBA|ACT|STEM|ABM|HUMSS)\)', '', normalized, flags=re.IGNORECASE)

    # School Normalizations (ensure short acronyms like UP do NOT match English word 'up')
    normalized = re.sub(r'\b(?:UP Diliman|U\.P\.\s+Diliman)\b', "University of the Philippines Diliman", normalized, flags=re.I)
    normalized = re.sub(r'\bU\.P\.\b', "University of the Philippines", normalized)
    normalized = re.sub(r'(?<![a-zA-Z-])UP(?![a-zA-Z-])', "University of the Philippines", normalized)
    normalized = re.sub(r'\b(?:DLSU|De La Salle University|La Salle)\b', "De La Salle University", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:PUP|P\.U\.P\.|Polytechnic University of the Philippines)\b', "Polytechnic University of the Philippines", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:ADMU|Ateneo de Manila University|Ateneo(?:\s+de\s+Manila)?)\b', "Ateneo de Manila University", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:FEU Tech|FEU Institute of Technology)\b', "FEU Institute of Technology", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:FEU|Far Eastern University)\b', "Far Eastern University", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:MAPUA(?: UNIVERSITY)?|MAPÚA(?: UNIVERSITY)?|Mapua)\b', "Mapúa University", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:UST|U\.S\.T\.|University of Santo Tomas|University of St\. Tomas)\b', "University of Santo Tomas", normalized, flags=re.I)
    normalized = re.sub(r'\b(?:UDM|Universidad [Dd]e Manila)\b', "Universidad De Manila", normalized, flags=re.I)

    normalized = re.sub(r'\(\s*\)', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def _is_header(line: str, keywords: list[str]) -> bool:
    """Check if a line is a section header."""
    clean = line.strip().upper()
    if not clean or len(clean.split()) >= 7:
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
            if re.search(r'\b' + p + r'\b', line, re.IGNORECASE):
                return True
    return False


def _has_institution_mention(line: str) -> bool:
    """Check if a line mentions an educational institution."""
    for p in _INSTITUTION_PATTERNS:
        match = re.search(p, line, re.IGNORECASE)
        if match:
            found = match.group(0).strip()
            if not _is_invalid_institution(found):
                return True
    return False


def _is_invalid_institution(name: str) -> bool:
    """Disqualify strings that are not real institution names."""
    if not name or len(name) < 3:
        return True
    lower = name.lower()
    # Check for college year level
    if re.search(r'\b(?:\d+(?:st|nd|rd|th)?|first|second|third|fourth)?\s*year\s+college\b', lower):
        return True
    if any(lower == w or lower.startswith(w + " ") for w in ["grade", "level", "semester", "strand", "academic"]):
        return True
    if "computer science" in lower or "information technology" in lower:
        return True
    return False


def extract_highest_degree(text: str) -> str:
    """
    Identifies the highest academic degree level tier (DOCTORATE, MASTER, BACHELOR, etc.)
    Used for filtering and ATS scoring algorithms.
    """
    if not text:
        return ""

    for degree_label, patterns in _DEGREE_HIERARCHY:
        for pattern in patterns:
            if re.search(r'\b' + pattern + r'\b', text, re.IGNORECASE):
                return degree_label

    return ""


def _extract_single_institution(text: str) -> str:
    """Isolate an institution/university name cleanly from text."""
    if not text:
        return ""

    # If text contains separators like " - " or " | ", check each chunk
    chunks = re.split(r'\s*[-–—|]\s*', text)
    if len(chunks) > 1:
        for chunk in chunks:
            if _has_degree_mention(chunk) and not _has_institution_mention(chunk):
                continue
            inst = _extract_single_institution(chunk)
            if inst:
                return inst

    for pattern in _INSTITUTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found = match.group(0).strip()
            found = re.sub(r'^[,\-–—\s(]+|[,\-–—\s)]+$', '', found).strip()
            # Strip any leading degree words
            found = re.sub(r'^(?:Bachelor|Master|Doctor|Associate|B\.S\.|B\.A\.|M\.S\.|M\.A\.|MBA|BSCS|BSIT|PhD)(?:\s+of|\s+in|\s+Science|\s+Arts)?\s*(?:in\s+[A-Za-z\s]+)?\s*[-–—:]\s*', '', found, flags=re.I).strip()
            if len(found) > 3 and not _is_invalid_institution(found):
                return _normalize_education_text(found)

    return ""


def _extract_single_degree(text: str) -> str:
    """Isolate a degree name (e.g. 'Bachelor of Science in Computer Science') from text."""
    if not text:
        return ""

    # If text contains separators like " - " or " | ", check each chunk
    chunks = re.split(r'\s*[-–—|]\s*', text)
    if len(chunks) > 1:
        for chunk in chunks:
            if _has_institution_mention(chunk) and not _has_degree_mention(chunk):
                continue
            deg = _extract_single_degree(chunk)
            if deg:
                return deg

    for _, patterns in _DEGREE_HIERARCHY:
        for p in patterns:
            match = re.search(r'\b' + p + r'(?:\s+in\s+[A-Za-z\s]+)?\b', text, re.IGNORECASE)
            if match:
                deg = match.group(0).strip()
                deg = re.sub(r'^[,\-–—\s(]+|[,\-–—\s)]+$', '', deg).strip()
                # Strip institution part if caught
                deg = re.sub(r'\s*[-–—]\s*(?:University|College|Institute|De La Salle|UP|PUP|ADMU|Ateneo|UST|FEU|Mapúa|Universidad).*$', '', deg, flags=re.I).strip()
                if len(deg) > 2:
                    return _normalize_education_text(deg)

    return ""


def extract_education_entries(text: str) -> list[dict]:
    """
    Parse structured education entries from the resume.
    Returns list of dicts: [{"degree": str, "institution": str, "year": str, "raw": str}]
    """
    sections = split_into_sections(text)
    edu_text = sections.get("EDUCATION", "")

    lines = [l.strip() for l in edu_text.split('\n') if l.strip()] if edu_text else [l.strip() for l in text.split('\n') if l.strip()]
    entries = []
    current_entry_lines = []

    for line in lines:
        if _is_header(line, _EDUCATION_HEADERS + _STOP_HEADERS):
            continue

        has_deg = _has_degree_mention(line)
        has_inst = _has_institution_mention(line)

        if has_deg or has_inst:
            if current_entry_lines:
                prev_text = " ".join(current_entry_lines)
                # If prev_text already has degree and line has institution (or vice versa), combine!
                if (_has_degree_mention(prev_text) and not _has_institution_mention(prev_text) and has_inst) or \
                   (_has_institution_mention(prev_text) and not _has_degree_mention(prev_text) and has_deg):
                    current_entry_lines.append(line)
                    continue

                entry = _parse_entry_from_lines(current_entry_lines)
                if entry:
                    entries.append(entry)
                current_entry_lines = [line]
            else:
                current_entry_lines = [line]
        elif current_entry_lines:
            current_entry_lines.append(line)

    if current_entry_lines:
        entry = _parse_entry_from_lines(current_entry_lines)
        if entry:
            entries.append(entry)

    # spaCy-based extraction fallback
    if not entries:
        try:
            doc = get_doc(text)
            nlp_entries = extract_advanced_education(doc)
            for ne in nlp_entries:
                deg = _extract_single_degree(ne)
                inst = _extract_single_institution(ne)
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', ne)
                year = year_match.group(0) if year_match else ""
                entries.append({
                    "degree": deg,
                    "institution": inst,
                    "year": year,
                    "raw": ne
                })
        except Exception:
            pass

    return entries


def _parse_entry_from_lines(lines: list[str]) -> Optional[dict]:
    """Combine lines into an education entry dict with degree, institution, and year."""
    full_text = " - ".join(lines)
    norm_text = _normalize_education_text(full_text)

    # Extract year
    year_match = re.search(r'\b(?:19|20)\d{2}(?:\s*[-–—to]+\s*(?:(?:19|20)\d{2}|Present))?\b', norm_text)
    year = year_match.group(0) if year_match else ""

    # Split lines/chunks to isolate degree and institution
    institution = ""
    degree = ""

    # Check each individual line first
    for l in lines:
        nl = _normalize_education_text(l)
        if not institution and _has_institution_mention(nl):
            institution = _extract_single_institution(nl)
        if not degree and _has_degree_mention(nl):
            degree = _extract_single_degree(nl)

    # Fallback to scanning norm_text
    if not institution:
        institution = _extract_single_institution(norm_text)
    if not degree:
        degree = _extract_single_degree(norm_text)

    # Clean raw string
    raw_parts = []
    if degree:
        raw_parts.append(degree)
    if institution:
        raw_parts.append(institution)
    if year:
        raw_parts.append(f"({year})")

    raw_str = " - ".join(raw_parts[:2])
    if len(raw_parts) > 2:
        raw_str += f" {raw_parts[2]}"

    if not raw_str:
        raw_str = norm_text

    if degree or institution:
        return {
            "degree": degree,
            "institution": institution,
            "year": year,
            "raw": raw_str
        }
    return None


def extract_degree_title(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the full degree title (e.g. 'Bachelor of Science in Computer Science',
    'Master of Business Administration'), NOT just the generic level 'BACHELOR'.
    """
    if not text:
        return ""

    if entries is None:
        entries = extract_education_entries(text)

    if entries:
        for e in entries:
            deg = e.get("degree", "").strip()
            if deg and len(deg) > 3:
                return deg

    deg = _extract_single_degree(text)
    if deg:
        return deg

    return extract_highest_degree(text)


def extract_institution(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's university / college / institution name cleanly.
    Prioritizes tertiary (universities, colleges, polytechnics) over high schools.
    """
    if not text:
        return ""

    if entries is None:
        entries = extract_education_entries(text)

    # First pass: find a tertiary institution (University, College, etc.)
    if entries:
        for e in entries:
            inst = e.get("institution", "").strip()
            if inst and len(inst) > 3 and not re.search(r'\b(?:High\s*School|Junior\s*High|Senior\s*High|Elementary)\b', inst, re.I):
                return inst
        # Second pass: if only high school is present, return it
        for e in entries:
            inst = e.get("institution", "").strip()
            if inst and len(inst) > 3:
                return inst

    inst = _extract_single_institution(text)
    if inst:
        return inst

    return ""


def extract_education(text: str) -> str:
    """
    Extracts education details from resume text.
    Returns pipe-separated entries: "Degree - Institution (Year) | ..."
    """
    entries = extract_education_entries(text)
    formatted = []

    for e in entries:
        raw = e.get("raw", "").strip()
        if raw and raw not in formatted:
            formatted.append(raw)

    if formatted:
        return " | ".join(formatted[:6])

    try:
        doc = get_doc(text)
        nlp_entries = extract_advanced_education(doc)
        return " | ".join(nlp_entries[:6]) if nlp_entries else ""
    except Exception:
        return ""