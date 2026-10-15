"""
Philippine Education Extractor
------------------------------
Deterministic NLP extraction pipeline for parsing structured educational attainment,
degrees, SHS strands, TESDA certifications, and academic institutions from Philippine resumes.

Levels:
  - Postgraduate (Master's, Doctorate, MBA, MIT, MPA, PhD, JD, MD)
  - Tertiary / College (Bachelor's degrees, Associate degrees, Diplomas, College Undergrad)
  - Vocational / Technical (TESDA) (National Certificates NC I - IV, TVET trade qualifications)
  - Senior High School (SHS) (Grades 11-12: STEM, ABM, HUMSS, GAS, TVL-ICT/HE/IA/AFA)
  - Secondary / High School (Junior High School Grades 7-10, Old Curriculum 1st-4th Year, ALS Completer)
  - Primary / Elementary (Grades 1-6)

Strictly local, deterministic NLP (spaCy + EntityRuler + PhraseMatcher + flashtext + dateparser + re).
"""

import re
import json
from typing import Optional, List, Dict, Any, Tuple

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except ImportError:
    spacy = None
    PhraseMatcher = None

try:
    from flashtext import KeywordProcessor
except ImportError:
    KeywordProcessor = None

try:
    import dateparser
except ImportError:
    dateparser = None

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extractors.nlp.nlp_engine import get_doc, extract_advanced_education
from app.extractors.content.section_parser import split_into_sections


# ─── 1. Philippine Education Taxonomy & Degree Map ────────────────────────────

_PHILIPPINE_DEGREE_MAP: Dict[str, str] = {
    # ── Information Technology & Computing
    "BSIT": "Bachelor of Science in Information Technology",
    "B.S.I.T.": "Bachelor of Science in Information Technology",
    "BS INFORMATION TECHNOLOGY": "Bachelor of Science in Information Technology",
    "B.S. INFORMATION TECHNOLOGY": "Bachelor of Science in Information Technology",
    "BACHELOR OF SCIENCE IN INFORMATION TECHNOLOGY": "Bachelor of Science in Information Technology",
    "BSCS": "Bachelor of Science in Computer Science",
    "B.S.C.S.": "Bachelor of Science in Computer Science",
    "BS COMPUTER SCIENCE": "Bachelor of Science in Computer Science",
    "B.S. COMPUTER SCIENCE": "Bachelor of Science in Computer Science",
    "BACHELOR OF SCIENCE IN COMPUTER SCIENCE": "Bachelor of Science in Computer Science",
    "BSIS": "Bachelor of Science in Information Systems",
    "B.S.I.S.": "Bachelor of Science in Information Systems",
    "BS INFORMATION SYSTEMS": "Bachelor of Science in Information Systems",
    "ACT": "Associate in Computer Technology",
    "ASSOCIATE IN COMPUTER TECHNOLOGY": "Associate in Computer Technology",
    "ASSOCIATE IN COMPUTER TECH": "Associate in Computer Technology",

    # ── Engineering & Architecture
    "BSCE": "Bachelor of Science in Civil Engineering",
    "B.S.C.E.": "Bachelor of Science in Civil Engineering",
    "BS CIVIL ENGINEERING": "Bachelor of Science in Civil Engineering",
    "BACHELOR OF SCIENCE IN CIVIL ENGINEERING": "Bachelor of Science in Civil Engineering",
    "BSCPE": "Bachelor of Science in Computer Engineering",
    "BSCpE": "Bachelor of Science in Computer Engineering",
    "B.S.C.P.E.": "Bachelor of Science in Computer Engineering",
    "BS COMPUTER ENGINEERING": "Bachelor of Science in Computer Engineering",
    "BACHELOR OF SCIENCE IN COMPUTER ENGINEERING": "Bachelor of Science in Computer Engineering",
    "BSME": "Bachelor of Science in Mechanical Engineering",
    "B.S.M.E.": "Bachelor of Science in Mechanical Engineering",
    "BS MECHANICAL ENGINEERING": "Bachelor of Science in Mechanical Engineering",
    "BACHELOR OF SCIENCE IN MECHANICAL ENGINEERING": "Bachelor of Science in Mechanical Engineering",
    "BSEE": "Bachelor of Science in Electrical Engineering",
    "B.S.E.E.": "Bachelor of Science in Electrical Engineering",
    "BS ELECTRICAL ENGINEERING": "Bachelor of Science in Electrical Engineering",
    "BACHELOR OF SCIENCE IN ELECTRICAL ENGINEERING": "Bachelor of Science in Electrical Engineering",
    "BSECE": "Bachelor of Science in Electronics Engineering",
    "B.S.E.C.E.": "Bachelor of Science in Electronics Engineering",
    "BS ELECTRONICS ENGINEERING": "Bachelor of Science in Electronics Engineering",
    "BS ELECTRONICS AND COMMUNICATIONS ENGINEERING": "Bachelor of Science in Electronics Engineering",
    "BSIE": "Bachelor of Science in Industrial Engineering",
    "B.S.I.E.": "Bachelor of Science in Industrial Engineering",
    "BS INDUSTRIAL ENGINEERING": "Bachelor of Science in Industrial Engineering",
    "BS ARCHITECTURE": "Bachelor of Science in Architecture",
    "BS ARCHI": "Bachelor of Science in Architecture",
    "BS ARCH": "Bachelor of Science in Architecture",
    "B.S. ARCHITECTURE": "Bachelor of Science in Architecture",
    "BACHELOR OF SCIENCE IN ARCHITECTURE": "Bachelor of Science in Architecture",
    "BSCHE": "Bachelor of Science in Chemical Engineering",
    "BS CHEMICAL ENGINEERING": "Bachelor of Science in Chemical Engineering",

    # ── Business, Accountancy, Hospitality & Administration
    "BSA": "Bachelor of Science in Accountancy",
    "B.S.A.": "Bachelor of Science in Accountancy",
    "BS ACCOUNTANCY": "Bachelor of Science in Accountancy",
    "BS ACCOUNTING": "Bachelor of Science in Accountancy",
    "BACHELOR OF SCIENCE IN ACCOUNTANCY": "Bachelor of Science in Accountancy",
    "BSMA": "Bachelor of Science in Management Accounting",
    "BS MANAGEMENT ACCOUNTING": "Bachelor of Science in Management Accounting",
    "BSAT": "Bachelor of Science in Accounting Technology",
    "BS ACCOUNTING TECHNOLOGY": "Bachelor of Science in Accounting Technology",
    "BSBA": "Bachelor of Science in Business Administration",
    "B.S.B.A.": "Bachelor of Science in Business Administration",
    "BS BUSINESS ADMINISTRATION": "Bachelor of Science in Business Administration",
    "BACHELOR OF SCIENCE IN BUSINESS ADMINISTRATION": "Bachelor of Science in Business Administration",
    "BSBA-FM": "Bachelor of Science in Business Administration Major in Financial Management",
    "BSBA FM": "Bachelor of Science in Business Administration Major in Financial Management",
    "BSBA-MM": "Bachelor of Science in Business Administration Major in Marketing Management",
    "BSBA MM": "Bachelor of Science in Business Administration Major in Marketing Management",
    "BSBA-HRDM": "Bachelor of Science in Business Administration Major in Human Resource Development Management",
    "BSBA HRDM": "Bachelor of Science in Business Administration Major in Human Resource Development Management",
    "BSBA-HRM": "Bachelor of Science in Business Administration Major in Human Resource Management",
    "BSBA HRM": "Bachelor of Science in Business Administration Major in Human Resource Management",
    "BSBA-OM": "Bachelor of Science in Business Administration Major in Operations Management",
    "BSBA OM": "Bachelor of Science in Business Administration Major in Operations Management",
    "BSHM": "Bachelor of Science in Hospitality Management",
    "BSHRM": "Bachelor of Science in Hospitality Management",
    "BS IN HOTEL AND RESTAURANT MANAGEMENT": "Bachelor of Science in Hospitality Management",
    "BS HOTEL AND RESTAURANT MANAGEMENT": "Bachelor of Science in Hospitality Management",
    "BS HOSPITALITY MANAGEMENT": "Bachelor of Science in Hospitality Management",
    "BACHELOR OF SCIENCE IN HOSPITALITY MANAGEMENT": "Bachelor of Science in Hospitality Management",
    "BACHELOR OF SCIENCE IN HOTEL AND RESTAURANT MANAGEMENT": "Bachelor of Science in Hospitality Management",
    "BSTM": "Bachelor of Science in Tourism Management",
    "BS TOURISM": "Bachelor of Science in Tourism Management",
    "BS TOURISM MANAGEMENT": "Bachelor of Science in Tourism Management",
    "BACHELOR OF SCIENCE IN TOURISM MANAGEMENT": "Bachelor of Science in Tourism Management",
    "BSCA": "Bachelor of Science in Customs Administration",
    "BS CUSTOMS ADMINISTRATION": "Bachelor of Science in Customs Administration",
    "BACHELOR OF SCIENCE IN CUSTOMS ADMINISTRATION": "Bachelor of Science in Customs Administration",

    # ── Healthcare, Education & Criminology
    "BSN": "Bachelor of Science in Nursing",
    "B.S.N.": "Bachelor of Science in Nursing",
    "BS NURSING": "Bachelor of Science in Nursing",
    "BACHELOR OF SCIENCE IN NURSING": "Bachelor of Science in Nursing",
    "BS MEDICAL TECHNOLOGY": "Bachelor of Science in Medical Technology",
    "BS MEDTECH": "Bachelor of Science in Medical Technology",
    "BSMLS": "Bachelor of Science in Medical Laboratory Science",
    "BS MEDICAL LABORATORY SCIENCE": "Bachelor of Science in Medical Laboratory Science",
    "BS PHARMACY": "Bachelor of Science in Pharmacy",
    "B.S. PHARMACY": "Bachelor of Science in Pharmacy",
    "BACHELOR OF SCIENCE IN PHARMACY": "Bachelor of Science in Pharmacy",
    "BSCRIM": "Bachelor of Science in Criminology",
    "BS CRIMINOLOGY": "Bachelor of Science in Criminology",
    "B.S. CRIMINOLOGY": "Bachelor of Science in Criminology",
    "BACHELOR OF SCIENCE IN CRIMINOLOGY": "Bachelor of Science in Criminology",
    "BSED": "Bachelor of Secondary Education",
    "B.S.ED.": "Bachelor of Secondary Education",
    "B.S.ED": "Bachelor of Secondary Education",
    "BACHELOR OF SECONDARY EDUCATION": "Bachelor of Secondary Education",
    "BEED": "Bachelor of Elementary Education",
    "B.E.ED.": "Bachelor of Elementary Education",
    "B.E.ED": "Bachelor of Elementary Education",
    "BACHELOR OF ELEMENTARY EDUCATION": "Bachelor of Elementary Education",
    "BS PSYCHOLOGY": "Bachelor of Science in Psychology",
    "BS PSYCH": "Bachelor of Science in Psychology",
    "AB PSYCHOLOGY": "Bachelor of Arts in Psychology",
    "AB PSYCH": "Bachelor of Arts in Psychology",
    "AB COMM": "Bachelor of Arts in Communication",
    "BA COMM": "Bachelor of Arts in Communication",
    "BA COMMUNICATION": "Bachelor of Arts in Communication",
    "AB COMMUNICATION": "Bachelor of Arts in Communication",
    "BACHELOR OF ARTS IN COMMUNICATION": "Bachelor of Arts in Communication",
    "AB POLSCI": "Bachelor of Arts in Political Science",
    "AB POLITICAL SCIENCE": "Bachelor of Arts in Political Science",
    "BA POLITICAL SCIENCE": "Bachelor of Arts in Political Science",
    "AB ENGLISH": "Bachelor of Arts in English",
    "BA ENGLISH": "Bachelor of Arts in English",

    # ── Postgraduate
    "MBA": "Master of Business Administration",
    "M.B.A.": "Master of Business Administration",
    "MASTER OF BUSINESS ADMINISTRATION": "Master of Business Administration",
    "MIT": "Master in Information Technology",
    "M.I.T.": "Master in Information Technology",
    "MASTER IN INFORMATION TECHNOLOGY": "Master in Information Technology",
    "MPA": "Master of Public Administration",
    "M.P.A.": "Master of Public Administration",
    "MASTER OF PUBLIC ADMINISTRATION": "Master of Public Administration",
    "MSIT": "Master of Science in Information Technology",
    "M.S.I.T.": "Master of Science in Information Technology",
    "MSCS": "Master of Science in Computer Science",
    "M.S.C.S.": "Master of Science in Computer Science",
    "MAED": "Master of Arts in Education",
    "M.A.ED.": "Master of Arts in Education",
    "MS": "Master of Science",
    "M.SC.": "Master of Science",
    "MA": "Master of Arts",
    "M.A.": "Master of Arts",
    "PHD": "Doctor of Philosophy",
    "PH.D.": "Doctor of Philosophy",
    "DOCTOR OF PHILOSOPHY": "Doctor of Philosophy",
    "MD": "Doctor of Medicine",
    "M.D.": "Doctor of Medicine",
    "DOCTOR OF MEDICINE": "Doctor of Medicine",
    "JD": "Juris Doctor",
    "J.D.": "Juris Doctor",
    "JURIS DOCTOR": "Juris Doctor",
    "BACHELOR OF LAWS": "Juris Doctor",
    "LLB": "Juris Doctor",
    "LL.B.": "Juris Doctor"
}

# ── Senior High School (K-12) Strands ──
_SHS_STRANDS_INFO = {
    "STEM": {
        "canonical": "STEM",
        "specialization": "Science, Technology, Engineering, and Mathematics"
    },
    "ABM": {
        "canonical": "ABM",
        "specialization": "Accountancy, Business, and Management"
    },
    "HUMSS": {
        "canonical": "HUMSS",
        "specialization": "Humanities and Social Sciences"
    },
    "GAS": {
        "canonical": "GAS",
        "specialization": "General Academic Strand"
    },
    "TVL": {
        "canonical": "Technical-Vocational-Livelihood (TVL)",
        "specialization": None
    }
}

# ── Honors & Awards Patterns ──
_HONORS_PATTERNS = [
    (re.compile(r'\b(?:Summa\s+Cum\s+Laude)\b', re.I), "Summa Cum Laude"),
    (re.compile(r'\b(?:Magna\s+Cum\s+Laude)\b', re.I), "Magna Cum Laude"),
    (re.compile(r'\b(?:Cum\s+Laude)\b', re.I), "Cum Laude"),
    (re.compile(r'\b(?:With\s+Highest\s+Honors)\b', re.I), "With Highest Honors"),
    (re.compile(r'\b(?:With\s+High\s+Honors)\b', re.I), "With High Honors"),
    (re.compile(r'\b(?:With\s+Honors)\b', re.I), "With Honors"),
    (re.compile(r'\b(?:Dean\'?s\s+Lister)\b', re.I), "Dean's Lister"),
    (re.compile(r'\b(?:President\'?s\s+Lister)\b', re.I), "President's Lister"),
    (re.compile(r'\b(?:Academic\s+Scholar|University\s+Scholar)\b', re.I), "Academic Scholar"),
    (re.compile(r'\b(?:Valedictorian)\b', re.I), "Valedictorian"),
    (re.compile(r'\b(?:Salutatorian)\b', re.I), "Salutatorian"),
    (re.compile(r'\b(?:Honorable\s+Mention)\b', re.I), "Honorable Mention"),
    (re.compile(r'\b(?:Best\s+in\s+Capstone(?:\s+Project)?)\b', re.I), "Best in Capstone Project"),
    (re.compile(r'\b(?:Best\s+in\s+Thesis)\b', re.I), "Best in Thesis"),
    (re.compile(r'\b(?:Best\s+in\s+OJT)\b', re.I), "Best in OJT"),
    (re.compile(r'\b(?:Best\s+in\s+Practicum)\b', re.I), "Best in Practicum"),
    (re.compile(r'\b(?:Leadership\s+Award)\b', re.I), "Leadership Award"),
]

# ── Known Philippine Educational Institutions ──
_KNOWN_PH_INSTITUTIONS = [
    "STI College", "STI Colleges", "AMA Computer College", "AMA Computer University", "AMA College",
    "Polytechnic University of the Philippines (PUP)", "Polytechnic University of the Philippines", "PUP",
    "University of the Philippines Diliman", "University of the Philippines", "UP Diliman", "U.P. Diliman", "UP",
    "De La Salle University", "DLSU", "Ateneo de Manila University", "ADMU",
    "Far Eastern University", "FEU", "FEU Tech", "FEU Institute of Technology",
    "University of Santo Tomas", "UST", "Mapúa University", "Mapua University", "Mapua Institute of Technology",
    "Technological Institute of the Philippines", "TIP", "Technological University of the Philippines", "TUP",
    "National University", "NU", "University of the East", "UE", "Pamantasan ng Lungsod ng Maynila", "PLM",
    "Adamson University", "San Beda University", "San Beda College", "Centro Escolar University", "CEU",
    "Rizal Technological University", "RTU", "Eulogio \"Amang\" Rodriguez Institute of Science and Technology", "EARIST",
    "Cavite State University", "CvSU", "Bulacan State University", "BulSU",
    "Batangas State University", "BatStateU", "Laguna State Polytechnic University", "LSPU",
    "ICCT Colleges Foundation Inc.", "ICCT Colleges Foundation", "ICCT Colleges",
    "Access Computer College", "Access Computer College Inc.", "Datamex Institute of Computer Technology", "Datamex",
    "Informatics College", "CIIT College of Arts and Technology", "CIIT", "iACADEMY", "ACLC College",
    "TESDA Provincial Training Center", "TESDA Regional Training Center", "TESDA Training Center", "TESDA",
    "DepEd Rizal", "DepEd Manila", "DepEd Quezon City", "DepEd"
]

_SCHOOL_SUFFIXES = [
    "National High School", "Memorial National High School", "Science High School",
    "Vocational High School", "High School", "Senior High School", "Junior High School",
    "Elementary School", "Central School", "Integrated School", "State University",
    "University", "Colleges Foundation Inc.", "Colleges Foundation", "Colleges", "College",
    "Institute of Technology", "Institute", "Polytechnic", "Academy", "Training Center"
]

_PHIL_LOCATIONS_SET = {
    "manila", "quezon city", "makati", "makati city", "taguig", "taguig city", "bgc",
    "bonifacio global city", "pasig", "pasig city", "ortigas", "mandaluyong",
    "san juan", "marikina", "pasay", "parañaque", "muntinlupa", "las piñas",
    "caloocan", "malabon", "navotas", "valenzuela", "rizal", "antipolo", "antipolo city",
    "taytay", "cainta", "teresa", "binangonan", "san mateo", "rodriguez", "laguna", "calamba",
    "santa rosa", "biñan", "san pedro", "cabuyao", "los baños", "cavite", "bacoor",
    "dasmarinas", "dasmariñas", "imus", "general trias", "tagaytay", "batangas",
    "bulacan", "pampanga", "angeles city", "san fernando", "clark", "subic",
    "cebu", "cebu city", "davao", "davao city", "iloilo", "baguio", "baguio city",
    "cagayan de oro", "bacolod", "sta. mesa"
}


# ─── 2. Section Headers ───────────────────────────────────────────────────────

_EDUCATION_HEADERS_RE = re.compile(
    r'^(?:EDUCATIONAL\s+BACKGROUND|EDUCATIONAL\s+ATTAINMENT|ACADEMIC\s+BACKGROUND|'
    r'EDUCATION|SCHOLASTIC\s+RECORD|VOCATIONAL\s*/?\s*TECHNICAL\s+TRAINING|'
    r'ACADEMIC\s+HISTORY|EDUCATIONAL\s+HISTORY|ACADEMIC\s+QUALIFICATIONS|'
    r'EDUCATIONAL\s+QUALIFICATIONS|STUDIES|SCHOOLING)(?:\s*[:\-–—])?$',
    re.IGNORECASE
)

_SUB_TIER_HEADERS = [
    ("Postgraduate", re.compile(r'^(?:Postgraduate|Graduate\s+Studies|Doctorate|Masteral)(?:\s*[:\-–—])?$', re.IGNORECASE)),
    ("Tertiary / College", re.compile(r'^(?:Tertiary|College|Collegiate|Undergraduate\s+Studies)(?:\s*[:\-–—])?$', re.IGNORECASE)),
    ("Vocational / Technical (TESDA)", re.compile(r'^(?:Vocational\s*/?\s*Technical(?:\s+Training)?|Vocational|Technical|TESDA)(?:\s*[:\-–—])?$', re.IGNORECASE)),
    ("Senior High School (SHS)", re.compile(r'^(?:Senior\s+High\s+School|Senior\s+High|SHS)(?:\s*[:\-–—])?$', re.IGNORECASE)),
    ("Secondary / High School", re.compile(r'^(?:Junior\s+High\s+School|Junior\s+High|JHS|High\s+School|Secondary)(?:\s*[:\-–—])?$', re.IGNORECASE)),
    ("Primary / Elementary", re.compile(r'^(?:Primary|Elementary|Grade\s+School)(?:\s*[:\-–—])?$', re.IGNORECASE)),
]

_STOP_SECTION_RE = re.compile(
    r'^(?:WORK\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|PROFESSIONAL\s+EXPERIENCE|'
    r'RELEVANT\s+EXPERIENCE|WORK\s+HISTORY|ON-THE-JOB\s+TRAINING(?:\s*\(OJT\))?|'
    r'SKILLS|TECHNICAL\s+SKILLS|CERTIFICATIONS(?:\s*(?:AND|&)\s*LICENSES)?|'
    r'LICENSES(?:\s*(?:AND|&)\s*ELIGIBILITY)?|ELIGIBILITY|LICENSES|'
    r'PROJECTS|SEMINARS(?:\s*/?\s*TRAININGS)?|'
    r'TRAININGS|PERSONAL\s+DATA|PERSONAL\s+INFORMATION|CHARACTER\s+REFERENCES|'
    r'REFERENCES|SUMMARY|AFFILIATIONS|AWARDS)(?:\s*[:\-–—])?$',
    re.IGNORECASE
)


# ─── 3. flashtext & spaCy Pipeline Setup ──────────────────────────────────────

_KEYWORD_PROCESSOR = None
if KeywordProcessor is not None:
    _KEYWORD_PROCESSOR = KeywordProcessor(case_sensitive=False)
    for deg_acronym, full_deg in _PHILIPPINE_DEGREE_MAP.items():
        _KEYWORD_PROCESSOR.add_keyword(deg_acronym, full_deg)
    for strand, s_info in _SHS_STRANDS_INFO.items():
        _KEYWORD_PROCESSOR.add_keyword(strand, s_info["canonical"])
    for inst in _KNOWN_PH_INSTITUTIONS:
        _KEYWORD_PROCESSOR.add_keyword(inst, inst)

_SPACY_NLP = None
_PHRASE_MATCHER = None

def _get_spacy_pipeline():
    global _SPACY_NLP, _PHRASE_MATCHER
    if _SPACY_NLP is not None:
        return _SPACY_NLP, _PHRASE_MATCHER

    if spacy is None:
        return None, None

    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        return None, None

    if "entity_ruler" not in nlp.pipe_names:
        try:
            ruler = nlp.add_pipe("entity_ruler", before="ner")
            patterns = []
            for deg_term in _PHILIPPINE_DEGREE_MAP.keys():
                patterns.append({"label": "PH_DEGREE", "pattern": deg_term})
            for strand in _SHS_STRANDS_INFO.keys():
                patterns.append({"label": "PH_SHS_STRAND", "pattern": strand})
            for inst in _KNOWN_PH_INSTITUTIONS:
                patterns.append({"label": "PH_INSTITUTION", "pattern": inst})
            for _, honor_label in _HONORS_PATTERNS:
                patterns.append({"label": "PH_HONOR", "pattern": honor_label})
            ruler.add_patterns(patterns)
        except Exception:
            pass

    try:
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        inst_docs = [nlp.make_doc(inst) for inst in _KNOWN_PH_INSTITUTIONS]
        matcher.add("PH_INSTITUTIONS", inst_docs)
    except Exception:
        matcher = None

    _SPACY_NLP = nlp
    _PHRASE_MATCHER = matcher
    return _SPACY_NLP, _PHRASE_MATCHER


# ─── 4. Parsing Helpers ───────────────────────────────────────────────────────

def _extract_years(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract start_year and end_year (or Present)."""
    # Pattern 1: AY 2022 - 2026 or 2020 - 2022 or (2019 - 2021)
    m = re.search(r'(?:(?:A\.?Y\.?|S\.?Y\.?)\s*)?((?:19|20)\d{2})\s*[-–—to]+\s*((?:19|20)\d{2}|Present)', text, re.I)
    if m:
        return m.group(1), m.group(2)

    # Pattern 2: Single year in parenthesis e.g. (2022) or (2018)
    m2 = re.search(r'\(((?:19|20)\d{2})\)', text)
    if m2:
        return None, m2.group(1)

    # Pattern 3: Batch 2022 or Class of 2021
    m3 = re.search(r'\b(?:Batch|Class\s+of)\s+((?:19|20)\d{2})\b', text, re.I)
    if m3:
        return None, m3.group(1)

    # Pattern 4: Year range without AY/SY: 2010 - 2016
    m4 = re.search(r'\b((?:19|20)\d{2})\s*[-–—to]+\s*((?:19|20)\d{2}|Present)\b', text, re.I)
    if m4:
        return m4.group(1), m4.group(2)

    # Pattern 5: Single standalone 4-digit year
    m5 = re.search(r'\b((?:19|20)\d{2})\b', text)
    if m5:
        return None, m5.group(1)

    return None, None


def _extract_honors(text: str) -> List[str]:
    """Find all matching honors and awards in text."""
    honors = []
    for pattern, label in _HONORS_PATTERNS:
        if pattern.search(text):
            if label not in honors:
                honors.append(label)
    return honors


def _is_invalid_institution(name: str) -> bool:
    if not name or len(name) < 3:
        return True
    lower = name.lower()
    if re.search(r'\b(?:\d+(?:st|nd|rd|th)?|first|second|third|fourth)?\s*year\s+college\b', lower):
        return True
    if re.search(r'\bcollege\s+(?:level|undergrad(?:uate)?)\b', lower):
        return True
    if any(lower == w or lower.startswith(w + " ") for w in ["grade", "level", "semester", "strand", "academic"]):
        return True
    if "hotel and restaurant management" in lower or "information technology" in lower:
        return True
    if re.search(r'\b(?:course|curriculum|program|bachelor|master|doctor|diploma|certificate|associate)\b', lower):
        if not any(w in lower for w in ["training center", "institute", "college", "university", "school", "academy"]):
            return True
    return False


def _detect_status(text: str, end_year: Optional[str] = None, level: str = "") -> str:
    """Determine enrollment status."""
    if re.search(r'\b(?:Ongoing|Currently\s+Enrolled|Present|In\s+Progress|Current)\b', text, re.I) or end_year == "Present":
        return "Ongoing"
    if re.search(r'\b(?:College\s+Level|College\s+Undergrad(?:uate)?|Undergraduate|Undergrad|\d+(?:st|nd|rd|th)?\s+Year(?:\s+College|\s+Level|\s+irregular)?|Completed\s+\d+(?:st|nd|rd|th)?\s+Year|Units\s+Earned)\b', text, re.I):
        return "Undergraduate / College Level"
    if re.search(r'\b(?:ALS\s+Completer|Completer|Completed|Finished|NC\s+I{1,3}\s+Holder|Certified)\b', text, re.I):
        return "Completed"
    if level == "Vocational / Technical (TESDA)":
        return "Completed"
    return "Graduated"


def _extract_school_and_location(text: str) -> Tuple[str, Optional[str]]:
    """Separates institution name from campus, branch, or city/province."""
    clean = text.strip()
    # Strip sub-tier prefixes if present
    clean = re.sub(r'^(?:Tertiary|Senior\s+High\s+School|Junior\s+High\s+School|Primary|Vocational\s*/?\s*Technical|Secondary)[:\s\-–—]+', '', clean, flags=re.I).strip()
    # Strip year notations like (2019 - 2021) or (2022)
    clean = re.sub(r'\((?:19|20)\d{2}(?:\s*[-–—to]+\s*(?:(?:19|20)\d{2}|Present))?\)', '', clean).strip()
    clean = re.sub(r'\((?:19|20)\d{2}\)', '', clean).strip()

    # Check if TESDA + Training Center / Center / Institute
    m_tesda = re.search(r'\b(TESDA\s+[A-Za-z0-9\s]+?(?:Training\s+Center|Center|Institute))\b', clean, re.I)
    if m_tesda:
        inst = m_tesda.group(1).strip()
        loc = clean[m_tesda.end():].strip(' ,-–—')
        loc = re.sub(r'(?:S\.?Y\.?|A\.?Y\.?)?\s*\d{4}.*$', '', loc).strip(' ,-–—()') or None
        return inst, loc

    # 1. Known schools with safe boundaries
    for ks in sorted(_KNOWN_PH_INSTITUTIONS, key=len, reverse=True):
        m = re.search(rf'(?<!\w){re.escape(ks)}(?!\w)', clean, re.I)
        if m:
            after = clean[m.end():].strip(' ,-–—')
            loc = None
            if after:
                after_clean = re.sub(r'(?:S\.?Y\.?|A\.?Y\.?)?\s*\d{4}.*$', '', after).strip(' ,-–—()')
                if after_clean:
                    loc = after_clean
            return ks, loc

    # 2. Suffix-based patterns
    for suffix in sorted(_SCHOOL_SUFFIXES, key=len, reverse=True):
        pat = rf'\b([A-Za-z0-9.\'\" ]+?\s+{re.escape(suffix)})\b'
        m = re.search(pat, clean, re.I)
        if m:
            found = m.group(1).strip()
            if not _is_invalid_institution(found):
                after = clean[m.end():].strip(' ,-–—')
                loc = None
                if after:
                    after_clean = re.sub(r'(?:S\.?Y\.?|A\.?Y\.?)?\s*\d{4}.*$', '', after).strip(' ,-–—()')
                    if after_clean:
                        loc = after_clean
                return found, loc

    # 3. If DepEd
    if "deped" in clean.lower():
        m_dep = re.search(r'\b(DepEd(?:\s+[A-Za-z0-9]+)?)\b', clean, re.I)
        if m_dep:
            inst = m_dep.group(1).strip()
            loc = clean[m_dep.end():].strip(' ,-–—') or None
            return inst, loc

    return clean, None


def _normalize_degree_or_course(text: str, level: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Returns: (degree_or_course, raw_degree_or_course, major_or_specialization)
    """
    clean = text.strip()

    # 0. Check Vocational / Technical courses
    voc_match = re.search(r'\b((?:Vocational|Technical|Vocational\s*/\s*Technical)\s+(?:Course|Program|Training|Education)(?:\s+in\s+[A-Za-z0-9\s/&,()-]+)?)\b', clean, re.I)
    if voc_match:
        raw = voc_match.group(1).strip()
        spec = raw.split(" in ", 1)[1].strip() if " in " in raw else None
        return raw.title(), raw, spec

    # 0b. Check High School Graduate / Completer
    hs_match = re.search(r'\b(High\s+School\s+Graduate|Secondary\s+Graduate|High\s+School\s+Diploma|Junior\s+High\s+School\s+Completer|Senior\s+High\s+School\s+Graduate)\b', clean, re.I)
    if hs_match:
        raw = hs_match.group(1).strip()
        return raw.title(), raw, None

    # 1. Check TESDA National Certificate courses
    nc_match = re.search(r'\b([A-Za-z0-9\s/&,()-]+?\s+NC\s+I{1,3}(?:\s*&\s*[A-Za-z0-9\s/&,()-]+?\s+NC\s+I{1,3})?)\b', clean, re.I)
    if nc_match:
        raw = nc_match.group(1).strip()
        return raw, raw, None

    # 2. Check SHS Strands
    for strand, s_info in _SHS_STRANDS_INFO.items():
        if re.search(rf'\b{strand}\b', clean, re.I):
            raw = clean
            canonical = s_info["canonical"]
            spec = s_info["specialization"]
            # Check if there is specific track specialization e.g. TVL - ICT
            ict_match = re.search(r'[-–—]\s*(Information and Communications Technology\s*\(ICT\)|ICT|Home Economics\s*\(HE\)|Home Economics|Industrial Arts|Agri-Fishery Arts)', clean, re.I)
            if ict_match:
                spec = ict_match.group(1).strip()
            return canonical, raw, spec

    # 3. Check Alternative Learning System
    if re.search(r'\bAlternative\s+Learning\s+System\s*(?:\(ALS\))?', clean, re.I):
        return "Alternative Learning System (ALS)", "Alternative Learning System (ALS) Completer", None

    # 4. Check College / Tertiary Degrees
    for deg_key, deg_val in sorted(_PHILIPPINE_DEGREE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        pat = rf'\b{re.escape(deg_key)}\b'
        if re.search(pat, clean, re.I):
            raw = clean
            # Strip status prefix like College Level
            raw = re.sub(r'^(?:College\s+Level(?:\s*\([^)]*\))?\s*[-–—]\s*)', '', raw, flags=re.I).strip()
            major = None
            if "Major in" in deg_val:
                parts = deg_val.split("Major in", 1)
                major = parts[1].strip()
            elif re.search(r'\bmajor\s+in\s+([A-Za-z\s]+)', clean, re.I):
                m_maj = re.search(r'\bmajor\s+in\s+([A-Za-z\s]+)', clean, re.I)
                major = m_maj.group(1).strip()

            return deg_val, raw, major

    # Generic Bachelor/Master/Doctor/Associate match
    deg_gen = re.search(r'\b((?:Bachelor|Master|Doctor|Associate)\s+(?:of|in)\s+[A-Za-z\s]+?)(?:\s*\(|\s*[-–—|,]|\s*$)', clean, re.I)
    if deg_gen:
        raw = deg_gen.group(1).strip()
        return raw.title(), raw, None

    # For Junior High / Primary, courses are None
    if level in ["Secondary / High School", "Primary / Elementary"]:
        return None, None, None

    return None, clean if clean else None, None


def resolve_highest_educational_attainment(entries: List[Dict[str, Any]]) -> str:
    """
    Resolve highest educational attainment based on standardized Philippine hierarchy,
    accounting for 'Undergraduate / College Level' vs 'Graduated / Completed'.
    Hierarchy rank:
    1. Postgraduate (Graduated / Completed) -> 100
    2. Postgraduate (Undergraduate / Ongoing) -> 90
    3. Tertiary / College (Graduated / Completed) -> 80
    4. Vocational / Technical (TESDA) (Graduated / Completed) -> 70
    5. Tertiary / College (Undergraduate / College Level / Ongoing) -> 60
    6. Vocational / Technical (TESDA) (Undergraduate / Ongoing) -> 55
    7. Senior High School (SHS) (Graduated / Completed) -> 50
    8. Secondary / High School (Graduated / Completed) -> 35
    9. Senior High School (SHS) (Undergraduate / Ongoing) -> 30
    10. Secondary / High School (Undergraduate / Ongoing) -> 25
    11. Primary / Elementary -> 10
    """
    if not entries:
        return "Unknown"

    def rank_entry(entry: Dict[str, Any]) -> int:
        lvl = entry.get("education_level", "")
        status = entry.get("status", "")
        is_completed = status in ("Graduated", "Completed")

        if lvl == "Postgraduate":
            return 100 if is_completed else 90
        elif lvl == "Tertiary / College":
            return 80 if is_completed else 60
        elif lvl == "Vocational / Technical (TESDA)":
            return 70 if is_completed else 55
        elif lvl == "Senior High School (SHS)":
            return 50 if is_completed else 30
        elif lvl == "Secondary / High School":
            return 35 if is_completed else 25
        elif lvl == "Primary / Elementary":
            return 10
        return 0

    best_entry = max(entries, key=rank_entry, default=None)
    if best_entry and rank_entry(best_entry) > 0:
        return best_entry.get("education_level", "Unknown")

    return "Unknown"


# ─── 5. Primary Structured Extractor ──────────────────────────────────────────

def extract_structured_education(text: str) -> Dict[str, Any]:
    """
    Extracts structured educational attainment and entries from Philippine resumes.
    Returns:
    {
      "highest_educational_attainment": "<Postgraduate | Tertiary / College | Vocational / Technical (TESDA) | Senior High School (SHS) | Secondary / High School | Primary / Elementary | Unknown>",
      "education_entries": [
        {
          "education_level": "<Standardized Level String>",
          "degree_or_course": "<Normalized Course/Track/Certificate String or None>",
          "raw_degree_or_course": "<Exact Course Text from Resume or None>",
          "major_or_specialization": "<Major/Strand/Specialization String or None>",
          "institution_name": "<School/University/Training Center String>",
          "location": "<City/Province/Campus String or None>",
          "status": "<Graduated | Undergraduate / College Level | Ongoing | Completed>",
          "start_year": "<YYYY or None>",
          "end_year": "<YYYY | Present | None>",
          "honors_and_awards": ["<Honor 1>", "<Honor 2>"]
        }
      ]
    }
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]

    # 1. Isolate education section
    in_edu = False
    edu_lines = []
    for line in lines:
        if _EDUCATION_HEADERS_RE.match(line):
            in_edu = True
            continue
        elif _STOP_SECTION_RE.match(line):
            if in_edu:
                break
            continue
        if in_edu:
            edu_lines.append(line)

    if not edu_lines:
        edu_lines = lines

    # 2. Check if inline pipe-delimited format (Template 3)
    is_pipe_format = any(l.count('|') >= 2 for l in edu_lines)
    entries = []

    if is_pipe_format:
        for line in edu_lines:
            if line.count('|') < 1:
                continue
            parts = [p.strip() for p in line.split('|')]
            part_deg = parts[0]
            part_inst = parts[1] if len(parts) > 1 else ""
            part_dates = parts[2] if len(parts) > 2 else ""
            part_honors = parts[3] if len(parts) > 3 else ""

            # Detect level
            level = "Tertiary / College"
            if re.search(r'\b(?:Senior\s+High|STEM|ABM|HUMSS|GAS|TVL|SHS)\b', line, re.I):
                level = "Senior High School (SHS)"
            elif re.search(r'\b(?:TESDA|NC\s+I{1,3})\b', line, re.I):
                level = "Vocational / Technical (TESDA)"
            elif re.search(r'\b(?:Master(?:\'s|al)?\s+(?:Degree|in|of)|MBA|MSIT|MIT|Doctor(?:ate)?|PhD)\b', line, re.I) and not re.search(r'\bMaster\s+Plumber\b', line, re.I):
                level = "Postgraduate"
            elif re.search(r'\b(?:High\s+School|Secondary|Junior\s+High|ALS)\b', line, re.I):
                level = "Secondary / High School"
            elif re.search(r'\b(?:Elementary|Primary)\b', line, re.I):
                level = "Primary / Elementary"

            # Parse degree, school, dates, honors
            deg, raw_deg, spec = _normalize_degree_or_course(part_deg, level)
            inst, loc = _extract_school_and_location(part_inst)
            s_yr, e_yr = _extract_years(part_dates)
            honors = _extract_honors(part_honors + " " + line)
            status = _detect_status(line, e_yr, level)

            if s_yr and e_yr:
                yr_str = f"{s_yr} - {e_yr}"
            elif e_yr:
                yr_str = e_yr
            elif s_yr:
                yr_str = s_yr
            else:
                yr_str = ""
            honors_str = ", ".join(honors) if isinstance(honors, list) else (honors or "")

            entries.append({
                "education_level": level,
                "degree_or_course": deg,
                "degree": deg or raw_deg or "",
                "raw_degree_or_course": raw_deg,
                "major_or_specialization": spec,
                "institution_name": inst,
                "institution": inst,
                "college": inst,
                "location": loc,
                "status": status,
                "start_year": s_yr,
                "end_year": e_yr,
                "year": yr_str,
                "honors_and_awards": honors,
                "honors": honors_str
            })

    else:
        # Block-based format with sub-tier headers or multi-line entries
        current_tier = None
        current_block = []

        def process_block(tier: Optional[str], block_lines: List[str]):
            if not block_lines:
                return
            combined_text = " \n ".join(block_lines)

            # Determine level
            level = tier
            if not level:
                if re.search(r'\b(?:Master(?:\'s|al)?\s+(?:Degree|in|of)|MBA|MSIT|MIT|Doctor(?:ate)?|PhD)\b', combined_text, re.I) and not re.search(r'\bMaster\s+Plumber\b', combined_text, re.I):
                    level = "Postgraduate"
                elif re.search(r'\b(?:College\s+Level|Bachelor|BS|BA|Associate|ACT)\b', combined_text, re.I):
                    level = "Tertiary / College"
                elif re.search(r'\b(?:TESDA|NC\s+I{1,3}|Vocational)\b', combined_text, re.I):
                    level = "Vocational / Technical (TESDA)"
                elif re.search(r'\b(?:Senior\s+High|STEM|ABM|HUMSS|GAS|TVL|SHS)\b', combined_text, re.I):
                    level = "Senior High School (SHS)"
                elif re.search(r'\b(?:Junior\s+High|High\s+School|Secondary|ALS)\b', combined_text, re.I):
                    level = "Secondary / High School"
                elif re.search(r'\b(?:Elementary|Primary)\b', combined_text, re.I):
                    level = "Primary / Elementary"
                else:
                    level = "Tertiary / College"

            # Dates, honors, status
            s_yr, e_yr = _extract_years(combined_text)
            honors = _extract_honors(combined_text)
            status = _detect_status(combined_text, e_yr, level)

            # Degree / Course & Institution
            deg, raw_deg, spec = None, None, None
            inst, loc = "", None

            for bline in block_lines:
                bline_clean = bline.strip(' -•*')
                # Check degree
                d, rd, sp = _normalize_degree_or_course(bline_clean, level)
                if d and not deg:
                    deg, raw_deg, spec = d, rd, sp
                # Check institution
                i, l = _extract_school_and_location(bline_clean)
                if i and not _is_invalid_institution(i) and any(s.lower() in i.lower() for s in _SCHOOL_SUFFIXES + _KNOWN_PH_INSTITUTIONS) and not inst:
                    inst, loc = i, l

            if not inst:
                inst, loc = _extract_school_and_location(combined_text)

            if s_yr and e_yr:
                yr_str = f"{s_yr} - {e_yr}"
            elif e_yr:
                yr_str = e_yr
            elif s_yr:
                yr_str = s_yr
            else:
                yr_str = ""
            honors_str = ", ".join(honors) if isinstance(honors, list) else (honors or "")

            entries.append({
                "education_level": level,
                "degree_or_course": deg,
                "degree": deg or raw_deg or "",
                "raw_degree_or_course": raw_deg,
                "major_or_specialization": spec,
                "institution_name": inst or "Not Specified",
                "institution": inst or "Not Specified",
                "college": inst or "Not Specified",
                "location": loc,
                "status": status,
                "start_year": s_yr,
                "end_year": e_yr,
                "year": yr_str,
                "honors_and_awards": honors,
                "honors": honors_str
            })

        def _is_edu_entry_boundary(line_str: str, curr_lines: List[str]) -> bool:
            if not curr_lines:
                return False
            clean_l = line_str.strip()
            if not clean_l:
                return False

            curr_t = " \n ".join(curr_lines)
            s_y, e_y = _extract_years(curr_t)
            has_y = bool(s_y or e_y)

            deg_pats = [
                r'\b(?:Bachelor|Master|Doctor|Associate|Diploma|Certificate|Vocational|Technical\s+Course)\b',
                r'\b(?:BSIT|BSCS|BSCE|BSME|BSEE|BSBA|BSHRM|BSHM|BSN|BSC|BSA|BSED|BEED|BSCpE|MSIT|MSCS|MBA|MPA|MIT|PhD)\b',
                r'\b(?:High\s+School\s+Graduate|Secondary\s+Graduate|High\s+School\s+Diploma|Junior\s+High\s+School\s+Completer|Senior\s+High\s+School\s+Graduate|ALS\s+Completer)\b',
                r'\b(?:STEM|ABM|HUMSS|GAS|TVL)\b',
            ]
            is_deg_l = any(re.search(p, clean_l, re.I) for p in deg_pats)
            if is_deg_l:
                has_d = any(any(re.search(p, prev, re.I) for p in deg_pats) for prev in curr_lines)
                if has_y or has_d:
                    return True

            is_school_l = any(s.lower() in clean_l.lower() for s in _SCHOOL_SUFFIXES + _KNOWN_PH_INSTITUTIONS)
            if is_school_l and has_y:
                return True

            return False

        for line in edu_lines:
            matched_tier = None
            for tier_name, tier_re in _SUB_TIER_HEADERS:
                if tier_re.match(line):
                    matched_tier = tier_name
                    break

            if matched_tier:
                if current_block:
                    process_block(current_tier, current_block)
                    current_block = []
                current_tier = matched_tier
            else:
                if not current_tier and _is_edu_entry_boundary(line, current_block):
                    process_block(current_tier, current_block)
                    current_block = [line]
                else:
                    current_block.append(line)

        if current_block:
            process_block(current_tier, current_block)

    # 3. Resolve Highest Educational Attainment
    highest = resolve_highest_educational_attainment(entries)

    return {
        "highest_educational_attainment": highest,
        "education_entries": entries
    }


# ─── 6. Backward Compatibility Functions ─────────────────────────────────────

def extract_education_entries(text: str) -> list[dict]:
    """
    Parse structured education entries from the resume.
    Returns list of dicts: [{"degree": str, "institution": str, "year": str, "raw": str}]
    Provides 100% backward compatibility for legacy callers.
    """
    structured = extract_structured_education(text)
    entries = []
    for exp in structured.get("education_entries", []):
        deg = exp.get("degree_or_course") or exp.get("raw_degree_or_course") or ""
        inst = exp.get("institution_name") or ""
        loc = exp.get("location") or ""
        if loc and inst:
            inst_display = f"{inst} - {loc}"
        else:
            inst_display = inst

        s_yr = exp.get("start_year")
        e_yr = exp.get("end_year")
        if s_yr and e_yr:
            yr_display = f"{s_yr} - {e_yr}"
        elif e_yr:
            yr_display = e_yr
        else:
            yr_display = ""

        raw_parts = [p for p in [deg, inst_display] if p]
        raw_str = " - ".join(raw_parts)
        if yr_display:
            raw_str += f" ({yr_display})"

        entries.append({
            "degree": deg,
            "institution": inst,
            "college": inst,
            "location": loc,
            "year": yr_display,
            "status": exp.get("status", "Graduated"),
            "education_level": exp.get("education_level", "Tertiary / College"),
            "honors_and_awards": exp.get("honors_and_awards", []),
            "raw": raw_str
        })
    return entries


def extract_highest_degree(text: str) -> str:
    """
    Identifies the highest academic degree tier (POSTGRADUATE, TERTIARY / COLLEGE, etc.)
    """
    structured = extract_structured_education(text)
    highest = structured.get("highest_educational_attainment", "")
    if highest == "Tertiary / College":
        return "BACHELOR"
    if highest == "Postgraduate":
        return "MASTER"
    if highest == "Vocational / Technical (TESDA)":
        return "VOCATIONAL"
    if highest == "Senior High School (SHS)":
        return "SENIOR HIGH SCHOOL"
    if highest == "Secondary / High School":
        return "HIGH SCHOOL"
    return highest.upper() if highest else ""


def extract_degree_title(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the full normalized degree title (e.g. 'Bachelor of Science in Information Technology')
    """
    if entries is not None and entries:
        for e in entries:
            deg = e.get("degree", "").strip()
            if deg and len(deg) > 3:
                return deg

    structured = extract_structured_education(text)
    for entry in structured.get("education_entries", []):
        if entry.get("education_level") in ["Tertiary / College", "Postgraduate"]:
            if entry.get("degree_or_course"):
                return entry["degree_or_course"]
            if entry.get("raw_degree_or_course"):
                return entry["raw_degree_or_course"]

    # Fallback to any non-empty degree
    for entry in structured.get("education_entries", []):
        if entry.get("degree_or_course"):
            return entry["degree_or_course"]

    return ""


def extract_institution(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's university / college / institution name cleanly.
    Prioritizes tertiary institutions over secondary.
    """
    if entries is not None and entries:
        for e in entries:
            inst = e.get("institution", "").strip()
            level = e.get("education_level", "")
            if inst and level in ["Tertiary / College", "Postgraduate"]:
                return inst

    structured = extract_structured_education(text)
    for entry in structured.get("education_entries", []):
        if entry.get("education_level") in ["Tertiary / College", "Postgraduate"]:
            if entry.get("institution_name"):
                return entry["institution_name"]

    # Fallback to any institution
    for entry in structured.get("education_entries", []):
        if entry.get("institution_name"):
            return entry["institution_name"]

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
    return " | ".join(formatted[:6]) if formatted else ""


# ─── Aliases & Helper Accessors ──────────────────────────────────────────────
_resolve_highest_attainment = resolve_highest_educational_attainment


def _normalize_degree_or_strand(text: str, level: str = "Tertiary / College") -> Optional[str]:
    deg, _, _ = _normalize_degree_or_course(text, level)
    return deg


_extract_honors_and_awards = _extract_honors


def _detect_completion_status(text: str, end_year: Optional[str] = None, level: str = "") -> str:
    return _detect_status(text, end_year, level)


_parse_academic_years = _extract_years
_split_school_and_location = _extract_school_and_location


# ─── 7. Runnable Demonstration & Test Block ───────────────────────────────────

if __name__ == "__main__":
    t1 = """
EDUCATIONAL BACKGROUND
Tertiary:
Bachelor of Science in Information Technology (BSIT)
STI College - Ortigas-Cainta Campus
A.Y. 2022 - 2026
- Cum Laude, Best in Capstone Project

Senior High School:
Technical-Vocational-Livelihood (TVL) - Information and Communications Technology (ICT)
Antipolo National High School, Antipolo City, Rizal
S.Y. 2020 - 2022
- With High Honors

Junior High School:
Teresa National High School, Teresa, Rizal
S.Y. 2016 - 2020

Primary:
Teresa Elementary School
2010 - 2016
"""

    t2 = """
EDUCATIONAL ATTAINMENT
College Level (2nd Year irregular) - BS in Hotel and Restaurant Management (BSHRM)
ICCT Colleges Foundation Inc. - Cainta Main Campus (2019 - 2021)

Vocational / Technical:
Food and Beverage Services (FBS) NC II & Bread and Pastry Production NC II
TESDA Provincial Training Center - Rizal (2022)

Secondary:
Alternative Learning System (ALS) Completer - DepEd Rizal (2018)
"""

    t3 = """
EDUCATION
BS Civil Engineering | Polytechnic University of the Philippines (PUP) - Sta. Mesa, Manila | 2018 - 2022 | Dean's Lister
STEM Strand (Senior High School) | Rizal National Science High School, Binangonan, Rizal | 2016 - 2018 | With Honors
"""

    print("=" * 60)
    print("TEMPLATE 1: Multi-Tier Classic Filipino Bio-Data / Resume")
    print("=" * 60)
    print(json.dumps(extract_structured_education(t1), indent=2))

    print("\n" + "=" * 60)
    print("TEMPLATE 2: Service Crew / Undergrad + TESDA")
    print("=" * 60)
    print(json.dumps(extract_structured_education(t2), indent=2))

    print("\n" + "=" * 60)
    print("TEMPLATE 3: Compact Professional / Engineering")
    print("=" * 60)
    print(json.dumps(extract_structured_education(t3), indent=2))