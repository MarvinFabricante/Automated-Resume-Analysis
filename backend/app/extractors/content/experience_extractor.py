"""
Philippine Work Experience Extractor
-------------------------------------
High-accuracy deterministic NLP extraction pipeline for parsing structured work experience,
employment history, and OJT/internship records from Philippine resumes.

Covers:
  - Fast Food & Service: Service Crew, Dining Crew, Kitchen Crew, Fryman, Cashier, Barista, Dishwasher, Busboy
  - Retail, Logistics & Blue-Collar: Bagger, Sales Lady, Promodiser, Merchandiser, Warehouseman, Delivery Rider, Driver, Pahinante, Security Guard, Factory Worker, Welder, Electrician
  - BPO & Corporate: CSR, TSR, Call Center Agent, Virtual Assistant (VA), Data Encoder, Administrative Aide, HR Assistant, Accounting Clerk
  - Technical & Professional: Software Developer, Web Developer, Backend/Frontend Developer, QA Analyst, Civil Engineer, Site Engineer, Registered Nurse, CPA, LPT
  - Employment Status Markers: Full-Time, Contractual, End of Contract (ENDO), OJT, Intern, Practicum, Seasonal, Reliever, Project-Based, Agency-Hired

Strictly deterministic local NLP (spaCy + EntityRuler + PhraseMatcher + flashtext + dateparser + re).
"""

import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

try:
    import spacy
    from spacy.matcher import PhraseMatcher, Matcher
    from spacy.tokens import Doc
except ImportError:
    spacy = None
    PhraseMatcher = None
    Matcher = None
    Doc = None

try:
    from flashtext import KeywordProcessor
except ImportError:
    KeywordProcessor = None

try:
    import dateparser
except ImportError:
    dateparser = None

from app.extractors.content.section_parser import split_into_sections


# ─── 1. Philippine Job Taxonomy & Canonical Map ──────────────────────────────

_PHILIPPINE_JOB_TAXONOMY: Dict[str, List[str]] = {
    # ── Service, Retail & Blue-Collar
    "Service Crew": [
        "Service Crew", "Kitchen Crew", "Dining Crew", "Counter Crew",
        "Fryman", "Grill Crew", "Grill Station Crew", "Food Server",
        "Kitchen Helper", "Kitchen Staff", "Crew Member", "Dining Attendant",
        "Barista", "Cook", "Assistant Cook", "Fast Food Crew", "Pantry Crew"
    ],
    "Dishwasher": [
        "Dishwasher", "Busboy", "Kitchen Dishwasher", "Plate Cleaner", "Pot Washer"
    ],
    "Janitor": [
        "Janitor", "Janitress", "Utility Personnel", "Utility Staff",
        "Housekeeping Attendant", "Room Attendant", "Cleaner", "Sanitation Worker",
        "Maintenance Janitor", "Utility Worker", "Sanitation Crew"
    ],
    "Cashier": [
        "Cashier", "Head Cashier", "Counter Cashier", "POS Cashier",
        "Supermarket Cashier", "Retail Cashier", "Restaurant Cashier"
    ],
    "Bagger": [
        "Bagger", "Supermarket Bagger", "Package Boy", "Grocery Bagger"
    ],
    "Promodiser": [
        "Promodiser", "Merchandiser", "Sales Clerk", "Sales Lady", "Saleslady",
        "Sales Associate", "Store Crew", "Store Associate", "Salesman",
        "Retail Sales Associate", "Brand Ambassador", "Product Demonstrator"
    ],
    "Warehouseman": [
        "Warehouseman", "Warehouse Staff", "Warehouse Associate", "Warehouse Worker",
        "Warehouse Assistant", "Stockman", "Stock Custodian", "Inventory Clerk",
        "Forklift Operator", "Material Handler", "Warehouse Inventory Staff"
    ],
    "Delivery Rider": [
        "Delivery Rider", "Courier", "Company Driver", "Driver", "Truck Driver",
        "Delivery Driver", "Pahinante", "Delivery Helper", "Van Driver",
        "Motorcycle Rider", "Rider", "Food Delivery Rider", "Dispatch Rider"
    ],
    "Security Guard": [
        "Security Guard", "Lady Guard", "Security Officer", "Watchman",
        "CCTV Operator", "Roving Guard"
    ],
    "Factory Worker": [
        "Factory Worker", "Production Operator", "Assembly Worker", "Assembler",
        "Machine Operator", "Line Leader", "Production Staff", "Production Assistant",
        "Quality Control Inspector", "QC Inspector", "Manufacturing Operator"
    ],
    "Tradesman": [
        "Welder", "Mason", "Electrician", "Carpenter", "Plumber",
        "Maintenance Technician", "Aircon Technician", "Auto Mechanic",
        "Automotive Mechanic", "Heavy Equipment Operator"
    ],

    # ── BPO, Admin & Corporate
    "Customer Service Representative": [
        "Customer Service Representative", "CSR", "Call Center Agent",
        "Customer Care Specialist", "Customer Support Representative",
        "Chat Support Agent", "Email Support Agent", "Inbound Agent",
        "Outbound Agent", "Customer Support Specialist", "Contact Center Agent"
    ],
    "Technical Support Representative": [
        "Technical Support Representative", "TSR", "Technical Support Specialist",
        "Helpdesk Support", "IT Helpdesk Specialist", "Technical Support Agent"
    ],
    "Virtual Assistant": [
        "Virtual Assistant", "VA", "Executive Virtual Assistant", "General VA",
        "Real Estate Virtual Assistant", "E-commerce VA"
    ],
    "Data Encoder": [
        "Data Encoder", "Data Entry Specialist", "Data Entry Operator", "Encoder",
        "Data Processing Clerk", "Typist"
    ],
    "Admin Staff": [
        "Administrative Aide", "Admin Staff", "Administrative Assistant",
        "Office Clerk", "Office Staff", "Receptionist", "Front Desk Officer",
        "Liaison Officer", "Messenger", "Office Assistant", "Executive Assistant",
        "Office Administrator", "Administrative Officer"
    ],
    "HR Assistant": [
        "HR Assistant", "HR Staff", "HR Officer", "Recruitment Assistant",
        "Talent Acquisition Associate", "HR Specialist", "Human Resources Assistant"
    ],
    "Accounting Clerk": [
        "Accounting Clerk", "Accounting Assistant", "Bookkeeper", "Billing Clerk",
        "Billing Specialist", "Accounting Staff", "Accounts Payable Clerk",
        "Accounts Receivable Clerk", "Payroll Assistant"
    ],

    # ── Technical, Engineering & IT
    "Software Developer": [
        "Software Engineer", "Software Developer", "Web Developer",
        "Frontend Developer", "Backend Developer", "Full Stack Developer",
        "Full-Stack Developer", "Full Stack Web Developer",
        "Junior Backend Developer", "Junior Frontend Developer",
        "Senior Backend Developer", "Senior Frontend Developer",
        "Junior Software Engineer", "Senior Software Engineer",
        "Java Developer", "C# Developer", "Node.js Developer", "Python Developer",
        "React Developer", "PHP Developer", "Mobile Developer", "Android Developer",
        "iOS Developer", "Game Developer", "API Developer"
    ],
    "Software Developer Intern": [
        "Software Developer Intern", "Software Engineer Intern",
        "Software Developer Intern (OJT)", "Software Intern"
    ],
    "QA Engineer": [
        "QA Analyst", "QA Engineer", "Quality Assurance Analyst", "Quality Assurance Engineer",
        "Quality Engineer", "Software Tester", "Test Engineer", "Manual Tester", "Automation QA"
    ],
    "IT Support Specialist": [
        "IT Support Specialist", "System Administrator", "Network Engineer",
        "Database Administrator", "DevOps Engineer", "Cloud Engineer",
        "IT Technician", "Desktop Support Engineer"
    ],
    "Civil Engineer": [
        "Civil Engineer", "Site Civil Engineer", "Site Engineer", "Project Engineer",
        "Structural Engineer", "Quantity Surveyor", "Field Engineer",
        "Construction Engineer", "Cad Operator"
    ],
    "Safety Officer": [
        "Safety Officer", "BOSH Safety Officer", "COSH Safety Officer",
        "HSE Officer", "Health and Safety Officer"
    ],
    "Mechanical Engineer": [
        "Mechanical Engineer", "HVAC Engineer", "Piping Engineer", "Plant Engineer"
    ],
    "Electrical Engineer": [
        "Electrical Engineer", "Electronics Engineer", "ECE", "Power Engineer"
    ],
    "Chemical Engineer": [
        "Chemical Engineer", "Process Engineer", "Plant Chemist", "Chemical Analyst"
    ],
    "Industrial Engineer": [
        "Industrial Engineer", "Continuous Improvement Specialist", "Process Analyst",
        "Operations Analyst", "Supply Chain Analyst", "Methods Analyst"
    ],
    "Materials Engineer": [
        "Materials Engineer", "Materials Quality Engineer", "Materials Science and Engineering",
        "Metallurgical Engineer", "Ceramic Engineer", "Corrosion Engineer", "Materials Testing Technician"
    ],
    "Architect": [
        "Architect", "Architectural Designer", "Junior Architect", "Architectural Apprentice"
    ],

    # ── Healthcare & Professional
    "Registered Nurse": [
        "Registered Nurse", "Staff Nurse", "Clinic Nurse", "Company Nurse",
        "Ward Nurse", "ICU Nurse", "Nurse"
    ],
    "Medical Technologist": [
        "Medical Technologist", "MedTech", "Laboratory Analyst", "Lab Technician"
    ],
    "Pharmacist": [
        "Pharmacist", "Pharmacy Assistant", "Clinical Pharmacist", "Drugstore Pharmacist"
    ],
    "Licensed Professional Teacher": [
        "Licensed Professional Teacher", "LPT", "Teacher", "High School Teacher",
        "Elementary Teacher", "Instructor", "College Instructor", "Professor"
    ],
    "Certified Public Accountant": [
        "Certified Public Accountant", "CPA", "Audit Associate", "External Auditor",
        "Internal Auditor", "Senior Auditor", "Tax Associate"
    ],
    "Bank Teller": [
        "Bank Teller", "Universal Banker", "Branch Teller", "Customer Service Teller",
        "Loan Officer", "Account Officer", "Store Manager", "Branch Manager"
    ],
    "Intern / OJT": [
        "Intern", "OJT", "On-the-Job Trainee", "Student Trainee", "Practicum Trainee",
        "Engineering Intern", "IT Intern", "Accounting Intern", "Marketing Intern",
        "HR Intern", "Apprentice"
    ]
}

# Flashtext KeywordProcessor
_KEYWORD_PROCESSOR = None
if KeywordProcessor is not None:
    _KEYWORD_PROCESSOR = KeywordProcessor(case_sensitive=False)
    for canonical, variations in _PHILIPPINE_JOB_TAXONOMY.items():
        for var in variations:
            _KEYWORD_PROCESSOR.add_keyword(var, canonical)


# ─── 2. Employment Status Markers ────────────────────────────────────────────

_EMPLOYMENT_TYPE_RULES = [
    (re.compile(r'\b(?:OJT|On-the-Job\s+Training|Intern(?:ship)?|Practicum|Student\s+Trainee|Trainee|Apprentice)\b', re.IGNORECASE), "OJT"),
    (re.compile(r'\b(?:End\s+of\s+Contract|ENDO|Contractual|Fixed-Term|Contract|Temporary)\b', re.IGNORECASE), "Contractual"),
    (re.compile(r'\b(?:Project-Based|Project\s+Based|Per\s+Project)\b', re.IGNORECASE), "Contractual"),
    (re.compile(r'\b(?:via\s+Manpower\s+Agency|Manpower\s+Agency|Agency-Hired|Agency|Outsourced)\b', re.IGNORECASE), "Contractual"),
    (re.compile(r'\b(?:Seasonal|Holiday(?:\s+(?:Hire|Reliever|Staff))?|Peak\s+Season|Christmas\s+Hire)\b', re.IGNORECASE), "Seasonal"),
    (re.compile(r'\b(?:Reliever|Substitute)\b', re.IGNORECASE), "Contractual"),
    (re.compile(r'\b(?:Part-Time|Part\s+Time|Parttime)\b', re.IGNORECASE), "Part-time"),
    (re.compile(r'\b(?:Full-Time|Full\s+Time|Regular|Permanent)\b', re.IGNORECASE), "Full-time"),
]


# ─── 3. Philippine Corporate and Employer Patterns ───────────────────────────

_PHIL_COMPANY_NAMES = [
    "Jollibee", "Jollibee Foods Corporation", "McDonald's", "McDonalds", "Chowking",
    "Mang Inasal", "Greenwich", "Red Ribbon", "Goldilocks", "KFC", "Gerry's Grill",
    "Robinsons", "Robinsons Place", "Robinsons Galleria", "Robinsons Land", "SM",
    "SM Supermalls", "SM City", "Puregold", "Ayala Malls", "Ayala Land", "DMCI",
    "DMCI Homes", "Accenture", "Accenture Philippines", "Teleperformance", "Concentrix",
    "Convergys", "TaskUs", "Alorica", "Foundever", "Sitel", "Cognizant", "Globe Telecom",
    "Smart Communications", "PLDT", "San Miguel Corporation", "San Miguel Brewery",
    "BDO", "BPI", "Metrobank", "Foodpanda", "Food Panda", "Grab", "Lalamove", "Shopee",
    "Lazada", "Angkas", "Monde Nissin", "Universal Robina", "ChanzIT", "Fourello",
    "Vaskeappen", "Maxim", "Ninja Van", "J&T Express", "Flash Express", "Toktok",
    "Mariwasa", "Mariwasa Siam Ceramics", "Mariwasa Siam Ceramics Inc.",
    "XYZ Tech Solutions Inc."
]

_COMPANY_LEGAL_SUFFIXES_RE = re.compile(
    r'\b(?:Inc\.?|Corp\.?|Corporation|Co\.?|Ltd\.?|LLC|Holdings|Enterprises|Services|Trading|Foods|Solutions|Technologies|Group|Agency|Branch|Manpower|Industries|Manufacturing|Ceramics|Systems|Consulting|Logistics|Phils\.?|Philippines)\b',
    re.IGNORECASE
)

_JOB_TITLE_KEYWORDS_RE = re.compile(
    r'\b(?:Engineer|Engineering|Developer|Programmer|Specialist|Manager|Director|Officer|Analyst|Lead|Supervisor|'
    r'Technician|Assistant|Associate|Operator|Representative|Consultant|Architect|Designer|Coordinator|'
    r'Administrator|Crew|Cashier|Rider|Driver|Clerk|Intern|Trainee|Nurse|Teacher|Instructor|Professor|'
    r'Accountant|Auditor|Chemist|Pharmacist|Janitor|Cook|Chef|Staff|Executive|Practitioner|Worker|Scientist)\b',
    re.IGNORECASE
)

# Philippine Locations
_PHIL_LOCATIONS_SET = {
    "manila", "quezon city", "makati", "makati city", "taguig", "taguig city", "bgc",
    "bonifacio global city", "pasig", "pasig city", "ortigas", "mandaluyong",
    "san juan", "marikina", "pasay", "parañaque", "muntinlupa", "las piñas",
    "caloocan", "malabon", "navotas", "valenzuela", "rizal", "antipolo", "taytay",
    "cainta", "teresa", "binangonan", "san mateo", "rodriguez", "laguna", "calamba",
    "santa rosa", "biñan", "san pedro", "cabuyao", "los baños", "cavite", "bacoor",
    "dasmarinas", "dasmariñas", "imus", "general trias", "tagaytay", "batangas",
    "bulacan", "pampanga", "angeles city", "san fernando", "clark", "subic",
    "cebu", "cebu city", "davao", "davao city", "iloilo", "baguio", "baguio city",
    "cagayan de oro", "bacolod", "general santos"
}


# ─── 4. spaCy Pipeline Setup ─────────────────────────────────────────────────

_SPACY_NLP = None
_PHRASE_MATCHER = None

def _get_spacy_pipeline():
    global _SPACY_NLP, _PHRASE_MATCHER
    if _SPACY_NLP is not None:
        return _SPACY_NLP, _PHRASE_MATCHER

    if spacy is None:
        return None, None

    try:
        from app.extractors.nlp.nlp_engine import get_doc
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        return None, None

    # Add EntityRuler for Philippine Job Titles & Employers
    if "entity_ruler" not in nlp.pipe_names:
        try:
            ruler = nlp.add_pipe("entity_ruler", before="ner")
            patterns = []
            for canonical, vars_list in _PHILIPPINE_JOB_TAXONOMY.items():
                for v in vars_list:
                    patterns.append({"label": "PH_JOB_TITLE", "pattern": v})
            for c in _PHIL_COMPANY_NAMES:
                patterns.append({"label": "PH_EMPLOYER", "pattern": c})
            ruler.add_patterns(patterns)
        except Exception:
            pass

    # Add PhraseMatcher for rapid token matching
    try:
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        for canonical, vars_list in _PHILIPPINE_JOB_TAXONOMY.items():
            patterns = [nlp.make_doc(v) for v in vars_list]
            matcher.add(canonical, patterns)
        _PHRASE_MATCHER = matcher
    except Exception:
        pass

    _SPACY_NLP = nlp
    return _SPACY_NLP, _PHRASE_MATCHER


def _extract_title_with_spacy(line: str) -> Optional[str]:
    """
    Uses spaCy EntityRuler, PhraseMatcher, and POS dependency parsing
    to extract job titles, including out-of-vocabulary titles (Noun Phrases
    adjacent to dates or company indicators).
    """
    nlp, matcher = _get_spacy_pipeline()
    if not nlp:
        return None

    try:
        doc = nlp(line[:100])
        # 1. Check EntityRuler PH_JOB_TITLE entities
        for ent in doc.ents:
            if ent.label_ == "PH_JOB_TITLE":
                return ent.text

        # 2. Check PhraseMatcher
        if matcher:
            matches = matcher(doc)
            if matches:
                match_id, start, end = matches[0]
                return doc[start:end].text

        # 3. POS tagging & Dependency parsing for Out-of-Vocabulary titles
        action_verbs = {
            "assigned", "responsible", "handled", "managed", "supervised",
            "developed", "maintained", "performed", "duties"
        }
        words_lower = {tok.text.lower() for tok in doc}
        if words_lower & action_verbs:
            return None

        # Check noun chunks
        noun_chunks = [chunk.text for chunk in doc.noun_chunks if 1 <= len(chunk.text.split()) <= 5]
        if noun_chunks and len(line.split()) <= 6:
            if all(tok.pos_ in ("NOUN", "PROPN", "ADJ", "PUNCT", "CCONJ", "SYM") for tok in doc if not tok.is_space):
                return line.strip()
    except Exception:
        pass

    return None


# ─── 5. Date & Duration Parsing ──────────────────────────────────────────────

_MONTHS_NAMES = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
)
_YEAR_RE = r'(?:19|20)\d{2}'
_PRESENT_RE = r'(?:Present|Current|Now|To\s+Date|Ongoing|Today|Up\s+to\s+present)'

_DATE_RANGE_REGEX = re.compile(
    rf'({_MONTHS_NAMES}\s*\.?\s*{_YEAR_RE}|\d{{1,2}}/\d{{4}}|{_YEAR_RE})\s*(?:[-–—]|to|until|up\s+to)\s*({_MONTHS_NAMES}\s*\.?\s*{_YEAR_RE}|\d{{1,2}}/\d{{4}}|{_YEAR_RE}|{_PRESENT_RE})',
    re.IGNORECASE
)

_HOURS_REGEX = re.compile(r'\(?(\d+)\s*(?:Hours?|Hrs?)\)?', re.IGNORECASE)


def _month_name_to_num(month_str: str) -> int:
    m = month_str.strip().lower().rstrip('.')
    mapping = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    return mapping.get(m, 1)


def _parse_single_date(d_str: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Parse string like 'June 2023', '06/2023', '2023' into ('2023-06', year, month)."""
    if not d_str:
        return None, None, None
    d_clean = d_str.strip()
    if re.match(rf'^{_PRESENT_RE}$', d_clean, re.IGNORECASE):
        now = datetime.now()
        return "Present", now.year, now.month

    # Check "Month YYYY"
    m_match = re.search(rf'({_MONTHS_NAMES})\s*\.?\s*({_YEAR_RE})', d_clean, re.IGNORECASE)
    if m_match:
        m_num = _month_name_to_num(m_match.group(1))
        yr = int(m_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # Check MM/YYYY
    slash_match = re.search(r'(\d{1,2})/(\d{4})', d_clean)
    if slash_match:
        m_num = max(1, min(12, int(slash_match.group(1))))
        yr = int(slash_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # Check YYYY
    y_match = re.search(rf'\b({_YEAR_RE})\b', d_clean)
    if y_match:
        yr = int(y_match.group(1))
        return f"{yr:04d}-01", yr, 1

    # Fallback to dateparser if available
    if dateparser is not None:
        try:
            parsed = dateparser.parse(d_clean)
            if parsed:
                return f"{parsed.year:04d}-{parsed.month:02d}", parsed.year, parsed.month
        except Exception:
            pass

    return None, None, None


def _parse_date_and_duration(text: str) -> Tuple[Optional[str], Optional[str], int, str]:
    """
    Extracts start_date (YYYY-MM), end_date (YYYY-MM | Present), duration_months, and extra status string.
    """
    match = _DATE_RANGE_REGEX.search(text)
    if not match:
        return None, None, 0, ""

    raw_start = match.group(1).strip()
    raw_end = match.group(2).strip()

    start_iso, s_yr, s_mo = _parse_single_date(raw_start)
    end_iso, e_yr, e_mo = _parse_single_date(raw_end)

    # If raw_end is strictly a 4-digit year, default to December of that year
    if e_yr and re.fullmatch(r'\d{4}', raw_end.strip()):
        e_mo = 12
        end_iso = f"{e_yr:04d}-12"

    duration = 0
    now = datetime.now()
    if s_yr and s_mo:
        if end_iso == "Present" or not e_yr:
            target_yr, target_mo = now.year, now.month
            duration = max(1, (target_yr - s_yr) * 12 + (target_mo - s_mo) + 1)
        elif e_yr and e_mo:
            duration = max(1, (e_yr - s_yr) * 12 + (e_mo - s_mo) + 1)

    # Check if hours mentioned (e.g. 486 Hours)
    hrs_match = _HOURS_REGEX.search(text)
    if hrs_match and duration == 0:
        hrs = int(hrs_match.group(1))
        duration = max(1, round(hrs / 160.0))

    # Extra text (status info outside date range)
    extra_text = text[:match.start()] + " " + text[match.end():]
    extra_text = re.sub(r'[\s\-–—()|]+', ' ', extra_text).strip()

    return start_iso, end_iso, duration, extra_text


def _detect_employment_type(raw_title: str, company: str = "", date_line: str = "", responsibilities: Optional[List[str]] = None) -> str:
    resps = responsibilities or []
    combined = f"{raw_title} {company} {date_line} {' '.join(resps)}"
    for regex, emp_type in _EMPLOYMENT_TYPE_RULES:
        if regex.search(combined):
            return emp_type
    return "Full-time"


_RESUME_SECTION_HEADERS = {
    "professional experience", "work experience", "experience", "employment history",
    "work history", "career history", "relevant experience", "on-the-job training",
    "education", "educational background", "academic background", "qualifications",
    "skills", "technical skills", "core competencies", "certifications", "licenses",
    "licenses and eligibility", "trainings", "seminars", "projects", "references",
    "character references", "personal information", "contact information",
    "summary", "professional summary", "career objective", "objective"
}


_ADDRESS_PATTERNS = re.compile(
    r'\b(?:Avenue|Ave\.?|Street|St\.?|Barangay|Brgy\.?|Subdivision|Subd\.?|Boulevard|Blvd\.?|Road|Rd\.?|Highway|Hwy\.?|Bldg\.?|Building|Block|Blk\.?|Lot|Compound|Phase|Sitio|Purok)\b',
    re.IGNORECASE
)


def _is_address_or_location(text: str) -> bool:
    """Detect if text is an address or location rather than job title or company."""
    if not text:
        return False
    lower = text.lower().strip()
    if _ADDRESS_PATTERNS.search(lower):
        job_words = ["developer", "engineer", "crew", "cashier", "rider", "driver", "clerk", "agent", "assistant", "manager", "specialist", "technician", "worker", "officer", "analyst"]
        if not any(w in lower for w in job_words):
            return True
    # If string consists primarily of Philippine location names
    if any(loc == lower or f", {loc}" in lower for loc in _PHIL_LOCATIONS_SET):
        job_words = ["developer", "engineer", "crew", "cashier", "rider", "driver", "clerk", "agent", "assistant", "manager", "specialist", "technician", "worker", "officer", "analyst"]
        if not any(w in lower for w in job_words) and not _COMPANY_LEGAL_SUFFIXES_RE.search(lower):
            return True
    return False


def _normalize_job_title(raw_title: str) -> str:
    """
    Normalizes raw job title to clean, standardized title string:
    - Strips noisy annotations like (OJT), (Kitchen / Grill), (Full-time), etc.
    - Strips leading/trailing symbols, bullets, or separators.
    - Normalizes casing to Title Case.
    - Standardizes known abbreviations where appropriate (e.g., CSR -> Customer Service Representative).
    """
    if not raw_title:
        return ""

    clean = re.sub(r'\s*\([^)]*\)', '', raw_title).strip()
    clean = re.sub(r'\s*\|\s*.*$', '', clean).strip()
    clean = re.sub(r'^[•\-\*▪►✓\s:]+|[•\-\*▪►✓\s:]+$', '', clean).strip()

    if clean.lower() in _RESUME_SECTION_HEADERS or any(clean.lower().startswith(h) for h in _RESUME_SECTION_HEADERS):
        return ""

    if _is_address_or_location(clean):
        return ""

    acronym_map = {
        "CSR": "Customer Service Representative",
        "TSR": "Technical Support Representative",
        "VA": "Virtual Assistant",
        "QA": "QA Engineer",
        "QC": "Quality Control Inspector",
        "LPT": "Licensed Professional Teacher",
        "CPA": "Certified Public Accountant",
        "ECE": "Electronics Engineer",
    }
    if clean.upper() in acronym_map:
        return acronym_map[clean.upper()]

    if '/' in clean:
        parts = [p.strip() for p in clean.split('/')]
        norm_parts = [acronym_map.get(p.upper(), p.title() if p.isupper() else p) for p in parts]
        dedup = []
        for np in norm_parts:
            if np not in dedup:
                dedup.append(np)
        return " / ".join(dedup)

    if clean.isupper():
        return clean.title()

    # Check spaCy POS / entity fallback
    spacy_cand = _extract_title_with_spacy(clean)
    if spacy_cand:
        return spacy_cand.title() if spacy_cand.isupper() else spacy_cand

    return clean


def _split_company_and_location(raw_text: str) -> Tuple[str, Optional[str]]:
    """
    Splits company string into (company_name, location).
    """
    clean = raw_text.strip()
    # Strip parenthetical agency remarks from company name
    clean = re.sub(r'\(via\s+[^)]+\)', '', clean, flags=re.IGNORECASE).strip()

    # Case 1: Pipe separator 'Accenture Philippines | BGC, Taguig City'
    if '|' in clean:
        parts = [p.strip() for p in clean.split('|', 1)]
        return parts[0], parts[1] if len(parts) > 1 and parts[1] else None

    # Case 2: Dash separator 'Chowking - SM City Taytay' or 'Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna'
    if ' - ' in clean or ' – ' in clean or ' — ' in clean:
        parts = re.split(r'\s+[-–—]\s+', clean, maxsplit=1)
        comp = parts[0].strip()
        loc = parts[1].strip() if len(parts) > 1 else None
        return comp, loc

    # Case 3: Comma separator 'XYZ Tech Solutions Inc., Makati City'
    if ',' in clean:
        parts = [p.strip() for p in clean.split(',', 1)]
        first = parts[0]
        rest = parts[1]
        if _COMPANY_LEGAL_SUFFIXES_RE.search(first) or any(c.lower() in first.lower() for c in _PHIL_COMPANY_NAMES):
            return first, rest
        if any(loc in rest.lower() for loc in _PHIL_LOCATIONS_SET):
            return first, rest

    # Case 4: No separator, check if location is trailing
    for loc in sorted(_PHIL_LOCATIONS_SET, key=len, reverse=True):
        if clean.lower().endswith(loc):
            idx = clean.lower().rfind(loc)
            comp = clean[:idx].strip(' ,-–—')
            found_loc = clean[idx:].strip(' ,-–—')
            if comp:
                return comp, found_loc

    return clean, None


def _extract_title_company_location(title_cand: str, comp_cand: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Decouples raw title, company, and location strings even when written on the same line,
    swapped, or combined (e.g. 'Food Panda Delivery Rider', 'Delivery Rider at Food Panda').
    Returns (job_title, company_name, location).
    """
    title_cand = title_cand.strip() if title_cand else ""
    comp_cand = comp_cand.strip() if comp_cand else ""

    # Check if comp_cand is actually an address
    loc_override = None
    if comp_cand and _is_address_or_location(comp_cand):
        loc_override = comp_cand
        comp_cand = ""

    # Check if lines were swapped: title_cand is company and comp_cand is job title
    if comp_cand:
        title_has_comp_signals = bool(_COMPANY_LEGAL_SUFFIXES_RE.search(title_cand) or any(c.lower() in title_cand.lower() for c in _PHIL_COMPANY_NAMES))
        comp_has_comp_signals = bool(_COMPANY_LEGAL_SUFFIXES_RE.search(comp_cand) or any(c.lower() in comp_cand.lower() for c in _PHIL_COMPANY_NAMES))

        title_has_job_signals = bool(_JOB_TITLE_KEYWORDS_RE.search(title_cand) or any(t.lower() in title_cand.lower() for vars_list in _PHILIPPINE_JOB_TAXONOMY.values() for t in vars_list))
        comp_has_job_signals = bool(_JOB_TITLE_KEYWORDS_RE.search(comp_cand) or any(t.lower() in comp_cand.lower() for vars_list in _PHILIPPINE_JOB_TAXONOMY.values() for t in vars_list))

        should_swap = False
        if title_has_comp_signals and comp_has_job_signals and not comp_has_comp_signals:
            should_swap = True
        elif not title_has_job_signals and comp_has_job_signals and not comp_has_comp_signals:
            should_swap = True

        if should_swap:
            title_cand, comp_cand = comp_cand, title_cand

    if comp_cand:
        company, location = _split_company_and_location(comp_cand)
        norm_title = _normalize_job_title(title_cand)
        return norm_title, company, location or loc_override

    # If comp_cand is empty, parse title_cand
    if not title_cand:
        return "", "", loc_override

    # 1. Check ' at ' or ' @ '
    at_match = re.search(r'\s+(?:at|@)\s+', title_cand, re.IGNORECASE)
    if at_match:
        t_part = title_cand[:at_match.start()].strip()
        c_part = title_cand[at_match.end():].strip()
        comp, loc = _split_company_and_location(c_part)
        return _normalize_job_title(t_part), comp, loc or loc_override

    # 2. Check ' - ' or ' – ' or ' — '
    if re.search(r'\s+[-–—]\s+', title_cand):
        parts = re.split(r'\s+[-–—]\s+', title_cand, maxsplit=1)
        p1, p2 = parts[0].strip(), parts[1].strip()
        p1_comp = bool(_COMPANY_LEGAL_SUFFIXES_RE.search(p1) or any(c.lower() == p1.lower() for c in _PHIL_COMPANY_NAMES))
        p2_comp = bool(_COMPANY_LEGAL_SUFFIXES_RE.search(p2) or any(c.lower() == p2.lower() for c in _PHIL_COMPANY_NAMES))
        if p1_comp and not p2_comp:
            comp, loc = _split_company_and_location(p1)
            return _normalize_job_title(p2), comp, loc or loc_override
        else:
            comp, loc = _split_company_and_location(p2)
            return _normalize_job_title(p1), comp, loc or loc_override

    # 3. Check known Philippine company prefixes/suffixes
    for c in sorted(_PHIL_COMPANY_NAMES, key=len, reverse=True):
        c_low = c.lower()
        t_low = title_cand.lower()
        if t_low.startswith(c_low) and len(title_cand) > len(c):
            boundary_char = title_cand[len(c):len(c)+1]
            if boundary_char in " \t-–—|,/":
                rem = title_cand[len(c):].strip(" \t-–—|,/")
                if rem:
                    return _normalize_job_title(rem), c, loc_override
        elif t_low.endswith(c_low) and len(title_cand) > len(c):
            boundary_char = title_cand[-len(c)-1:-len(c)]
            if boundary_char in " \t-–—|,/":
                rem = title_cand[:-len(c)].strip(" \t-–—|,/")
                if rem:
                    return _normalize_job_title(rem), c, loc_override

    # 4. Check known job taxonomy suffixes (e.g. 'Food Panda Delivery Rider')
    all_taxonomy_titles = []
    for vars_list in _PHILIPPINE_JOB_TAXONOMY.values():
        all_taxonomy_titles.extend(vars_list)
    for tax_title in sorted(all_taxonomy_titles, key=len, reverse=True):
        tax_low = tax_title.lower()
        t_low = title_cand.lower()
        if t_low.endswith(tax_low) and len(title_cand) > len(tax_title):
            boundary_char = title_cand[-len(tax_title)-1:-len(tax_title)]
            if boundary_char in " \t-–—|,/":
                prefix = title_cand[:-len(tax_title)].strip(" \t-–—|,/")
                if len(prefix) >= 3 and not _is_address_or_location(prefix):
                    comp, loc = _split_company_and_location(prefix)
                    return _normalize_job_title(tax_title), comp, loc or loc_override

    norm_title = _normalize_job_title(title_cand)
    return norm_title, "", loc_override


def _is_section_header(line: str) -> bool:
    clean = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', line.strip()).upper()
    headers = [
        "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE",
        "RELEVANT EXPERIENCE", "WORK HISTORY", "ON-THE-JOB TRAINING (OJT)",
        "ON-THE-JOB TRAINING", "OJT", "INTERNSHIP", "PRACTICUM",
        "EDUCATION", "SKILLS", "CERTIFICATIONS", "PROJECTS", "SUMMARY",
        "CHARACTER REFERENCES", "REFERENCES", "PERSONAL DATA", "SEMINARS/TRAININGS",
        "TRAINING", "SEMINARS", "PERSONAL INFORMATION", "AFFILIATIONS", "AWARDS"
    ]
    return clean in headers or any(clean.startswith(h + ":") for h in headers)


def _extract_experience_blocks(text: str) -> List[str]:
    """
    Extracts all sections corresponding to Work Experience and OJT/Internship.
    """
    exp_headers = [
        "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE",
        "RELEVANT EXPERIENCE", "WORK HISTORY", "CAREER HISTORY", "JOB EXPERIENCE",
        "CAREER SUMMARY", "CAREER EXPERIENCE", "POSITIONS HELD", "WORK RECORD",
        "INDUSTRY EXPERIENCE", "PROFESSIONAL HISTORY", "WORK AND EXPERIENCE",
        "RELEVANT WORK EXPERIENCE", "EMPLOYMENT RECORD", "WORK BACKGROUND",
        "OCCUPATIONAL HISTORY", "EMPLOYMENT BACKGROUND", "CAREER BACKGROUND",
        "RELEVANT EMPLOYMENT", "ON-THE-JOB TRAINING (OJT)", "ON-THE-JOB TRAINING",
        "ON THE JOB TRAINING", "OJT", "INTERNSHIP", "INTERNSHIPS", "PRACTICUM",
        "ON-THE-JOB TRAINING / INTERNSHIP", "ON-THE-JOB TRAINING (OJT) / INTERNSHIP / PRACTICUM",
        "PRACTICUM / INTERNSHIP", "INTERNSHIP / PRACTICUM", "APPRENTICESHIP",
    ]
    stop_headers = [
        "EDUCATION", "SKILLS", "CERTIFICATIONS", "PROJECTS", "QUALIFICATIONS",
        "ACHIEVEMENTS", "AFFILIATIONS", "REFERENCES", "CHARACTER REFERENCES",
        "INTERESTS", "AWARDS", "PUBLICATIONS", "HOBBIES", "VOLUNTEER",
        "PERSONAL", "PERSONAL DATA", "BIODATA", "TRAINING", "SEMINARS",
        "SEMINARS/TRAININGS", "TECHNICAL SKILLS", "LANGUAGES"
    ]

    lines = text.split('\n')
    extracted_blocks = []
    current_block = []
    in_exp = False

    for line in lines:
        cleaned = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', line.strip()).upper()

        if any(cleaned == h or cleaned.startswith(h + ":") for h in exp_headers):
            if current_block:
                extracted_blocks.append('\n'.join(current_block))
                current_block = []
            in_exp = True
            continue
        elif any(cleaned == h or cleaned.startswith(h + ":") for h in stop_headers):
            if in_exp and current_block:
                extracted_blocks.append('\n'.join(current_block))
                current_block = []
            in_exp = False
            continue

        if in_exp:
            current_block.append(line)

    if current_block:
        extracted_blocks.append('\n'.join(current_block))

    if extracted_blocks:
        return extracted_blocks

    # If other section headers (like EDUCATION, SKILLS, etc.) exist in the document,
    # but NO experience header was found, then there is NO work experience section!
    has_other_section_headers = any(
        any(re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', l.strip()).upper() == sh or 
            re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', l.strip()).upper().startswith(sh + ":")
            for sh in stop_headers)
        for l in lines
    )
    if has_other_section_headers:
        return []

    return [text]


# ─── 6. Primary Structured Extractor ─────────────────────────────────────────

def extract_structured_experience(text: str) -> Dict[str, Any]:
    """
    Extracts structured work experience entries tailored to Philippine resumes.
    Returns:
    {
      "total_experience_months": <int>,
      "work_experiences": [
        {
          "job_title": "<Normalized Title String>",
          "raw_job_title": "<Exact Title Text from Resume>",
          "company_name": "<Company/Employer String>",
          "location": "<City/Province/Branch String or None>",
          "employment_type": "<Full-time | Contractual | OJT | Part-time | Seasonal | Unknown>",
          "start_date": "<YYYY-MM or None>",
          "end_date": "<YYYY-MM | Present | None>",
          "duration_months": <int>,
          "responsibilities": ["<Duty 1>", "<Duty 2>"]
        }
      ]
    }
    """
    if not text:
        return {"total_experience_months": 0, "work_experiences": []}

    blocks = _extract_experience_blocks(text)
    combined_exp_text = "\n\n".join(blocks)

    lines = [l.strip() for l in combined_exp_text.split('\n') if l.strip()]
    if not lines:
        return {"total_experience_months": 0, "work_experiences": []}

    work_experiences = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if _is_section_header(line) or line.strip().lower() in _RESUME_SECTION_HEADERS or any(line.strip().lower().startswith(h) for h in _RESUME_SECTION_HEADERS):
            i += 1
            continue

        # ── Case A: Inline or Date-First entry format ─────────────────────────
        if _DATE_RANGE_REGEX.search(line):
            dm = _DATE_RANGE_REGEX.search(line)
            before_date = line[:dm.start()].strip(' -–—(),|')
            after_date = line[dm.end():].strip(' -–—(),|')

            if not before_date:
                # Standalone date or Date-First line (e.g. "2021 - Present" or "2021 - Present | Senior Developer | Tech Mahindra")
                date_str = line[dm.start():dm.end()].strip()
                if after_date:
                    if '|' in after_date:
                        segs = [s.strip() for s in after_date.split('|') if s.strip()]
                        raw_title = segs[0] if segs else ""
                        comp_loc_str = " | ".join(segs[1:]) if len(segs) > 1 else ""
                    else:
                        raw_title = after_date
                        comp_loc_str = ""
                    consumed_header = 1
                else:
                    consumed_header = 1
                    raw_title = ""
                    comp_loc_str = ""
                    if i + 1 < len(lines) and not _is_section_header(lines[i + 1]) and not lines[i + 1].startswith(('•', '-', '*', '▪', '►', '✓')) and not _DATE_RANGE_REGEX.search(lines[i + 1]):
                        raw_title = lines[i + 1]
                        consumed_header = 2
                        if i + 2 < len(lines) and not _is_section_header(lines[i + 2]) and not lines[i + 2].startswith(('•', '-', '*', '▪', '►', '✓')) and not _DATE_RANGE_REGEX.search(lines[i + 2]):
                            comp_loc_str = lines[i + 2]
                            consumed_header = 3
                            if i + 3 < len(lines) and not _is_section_header(lines[i + 3]) and not lines[i + 3].startswith(('•', '-', '*', '▪', '►', '✓')) and not _DATE_RANGE_REGEX.search(lines[i + 3]) and _is_address_or_location(lines[i + 3]):
                                comp_loc_str = f"{comp_loc_str} - {lines[i + 3]}"
                                consumed_header = 4
                norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
            elif '|' in line:
                segments = [s.strip() for s in line.split('|')]
                date_idx = next((idx for idx, s in enumerate(segments) if _DATE_RANGE_REGEX.search(s)), -1)
                if date_idx >= 0:
                    date_str = segments[date_idx]
                    other_segs = [s for idx, s in enumerate(segments) if idx != date_idx]
                    raw_title = other_segs[0] if other_segs else ""
                    comp_loc_str = " | ".join(other_segs[1:]) if len(other_segs) > 1 else ""
                else:
                    raw_title = segments[0]
                    comp_loc_str = segments[1] if len(segments) > 1 else ""
                    date_str = segments[2] if len(segments) > 2 else ""
                norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
                consumed_header = 1
            else:
                title_comp_str = before_date
                date_str = line[dm.start():].strip(' ()')
                raw_title = title_comp_str
                norm_title, company, location = _extract_title_company_location(title_comp_str)
                comp_loc_str = company + (f" - {location}" if location else "")
                consumed_header = 1

            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_str)

            # Responsibilities in subsequent lines
            responsibilities = []
            curr_idx = i + consumed_header
            while curr_idx < len(lines):
                next_l = lines[curr_idx]
                if _DATE_RANGE_REGEX.search(next_l):
                    break
                if _is_section_header(next_l):
                    break
                d_match = re.match(r'^(?:Duties|Responsibilities|Key\s+Tasks)\s*[:.\-]\s*(.+)', next_l, re.IGNORECASE)
                if d_match:
                    responsibilities.append(d_match.group(1).strip())
                    curr_idx += 1
                    continue
                elif next_l.startswith(('•', '-', '*', '▪', '►', '✓')):
                    duty_text = next_l.lstrip('•-*▪►✓ ').strip()
                    if duty_text:
                        responsibilities.append(duty_text)
                    curr_idx += 1
                    continue
                elif not _DATE_RANGE_REGEX.search(next_l) and not any(comp.lower() in next_l.lower() for comp in _PHIL_COMPANY_NAMES):
                    if len(next_l) > 15 and not _is_address_or_location(next_l):
                        responsibilities.append(next_l)
                        curr_idx += 1
                        continue
                break

            emp_type = _detect_employment_type(raw_title, comp_loc_str, date_str, responsibilities)
            # Reject academic degrees / schooling mistaken as employment roles
            if re.search(r'\b(?:bachelor|master|doctor|phd|diploma|associate|elementary|high\s+school)\b', raw_title, re.I):
                i = curr_idx
                continue
            if re.search(r'\b(?:university|college|polytechnic)\b', comp_loc_str or company or "", re.I) and re.search(r'\b(?:bachelor|master|degree|course|bs|ba|ab|bba|bsba|bscpe|bsit|bscs)\b', raw_title, re.I):
                i = curr_idx
                continue

            if norm_title and not _is_address_or_location(norm_title):
                work_experiences.append({
                    "job_title": norm_title,
                    "role": norm_title,
                    "title": norm_title,
                    "raw_job_title": raw_title,
                    "company_name": company,
                    "company": company,
                    "location": location,
                    "employment_type": emp_type,
                    "start_date": start_iso,
                    "end_date": end_iso,
                    "duration_months": duration,
                    "responsibilities": responsibilities,
                    "highlights": responsibilities,
                })
            i = curr_idx
            continue

        # ── Case B: Multi-line block format (Template 1 & Template 3) ─────────
        has_date_ahead = False
        date_offset = -1
        for offset in range(1, min(4, len(lines) - i)):
            if _DATE_RANGE_REGEX.search(lines[i + offset]):
                has_date_ahead = True
                date_offset = offset
                break

        if has_date_ahead:
            raw_title = line
            date_line = lines[i + date_offset]
            if date_offset == 3:
                comp_loc_str = f"{lines[i + 1]} - {lines[i + 2]}"
                consumed_header = 4
            elif date_offset == 2:
                comp_loc_str = lines[i + 1]
                consumed_header = 3
            elif date_offset == 1:
                comp_loc_str = lines[i + 2] if i + 2 < len(lines) and not lines[i + 2].startswith(('-', '•', '*')) else ""
                consumed_header = 3 if comp_loc_str else 2

            if '|' in raw_title:
                parts = [p.strip() for p in raw_title.split('|', 1)]
                raw_title = parts[0]
                if not comp_loc_str and len(parts) > 1:
                    comp_loc_str = parts[1]

            norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_line)

            # Responsibilities
            responsibilities = []
            curr_idx = i + consumed_header
            while curr_idx < len(lines):
                curr_l = lines[curr_idx]
                if _is_section_header(curr_l):
                    break
                is_next_role = False
                for fwd in range(1, 3):
                    if curr_idx + fwd < len(lines) and _DATE_RANGE_REGEX.search(lines[curr_idx + fwd]):
                        is_next_role = True
                        break
                if is_next_role and not curr_l.startswith(('•', '-', '*', '▪', '►', '✓')):
                    break

                d_match = re.match(r'^(?:Duties|Responsibilities|Key\s+Tasks)\s*[:.\-]\s*(.+)', curr_l, re.IGNORECASE)
                if d_match:
                    responsibilities.append(d_match.group(1).strip())
                elif curr_l.startswith(('•', '-', '*', '▪', '►', '✓')):
                    cleaned_duty = curr_l.lstrip('•-*▪►✓ ').strip()
                    if cleaned_duty:
                        responsibilities.append(cleaned_duty)
                elif len(curr_l) > 15 and not _is_address_or_location(curr_l):
                    responsibilities.append(curr_l)
                curr_idx += 1

            emp_type = _detect_employment_type(raw_title, comp_loc_str, date_line, responsibilities)
            # Reject academic degrees / schooling mistaken as employment roles
            if re.search(r'\b(?:bachelor|master|doctor|phd|diploma|associate|elementary|high\s+school)\b', raw_title, re.I):
                i = curr_idx
                continue
            if re.search(r'\b(?:university|college|polytechnic)\b', comp_loc_str or company or "", re.I) and re.search(r'\b(?:bachelor|master|degree|course|bs|ba|ab|bba|bsba|bscpe|bsit|bscs)\b', raw_title, re.I):
                i = curr_idx
                continue

            if norm_title and not _is_address_or_location(norm_title):
                work_experiences.append({
                    "job_title": norm_title,
                    "role": norm_title,
                    "title": norm_title,
                    "raw_job_title": raw_title,
                    "company_name": company,
                    "company": company,
                    "location": location,
                    "employment_type": emp_type,
                    "start_date": start_iso,
                    "end_date": end_iso,
                    "duration_months": duration,
                    "responsibilities": responsibilities,
                    "highlights": responsibilities,
                })

            i = curr_idx
            continue


        i += 1

    total_months = sum(e["duration_months"] for e in work_experiences)
    return {
        "total_experience_months": total_months,
        "work_experiences": work_experiences
    }


# ─── 7. Backward Compatibility Functions ─────────────────────────────────────

def extract_experience_entries(text: str) -> list[dict]:
    """
    Parses structured experience entries from resume text.
    Provides backward compatibility with legacy dict format while including new structured fields.
    """
    structured = extract_structured_experience(text)
    entries = []
    for exp in structured.get("work_experiences", []):
        dates_display = ""
        if exp.get("start_date") and exp.get("end_date"):
            dates_display = f"{exp['start_date']} - {exp['end_date']}"
        elif exp.get("start_date"):
            dates_display = exp["start_date"]

        entries.append({
            "title": exp.get("job_title", ""),
            "role": exp.get("job_title", ""),
            "job_title": exp.get("job_title", ""),
            "raw_job_title": exp.get("raw_job_title", ""),
            "company": exp.get("company_name", ""),
            "company_name": exp.get("company_name", ""),
            "location": exp.get("location"),
            "employment_type": exp.get("employment_type", "Full-time"),
            "dates": dates_display,
            "start_date": exp.get("start_date"),
            "end_date": exp.get("end_date"),
            "duration_months": exp.get("duration_months", 0),
            "descriptions": exp.get("responsibilities", []),
            "responsibilities": exp.get("responsibilities", []),
        })
    return entries


def extract_experience(text: str) -> str:
    """
    Extracts work experience from resume text with structured parsing.
    Returns pipe-separated entries: "Role at Company (Dates) - Responsibilities: ..."
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

    return " | ".join(formatted_entries[:10]) if formatted_entries else ""


def extract_years_experience(text: str) -> int:
    """
    Calculates total years of experience from structured duration months or explicit mentions.
    """
    if not text:
        return 0

    explicit_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|exp|work|expertise)',
        r'(?:over|more\s+than|at\s+least)\s+(\d+)\s*years?',
        r'(\d+)\+?\s*years?\s+(?:in\s+(?:the\s+)?(?:industry|field|practice|IT|tech|software))',
        r'(\d+)\+?\s*years?\s+(?:as\s+(?:a\s+|an\s+)?)',
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional|related|relevant)\s+(?:experience|work)',
    ]
    for pattern in explicit_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for m in matches:
                try:
                    val = int(m)
                    if 0 < val < 50:
                        return val
                except ValueError:
                    continue

    structured = extract_structured_experience(text)
    total_months = structured.get("total_experience_months", 0)
    if total_months > 0:
        return max(1, round(total_months / 12.0))

    return 0


def extract_job_title(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's primary job title from resume.
    Prefers recent work experience role, falling back to header role tag.
    """
    if not text:
        return ""

    if entries is None:
        entries = extract_experience_entries(text)

    # 1. Most recent work experience role (highest confidence if available)
    if entries:
        for ent in entries:
            t = ent.get("job_title") or ent.get("role") or ent.get("raw_job_title")
            if t:
                norm = _normalize_job_title(t)
                if norm and norm.lower() not in _RESUME_SECTION_HEADERS:
                    return norm

    # 2. Header inspection (e.g. Subtitle under candidate's name)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[1:6]:
        if _is_section_header(line) or line.strip().lower() in _RESUME_SECTION_HEADERS:
            break
        if len(line) > 60:
            continue
        if re.search(r'@|\d{3,}|http', line):
            continue
        # Avoid matching educational degrees or school institutions as a job title
        if re.search(r'\b(?:bachelor|master|doctor|phd|diploma|associate|elementary|high\s+school|university|college|institute|polytechnic|campus)\b', line, re.I):
            continue
        norm = _normalize_job_title(line)
        if norm and len(norm) > 3 and norm.lower() not in _RESUME_SECTION_HEADERS:
            return norm

    return ""


def extract_company(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's most recent company name.
    """
    if entries is None:
        entries = extract_experience_entries(text)

    if entries:
        for e in entries:
            comp = e.get("company_name") or e.get("company", "")
            if comp and len(comp) > 2 and not _is_address_or_location(comp):
                return comp

    # Fallback: scan text / experience blocks for known company names
    blocks = _extract_experience_blocks(text)
    comb = "\n".join(blocks)
    for c in sorted(_PHIL_COMPANY_NAMES, key=len, reverse=True):
        if re.search(rf'\b{re.escape(c)}\b', comb, re.I):
            return c

    # Fallback: scan lines in experience blocks for company legal suffixes
    for block in blocks:
        for line in block.split('\n'):
            line_str = line.strip()
            if len(line_str) > 3 and not _is_address_or_location(line_str) and not _JOB_TITLE_KEYWORDS_RE.search(line_str):
                if _COMPANY_LEGAL_SUFFIXES_RE.search(line_str):
                    c_clean, _ = _split_company_and_location(line_str)
                    if c_clean:
                        return c_clean

    # Fallback: search for 'at <Company>' pattern
    at_m = re.search(r'\b(?:at|@)\s+([A-Za-z0-9\s&.,\'-]+?)(?:\s*\(|\s*[-–—|,]|\s*[\r\n]|$)', comb, re.I)
    if at_m:
        cand = at_m.group(1).strip()
        if len(cand) > 2 and not _is_address_or_location(cand):
            return cand

    # Fallback: scan candidate company lines in experience blocks
    for block in blocks:
        block_lines = [l.strip() for l in block.split('\n') if l.strip()]
        for line_str in block_lines:
            if 2 < len(line_str) < 60:
                if not _is_section_header(line_str) and not line_str.startswith(('•', '-', '*', '▪', '►', '✓')):
                    if not _DATE_RANGE_REGEX.search(line_str) and not _is_address_or_location(line_str):
                        if not _JOB_TITLE_KEYWORDS_RE.search(line_str):
                            c_cand, _ = _split_company_and_location(line_str)
                            if c_cand and len(c_cand) > 2 and not _is_address_or_location(c_cand) and not _JOB_TITLE_KEYWORDS_RE.search(c_cand):
                                return c_cand

    return ""



def extract_relevance(text: str, years: int = 0, job_title: str = "", skills: str = "") -> str:
    """
    Generates a concise relevance statement highlighting candidate qualifications.
    """
    if text:
        if not job_title:
            try:
                job_title = extract_job_title(text)
            except Exception:
                pass
        if not years:
            try:
                y = extract_years_experience(text)
                if y:
                    years = int(y)
            except Exception:
                pass
        if not skills:
            try:
                from .skills_extractor import extract_skills
                skills = extract_skills(text)
            except Exception:
                pass

    parts = []
    if years and years > 0:
        if job_title:
            parts.append(f"{years}+ years of experience as {job_title}")
        else:
            parts.append(f"{years}+ years of professional experience")
    elif job_title:
        parts.append(f"Experienced {job_title}")

    if skills:
        top_skills = [s.strip() for s in skills.split('|') if s.strip()][:3]
        if top_skills:
            parts.append(f"specializing in {', '.join(top_skills)}")

    if parts:
        return " ".join(parts)
    return ""



# ─── 8. Runnable Test Block for Templates 1, 2, and 3 ────────────────────────

if __name__ == "__main__":
    t1 = """WORK EXPERIENCE
Service Crew (Kitchen / Grill)
Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna
June 2023 - December 2023 (End of Contract)
- Assigned in kitchen area as fryman and grill station crew.
- Maintained cleanliness of the station and washed dishes/utensils during closing.

Utility Personnel / Janitor
Robinsons Place Antipolo (via Manpower Agency)
January 2022 - May 2023
- Responsible for floor maintenance, trash collection, and restroom sanitation.
"""

    t2 = """EMPLOYMENT HISTORY
Cashier / Counter Crew | Chowking - SM City Taytay | March 2021 to August 2022
Duties: Handled POS transactions, assisted customers at the front counter, and performed daily cash balancing.
Dishwasher / Kitchen Helper | Gerry's Grill - Robinsons Galleria | Oct 2020 - Feb 2021
Duties: Washed plates, glassware, and kitchen cookware during peak dining hours.
"""

    t3 = """PROFESSIONAL EXPERIENCE
Junior Backend Developer
Accenture Philippines | BGC, Taguig City
August 2025 - Present
- Developed and maintained RESTful APIs using Node.js, NestJS, and PostgreSQL.
- Collaborated with frontend developers and QA engineers in an Agile Scrum environment.

Site Civil Engineer
DMCI Homes - Quezon City Project Site
March 2024 - July 2025
- Supervised daily site construction activities, rebar installation, and concrete pouring.
- Prepared daily accomplishment reports and monitored sub-contractor manpower.

ON-THE-JOB TRAINING (OJT)
Software Developer Intern (OJT)
XYZ Tech Solutions Inc., Makati City
January 2024 - April 2024 (486 Hours)
- Assisted in debugging C# and Java modules and performing manual regression testing.
"""

    print("=== TEMPLATE 1: Service / Blue-Collar Style ===")
    out1 = extract_structured_experience(t1)
    print(json.dumps(out1, indent=2))

    print("\n=== TEMPLATE 2: Inline / Tabular Philippine Style ===")
    out2 = extract_structured_experience(t2)
    print(json.dumps(out2, indent=2))

    print("\n=== TEMPLATE 3: Technical / Engineering / IT Style ===")
    out3 = extract_structured_experience(t3)
    print(json.dumps(out3, indent=2))