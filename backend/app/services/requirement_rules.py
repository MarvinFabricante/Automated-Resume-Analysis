"""
Shared Requirement Normalization & Hierarchy Rules (Single Source of Truth)
--------------------------------------------------------------------------
Centralizes:
1. No-value ("None", "N/A", "wala", "-", empty, etc.) normalization for job
   requirements and resume fields across all criteria.
2. Configurable 1-8 Philippine education-level ranking, punctuation-tolerant
   alias resolution, ongoing/undergraduate completion rules, and field checks.
3. Graded certification / license hierarchies (e.g., TESDA NC I-IV, DOLE SO1-4,
   Six Sigma belts, CSC eligibility).
4. Standardized plain-language criterion status labels.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Standardized Criterion Status Labels ─────────────────────────────────────

STATUS_MEETS = "Meets requirement"
STATUS_EXCEEDS = "Exceeds requirement"
STATUS_PARTIAL = "Partially meets"
STATUS_NOT_REQUIRED = "Not required"
STATUS_MANUAL_REVIEW = "Needs manual review"
STATUS_DOES_NOT_MEET = "Does not meet"

VALID_CRITERION_STATUSES = (
    STATUS_MEETS,
    STATUS_EXCEEDS,
    STATUS_PARTIAL,
    STATUS_NOT_REQUIRED,
    STATUS_MANUAL_REVIEW,
    STATUS_DOES_NOT_MEET,
)


def format_criterion_reason(status: str, detail: str = "") -> str:
    """Prefix a plain-language reason with one of the standardized criterion statuses."""
    clean_detail = re.sub(r"\s+", " ", str(detail or "")).strip()
    if not clean_detail:
        return status
    prefix = f"{status}:"
    if clean_detail.lower().startswith(prefix.lower()):
        return clean_detail
    return f"{status}: {clean_detail}"


def extract_criterion_status(reason: Optional[str]) -> Optional[str]:
    """Extract the leading standardized status label from a reason string, if present."""
    if not reason:
        return None
    text = str(reason).strip()
    low = text.lower()
    for status in VALID_CRITERION_STATUSES:
        s_low = status.lower()
        if low == s_low or low.startswith(f"{s_low}:"):
            return status
    return None


# ─── Configurable No-Value Normalization ──────────────────────────────────────

NO_VALUE_MARKERS: frozenset[str] = frozenset({
    "",
    "none",
    "none required",
    "none specified",
    "none provided",
    "none yet",
    "n/a",
    "na",
    "n.a",
    "not applicable",
    "not required",
    "not specified",
    "not provided",
    "no requirement",
    "no requirements",
    "no specific requirement",
    "no specific requirements",
    "no education required",
    "no education provided",
    "no experience required",
    "no experience provided",
    "no work experience required",
    "no skills required",
    "no certification",
    "no certifications",
    "no certification found",
    "no certification required",
    "no certifications required",
    "no specific certification",
    "no specific certifications",
    "no specific certification required",
    "no specific certifications required",
    "no experience",
    "no work experience",
    "no prior experience",
    "no relevant experience",
    "no",
    "wala",
    "walang requirement",
    "nil",
    "null",
    "unspecified",
    "unknown",
    "any",
    "optional",
    "-",
    "--",
    "---",
})


def normalize_requirement_text(value: Any) -> Optional[str]:
    """
    Normalize a single requirement or extracted resume field value.

    Returns None when the WHOLE value (case-insensitive, trimmed, tolerant of
    trailing punctuation and internal whitespace) matches a configured no-value
    marker; otherwise returns the whitespace-collapsed string intact.
    Real requirements that merely contain 'none' in a larger sentence (e.g.
    'None of the above, but must know Excel') are preserved.
    """
    if value is None:
        return None

    collapsed = re.sub(r"\s+", " ", str(value)).strip()
    if not collapsed:
        return None

    # Pure punctuation / dashes like "-", "--", "...", "/"
    if re.fullmatch(r"[-–—_./,\s]+", collapsed):
        return None

    # Build comparison key tolerant of trailing periods/punctuation and spaces around '/'
    key = re.sub(r"\s*/\s*", "/", collapsed).lower()
    key = re.sub(r"[.\s,;:!?]+$", "", key).strip()

    if key in NO_VALUE_MARKERS:
        return None

    return collapsed


def is_no_value(value: Any) -> bool:
    """Return True if value represents 'no requirement' / 'none provided'."""
    if isinstance(value, (list, tuple, set)):
        return len(clean_list_items(value)) == 0
    return normalize_requirement_text(value) is None


def clean_list_items(items: Any, delimiter_pattern: str = r"[|,\n;•]") -> list[str]:
    """
    Split and normalize a string or collection of items, dropping empty items and
    any standalone no-value markers (e.g. 'None', 'N/A', 'wala', '-').
    """
    if not items:
        return []

    raw_items: list[str] = []
    if isinstance(items, (list, tuple, set)):
        for item in items:
            if isinstance(item, dict):
                val = (
                    item.get("canonical_name")
                    or item.get("skill_name")
                    or item.get("name")
                    or ""
                )
                if val:
                    raw_items.extend(re.split(delimiter_pattern, str(val)))
            elif item is not None:
                raw_items.extend(re.split(delimiter_pattern, str(item)))
    else:
        raw_items = re.split(delimiter_pattern, str(items))

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        norm = normalize_requirement_text(raw)
        if not norm:
            continue
        low = norm.lower()
        if low not in seen:
            seen.add(low)
            cleaned.append(norm)
    return cleaned


# ─── Configurable Philippine Education-Level Hierarchy (1-8) ──────────────────
# Edit this dictionary (and EDUCATION_SHORT_LABELS / ONGOING_COMPLETED_LEVEL_MAP)
# to adjust the Philippine education ranking in one place.

EDUCATION_LEVELS: dict[int, str] = {
    1: "Elementary",
    2: "High School (Junior High School)",
    3: "Senior High School",
    4: "Vocational / TESDA / Technical-Vocational",
    5: "Associate / Short course (2-year)",
    6: "Bachelor's degree",
    7: "Post-graduate certificate / Master's",
    8: "Doctorate",
}

EDUCATION_SHORT_LABELS: dict[int, str] = {
    1: "Elementary",
    2: "High School",
    3: "Senior High School",
    4: "Vocational / TESDA",
    5: "Associate degree",
    6: "Bachelor's degree",
    7: "Master's degree",
    8: "Doctorate",
}

# Configurable education scoring parameters
EDUCATION_PARTIAL_SCORE_MODE = "proportional"  # candidate_level / required_level
EDUCATION_MANUAL_REVIEW_SCORE = 0.5
EDUCATION_LEVEL_MET_WRONG_FIELD_SCORE = 0.4
EDUCATION_LEVEL_MET_UNSPECIFIED_FIELD_SCORE = 0.5
EDUCATION_RELATED_FIELD_SCORE = 0.8
EDUCATION_PARTIAL_FIELD_SCORE = 0.65

# Highest level fully completed when a candidate is currently enrolled / undergraduate
ONGOING_COMPLETED_LEVEL_MAP: dict[int, int] = {
    8: 7,  # PhD student -> Master's completed
    7: 6,  # Master's student -> Bachelor's completed
    6: 3,  # College undergraduate -> Senior High School completed
    5: 3,  # Associate student -> Senior High School completed
    4: 3,  # Tech-Voc trainee -> Senior High School completed
    3: 2,  # SHS student -> Junior High School completed
    2: 1,  # JHS student -> Elementary completed
    1: 0,
}

# Canonical acronyms (after stripping periods) -> (education level, implied field or None)
DEGREE_ACRONYM_FIELDS: dict[str, tuple[int, Optional[str]]] = {
    # Doctorate (8)
    "phd": (8, None),
    "edd": (8, "education"),
    "dba": (8, "business administration"),
    "dmd": (8, "dental medicine"),
    # Master's / Post-graduate (7)
    "mba": (7, "business administration"),
    "mpa": (7, "public administration"),
    "mit": (7, "information technology"),
    "msit": (7, "information technology"),
    "mscs": (7, "computer science"),
    "maed": (7, "education"),
    "meng": (7, "engineering"),
    "mfa": (7, "fine arts"),
    "llm": (7, "law"),
    "jd": (7, "law"),
    "md": (7, "medicine"),
    "ms": (7, None),
    "ma": (7, None),
    "msc": (7, None),
    # Bachelor's (6)
    "bsba": (6, "business administration"),
    "bsit": (6, "information technology"),
    "bscs": (6, "computer science"),
    "bsis": (6, "information systems"),
    "bsa": (6, "accountancy"),
    "bsma": (6, "management accounting"),
    "bsat": (6, "accounting technology"),
    "bsce": (6, "civil engineering"),
    "bsme": (6, "mechanical engineering"),
    "bsee": (6, "electrical engineering"),
    "bsece": (6, "electronics engineering"),
    "bsie": (6, "industrial engineering"),
    "bsche": (6, "chemical engineering"),
    "bscpe": (6, "computer engineering"),
    "bsmse": (6, "materials science engineering"),
    "bsn": (6, "nursing"),
    "bsmls": (6, "medical laboratory science"),
    "bshm": (6, "hospitality management"),
    "bshrm": (6, "hospitality management"),
    "bstm": (6, "tourism management"),
    "bsca": (6, "customs administration"),
    "bscrim": (6, "criminology"),
    "bsed": (6, "secondary education"),
    "beed": (6, "elementary education"),
    "bspsych": (6, "psychology"),
    "bsarch": (6, "architecture"),
    "bsarchi": (6, "architecture"),
    "bsbio": (6, "biology"),
    "bschem": (6, "chemistry"),
    "bsmath": (6, "mathematics"),
    "bsstat": (6, "statistics"),
    "bs": (6, None),
    "ba": (6, None),
    "ab": (6, None),
    "bsc": (6, None),
    "llb": (6, "law"),
    # Associate (5)
    "act": (5, "computer technology"),
}

_DOT_ABBR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bph\.?\s*d\.?", re.I), "phd"),
    (re.compile(r"\bed\.?\s*d\.?", re.I), "edd"),
    (re.compile(r"\bd\.?\s*b\.?\s*a\.?", re.I), "dba"),
    (re.compile(r"\bm\.?\s*b\.?\s*a\.?", re.I), "mba"),
    (re.compile(r"\bm\.?\s*p\.?\s*a\.?", re.I), "mpa"),
    (re.compile(r"\bm\.?\s*i\.?\s*t\.?", re.I), "mit"),
    (re.compile(r"\bm\.?\s*s\.?\s*i\.?\s*t\.?", re.I), "msit"),
    (re.compile(r"\bm\.?\s*s\.?\s*c\.?\s*s\.?", re.I), "mscs"),
    (re.compile(r"\bm\.?\s*a\.?\s*ed\.?", re.I), "maed"),
    (re.compile(r"\bm\.?\s*sc\.?", re.I), "msc"),
    (re.compile(r"\bm\.?\s*s\.?", re.I), "ms"),
    (re.compile(r"\bm\.?\s*a\.?", re.I), "ma"),
    (re.compile(r"\bm\.?\s*d\.?", re.I), "md"),
    (re.compile(r"\bj\.?\s*d\.?", re.I), "jd"),
    (re.compile(r"\bll\.?\s*b\.?", re.I), "llb"),
    (re.compile(r"\bb\.?\s*s\.?\s*b\.?\s*a\.?", re.I), "bsba"),
    (re.compile(r"\bb\.?\s*s\.?\s*i\.?\s*t\.?", re.I), "bsit"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*s\.?", re.I), "bscs"),
    (re.compile(r"\bb\.?\s*s\.?\s*i\.?\s*s\.?", re.I), "bsis"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*p\.?\s*e\.?", re.I), "bscpe"),
    (re.compile(r"\bb\.?\s*s\.?\s*e\.?\s*c\.?\s*e\.?", re.I), "bsece"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*h\.?\s*e\.?", re.I), "bsche"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*e\.?", re.I), "bsce"),
    (re.compile(r"\bb\.?\s*s\.?\s*m\.?\s*e\.?", re.I), "bsme"),
    (re.compile(r"\bb\.?\s*s\.?\s*e\.?\s*e\.?", re.I), "bsee"),
    (re.compile(r"\bb\.?\s*s\.?\s*i\.?\s*e\.?", re.I), "bsie"),
    (re.compile(r"\bb\.?\s*s\.?\s*h\.?\s*r\.?\s*m\.?", re.I), "bshrm"),
    (re.compile(r"\bb\.?\s*s\.?\s*h\.?\s*m\.?", re.I), "bshm"),
    (re.compile(r"\bb\.?\s*s\.?\s*t\.?\s*m\.?", re.I), "bstm"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*a\.?", re.I), "bsca"),
    (re.compile(r"\bb\.?\s*s\.?\s*c\.?\s*r\.?\s*i\.?\s*m\.?", re.I), "bscrim"),
    (re.compile(r"\bb\.?\s*s\.?\s*e\.?\s*d\.?", re.I), "bsed"),
    (re.compile(r"\bb\.?\s*e\.?\s*e\.?\s*d\.?", re.I), "beed"),
    (re.compile(r"\bb\.?\s*s\.?\s*a\.?", re.I), "bsa"),
    (re.compile(r"\bb\.?\s*s\.?\s*n\.?", re.I), "bsn"),
    (re.compile(r"\bb\.?\s*sc\.?", re.I), "bsc"),
    (re.compile(r"\bb\.?\s*s\.?", re.I), "bs"),
    (re.compile(r"\bb\.?\s*a\.?", re.I), "ba"),
    (re.compile(r"\ba\.?\s*b\.?", re.I), "ab"),
]

# Non-education phrases that start with "MS" (Microsoft software tools)
_MS_SOFTWARE_RE = re.compile(
    r"\bms\s+(?:office|word|excel|powerpoint|outlook|access|project|teams|visio|publisher|sql|windows|dos)\b",
    re.I,
)

# Phrases indicating ongoing / incomplete status on a resume education entry
_ONGOING_STATUS_RE = re.compile(
    r"\b(?:currently\s+(?:enrolled|studying|taking|pursuing)|"
    r"ongoing|in\s+progress|continuing|"
    r"undergraduate|undergrad|"
    r"(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth)\s+year"
    r"(?:\s+(?:college|university|shs|senior\s+high|high\s+school|vocational|associate|student|level|irregular))?|"
    r"college\s+level|units\s+earned|"
    r"(?:19|20)\d{2}\s*[-–—to]+\s*(?:present|current))\b",
    re.I,
)

# "Undergraduate degree" in a job description means a Bachelor's degree, not incomplete college
_UNDERGRADUATE_DEGREE_RE = re.compile(r"\bundergraduate\s+degree\b", re.I)

# Compound / precedence-sensitive patterns checked before generic keywords
_COMPOUND_LEVEL_RULES: list[tuple[int, re.Pattern[str]]] = [
    # Doctorate (8)
    (8, re.compile(r"\b(?:phd|doctorate|doctoral|post[-\s]?doc(?:toral)?|doctor\s+of\s+[a-z]+|edd|dba|dmd)\b", re.I)),
    # Post-graduate / Master's (7) - includes "graduate diploma", "postgraduate certificate"
    (7, re.compile(
        r"\b(?:post[-\s]?grad(?:uate)?(?:\s+(?:certificate|diploma|degree|studies))?|"
        r"graduate\s+(?:certificate|diploma|degree|studies)|"
        r"master(?:'?s|al)?(?:\s+(?:degree|of|in))?|mba|mpa|msit|mscs|maed|meng|mfa|llm|juris\s+doctor|jd)\b",
        re.I,
    )),
    # Bachelor's (6) - includes "Bachelor of Elementary/Secondary Education" before Elementary/Secondary
    (6, re.compile(
        r"\b(?:bachelor(?:'?s)?(?:\s+(?:degree|of|in))?|baccalaureate|"
        r"college\s+(?:graduate|degree|diploma)|university\s+(?:graduate|degree)|"
        r"(?:4|four)[-\s]?year\s+(?:college|degree|course)|undergraduate\s+degree|"
        r"bsba|bsit|bscs|bsis|bsa|bsma|bsat|bsce|bsme|bsee|bsece|bsie|bsche|bscpe|bsmse|"
        r"bsn|bsmls|bshm|bshrm|bstm|bsca|bscrim|bsed|beed|bspsych|bsarch|bsarchi|bsbio|bschem|bsmath|bsstat|llb|"
        r"bs|ba|ab|bsc)\b",
        re.I,
    )),
    # Associate / 2-year (5)
    (5, re.compile(
        r"\b(?:associate(?:'?s)?(?:\s+(?:degree|of|in))?|"
        r"(?:2|two)[-\s]?year\s+(?:degree|course|college(?:\s+level)?|diploma|program)|"
        r"short\s+course)\b",
        re.I,
    )),
    # Senior High School (3) - must precede High School (2) and Diploma (4)
    (3, re.compile(
        r"\b(?:senior\s+high(?:\s+school)?(?:\s+(?:graduate|diploma|completer))?|"
        r"shs(?:\s+(?:graduate|diploma))?|"
        r"k[-\s]?(?:to[-\s]?)?12|"
        r"grade\s*(?:11|12)|gr\.?\s*(?:11|12)|"
        r"(?:stem|abm|humss)\s*(?:strand|track)?|"
        r"(?:general\s+academic|tvl)\s+(?:strand|track))\b",
        re.I,
    )),
    # Junior High School / High School (2) - "High School Diploma" must precede generic "Diploma" (4)
    (2, re.compile(
        r"\b(?:junior\s+high(?:\s+school)?(?:\s+(?:graduate|completer|diploma))?|"
        r"jhs|"
        r"high\s+school(?:\s+(?:graduate|diploma|completer))?|"
        r"hs\s+(?:graduate|diploma)|"
        r"secondary(?:\s+(?:education|school|graduate|diploma))?|"
        r"als\s+completer|alternative\s+learning\s+system|"
        r"grade\s*(?:7|8|9|10)|gr\.?\s*(?:7|8|9|10))\b",
        re.I,
    )),
    # Vocational / TESDA / Tech-Voc (4)
    (4, re.compile(
        r"\b(?:tesda|tech[-\s]?voc|technical[-\s]?vocational|vocational|tvet|"
        r"nc\s*(?:i|ii|iii|iv|1|2|3|4)|nc(?:i|ii|iii|iv)|"
        r"national\s+certificate(?:\s+(?:i|ii|iii|iv|1|2|3|4))?|"
        r"trade\s+(?:course|school|certificate)|diploma)\b",
        re.I,
    )),
    # Elementary (1)
    (1, re.compile(
        r"\b(?:elementary(?:\s+(?:school|education|graduate))?|"
        r"primary\s+(?:school|education|graduate)|grade\s+school|"
        r"grade\s*[1-6]|gr\.?\s*[1-6])\b",
        re.I,
    )),
]

# Case-sensitive short acronyms that would collide with common lowercase words
_CASE_SENSITIVE_LEVEL_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (5, re.compile(r"\bACT\b")),  # Associate in Computer Technology
    (3, re.compile(r"\b(?:GAS|TVL)\b")),  # SHS strands
]

# Generic "ms" / "ma" / "md" / "doctor" checks
_FALLBACK_LEVEL_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (8, re.compile(r"\bdoctor\b", re.I)),
    (7, re.compile(r"\b(?:ms|ma|msc|md)\b", re.I)),
    # "College" alone (e.g., "currently enrolled in college", "2nd year college") implies level 6 target
    (6, re.compile(r"\bcollege\b", re.I)),
]

# Canonical field synonyms & related field groups
EDUCATION_FIELD_SYNONYMS: dict[str, str] = {
    "accountancy": "accounting",
    "accounting": "accounting",
    "management accounting": "accounting",
    "accounting technology": "accounting",
    "information technology": "information technology",
    "it": "information technology",
    "computer science": "computer science",
    "cs": "computer science",
    "human resources": "human resource",
    "human resource": "human resource",
    "human resource management": "human resource",
    "human resource development management": "human resource",
    "hr": "human resource",
    "hrdm": "human resource",
    "hrm": "human resource",
    "business administration": "business administration",
    "hrm hospitality": "hospitality management",
    "hotel and restaurant management": "hospitality management",
    "hospitality management": "hospitality management",
    "math": "mathematics",
    "mathematics": "mathematics",
    "stats": "statistics",
    "statistics": "statistics",
    "comm": "communication",
    "communications": "communication",
    "communication": "communication",
    "psych": "psychology",
    "psychology": "psychology",
    "archi": "architecture",
    "architecture": "architecture",
    "crim": "criminology",
    "criminology": "criminology",
}

RELATED_EDUCATION_FIELDS: dict[str, list[str]] = {
    "computer science": [
        "information technology", "software engineering", "computer engineering",
        "information systems", "computing", "data science", "computer technology",
    ],
    "information technology": [
        "computer science", "software engineering", "computer engineering",
        "information systems", "computing", "computer technology",
    ],
    "business administration": [
        "management", "administration", "commerce", "finance", "accounting",
        "marketing", "entrepreneurship", "economics", "operations management",
        "human resource", "supply chain",
    ],
    "business": [
        "business administration", "management", "commerce", "finance", "accounting",
        "marketing", "entrepreneurship", "economics", "supply chain",
    ],
    "accounting": [
        "finance", "financial management", "business administration",
        "commerce", "banking", "economics", "auditing",
    ],
    "engineering": [
        "mechanical", "electrical", "electronics", "civil", "chemical",
        "industrial", "ceramic", "materials", "metallurgical", "computer engineering",
        "software", "industrial technology", "mechatronics",
    ],
    "chemical engineering": ["chemistry", "materials engineering", "ceramic engineering", "industrial engineering"],
    "mechanical engineering": ["industrial engineering", "electrical engineering", "mechatronics", "mechanical technology"],
    "electrical engineering": ["electronics engineering", "mechanical engineering", "electrical technology"],
    "industrial engineering": ["mechanical engineering", "manufacturing", "operations management", "chemical engineering"],
    "chemistry": ["chemical engineering", "chemical", "biochemistry", "materials", "ceramic", "industrial technology"],
    "human resource": ["psychology", "business administration", "management", "behavioral science", "organizational"],
    "psychology": ["human resource", "business administration", "behavioral science", "guidance"],
    "marketing": ["business administration", "commerce", "management", "communication", "advertising", "entrepreneurship"],
    "supply chain": ["logistics", "business administration", "industrial engineering", "operations management", "procurement"],
    "statistics": ["mathematics", "economics", "computer science", "data science", "data analysis"],
    "mathematics": ["statistics", "economics", "computer science", "engineering"],
    "fine arts": ["multimedia arts", "graphic design", "advertising", "communication"],
    "multimedia arts": ["fine arts", "graphic design", "communication"],
}

_GENERIC_FIELD_STOPWORDS: frozenset[str] = frozenset({
    "bachelor", "bachelors", "master", "masters", "masteral", "doctorate", "doctor",
    "associate", "associates", "diploma", "vocational", "technical", "tech", "tesda",
    "senior", "junior", "high", "school", "shs", "jhs", "secondary", "elementary", "primary",
    "college", "university", "colleges", "institute", "academy", "polytechnic", "campus",
    "degree", "course", "program", "curriculum", "strand", "track", "certificate", "certification",
    "nc", "i", "ii", "iii", "iv", "k12", "phd", "edd", "dba", "dmd", "bs", "ba", "ab", "ms", "ma", "msc",
    "bsc", "act", "grade", "grades", "gr", "als", "alternative", "learning", "system",
    "of", "in", "the", "at", "or", "and", "with", "from", "for", "to", "by", "on", "as", "a", "an",
    "any", "all", "related", "relevant", "field", "fields", "discipline", "disciplines",
    "equivalent", "similar", "minimum", "least", "preferred", "required", "must", "have",
    "holder", "level", "year", "years", "yr", "yrs", "four", "two", "short",
    "completer", "undergraduate", "undergrad", "graduate", "graduated", "postgraduate",
    "majoring", "major", "currently", "enrolled", "studying", "pursuing", "ongoing",
    "present", "current", "student", "irregular", "units", "earned", "status",
    "advantage", "plus", "desirable", "bonus", "attainment", "educational", "education",
    "background", "qualification", "qualifications", "academic", "general", "studies", "applied",
    "honors", "cum", "laude", "magna", "summa", "stem", "abm", "humss", "gas", "tvl",
    "1st", "2nd", "3rd", "4th", "5th", "first", "second", "third", "fourth", "fifth",
    "none", "na", "wala", "nil", "null",
} | set(DEGREE_ACRONYM_FIELDS.keys()))

_INSTITUTION_STRIP_RE = re.compile(
    r"(?:\s+[-–—|,]\s*|\s+(?:at|from)\s+)"
    r"[^,|\n;()]+?\b(?:University|College|Colleges|Institute|School|Academy|Polytechnic|TESDA|Campus|Training\s+Center)\b"
    r"[^|;\n]*",
    re.I,
)


def _normalize_edu_text_for_matching(text: str) -> str:
    """Normalize punctuation and dotted degree acronyms for boundary-safe regex matching."""
    if not text:
        return ""
    s = str(text).replace("’", "'").replace("‘", "'")
    s = _MS_SOFTWARE_RE.sub(" ", s)
    for pat, repl in _DOT_ABBR_PATTERNS:
        s = pat.sub(repl, s)
    s = re.sub(r"\bk\s*[-–—]?\s*(?:to\s+)?12\b", "k12", s, flags=re.I)
    s = re.sub(r"\bpost[-\s]+grad(?:uate)?\b", "postgraduate", s, flags=re.I)
    s = re.sub(r"\btech(?:nical)?[-\s]+voc(?:ational)?\b", "technical vocational", s, flags=re.I)
    s = re.sub(r"\b([a-z]+)'s\b", r"\1", s, flags=re.I)
    s = re.sub(r"[,.;:()\[\]/|]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _detect_raw_level(norm_text: str, raw_text: str = "") -> Optional[int]:
    """Detect the primary education level (1-8) from a normalized text fragment."""
    if not norm_text:
        return None

    # Check compound rules in precedence order (highest / most specific first)
    for lvl, pat in _COMPOUND_LEVEL_RULES:
        if pat.search(norm_text):
            return lvl

    for lvl, pat in _CASE_SENSITIVE_LEVEL_PATTERNS:
        if pat.search(raw_text or norm_text):
            return lvl

    for lvl, pat in _FALLBACK_LEVEL_PATTERNS:
        if pat.search(norm_text):
            return lvl

    return None


def _strip_institution_suffix_if_degree_remains(text: str) -> str:
    """Strip institution names like '- Far Eastern University' when a degree/level phrase precedes it."""
    if not text:
        return ""
    # Only strip when institution follows a separator (-, |, ,) and precedes nothing degree-like
    m = re.split(
        r"\s+[-–—|]\s+(?=[A-Za-z0-9.\"'&\s]*\b(?:University|College|Colleges|Institute|School|Academy|Polytechnic|Campus|Training\s+Center)\b)",
        text,
        maxsplit=1,
        flags=re.I,
    )
    if len(m) == 2 and m[0].strip():
        left = m[0].strip()
        if _detect_raw_level(_normalize_edu_text_for_matching(left), left) is not None:
            return left
    return text


def _strip_non_mandatory_advantage_clauses(text: str) -> str:
    """Remove optional 'Master's is an advantage / preferred / plus' sentences from job requirements."""
    parts = re.split(r"(?<=[.!?])\s+|\s*;\s*", text)
    mandatory = [
        p for p in parts
        if p.strip()
        and not re.search(
            r"\b(?:is\s+an\s+advantage|an\s+advantage|is\s+a\s+plus|a\s+plus|preferred|desirable)\b",
            p,
            re.I,
        )
    ]
    return " ".join(mandatory).strip() if mandatory else text


def _canonicalize_field_phrase(phrase: str) -> str:
    """Normalize a course/major phrase and apply canonical field synonyms."""
    cleaned = _normalize_edu_text_for_matching(phrase)
    # Remove trailing "or equivalent experience"
    cleaned = re.sub(r"\bor\s+equivalent(?:\s+experience)?\b.*$", "", cleaned, flags=re.I).strip()
    tokens = [
        t for t in re.findall(r"[a-z0-9]+", cleaned.lower())
        if len(t) >= 2 and not t.isdigit() and t not in _GENERIC_FIELD_STOPWORDS
    ]
    joined = " ".join(tokens).strip()
    if not joined:
        return ""
    return EDUCATION_FIELD_SYNONYMS.get(joined, joined)


def extract_education_fields(text: str) -> list[str]:
    """
    Extract required or held field(s) of study from education text.
    Returns an empty list when no specific course/major is specified (e.g. 'SHS',
    'College graduate', 'Bachelor's degree in any field', 'currently enrolled in college').
    """
    norm_raw = normalize_requirement_text(text)
    if not norm_raw:
        return []

    if re.search(r"\b(?:any\s+(?:field|course|degree|discipline|major)|in\s+any\s+field)\b", norm_raw, re.I):
        return []

    # Strip institution suffixes before field extraction
    work = _strip_institution_suffix_if_degree_remains(norm_raw)
    work = re.sub(r"\b(?:19|20)\d{2}\b", " ", work)
    work = _INSTITUTION_STRIP_RE.sub(" ", work)
    work = _MS_SOFTWARE_RE.sub(" ", work)
    work = _strip_non_mandatory_advantage_clauses(work)

    # Check degree acronyms that inherently encode a field (e.g. BSBA, BSIT, MBA)
    norm_for_acr = _normalize_edu_text_for_matching(work)
    fields: list[str] = []
    seen: set[str] = set()

    def _add_field(candidate: str) -> None:
        canon = EDUCATION_FIELD_SYNONYMS.get(candidate.strip().lower(), candidate.strip().lower())
        if canon and canon not in _GENERIC_FIELD_STOPWORDS and canon not in seen:
            seen.add(canon)
            fields.append(canon)

    for tok in re.findall(r"[a-z0-9]+", norm_for_acr.lower()):
        if tok in DEGREE_ACRONYM_FIELDS:
            _, implied = DEGREE_ACRONYM_FIELDS[tok]
            if implied:
                _add_field(implied)

    # Extract explicit "in <field(s)>" or "major in <field(s)>" clauses
    m_in = re.search(
        r"\b(?:major\s+in|specializing\s+in|bachelor(?:'?s)?(?:\s+of\s+(?:science|arts|secondary|elementary))?\s+in|"
        r"master(?:'?s)?(?:\s+of\s+(?:science|arts))?\s+in|associate(?:'?s)?\s+in|diploma\s+in|"
        r"vocational\s+(?:course|program|training)\s+in|bs|ba|ab|ms|ma|in)\s+([^.|;\n]+)",
        norm_raw,
        re.I,
    )
    clause = m_in.group(1).strip() if m_in else work

    # Split comma / "or" / "/" alternatives while preserving trailing shared head noun
    # e.g. "Chemical, Mechanical, or Industrial Engineering" -> each gets "engineering"
    alt_parts = [
        p.strip()
        for p in re.split(r"\s*,\s*(?:or\s+)?|\s+(?:or|and/or)\s+|/", clause, flags=re.I)
        if p.strip()
    ]
    cleaned_alts = [_canonicalize_field_phrase(p) for p in alt_parts]
    cleaned_alts = [p for p in cleaned_alts if p]

    if len(cleaned_alts) > 1:
        last_words = cleaned_alts[-1].split()
        head_noun = last_words[-1] if len(last_words) >= 2 else ""
        if head_noun in {"engineering", "technology", "management", "science", "administration", "education", "arts"}:
            expanded_alts: list[str] = []
            for idx, alt in enumerate(cleaned_alts):
                if idx < len(cleaned_alts) - 1 and head_noun not in alt.split():
                    expanded_alts.append(f"{alt} {head_noun}")
                else:
                    expanded_alts.append(alt)
            cleaned_alts = expanded_alts

    for alt in cleaned_alts:
        _add_field(alt)

    # If still empty, try stripping generic words from whole text
    if not fields:
        whole = _canonicalize_field_phrase(work)
        if whole:
            _add_field(whole)

    return fields


def _parse_single_education_segment(
    text: str,
    is_job_requirement: bool = False,
    explicit_status: Optional[str] = None,
) -> dict[str, Any]:
    """Parse a single education string/entry into level, ongoing flag, pursuing level, and fields."""
    norm_raw = normalize_requirement_text(text)
    if not norm_raw:
        return {
            "level": None,
            "label": None,
            "pursuing_level": None,
            "is_ongoing": False,
            "field_options": [],
            "recognized": False,
            "is_no_value": True,
        }

    eval_text = _strip_non_mandatory_advantage_clauses(norm_raw) if is_job_requirement else norm_raw
    eval_text = _strip_institution_suffix_if_degree_remains(eval_text)

    # Handle job requirement alternatives separated by "or" (e.g. "Bachelor's degree or 2-year college level")
    if is_job_requirement and re.search(r"\s+or\s+|/", eval_text, re.I):
        # Only split on "or" when multiple sides specify distinct education levels
        parts = [p.strip() for p in re.split(r"\s+or\s+|/", eval_text, flags=re.I) if p.strip()]
        sub_levels = []
        for part in parts:
            part_norm = _normalize_edu_text_for_matching(part)
            lvl = _detect_raw_level(part_norm, part)
            if lvl is not None:
                sub_levels.append(lvl)
        if len(sub_levels) >= 2:
            min_lvl = min(sub_levels)
            fields = extract_education_fields(eval_text)
            return {
                "level": min_lvl,
                "label": EDUCATION_SHORT_LABELS[min_lvl],
                "pursuing_level": min_lvl,
                "is_ongoing": False,
                "field_options": fields,
                "recognized": True,
                "is_no_value": False,
            }

    norm_match = _normalize_edu_text_for_matching(eval_text)
    raw_level = _detect_raw_level(norm_match, eval_text)

    # Determine ongoing / undergraduate status
    is_ongoing = False
    if explicit_status:
        st_low = explicit_status.strip().lower()
        if any(k in st_low for k in ("ongoing", "undergrad", "college level", "enrolled", "in progress")):
            is_ongoing = True
    elif not is_job_requirement:
        if _ONGOING_STATUS_RE.search(eval_text):
            is_ongoing = True
    else:
        # On job side, "undergraduate degree" = Bachelor's (completed), whereas
        # "college undergraduate" / "2nd year college" without "degree" = level 3
        if not _UNDERGRADUATE_DEGREE_RE.search(eval_text) and _ONGOING_STATUS_RE.search(eval_text):
            is_ongoing = True

    if is_ongoing:
        pursuing = raw_level or 6
        completed = ONGOING_COMPLETED_LEVEL_MAP.get(pursuing, 3)
        fields = extract_education_fields(eval_text)
        return {
            "level": completed,
            "label": EDUCATION_SHORT_LABELS.get(completed, "High School"),
            "pursuing_level": pursuing,
            "is_ongoing": True,
            "field_options": fields,
            "recognized": True,
            "is_no_value": False,
        }

    if raw_level is None:
        return {
            "level": None,
            "label": None,
            "pursuing_level": None,
            "is_ongoing": False,
            "field_options": [],
            "recognized": False,
            "is_no_value": False,
        }

    fields = extract_education_fields(eval_text)
    return {
        "level": raw_level,
        "label": EDUCATION_SHORT_LABELS[raw_level],
        "pursuing_level": raw_level,
        "is_ongoing": False,
        "field_options": fields,
        "recognized": True,
        "is_no_value": False,
    }


def parse_education_level(
    text: Any,
    is_job_requirement: bool = False,
    entries: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Normalize job or resume education into a 1-8 level dict:
      {
        "level": int | None,
        "label": str | None,
        "pursuing_level": int | None,
        "is_ongoing": bool,
        "field_options": list[str],
        "recognized": bool,
        "is_no_value": bool,
      }
    When multiple resume entries or pipe/newline segments exist, selects the
    highest completed level across all entries.
    """
    entry_segments: list[tuple[str, Optional[str]]] = []
    text_segments: list[tuple[str, Optional[str]]] = []

    if isinstance(entries, list) and entries and not is_job_requirement:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            pieces = [
                entry.get("degree_or_course"),
                entry.get("raw_degree_or_course"),
                entry.get("education_level"),
                entry.get("major_or_specialization"),
            ]
            combined = " ".join(str(p).strip() for p in pieces if p and not is_no_value(p))
            if combined:
                entry_segments.append((combined, entry.get("status")))

    raw_str = normalize_requirement_text(text)
    if raw_str:
        if is_job_requirement:
            text_segments.append((raw_str, None))
        else:
            for part in re.split(r"[|\n;]+", raw_str):
                if normalize_requirement_text(part):
                    text_segments.append((part.strip(), None))

    if not entry_segments and not text_segments:
        return {
            "level": None,
            "label": None,
            "pursuing_level": None,
            "is_ongoing": False,
            "field_options": [],
            "recognized": False,
            "is_no_value": True,
        }

    parsed_entries = [
        _parse_single_education_segment(seg_text, is_job_requirement=False, explicit_status=seg_status)
        for seg_text, seg_status in entry_segments
    ]
    recognized_entries = [p for p in parsed_entries if p["recognized"] and p["level"] is not None]

    parsed_text = [
        _parse_single_education_segment(seg_text, is_job_requirement=is_job_requirement, explicit_status=seg_status)
        for seg_text, seg_status in text_segments
    ]
    recognized_text = [p for p in parsed_text if p["recognized"] and p["level"] is not None]

    # When structured education_entries carry recognized levels and enrollment status,
    # prefer them so an ongoing/undergraduate entry isn't overwritten by a bare degree string.
    if recognized_entries:
        recognized = recognized_entries
        if not any(p["field_options"] for p in recognized) and recognized_text:
            for p in recognized:
                for tp in recognized_text:
                    if tp["field_options"] and (tp["pursuing_level"] == p["pursuing_level"] or tp["level"] == p["level"]):
                        p["field_options"] = list(tp["field_options"])
                        break
    else:
        recognized = recognized_text

    if not recognized:
        return {
            "level": None,
            "label": None,
            "pursuing_level": None,
            "is_ongoing": False,
            "field_options": [],
            "recognized": False,
            "is_no_value": False,
        }

    # Prefer highest completed level; break ties in favor of completed (non-ongoing) and richer field info
    best = max(
        recognized,
        key=lambda p: (
            p["level"] or 0,
            0 if p["is_ongoing"] else 1,
            len(p["field_options"]),
        ),
    )

    # Collect field options from entries matching the best level (or ongoing entry at/above best)
    all_fields: list[str] = []
    seen_fields: set[str] = set()
    for p in recognized:
        if p["level"] == best["level"] or (p["is_ongoing"] and (p["pursuing_level"] or 0) > (best["level"] or 0)):
            for f in p["field_options"]:
                if f not in seen_fields:
                    seen_fields.add(f)
                    all_fields.append(f)

    # Track highest ongoing pursuing level if candidate has an ongoing higher program
    max_ongoing = max(
        (p for p in recognized if p["is_ongoing"]),
        key=lambda p: p["pursuing_level"] or 0,
        default=None,
    )
    pursuing_level = best["pursuing_level"]
    is_ongoing = best["is_ongoing"]
    if max_ongoing and (max_ongoing["pursuing_level"] or 0) > (best["level"] or 0):
        pursuing_level = max_ongoing["pursuing_level"]
        is_ongoing = True

    return {
        "level": best["level"],
        "label": best["label"],
        "pursuing_level": pursuing_level,
        "is_ongoing": is_ongoing,
        "field_options": all_fields or best["field_options"],
        "parsed_entries": recognized,
        "recognized": True,
        "is_no_value": False,
    }


def map_education_level_to_ml_rank(level: Optional[int]) -> int:
    """
    Map the 1-8 education level onto the 0-4 tabular ML classifier rank:
      8 (Doctorate) -> 4
      7 (Master's) -> 3
      6 (Bachelor's) -> 2
      4-5 (Vocational / Associate) -> 1
      1-3 / None (SHS / HS / Elementary / Unknown) -> 0
    """
    if level is None:
        return 0
    if level >= 8:
        return 4
    if level == 7:
        return 3
    if level == 6:
        return 2
    if level in (4, 5):
        return 1
    return 0


# ─── Configurable Graded Certification / License Hierarchies ──────────────────

CERTIFICATION_HIERARCHIES: dict[str, dict[str, Any]] = {
    "tesda_nc": {
        "family_label": "TESDA National Certificate",
        "levels": [
            (4, re.compile(r"\b(?:nc\s*(?:iv|4)|nciv|national\s+certificate\s*(?:iv|4))\b", re.I), "NC IV"),
            (3, re.compile(r"\b(?:nc\s*(?:iii|3)|nciii|national\s+certificate\s*(?:iii|3))\b", re.I), "NC III"),
            (2, re.compile(r"\b(?:nc\s*(?:ii|2)|ncii|national\s+certificate\s*(?:ii|2))\b", re.I), "NC II"),
            (1, re.compile(r"\b(?:nc\s*(?:i|1)|nci|national\s+certificate\s*(?:i|1))\b", re.I), "NC I"),
        ],
    },
    "safety_officer": {
        "family_label": "DOLE Safety Officer",
        "levels": [
            (4, re.compile(r"\b(?:so\s*4|safety\s+officer\s*(?:4|iv))\b", re.I), "SO4"),
            (3, re.compile(r"\b(?:so\s*3|safety\s+officer\s*(?:3|iii))\b", re.I), "SO3"),
            (2, re.compile(r"\b(?:so\s*2|safety\s+officer\s*(?:2|ii))\b", re.I), "SO2"),
            (1, re.compile(r"\b(?:so\s*1|safety\s+officer\s*(?:1|i))\b", re.I), "SO1"),
        ],
    },
    "six_sigma": {
        "family_label": "Lean Six Sigma",
        "levels": [
            (5, re.compile(r"\bmaster\s+black\s+belt\b", re.I), "Master Black Belt"),
            (4, re.compile(r"\bblack\s+belt\b", re.I), "Black Belt"),
            (3, re.compile(r"\bgreen\s+belt\b", re.I), "Green Belt"),
            (2, re.compile(r"\byellow\s+belt\b", re.I), "Yellow Belt"),
            (1, re.compile(r"\bwhite\s+belt\b", re.I), "White Belt"),
        ],
    },
    "civil_service": {
        "family_label": "Civil Service Eligibility",
        "levels": [
            (2, re.compile(r"\b(?:civil|career)\s+service\s+professional\b|\bcse\s+professional\b", re.I), "Civil Service Professional"),
            (1, re.compile(r"\b(?:civil|career)\s+service\s+sub[-\s]?professional\b|\bcse\s+sub[-\s]?professional\b", re.I), "Civil Service Sub-Professional"),
        ],
    },
    "scrum_psm": {
        "family_label": "Professional Scrum Master",
        "levels": [
            (3, re.compile(r"\bpsm\s*(?:iii|3)\b", re.I), "PSM III"),
            (2, re.compile(r"\bpsm\s*(?:ii|2)\b", re.I), "PSM II"),
            (1, re.compile(r"\bpsm\s*(?:i|1)\b", re.I), "PSM I"),
        ],
    },
}

_GENERIC_CERT_SUBJECT_WORDS: frozenset[str] = frozenset({
    "tesda", "national", "certificate", "certification", "certified", "level",
    "dole", "osh", "bosh", "cosh", "lean", "six", "sigma", "sixsigma",
    "scrum", "professional", "master", "civil", "career", "service", "eligibility",
    "holder", "passer", "training", "in", "of", "for", "and", "or", "the", "a", "an",
})


def parse_graded_certification(cert_text: str) -> Optional[dict[str, Any]]:
    """
    Detect if a certification string belongs to a graded hierarchy (e.g. TESDA NC I-IV).
    Returns {"family": str, "level": int, "level_label": str, "subject": str} or None.
    """
    norm = normalize_requirement_text(cert_text)
    if not norm:
        return None

    for family, spec in CERTIFICATION_HIERARCHIES.items():
        for lvl, pat, lvl_label in spec["levels"]:
            m = pat.search(norm)
            if m:
                remainder = (norm[:m.start()] + " " + norm[m.end():]).lower()
                subject_tokens = [
                    tok for tok in re.findall(r"[a-z0-9]+", remainder)
                    if len(tok) >= 2 and tok not in _GENERIC_CERT_SUBJECT_WORDS
                ]
                return {
                    "family": family,
                    "family_label": spec["family_label"],
                    "level": lvl,
                    "level_label": lvl_label,
                    "subject": " ".join(subject_tokens),
                }
    return None


def compare_graded_certifications(cand_cert: str, req_cert: str) -> Optional[dict[str, Any]]:
    """
    Compare two graded certifications if both belong to the same hierarchy family.
    Returns None when either certification is non-graded or belongs to a different family.
    """
    req_info = parse_graded_certification(req_cert)
    cand_info = parse_graded_certification(cand_cert)
    if not req_info or not cand_info or req_info["family"] != cand_info["family"]:
        return None

    # If the requirement specifies a trade/domain subject (e.g., "SMAW NC II"),
    # verify the candidate certification covers the same trade/domain.
    req_subj = req_info["subject"]
    cand_subj = cand_info["subject"]
    if req_subj:
        req_tokens = set(req_subj.split())
        cand_tokens = set(cand_subj.split())
        if not cand_tokens or not (req_tokens <= cand_tokens or req_subj in cand_subj or cand_subj in req_subj):
            return {
                "matched": False,
                "exceeds": False,
                "below_level": False,
                "subject_mismatch": True,
                "score": 0.0,
                "req_info": req_info,
                "cand_info": cand_info,
            }

    req_lvl = req_info["level"]
    cand_lvl = cand_info["level"]
    if cand_lvl > req_lvl:
        return {
            "matched": True,
            "exceeds": True,
            "below_level": False,
            "subject_mismatch": False,
            "score": 1.0,
            "req_info": req_info,
            "cand_info": cand_info,
        }
    if cand_lvl == req_lvl:
        return {
            "matched": True,
            "exceeds": False,
            "below_level": False,
            "subject_mismatch": False,
            "score": 1.0,
            "req_info": req_info,
            "cand_info": cand_info,
        }
    return {
        "matched": False,
        "exceeds": False,
        "below_level": True,
        "subject_mismatch": False,
        "score": round(cand_lvl / float(req_lvl), 2),
        "req_info": req_info,
        "cand_info": cand_info,
    }
