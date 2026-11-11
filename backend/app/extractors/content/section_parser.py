"""
Section Parser
--------------
Centralized utility for splitting resume text into labelled sections.
Every extractor can reuse the same section boundaries instead of
each one duplicating header-detection logic.

The parser is resilient to:
  - ALL-CAPS, Title Case, or lowercase headers
  - Decorations (dashes, equals, bullets, unicode boxes)
  - Headers followed by colons
  - Multiple blank lines between sections
"""

import re
from typing import Optional


# ─── Canonical Section Labels ────────────────────────────────────────────────
# Mapping from header text (UPPER) → canonical label

_HEADER_MAP: dict[str, str] = {}

_SECTION_DEFINITIONS: dict[str, list[str]] = {
    "SKILLS": [
        "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES", "EXPERTISE",
        "TECHNOLOGIES", "TOOLS", "KEY SKILLS", "PROFICIENCIES",
        "COMPETENCIES", "TECH STACK", "TECHNICAL COMPETENCIES",
        "AREAS OF EXPERTISE", "PROFESSIONAL SKILLS", "SKILL SET",
        "TOOLS & TECHNOLOGIES", "TOOLS AND TECHNOLOGIES",
        "PROGRAMMING LANGUAGES", "FRAMEWORKS", "SOFTWARE",
        "TECHNICAL PROFICIENCY", "QUALIFICATIONS SUMMARY",
        "TECHNICAL EXPERTISE", "SKILL HIGHLIGHTS",
        "TOOLS & FRAMEWORKS", "TOOLS AND FRAMEWORKS",
        "TECHNOLOGY STACK", "RELEVANT SKILLS",
        "HARD SKILLS", "SOFT SKILLS", "SKILLS & EXPERTISE",
        "SKILLS INVENTORY", "CORE STRENGTHS",
        "SKILLS & COMPETENCIES", "SKILLS AND COMPETENCIES",
        "SKILLS / COMPETENCIES", "SKILLS/COMPETENCIES",
        "CORE SKILLS & COMPETENCIES", "CORE SKILLS AND COMPETENCIES",
        "KEY SKILLS & COMPETENCIES", "KEY SKILLS AND COMPETENCIES",
        "TECHNICAL SKILLS & COMPETENCIES", "TECHNICAL SKILLS AND COMPETENCIES",
        "PROFESSIONAL SKILLS & COMPETENCIES", "COMPETENCIES & SKILLS",
        "COMPETENCIES AND SKILLS", "SKILLS & ABILITIES", "SKILLS AND ABILITIES",
        "SKILLS / ABILITIES", "SKILLS/ABILITIES",
        "SKILLS & PROFICIENCIES", "SKILLS AND PROFICIENCIES",
        "SKILLS & CAPABILITIES", "SKILLS AND CAPABILITIES",
        "SKILLS & TRAITS", "SKILLS AND TRAITS",
        "SKILLS & QUALITIES", "SKILLS AND QUALITIES",
        "SKILLS & QUALIFICATIONS", "SKILLS AND QUALIFICATIONS",
        "QUALIFICATIONS & SKILLS", "QUALIFICATIONS AND SKILLS",
        "KEY QUALIFICATIONS", "SUMMARY OF QUALIFICATIONS",
        "CORE QUALIFICATIONS", "TECHNICAL QUALIFICATIONS",
        "SKILLS & TOOLS", "SKILLS AND TOOLS", "TOOLS & SKILLS", "TOOLS AND SKILLS",
        "SOFTWARE & TOOLS", "TOOLS & SOFTWARE",
        "SKILLS & LANGUAGES", "SKILLS AND LANGUAGES",
        "SKILLS & KNOWLEDGE", "SKILLS AND KNOWLEDGE",
        "SKILLS & EXPERTISE", "SKILLS AND EXPERTISE",
        "SKILLS SUMMARY", "SUMMARY OF SKILLS", "SKILLS OVERVIEW", "SKILL SUMMARY",
        "SKILLS PROFILE", "SKILLS MATRIX", "SKILL LIST", "LIST OF SKILLS",
        "COMPUTER SKILLS", "IT SKILLS", "DIGITAL SKILLS", "SOFTWARE SKILLS",
        "OFFICE SKILLS", "LANGUAGE & COMPUTER SKILLS", "TECHNICAL & COMPUTER SKILLS",
        "TECHNICAL & ENGINEERING SKILLS", "TECHNICAL AND ENGINEERING SKILLS",
        "ENGINEERING SKILLS", "PERSONAL SKILLS", "INTERPERSONAL SKILLS",
        "WORKPLACE SKILLS", "JOB SKILLS", "CAREER SKILLS", "INDUSTRY SKILLS",
        "TRANSFERABLE SKILLS", "APPLICABLE SKILLS", "ADDITIONAL SKILLS",
        "OTHER SKILLS", "PRIMARY SKILLS", "MAIN SKILLS", "GENERAL SKILLS",
        "PRACTICAL SKILLS", "LABORATORY SKILLS", "CLINICAL SKILLS",
        "TEACHING SKILLS", "ACCOUNTING SKILLS",
        "HARD & SOFT SKILLS", "HARD AND SOFT SKILLS",
        "SOFT & HARD SKILLS", "SOFT AND HARD SKILLS",
        "TECHNICAL & SOFT SKILLS", "TECHNICAL AND SOFT SKILLS",
        "CAPABILITIES", "CORE CAPABILITIES", "TECHNICAL CAPABILITIES",
        "PROFESSIONAL COMPETENCIES", "KEY COMPETENCIES", "RELEVANT COMPETENCIES",
        "COMPETENCIES & TOOLS", "AREAS OF COMPETENCE", "FIELDS OF EXPERTISE",
        "KEY STRENGTHS", "STRENGTHS", "SKILLSET", "MY SKILLS", "KNOWN SKILLS",
        "TECHNICAL KNOWLEDGE", "TECHNICAL BACKGROUND", "TECHNICAL SUMMARY",
        "TECH TOOLS", "LANGUAGES & TECHNOLOGIES", "LANGUAGES & FRAMEWORKS",
        "FRAMEWORKS & LIBRARIES", "DATABASES & CLOUD", "TOOLS & TESTING",
        "SKILLS USED", "CORE SKILLS", "FUNCTIONAL SKILLS", "SPECIAL SKILLS",
    ],
    "EXPERIENCE": [
        "EXPERIENCE", "WORK HISTORY", "EMPLOYMENT", "PROFESSIONAL BACKGROUND",
        "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY",
        "RELEVANT EXPERIENCE", "EMPLOYMENT HISTORY", "JOB EXPERIENCE",
        "CAREER SUMMARY", "CAREER EXPERIENCE",
        "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
        "PROFESSIONAL HISTORY", "WORK AND EXPERIENCE",
        "RELEVANT WORK EXPERIENCE", "EMPLOYMENT RECORD",
        "ON-THE-JOB TRAINING (OJT)", "ON-THE-JOB TRAINING", "ON THE JOB TRAINING",
        "OJT", "INTERNSHIP", "INTERNSHIPS", "PRACTICUM",
        "ON-THE-JOB TRAINING / INTERNSHIP", "ON-THE-JOB TRAINING (OJT) / INTERNSHIP / PRACTICUM",
        "PRACTICUM / INTERNSHIP", "INTERNSHIP / PRACTICUM", "APPRENTICESHIP",
        "WORK BACKGROUND", "OCCUPATIONAL HISTORY", "EMPLOYMENT BACKGROUND",
        "CAREER BACKGROUND", "RELEVANT EMPLOYMENT",
    ],
    "EDUCATION": [
        "EDUCATION", "ACADEMIC", "QUALIFICATIONS", "SCHOLASTIC",
        "EDUCATIONAL ATTAINMENT", "EDUCATIONAL BACKGROUND", "ACADEMIC BACKGROUND",
        "STUDIES", "SCHOOLING", "ACADEMIC QUALIFICATIONS", "ACADEMIC RECORD",
        "EDUCATIONAL HISTORY", "ACADEMIC HISTORY", "DEGREES",
        "EDUCATIONAL QUALIFICATIONS", "EDUCATION AND TRAINING",
    ],
    "CERTIFICATIONS": [
        "CERTIFICATIONS", "CERTIFICATES", "CERTIFICATION", "CERTIFICATE",
        "LICENSES", "LICENSURE", "PROFESSIONAL CERTIFICATIONS",
        "PROFESSIONAL LICENSES", "CERTIFICATIONS AND LICENSES",
        "LICENSES AND CERTIFICATIONS", "CREDENTIALS",
        "PROFESSIONAL CREDENTIALS", "ACCREDITATIONS",
        "TRAININGS AND CERTIFICATIONS", "CERTIFICATIONS AND TRAINING",
        "TRAINING AND CERTIFICATIONS", "CERTIFICATES & LICENSES",
        "CERTIFICATIONS & LICENSES", "PROFESSIONAL LICENSES & CERTIFICATIONS",
        "ELIGIBILITIES", "GOVERNMENT ELIGIBILITY", "ELIGIBILITY",
        "CERTIFICATION AND ACHIEVEMENTS", "CERTIFICATIONS AND ACHIEVEMENTS",
        "CERTIFICATION & ACHIEVEMENTS", "CERTIFICATIONS & ACHIEVEMENTS",
        "CERTIFICATES AND ACHIEVEMENTS", "CERTIFICATES & ACHIEVEMENTS",
        "ACHIEVEMENTS AND CERTIFICATIONS", "ACHIEVEMENTS & CERTIFICATIONS",
        "CERTIFICATIONS AND AWARDS", "CERTIFICATIONS & AWARDS",
        "AWARDS AND CERTIFICATIONS", "AWARDS & CERTIFICATIONS",
        "CERTIFICATES AND TRAININGS", "TRAININGS AND CERTIFICATES",
    ],
    "PROJECTS": [
        "PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS",
        "RELEVANT PROJECTS", "KEY PROJECTS", "PORTFOLIO",
        "SIDE PROJECTS", "CAPSTONE", "THESIS", "WORK PROJECTS",
        "PROJECT HIGHLIGHTS", "NOTABLE PROJECTS",
    ],
    "SUMMARY": [
        "SUMMARY", "PROFESSIONAL SUMMARY", "CAREER OBJECTIVE",
        "OBJECTIVE", "ABOUT ME", "PROFILE", "PERSONAL STATEMENT",
        "CAREER PROFILE", "EXECUTIVE SUMMARY",
    ],
    "TRAINING": [
        "TRAINING", "TRAININGS", "SEMINARS", "WORKSHOPS",
        "PROFESSIONAL DEVELOPMENT", "CONTINUING EDUCATION",
        "SEMINARS AND TRAININGS", "TRAININGS AND SEMINARS",
        "SEMINARS/TRAININGS", "SEMINARS / TRAININGS", "TRAININGS / SEMINARS",
        "SEMINARS & TRAININGS", "TRAININGS & SEMINARS", "SEMINARS ATTENDED",
        "TRAININGS ATTENDED", "SPECIALIZED TRAINING",
    ],
    "AWARDS": [
        "AWARDS", "ACHIEVEMENTS", "HONORS", "RECOGNITION",
        "AWARDS AND ACHIEVEMENTS", "ACCOMPLISHMENTS",
    ],
    "PUBLICATIONS": [
        "PUBLICATIONS", "RESEARCH", "PAPERS",
        "RESEARCH PUBLICATIONS",
    ],
    "VOLUNTEER": [
        "VOLUNTEER", "VOLUNTEER EXPERIENCE", "COMMUNITY SERVICE",
        "VOLUNTEER WORK", "CIVIC ACTIVITIES",
    ],
    "LANGUAGES": [
        "LANGUAGES", "LANGUAGE PROFICIENCY", "LANGUAGE SKILLS",
    ],
    "INTERESTS": [
        "INTERESTS", "HOBBIES", "HOBBIES AND INTERESTS",
    ],
    "REFERENCES": [
        "REFERENCES", "PROFESSIONAL REFERENCES", "CHARACTER REFERENCES",
        "CHARACTER REFERENCE", "PERSONAL REFERENCES", "LIST OF REFERENCES",
    ],
    "PERSONAL": [
        "PERSONAL INFORMATION", "PERSONAL DETAILS", "CONTACT",
        "CONTACT INFORMATION", "CONTACT DETAILS", "CONTACT US",
        "GET IN TOUCH", "PERSONAL PROFILE", "COMMUNICATION",
        "PERSONAL DATA", "BIODATA", "BIO-DATA", "APPLICANT INFORMATION",
        "CANDIDATE INFORMATION",
    ],
    "AFFILIATIONS": [
        "AFFILIATIONS", "MEMBERSHIPS", "ORGANIZATIONS",
        "PROFESSIONAL AFFILIATIONS", "PROFESSIONAL MEMBERSHIPS",
    ],
}

# Build reverse lookup
for label, headers in _SECTION_DEFINITIONS.items():
    for h in headers:
        _HEADER_MAP[h] = label


# ─── Header Detection ────────────────────────────────────────────────────────

# Decorations that surround or prefix section headers
_DECORATION_RE = re.compile(r'^[\s\-–—=_*#•►◆■□▪▸▹:│┃]+|[\s\-–—=_*#•►◆■□▪▸▹:│┃]+$')


_LEADING_NUM_RE = re.compile(r'^(?:\(?(?:\d{1,2}|[ivxlc]{1,4})\)?[\.\)\-:]\s+|\(\d{1,2}\)\s+)', re.I)
_TRAILING_PAREN_RE = re.compile(r'\s*\([^)]*\)\s*$')


def _normalise_header(line: str) -> str:
    """Strip decorations, numbering, and normalise a candidate header line to UPPER with normalized spaces."""
    clean = _DECORATION_RE.sub('', line).strip()
    if (clean.startswith('(') and clean.endswith(')')) or (clean.startswith('[') and clean.endswith(']')):
        clean = clean[1:-1].strip()
    clean = _LEADING_NUM_RE.sub('', clean).strip()
    clean = _DECORATION_RE.sub('', clean).strip()
    clean = clean.rstrip(':').strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean.upper()


def _match_header_text(normalised: str, allow_fuzzy: bool = True) -> Optional[str]:
    """Match an already-normalised uppercase header candidate to a canonical label."""
    if not normalised:
        return None

    res = _HEADER_MAP.get(normalised)
    if res:
        return res

    without_paren = _TRAILING_PAREN_RE.sub('', normalised).strip()
    if without_paren and without_paren != normalised:
        res = _HEADER_MAP.get(without_paren)
        if res:
            return res

    if not allow_fuzzy or ':' in normalised or '|' in normalised:
        return None

    # Flexible matching for compound headers
    if re.search(r'\bSKILLS?\b', normalised) and re.search(
        r'\b(?:COMPETENC|PROFICIENC|ABILIT|TECH|KNOWLEDGE|EXPERTISE|TRAIT|QUALIFICAT|CAPABILIT|STRENGTH|TOOL|INVENTORY|SUMMARY|OVERVIEW|HIGHLIGHT|MATRIX|SET)\w*\b',
        normalised
    ):
        return "SKILLS"
    if (
        len(normalised.split()) <= 4
        and re.search(r'\b(?:SKILLS|COMPETENCIES|PROFICIENCIES)\s*$', normalised)
        and not re.match(
            r'^(?:GOOD|STRONG|EXCELLENT|BASIC|PROVEN|DEMONSTRATED|PROBLEM[\s\-]SOLVING|'
            r'CRITICAL|COMMUNICATION|INTERPERSONAL|ANALYTICAL|ORGANIZATIONAL|TIME|'
            r'CUSTOMER|LEADERSHIP|PRESENTATION|NEGOTIATION|WRITING|READING|LISTENING|'
            r'VERBAL|WRITTEN|SOCIAL|PEOPLE|MULTITASKING)\b',
            normalised,
        )
    ):
        return "SKILLS"
    if re.search(r'\b(?:WORK|EMPLOYMENT|PROFESSIONAL|CAREER)\b', normalised) and re.search(r'\b(?:EXPERIENCE|HISTORY|BACKGROUND|RECORD)\b', normalised):
        return "EXPERIENCE"
    if re.search(r'\b(?:EDUCATION|EDUCATIONAL|ACADEMIC|SCHOLASTIC)\b', normalised) and not re.search(
        r'\b(?:PHYSICAL|SPECIAL|CONTINUING|DEPARTMENT|MINISTRY|BOARD)\s+EDUCATION\b', normalised
    ):
        return "EDUCATION"

    return None


def detect_section_label(line: str) -> Optional[str]:
    """
    If *line* looks like a section header, return the canonical label
    (e.g. ``"SKILLS"``). Otherwise return ``None``.

    Supports standalone headers, inline colon headers (``"Skills: a, b, c"``),
    and pipe-delimited table headers (``"Skills | a, b, c"``).
    """
    stripped = line.strip()
    if not stripped:
        return None

    # 1. Exact header map check first (even if line has punctuation)
    word_count = len(stripped.split())
    if word_count <= 9:
        normalised = _normalise_header(stripped)
        exact = _match_header_text(normalised, allow_fuzzy=False)
        if exact:
            return exact

    # 2. Inline colon header (e.g. "Skills: Python, FastAPI, React, TypeScript, Docker, Git")
    colon_idx = stripped.find(':')
    if colon_idx > 0:
        prefix = stripped[:colon_idx].strip()
        if prefix and len(prefix.split()) <= 5:
            norm_prefix = _normalise_header(prefix)
            if norm_prefix and norm_prefix != "COMMUNICATION":
                res = _match_header_text(norm_prefix)
                if res:
                    return res

    # 3. Inline pipe table row (e.g. "Skills | Python, React, Docker, PostgreSQL")
    pipe_idx = stripped.find('|')
    if pipe_idx > 0 and split_dual_column_header(stripped) is None:
        left = stripped[:pipe_idx].strip()
        right = stripped[pipe_idx + 1:].strip()
        if left and right and len(left.split()) <= 4:
            norm_left = _normalise_header(left)
            if norm_left and norm_left != "COMMUNICATION":
                res = _match_header_text(norm_left)
                if res:
                    return res

    # 4. Full-line flexible compound header match (only when no inline delimiter)
    if word_count <= 9:
        normalised = _normalise_header(stripped)
        res = _match_header_text(normalised, allow_fuzzy=True)
        if res:
            return res

    return None


def split_dual_column_header(line: str) -> Optional[tuple[str, str]]:
    """Detect two distinct section headers merged on a single line in 2-column PDFs/tables."""
    stripped = line.strip()
    if '|' in stripped:
        parts = [p.strip() for p in stripped.split('|') if p.strip()]
        if len(parts) == 2:
            left_label = _match_header_text(_normalise_header(parts[0]), allow_fuzzy=False)
            right_label = _match_header_text(_normalise_header(parts[1]), allow_fuzzy=False)
            if left_label and right_label and left_label != right_label:
                return left_label, right_label

    words = stripped.split()
    if not (2 <= len(words) <= 6):
        return None
    for idx in range(1, len(words)):
        left = _normalise_header(" ".join(words[:idx]))
        right = _normalise_header(" ".join(words[idx:]))
        left_label = _HEADER_MAP.get(left)
        right_label = _HEADER_MAP.get(right)
        if left_label and right_label and left_label != right_label:
            return left_label, right_label
    return None


_split_dual_column_header = split_dual_column_header


# ─── Section Splitter ────────────────────────────────────────────────────────

def split_into_sections(text: str) -> dict[str, str]:
    """
    Split the full resume text into a dict of ``{label: section_body}``.

    Keys are canonical labels like ``"SKILLS"``, ``"EXPERIENCE"``, etc.
    An unlabelled preamble (the header area before the first section)
    is stored under the key ``"HEADER"``.

    Includes intelligent boundary detection for multi-column / side-by-side
    resume templates where entries were placed right above or beside their header.
    """
    lines = text.split('\n')
    sections: dict[str, list[str]] = {}
    current_label = "HEADER"
    sections[current_label] = []

    _DEGREE_INST_HINTS = {
        "BACHELOR", "MASTER", "COLLEGE", "COLLEGES", "UNIVERSITY", "DEGREE",
        "STUDENT", "DIPLOMA", "ASSOCIATE", "BSIT", "BSCS", "BSCPE", "BSIS",
        "STI", "DLSU", "PUP", "UP", "UST", "FEU", "MAPUA", "UDM", "HIGH SCHOOL"
    }

    _ROLE_DATE_HINTS = {
        "PRESENT", "202", "201", "RIDER", "DEVELOPER", "ENGINEER", "MANAGER",
        "PANDA", "FOOD PANDA", "CREW", "OFFICER", "TECHNICIAN", "OPERATOR",
        "ASSISTANT", "LEAD", "DIRECTOR", "SUPERVISOR", "ANALYST", "SPECIALIST",
        "COORDINATOR", "DESIGNER", "INTERN", "DRIVER", "CASHIER", "CLERK"
    }

    _EDU_DUAL_LINE_RE = re.compile(
        r'\b(?:bachelor|master|doctor|associate|diploma|certificate|'
        r'bs\s+|b\.s\.|ba\s+|b\.a\.|bsit|bscs|bsis|bsce|bsme|bsee|bsie|'
        r'college|university|school|institute|academy|high\s+school|shs|jhs|'
        r'tesda|expected|graduated?|graduation|class\s+of)\b',
        re.I,
    )

    active_dual: Optional[tuple[str, str]] = None

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            sections[current_label].append(line)
            continue

        label = detect_section_label(cleaned_line)
        if not label:
            dual = split_dual_column_header(cleaned_line)
            if dual:
                left_label, right_label = dual
                sections.setdefault(left_label, [])
                sections.setdefault(right_label, [])
                if '|' in cleaned_line:
                    active_dual = (left_label, right_label)
                    current_label = left_label
                else:
                    active_dual = None
                    current_label = right_label
                continue

        if label:
            active_dual = None
            # Extract inline content after ':' or '|' if full line itself wasn't a bare header
            inline_after = ""
            full_norm = _normalise_header(cleaned_line)
            is_bare_header = bool(_match_header_text(full_norm, allow_fuzzy=False))
            if not is_bare_header:
                colon_idx = cleaned_line.find(':')
                pipe_idx = cleaned_line.find('|')
                split_idx = colon_idx if (colon_idx > 0 and (pipe_idx < 0 or colon_idx < pipe_idx)) else pipe_idx
                if split_idx > 0:
                    inline_after = cleaned_line[split_idx + 1:].strip()
                    is_colon_split = (split_idx == colon_idx)
                    # Inside PROJECTS or EXPERIENCE, inline colon lines ("Technologies: ...", "Skills: ...")
                    # should enrich SKILLS without hijacking subsequent project/job lines
                    if (
                        is_colon_split
                        and inline_after
                        and label == "SKILLS"
                        and current_label in ("PROJECTS", "EXPERIENCE")
                    ):
                        sections.setdefault("SKILLS", []).append(inline_after)
                        sections[current_label].append(line)
                        continue

            # Check if previous section has trailing lines that actually belong to this new section
            # e.g. "STI Colleges Ortigas-Cainta\nBachelor..." preceding EDUCATION header
            if label == "EDUCATION" and sections.get(current_label) and current_label not in ("EXPERIENCE", "SKILLS"):
                prev_lines = [l for l in sections[current_label] if l.strip()]
                if prev_lines:
                    tail = prev_lines[-4:]
                    tail_text = " ".join(tail).upper()
                    if any(hint in tail_text for hint in _DEGREE_INST_HINTS):
                        moved = []
                        while sections[current_label]:
                            top = sections[current_label][-1].strip()
                            if not top:
                                sections[current_label].pop()
                                continue
                            top_upper = top.upper()
                            if any(hint in top_upper for hint in _DEGREE_INST_HINTS):
                                moved.insert(0, sections[current_label].pop())
                                if len(moved) >= 4:
                                    break
                            else:
                                break
                        if label not in sections:
                            sections[label] = []
                        sections[label].extend(moved)

            elif label == "EXPERIENCE" and sections.get(current_label) and current_label not in ("EDUCATION", "SKILLS"):
                prev_lines = [l for l in sections[current_label] if l.strip()]
                if prev_lines:
                    tail = prev_lines[-4:]
                    tail_text = " ".join(tail).upper()
                    if any(hint in tail_text for hint in _ROLE_DATE_HINTS):
                        moved = []
                        while sections[current_label]:
                            top = sections[current_label][-1].strip()
                            if not top:
                                sections[current_label].pop()
                                continue
                            top_upper = top.upper()
                            if any(hint in top_upper for hint in _ROLE_DATE_HINTS):
                                moved.insert(0, sections[current_label].pop())
                                if len(moved) >= 4:
                                    break
                            else:
                                break
                        if label not in sections:
                            sections[label] = []
                        sections[label].extend(moved)

            current_label = label
            if current_label not in sections:
                sections[current_label] = []

            # Keep inline content after ':' or '|' if present
            if inline_after:
                sections[current_label].append(inline_after)
            else:
                colon_idx = cleaned_line.find(':')
                if colon_idx >= 0:
                    after = cleaned_line[colon_idx + 1:].strip()
                    if after:
                        sections[current_label].append(after)
        else:
            if active_dual:
                if '|' in cleaned_line and '@' not in cleaned_line:
                    parts = [p.strip() for p in cleaned_line.split('|')]
                    if len(parts) == 2:
                        if parts[0]:
                            sections[active_dual[0]].append(parts[0])
                        if parts[1]:
                            sections[active_dual[1]].append(parts[1])
                        continue
                if "EDUCATION" in active_dual and "SKILLS" in active_dual:
                    if _EDU_DUAL_LINE_RE.search(cleaned_line):
                        sections["EDUCATION"].append(line)
                        continue
                    if ',' in cleaned_line or not re.search(r'\b(?:19|20)\d{2}\b', cleaned_line):
                        sections["SKILLS"].append(line)
                        continue

            # Check if this line is an education graduation date right at top of SKILLS
            if current_label == "SKILLS" and not [l for l in sections["SKILLS"] if l.strip()]:
                clean_up = cleaned_line.upper()
                if any(w in clean_up for w in ["EXPECTED", "GRADUATED", "GRADUATION", "CLASS OF"]) and any(y in clean_up for y in ["202", "201"]):
                    if "EDUCATION" in sections:
                        sections["EDUCATION"].append(cleaned_line)
                        continue

            sections[current_label].append(line)

    # Join into contiguous text blocks
    return {label: '\n'.join(body) for label, body in sections.items()}


def get_section(text: str, label: str) -> str:
    """
    Convenience function: return the body text for a single canonical
    section label, or empty string if the section is not found.
    """
    sections = split_into_sections(text)
    return sections.get(label, "")
