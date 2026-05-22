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
        "HARD SKILLS", "SOFT SKILLS",
    ],
    "EXPERIENCE": [
        "EXPERIENCE", "WORK HISTORY", "EMPLOYMENT", "PROFESSIONAL BACKGROUND",
        "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY",
        "RELEVANT EXPERIENCE", "EMPLOYMENT HISTORY", "JOB EXPERIENCE",
        "CAREER SUMMARY", "CAREER EXPERIENCE",
        "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
        "PROFESSIONAL HISTORY",
    ],
    "EDUCATION": [
        "EDUCATION", "ACADEMIC", "QUALIFICATIONS", "SCHOLASTIC",
        "EDUCATIONAL ATTAINMENT", "EDUCATIONAL BACKGROUND", "ACADEMIC BACKGROUND",
        "STUDIES", "SCHOOLING", "ACADEMIC QUALIFICATIONS", "ACADEMIC RECORD",
        "EDUCATIONAL HISTORY", "ACADEMIC HISTORY", "DEGREES",
        "EDUCATIONAL QUALIFICATIONS",
    ],
    "CERTIFICATIONS": [
        "CERTIFICATIONS", "CERTIFICATES", "CERTIFICATION", "CERTIFICATE",
        "LICENSES", "LICENSURE", "PROFESSIONAL CERTIFICATIONS",
        "PROFESSIONAL LICENSES", "CERTIFICATIONS AND LICENSES",
        "LICENSES AND CERTIFICATIONS", "CREDENTIALS",
        "PROFESSIONAL CREDENTIALS", "ACCREDITATIONS",
        "TRAININGS AND CERTIFICATIONS", "CERTIFICATIONS AND TRAINING",
        "TRAINING AND CERTIFICATIONS",
    ],
    "PROJECTS": [
        "PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS",
        "RELEVANT PROJECTS", "KEY PROJECTS", "PORTFOLIO",
        "SIDE PROJECTS", "CAPSTONE", "THESIS",
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
        "CONTACT INFORMATION", "CONTACT DETAILS",
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
    """Strip decorations and normalise a candidate header line to UPPER."""
    clean = _DECORATION_RE.sub('', line).strip()
    # Remove trailing colon
    clean = clean.rstrip(':').strip()
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

    Each section body is the raw text between its header line and the
    next detected header (or end of document).
    """
    lines = text.split('\n')
    sections: dict[str, list[str]] = {}
    current_label = "HEADER"
    sections[current_label] = []

    for line in lines:
        label = detect_section_label(line)
        if label:
            current_label = label
            if current_label not in sections:
                sections[current_label] = []
            # If the header line contains inline content after a colon, keep it
            colon_idx = line.find(':')
            if colon_idx >= 0:
                after = line[colon_idx + 1:].strip()
                if after:
                    sections[current_label].append(after)
        else:
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
