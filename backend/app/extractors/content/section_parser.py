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
    ],
    "EXPERIENCE": [
        "EXPERIENCE", "WORK HISTORY", "EMPLOYMENT", "PROFESSIONAL BACKGROUND",
        "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY",
        "RELEVANT EXPERIENCE", "EMPLOYMENT HISTORY", "JOB EXPERIENCE",
        "CAREER SUMMARY", "CAREER EXPERIENCE",
        "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
        "PROFESSIONAL HISTORY", "WORK AND EXPERIENCE",
        "RELEVANT WORK EXPERIENCE", "EMPLOYMENT RECORD",
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
        "REFERENCES", "PROFESSIONAL REFERENCES",
    ],
    "PERSONAL": [
        "PERSONAL INFORMATION", "PERSONAL DETAILS", "CONTACT",
        "CONTACT INFORMATION", "CONTACT DETAILS", "CONTACT US",
        "GET IN TOUCH", "PERSONAL PROFILE", "COMMUNICATION",
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


def _normalise_header(line: str) -> str:
    """Strip decorations and normalise a candidate header line to UPPER with normalized spaces."""
    clean = _DECORATION_RE.sub('', line).strip()
    clean = clean.rstrip(':').strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean.upper()


def detect_section_label(line: str) -> Optional[str]:
    """
    If *line* looks like a section header, return the canonical label
    (e.g. ``"SKILLS"``). Otherwise return ``None``.

    A header must be short (< 7 words) and match one of the known patterns.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Headers are short
    word_count = len(stripped.split())
    if word_count >= 7:
        return None

    normalised = _normalise_header(stripped)
    if not normalised:
        return None

    return _HEADER_MAP.get(normalised)


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

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            sections[current_label].append(line)
            continue

        label = detect_section_label(cleaned_line)
        if label:
            # Check if previous section has trailing lines that actually belong to this new section
            # e.g. "STI Colleges Ortigas-Cainta\nBachelor..." preceding EDUCATION header
            if label == "EDUCATION" and sections.get(current_label):
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

            elif label == "EXPERIENCE" and sections.get(current_label):
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

            # If the header line contains inline content after a colon, keep it
            colon_idx = cleaned_line.find(':')
            if colon_idx >= 0:
                after = cleaned_line[colon_idx + 1:].strip()
                if after:
                    sections[current_label].append(after)
        else:
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
