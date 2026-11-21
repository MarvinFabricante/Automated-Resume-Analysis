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

try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None

try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz, process as rapidfuzz_process
except ImportError:
    rapidfuzz_fuzz = None
    rapidfuzz_process = None

from app.extractors.content.section_parser import (
    split_into_sections,
    detect_section_label,
    split_dual_column_header,
)


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
        "Quality Control Inspector", "QC Inspector", "Manufacturing Operator",
        "Production Supervisor", "Production Lead", "Packaging Operator",
        "Packer", "Checker", "Sorter", "Picker", "Loader", "Machinist", "CNC Operator"
    ],
    "Tradesman": [
        "Welder", "Mason", "Electrician", "Carpenter", "Plumber",
        "Maintenance Technician", "Aircon Technician", "Auto Mechanic",
        "Automotive Mechanic", "Heavy Equipment Operator", "Painter", "Fabricator",
        "Foreman", "Leadman", "Pipefitter", "Rigger", "Machinist", "Millwright"
    ],

    # ── BPO, Admin & Corporate
    "Customer Service Representative": [
        "Customer Service Representative", "CSR", "Call Center Agent",
        "Customer Care Specialist", "Customer Support Representative",
        "Chat Support Agent", "Email Support Agent", "Inbound Agent",
        "Outbound Agent", "Customer Support Specialist", "Contact Center Agent",
        "Team Leader", "Team Lead", "Operations Supervisor", "Shift Supervisor"
    ],
    "Technical Support Representative": [
        "Technical Support Representative", "TSR", "Technical Support Specialist",
        "Helpdesk Support", "IT Helpdesk Specialist", "Technical Support Agent"
    ],
    "Virtual Assistant": [
        "Virtual Assistant", "VA", "Executive Virtual Assistant", "General VA",
        "Real Estate Virtual Assistant", "E-commerce VA", "Social Media Manager",
        "Content Moderator", "Data Annotator", "Transcriber"
    ],
    "Data Encoder": [
        "Data Encoder", "Data Entry Specialist", "Data Entry Operator", "Encoder",
        "Data Processing Clerk", "Typist"
    ],
    "Admin Staff": [
        "Administrative Aide", "Admin Staff", "Administrative Assistant",
        "Office Clerk", "Office Staff", "Receptionist", "Front Desk Officer",
        "Liaison Officer", "Messenger", "Office Assistant", "Executive Assistant",
        "Office Administrator", "Administrative Officer", "Secretary"
    ],
    "HR Assistant": [
        "HR Assistant", "HR Staff", "HR Officer", "Recruitment Assistant",
        "Talent Acquisition Associate", "HR Specialist", "Human Resources Assistant",
        "HR Generalist", "HR Manager", "Recruiter"
    ],
    "Accounting Clerk": [
        "Accounting Clerk", "Accounting Assistant", "Bookkeeper", "Billing Clerk",
        "Billing Specialist", "Accounting Staff", "Accounts Payable Clerk",
        "Accounts Receivable Clerk", "Payroll Assistant", "Finance Officer",
        "Financial Analyst", "Treasury Assistant"
    ],
    "Sales & Marketing": [
        "Sales Executive", "Account Executive", "Account Manager",
        "Business Development Associate", "Business Development Manager",
        "Marketing Officer", "Marketing Specialist", "Marketing Associate",
        "Digital Marketer", "Copywriter", "Content Writer", "Graphic Designer",
        "Video Editor", "Store Supervisor", "Store Manager", "Branch Manager"
    ],
    "Project & Operations Management": [
        "Project Manager", "Product Manager", "Operations Manager",
        "Plant Manager", "Warehouse Supervisor", "Scrum Master",
        "Operations Lead", "Logistics Coordinator", "Procurement Officer", "Buyer"
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
        "iOS Developer", "Game Developer", "API Developer",
        "Data Analyst", "Data Scientist", "Data Engineer", "UI/UX Designer",
        "UX Designer", "UI Designer", "Solutions Architect"
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
    r'\b(?:Inc\.?|Corp\.?|Corporation|Co\.?|Ltd\.?|LLP|LLC|PLC|GmbH|Holdings|Enterprises|Services|Trading|Foods|Solutions|Technologies|Technology|Group|Agency|Branch|Manpower|Staffing|Industries|Manufacturing|Ceramics|Construction|Engineering|Builders|Realty|Properties|Studio|Studios|Consultancy|Systems|Consulting|Logistics|Ventures|Labs|Media|Networks|Telecom|Phils\.?|Philippines)\b',
    re.IGNORECASE
)

_COMPANY_PLACE_WORDS_RE = re.compile(
    r'\b(?:Hospital|Medical\s+Center|Clinic|Pharmacy|Drugstore|Supermarket|Hypermarket|Mart|Mall|Department\s+Store|Hotel|Resort|Restaurant|Cafe|Bakeshop|Factory|Plant|Mill|Foundry|Workshop|Bank|Barangay|Municipality|City\s+Government|LGU|Department\s+of)\b',
    re.IGNORECASE
)

_JOB_TITLE_KEYWORDS_RE = re.compile(
    r'\b(?:Engineer|Developer|Programmer|Specialist|Manager|Director|Officer|Analyst|Lead|Leader|Leadman|Foreman|Supervisor|'
    r'Technician|Assistant|Associate|Operator|Representative|Consultant|Architect|Designer|Coordinator|'
    r'Administrator|Secretary|Crew|Cashier|Rider|Driver|Clerk|Intern|Trainee|Nurse|Midwife|Caregiver|Therapist|Dentist|'
    r'Teacher|Instructor|Professor|Lecturer|Tutor|Trainer|Accountant|Auditor|Chemist|Pharmacist|Janitor|Cook|Chef|Baker|Butcher|'
    r'Waiter|Waitress|Server|Bartender|Staff|Executive|Practitioner|Worker|Scientist|Researcher|'
    r'Carpenter|Welder|Mason|Electrician|Plumber|Mechanic|Helper|Apprentice|Inspector|Bagger|Promodiser|'
    r'Merchandiser|Warehouseman|Stockman|Guard|Watchman|Barista|Dishwasher|Busboy|Bookkeeper|Encoder|Typist|Receptionist|'
    r'Checker|Packer|Picker|Loader|Sorter|Dispatcher|Assembler|Machinist|Painter|Fabricator|Tailor|'
    r'Writer|Editor|Marketer|Buyer|Purchaser|Broker|Collector|Teller|Moderator|Transcriber|Freelancer|Superintendent|Principal|Head|Chief)\b',
    re.IGNORECASE
)

_RESPONSIBILITY_VERB_START_RE = re.compile(
    r'^(?:[•\-*▪►✓]\s*)?(?:duties|responsibilities|key\s+tasks|tasks|achievements|'
    r'reviewed|developed|built|managed|supervised|performed|assisted|handled|'
    r'conducted|prepared|designed|created|led|worked|maintained|operated|'
    r'implemented|executed|engineered|monitored|verified|discovered|resolved|'
    r'processed|supported|collaborated|ensured|organized|coordinated|trained|'
    r'taught|delivered|administered|analyzed|investigated|troubleshot|inspected|'
    r'installed|configured|repaired|tested|documented|answered|responded|provided|'
    r'achieved|increased|reduced|improved|streamlined|generated|facilitated|assigned|responsible|'
    r'results[\s\-]driven|detail[\s\-]oriented|goal[\s\-]oriented|motivated|dedicated|'
    r'hardworking|dynamic|resourceful|passionate|versatile|seeking|looking\s+for|'
    r'carry\s+out|pioneered|spearheaded|oversee|oversees|leads\s+(?:the|a|an|daily|weekly|team|teams|projects?|operations?)|'
    r'established|initiated|exposed|programmed|awarded|recognized|completed|participated|attended)\b',
    re.IGNORECASE,
)

_PROSE_ROLE_RE = re.compile(
    r'^(?:worked|employed|served|hired|assigned|previously\s+worked)\s+'
    r'(?:as\s+(?:a|an)?\s*)?(?P<title>[A-Za-z0-9/&\-\s]{2,55}?)'
    r'(?:\s+(?:at|with|for|in)\s+(?P<company>[A-Za-z0-9&.,\'\-\s]{2,60}?))?'
    r'(?:\s+(?:from|between|during|since|\())',
    re.IGNORECASE,
)


def _is_likely_responsibility_or_sentence(text: str) -> bool:
    """Detect whether a line is a job duty/responsibility sentence rather than a title or company name."""
    if not text:
        return False
    clean = text.strip()
    if not clean:
        return False
    if clean[0].islower():
        return True
    if _RESPONSIBILITY_VERB_START_RE.match(clean):
        return True
    if re.search(r'\bwith\s+\d+\+?\s*(?:years?|yrs?)\s+of\s+experience\b', clean, re.IGNORECASE):
        return True
    if len(clean) > 70 and not _COMPANY_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if len(clean.split()) > 12 and not _COMPANY_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if clean.endswith('.') and len(clean.split()) >= 6 and not _COMPANY_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if (';' in clean or clean.count(',') >= 3) and not _COMPANY_LEGAL_SUFFIXES_RE.search(clean):
        return True
    return False

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


def _spacy_looks_like_org(text: str) -> bool:
    """Return True if spaCy NER identifies an ORG entity spanning most of text."""
    if not text or len(text.strip()) < 3:
        return False
    nlp, _ = _get_spacy_pipeline()
    if not nlp:
        return False
    try:
        doc = nlp(text.strip()[:100])
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PH_EMPLOYER") and len(ent.text) >= len(text.strip()) * 0.5:
                return True
    except Exception:
        pass
    return False


# ─── 5. Date & Duration Parsing ──────────────────────────────────────────────

_MONTHS_NAMES = (
    r'(?:Jan(?:uary|uray)?|Feb(?:ruary|uary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust|st)?|Sep(?:t(?:ember|mber)?)?|Oct(?:ober|ber)?|Nov(?:ember|emeber)?|Dec(?:ember|emeber)?)'
)
_YEAR_RE = r'(?:19|20)\d{2}'
_SHORT_YEAR_RE = r'(?:[0-3]\d|[5-9]\d)'
_PRESENT_RE = (
    r'(?:Present|Current(?:ly)?|Now|To\s+Date|To-Date|Up\s+to\s+(?:present|date|now)|'
    r'Till?\s+(?:date|present|now)|At\s+present|Ongoing|Today|Onwards|Continuing|'
    r'Active|Still\s+(?:employed|working)|Incumbent)'
)
_ORDINAL_DAY_RE = r'\d{1,2}(?:st|nd|rd|th)?'

_DATE_TOKEN_RE = (
    rf'(?:'
    rf'{_ORDINAL_DAY_RE}\s+{_MONTHS_NAMES}\s*[,.]?\s*{_YEAR_RE}'
    rf'|{_MONTHS_NAMES}(?:\s+{_ORDINAL_DAY_RE})?\s*[,. /]?\s*{_YEAR_RE}'
    rf'|{_YEAR_RE}\s+{_MONTHS_NAMES}'
    rf'|{_MONTHS_NAMES}\s*[\'’]{_SHORT_YEAR_RE}'
    rf'|(?:Q[1-4]|(?:1st|2nd|3rd|4th)\s+Quarter)\s*{_YEAR_RE}'
    rf'|\d{{4}}[-/.](?:0?[1-9]|1[0-2])(?:[-/.]\d{{1,2}})?\b'
    rf'|\b\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}}\b'
    rf'|\b(?:0?[1-9]|1[0-2])[./-]\d{{4}}\b'
    rf'|\b(?:0?[1-9]|1[0-2])[/-]{_SHORT_YEAR_RE}\b'
    rf'|{_YEAR_RE}'
    rf')'
)

_RANGE_CONNECTOR_RE = r'(?:[-–—~→]|->|to|until|up\s+to|thru|through|till?|\'til)'

_DATE_RANGE_REGEX = re.compile(
    rf'(?:'
    rf'(?P<start>{_DATE_TOKEN_RE})\s*{_RANGE_CONNECTOR_RE}\s*(?P<end>{_DATE_TOKEN_RE}|{_PRESENT_RE})'
    rf'|(?P<sm_start>{_MONTHS_NAMES}\.?)\s*(?:[-–—~]|to|until|thru|through)\s*(?P<sm_end>{_MONTHS_NAMES}\s*[,.]?\s*{_YEAR_RE})'
    rf'|(?:Since|From)\s+(?P<open_start>{_MONTHS_NAMES}(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*{_YEAR_RE}|(?:0?[1-9]|1[0-2])[/-]\d{{4}}|{_YEAR_RE})(?!\s*{_RANGE_CONNECTOR_RE})'
    rf'|(?P<trail_start>{_MONTHS_NAMES}(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*{_YEAR_RE}|(?:0?[1-9]|1[0-2])[/-]\d{{4}})\s*[-–—]\s*(?=$|[)\]|,])'
    rf')',
    re.IGNORECASE,
)

_HOURS_REGEX = re.compile(r'\(?(\d+)\s*(?:Hours?|Hrs?)\)?', re.IGNORECASE)

_WORD_NUM_MAP = {
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0,
    "fifteen": 15.0, "sixteen": 16.0, "seventeen": 17.0, "eighteen": 18.0,
    "nineteen": 19.0, "twenty": 20.0, "half": 0.5, "a": 1.0, "an": 1.0,
}

_STANDALONE_DATE_OR_DUR_RE = re.compile(
    rf'^\(?\s*(?:{_MONTHS_NAMES}\s*[,.]?\s*{_YEAR_RE}'
    rf'|(?:19|20)\d{{2}}'
    rf'|\d+(?:\.\d+)?\s*(?:years?|yrs?)(?:\s*(?:and|,)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?'
    rf'|\d+(?:\.\d+)?\s*(?:months?|mos?|weeks?|wks?|hours?|hrs?))\s*\)?$',
    re.IGNORECASE,
)

_INLINE_DURATION_OR_YEAR_RE = re.compile(
    r'(?:\(\s*(?P<paren_dur>(?:\d+(?:\.\d+)?\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|hours?|hrs?)(?:\s*(?:and|,)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?)|(?:19|20)\d{2})\s*\)'
    r'|\|\s*(?P<pipe_dur>\d+(?:\.\d+)?\s*(?:years?|yrs?|months?|mos?|hours?|hrs?)(?:\s*(?:and|,)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?)\s*$)',
    re.IGNORECASE,
)


def _expand_short_year(yy: int) -> int:
    max_2digit = (datetime.now().year + 2) % 100
    return (2000 + yy) if yy <= max(max_2digit, 40) else (1900 + yy)


def _month_name_to_num(month_str: str) -> int:
    m = re.sub(r'[^a-z]', '', month_str.strip().lower())
    mapping = {
        'jan': 1, 'january': 1, 'januray': 1,
        'feb': 2, 'february': 2, 'febuary': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'apirl': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'augst': 8,
        'sep': 9, 'sept': 9, 'september': 9, 'septmber': 9,
        'oct': 10, 'october': 10, 'octber': 10,
        'nov': 11, 'november': 11, 'novemeber': 11,
        'dec': 12, 'december': 12, 'decemeber': 12,
    }
    if m in mapping:
        return mapping[m]
    if rapidfuzz_process is not None and len(m) >= 3:
        best = rapidfuzz_process.extractOne(m, list(mapping.keys()), scorer=rapidfuzz_fuzz.ratio, score_cutoff=80)
        if best:
            return mapping[best[0]]
    return 1


def _parse_duration_text(text: str) -> int:
    """Parse explicit duration expressions like '2 yrs 6 mos', '1.5 years', '486 hours', or 'two years' into months."""
    if not text:
        return 0
    clean = text.strip()

    # 1. Combined years + months: "2 years 6 months", "1 yr, 3 mos"
    ym_match = re.search(
        r'\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*(?:and|,)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?)\b',
        clean,
        re.IGNORECASE,
    )
    if ym_match:
        yrs = float(ym_match.group(1))
        mos = float(ym_match.group(2))
        if 0 <= yrs < 50 and 0 <= mos < 60:
            return max(1, round(yrs * 12.0 + mos))

    # 2. Numeric years
    yr_match = re.search(r'\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b', clean, re.IGNORECASE)
    if yr_match:
        yrs = float(yr_match.group(1))
        if 0 < yrs < 50:
            return max(1, round(yrs * 12.0))

    # 3. Numeric months
    mo_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:months?|mos?)\b', clean, re.IGNORECASE)
    if mo_match:
        mos = float(mo_match.group(1))
        if 0 < mos < 600:
            return max(1, round(mos))

    # 4. Weeks
    wk_match = re.search(r'\b(\d+)\s*(?:weeks?|wks?)\b', clean, re.IGNORECASE)
    if wk_match:
        wks = int(wk_match.group(1))
        if 0 < wks < 500:
            return max(1, round(wks / 4.33))

    # 5. Hours (OJT standard ~160 hrs/month)
    hrs_match = _HOURS_REGEX.search(clean)
    if hrs_match:
        hrs = int(hrs_match.group(1))
        if hrs > 0:
            return max(1, round(hrs / 160.0))

    # 6. Word-number durations ("two years", "two and a half years", "six months")
    word_pat = '|'.join(sorted(_WORD_NUM_MAP.keys(), key=len, reverse=True))
    w_half = re.search(rf'\b({word_pat})\s+and\s+a\s+half\s*(?:years?|yrs?)\b', clean, re.IGNORECASE)
    if w_half:
        val = _WORD_NUM_MAP.get(w_half.group(1).lower(), 0.0) + 0.5
        if val > 0:
            return max(1, round(val * 12.0))
    w_yr = re.search(rf'\b({word_pat})\s*(?:years?|yrs?)\b', clean, re.IGNORECASE)
    if w_yr:
        val = _WORD_NUM_MAP.get(w_yr.group(1).lower(), 0.0)
        if val > 0:
            return max(1, round(val * 12.0))
    w_mo = re.search(rf'\b({word_pat})\s*(?:months?|mos?)\b', clean, re.IGNORECASE)
    if w_mo:
        val = _WORD_NUM_MAP.get(w_mo.group(1).lower(), 0.0)
        if val > 0:
            return max(1, round(val))

    return 0


def _parse_single_date(d_str: str, is_end: bool = False, prefer_day_first: bool = False) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Parse string like 'June 2023', '15 June 2020', '06/2023', 'Jan \'20', 'Q2 2023', '2023' into ('2023-06', year, month)."""
    if not d_str:
        return None, None, None
    d_clean = d_str.strip()
    if re.match(rf'^{_PRESENT_RE}$', d_clean, re.IGNORECASE):
        now = datetime.now()
        return "Present", now.year, now.month

    # Quarter: Q1-Q4 YYYY or 1st-4th Quarter YYYY
    q_match = re.search(r'(?:Q([1-4])|([1-4])(?:st|nd|rd|th)\s+Quarter)\s*(' + _YEAR_RE + r')', d_clean, re.IGNORECASE)
    if q_match:
        q = int(q_match.group(1) or q_match.group(2))
        yr = int(q_match.group(3))
        m_num = (q * 3) if is_end else ((q - 1) * 3 + 1)
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "DD Month[,] YYYY"
    dmy_word = re.search(rf'\b{_ORDINAL_DAY_RE}\s+({_MONTHS_NAMES})\s*[,.]?\s*({_YEAR_RE})\b', d_clean, re.IGNORECASE)
    if dmy_word:
        m_num = _month_name_to_num(dmy_word.group(1))
        yr = int(dmy_word.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "Month [DD,] YYYY"
    m_match = re.search(rf'({_MONTHS_NAMES})(?:\s+{_ORDINAL_DAY_RE})?\s*[,. /]?\s*({_YEAR_RE})', d_clean, re.IGNORECASE)
    if m_match:
        m_num = _month_name_to_num(m_match.group(1))
        yr = int(m_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "YYYY Month"
    ym_word = re.search(rf'\b({_YEAR_RE})\s+({_MONTHS_NAMES})\b', d_clean, re.IGNORECASE)
    if ym_word:
        yr = int(ym_word.group(1))
        m_num = _month_name_to_num(ym_word.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "Month 'YY"
    m_short_y = re.search(rf'({_MONTHS_NAMES})\s*[\'’]({_SHORT_YEAR_RE})\b', d_clean, re.IGNORECASE)
    if m_short_y:
        m_num = _month_name_to_num(m_short_y.group(1))
        yr = _expand_short_year(int(m_short_y.group(2)))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # ISO YYYY-MM(-DD) or YYYY/MM(/DD) or YYYY.MM(.DD)
    iso_match = re.search(r'\b(\d{4})[-/.](0?[1-9]|1[0-2])(?:[-/.]\d{1,2})?\b', d_clean)
    if iso_match:
        yr = int(iso_match.group(1))
        m_num = max(1, min(12, int(iso_match.group(2))))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # MM/DD/YYYY or DD/MM/YYYY (slash, hyphen, or dot)
    mdy_match = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', d_clean)
    if mdy_match:
        p1, p2, yr = int(mdy_match.group(1)), int(mdy_match.group(2)), int(mdy_match.group(3))
        if p1 > 12 and 1 <= p2 <= 12:
            m_num = p2
        elif prefer_day_first and 1 <= p2 <= 12:
            m_num = p2
        elif 1 <= p1 <= 12:
            m_num = p1
        else:
            m_num = max(1, min(12, p2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # MM/YYYY, MM-YYYY, MM.YYYY
    slash_match = re.search(r'\b(0?[1-9]|1[0-2])[./-](\d{4})\b', d_clean)
    if slash_match:
        m_num = max(1, min(12, int(slash_match.group(1))))
        yr = int(slash_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # MM/YY or MM-YY
    short_slash = re.search(rf'\b(0?[1-9]|1[0-2])[/-]({_SHORT_YEAR_RE})\b', d_clean)
    if short_slash:
        m_num = int(short_slash.group(1))
        yr = _expand_short_year(int(short_slash.group(2)))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # YYYY
    y_match = re.search(rf'\b({_YEAR_RE})\b', d_clean)
    if y_match:
        yr = int(y_match.group(1))
        return f"{yr:04d}-01", yr, 1

    # Fallback to python-dateutil (only when a 4-digit year is present)
    if dateutil_parser is not None and re.search(_YEAR_RE, d_clean):
        try:
            parsed = dateutil_parser.parse(d_clean, fuzzy=True)
            if parsed and 1950 <= parsed.year <= datetime.now().year + 2:
                return f"{parsed.year:04d}-{parsed.month:02d}", parsed.year, parsed.month
        except Exception:
            pass

    # Fallback to dateparser (strictly requiring year part, English)
    if dateparser is not None and re.search(_YEAR_RE, d_clean):
        try:
            parsed = dateparser.parse(d_clean, languages=['en'], settings={'REQUIRE_PARTS': ['year']})
            if parsed and 1950 <= parsed.year <= datetime.now().year + 2:
                return f"{parsed.year:04d}-{parsed.month:02d}", parsed.year, parsed.month
        except Exception:
            pass

    return None, None, None


def _parse_date_and_duration(text: str) -> Tuple[Optional[str], Optional[str], int, str]:
    """
    Extracts start_date (YYYY-MM), end_date (YYYY-MM | Present), duration_months, and extra status string.
    """
    match = _DATE_RANGE_REGEX.search(text or "")
    if not match:
        clean_t = (text or "").strip()
        dur_only = _parse_duration_text(clean_t)
        if dur_only > 0 and (_STANDALONE_DATE_OR_DUR_RE.match(clean_t) or _INLINE_DURATION_OR_YEAR_RE.search(clean_t)):
            return None, None, dur_only, clean_t
        if _STANDALONE_DATE_OR_DUR_RE.match(clean_t):
            iso, _, _ = _parse_single_date(clean_t)
            if iso:
                return iso, iso, 0, ""
        return None, None, 0, ""

    gd = match.groupdict()
    if gd.get("open_start") or gd.get("trail_start"):
        raw_start = (gd.get("open_start") or gd.get("trail_start") or "").strip()
        raw_end = "Present"
    elif gd.get("sm_start") and gd.get("sm_end"):
        raw_start = gd["sm_start"].strip()
        raw_end = gd["sm_end"].strip()
    else:
        raw_start = (gd.get("start") or "").strip()
        raw_end = (gd.get("end") or "").strip()

    # Detect unambiguous DD/MM/YYYY in either endpoint so the partner endpoint parses consistently
    prefer_day_first = False
    for ep in (raw_start, raw_end):
        dmy_check = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', ep)
        if dmy_check and int(dmy_check.group(1)) > 12 and 1 <= int(dmy_check.group(2)) <= 12:
            prefer_day_first = True
            break

    end_iso, e_yr, e_mo = _parse_single_date(raw_end, is_end=True, prefer_day_first=prefer_day_first)
    if gd.get("sm_start") and e_yr:
        start_iso, s_yr, s_mo = _parse_single_date(f"{raw_start} {e_yr}", is_end=False, prefer_day_first=prefer_day_first)
    else:
        start_iso, s_yr, s_mo = _parse_single_date(raw_start, is_end=False, prefer_day_first=prefer_day_first)

    # If raw_end is strictly a 4-digit year, default to December of that year
    if e_yr and re.fullmatch(r'\d{4}', raw_end.strip()):
        e_mo = 12
        end_iso = f"{e_yr:04d}-12"

    # Guard against reversed dates (e.g. typo)
    if s_yr and e_yr and end_iso != "Present" and (e_yr, e_mo or 1) < (s_yr, s_mo or 1):
        s_yr, e_yr = e_yr, s_yr
        s_mo, e_mo = e_mo, s_mo
        start_iso, end_iso = end_iso, start_iso

    duration = 0
    now = datetime.now()
    if s_yr and s_mo:
        if end_iso == "Present" or not e_yr:
            target_yr, target_mo = now.year, now.month
            if s_yr <= target_yr + 1:
                duration = max(1, (target_yr - s_yr) * 12 + (target_mo - s_mo) + 1)
        elif e_yr and e_mo:
            duration = max(1, (e_yr - s_yr) * 12 + (e_mo - s_mo) + 1)

    # Check if hours mentioned (e.g. 486 Hours) when calendar duration is zero
    hrs_match = _HOURS_REGEX.search(text)
    if hrs_match and duration == 0:
        hrs = int(hrs_match.group(1))
        duration = max(1, round(hrs / 160.0))

    # Extra text (status info outside date range)
    extra_text = text[:match.start()] + " " + text[match.end():]
    extra_text = re.sub(r'[\s\-–—()|]+', ' ', extra_text).strip()

    # Honor explicit year/month duration annotations on year-only ranges like "2020 - 2024 (4 years)"
    if re.fullmatch(r'\d{4}', raw_start.strip()) and re.fullmatch(r'\d{4}', raw_end.strip()) and extra_text:
        explicit_dur = _parse_duration_text(extra_text)
        if 0 < explicit_dur < 600:
            duration = explicit_dur

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
    clean = re.sub(r'^(?:\(?\d{1,2}\)?[\.\)]\s+|[•\-\*▪►✓\s:]+)|[•\-\*▪►✓\s:]+$', '', clean).strip()

    if clean.lower() in _RESUME_SECTION_HEADERS or any(clean.lower().startswith(h) for h in _RESUME_SECTION_HEADERS):
        return ""

    if _is_address_or_location(clean) or _is_likely_responsibility_or_sentence(clean):
        return ""

    if len(clean) > 85 or len(clean.split()) > 11:
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

    # If already a concise role title (<= 6 words with a recognized job keyword), preserve full title
    if len(clean.split()) <= 6 and _JOB_TITLE_KEYWORDS_RE.search(clean):
        return clean

    # Check spaCy POS / entity fallback for longer or out-of-vocabulary strings
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

    # Case 0: Trailing parenthetical location e.g. 'Rizal Packaging & Industrial Solutions Inc. (Taytay, Rizal)'
    paren_loc_m = re.search(r'^(.+?)\s*\(([^()]+)\)\s*$', clean)
    if paren_loc_m:
        base_comp = paren_loc_m.group(1).strip(' ,-–—|')
        inside_paren = paren_loc_m.group(2).strip()
        if any(loc in inside_paren.lower() for loc in _PHIL_LOCATIONS_SET) or _is_address_or_location(inside_paren):
            return base_comp, inside_paren

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

    # Case 3: Comma separator outside parentheses 'XYZ Tech Solutions Inc., Makati City'
    comma_parts = re.split(r',(?![^()]*\))', clean, maxsplit=1)
    if len(comma_parts) == 2:
        first = comma_parts[0].strip()
        rest = comma_parts[1].strip()
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


def _has_company_signals(text: str) -> bool:
    if not text:
        return False
    if _COMPANY_LEGAL_SUFFIXES_RE.search(text) or _COMPANY_PLACE_WORDS_RE.search(text):
        return True
    if any(c.lower() in text.lower() for c in _PHIL_COMPANY_NAMES):
        return True
    return False


def _has_job_signals(text: str) -> bool:
    if not text:
        return False
    if _JOB_TITLE_KEYWORDS_RE.search(text):
        return True
    if _KEYWORD_PROCESSOR and _KEYWORD_PROCESSOR.extract_keywords(text):
        return True
    return any(t.lower() in text.lower() for vars_list in _PHILIPPINE_JOB_TAXONOMY.values() for t in vars_list)


def _extract_title_company_location(title_cand: str, comp_cand: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Decouples raw title, company, and location strings even when written on the same line,
    swapped, or combined (e.g. 'Food Panda Delivery Rider', 'Delivery Rider at Food Panda').
    Returns (job_title, company_name, location).
    """
    title_cand = title_cand.strip() if title_cand else ""
    comp_cand = comp_cand.strip() if comp_cand else ""

    if _is_likely_responsibility_or_sentence(title_cand):
        return "", "", None

    if comp_cand and (_is_likely_responsibility_or_sentence(comp_cand) or _DATE_RANGE_REGEX.search(comp_cand)):
        comp_cand = ""

    # Check if comp_cand is actually an address or country/location
    loc_override = None
    if comp_cand and (_is_address_or_location(comp_cand) or comp_cand.lower() in ("philippines", "metro manila", "ncr", "remote")):
        loc_override = comp_cand
        comp_cand = ""

    # If title_cand itself contains ' at ' or ' @ ', split inline company first so it never duplicates
    inline_at_match = re.search(r'\s+(?:at|@)\s+', title_cand, re.IGNORECASE)
    if inline_at_match:
        t_part = title_cand[:inline_at_match.start()].strip()
        c_part = title_cand[inline_at_match.end():].strip()
        if not comp_cand:
            comp_cand = c_part
        title_cand = t_part

    # Check if lines were swapped: title_cand is company and comp_cand is job title
    if comp_cand:
        title_has_comp_signals = _has_company_signals(title_cand)
        comp_has_comp_signals = _has_company_signals(comp_cand)

        title_has_job_signals = _has_job_signals(title_cand)
        comp_has_job_signals = _has_job_signals(comp_cand)

        should_swap = False
        if title_has_comp_signals and comp_has_job_signals and not comp_has_comp_signals:
            should_swap = True
        elif not title_has_job_signals and comp_has_job_signals and not comp_has_comp_signals:
            should_swap = True
        elif not title_has_job_signals and not comp_has_job_signals and _spacy_looks_like_org(title_cand) and not _spacy_looks_like_org(comp_cand):
            should_swap = True

        if should_swap:
            title_cand, comp_cand = comp_cand, title_cand

    if comp_cand:
        company, location = _split_company_and_location(comp_cand)
        if _is_likely_responsibility_or_sentence(company) or _DATE_RANGE_REGEX.search(company):
            company = ""
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
        p1_comp = _has_company_signals(p1) or _spacy_looks_like_org(p1)
        p2_comp = _has_company_signals(p2) or _spacy_looks_like_org(p2)
        p1_job = _has_job_signals(p1)
        p2_job = _has_job_signals(p2)
        if (p1_comp and not p2_comp) or (p2_job and not p1_job and not p2_comp):
            comp, loc = _split_company_and_location(p1)
            return _normalize_job_title(p2), comp, loc or loc_override
        else:
            comp, loc = _split_company_and_location(p2)
            return _normalize_job_title(p1), comp, loc or loc_override

    # 2b. Check comma-separated 'Job Title, Company Name[, Location]' on a single line
    if ',' in title_cand:
        comma_segs = [s.strip() for s in re.split(r',(?![^()]*\))', title_cand) if s.strip()]
        if len(comma_segs) >= 2:
            seg0, seg1 = comma_segs[0], comma_segs[1]
            seg0_job = _has_job_signals(seg0)
            seg1_comp = _has_company_signals(seg1) or _spacy_looks_like_org(seg1)
            seg0_comp = _has_company_signals(seg0) or _spacy_looks_like_org(seg0)
            seg1_job = _has_job_signals(seg1)
            if seg0_job and (seg1_comp or (not seg1_job and not _is_address_or_location(seg1)) or (len(comma_segs) >= 3 and _is_address_or_location(comma_segs[-1]))):
                c_part = ", ".join(comma_segs[1:])
                comp, loc = _split_company_and_location(c_part)
                return _normalize_job_title(seg0), comp, loc or loc_override
            elif (seg0_comp or not seg0_job) and seg1_job:
                loc_tail = ", ".join(comma_segs[2:]) if len(comma_segs) >= 3 else None
                comp, loc = _split_company_and_location(seg0)
                return _normalize_job_title(seg1), comp, loc or loc_tail or loc_override

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
    # Do NOT split compound role titles separated by '/' (e.g. 'Apprentice Carpenter / Woodworking Assistant')
    if '/' not in title_cand:
        all_taxonomy_titles = []
        for vars_list in _PHILIPPINE_JOB_TAXONOMY.values():
            all_taxonomy_titles.extend(vars_list)
        for tax_title in sorted(all_taxonomy_titles, key=len, reverse=True):
            tax_low = tax_title.lower()
            t_low = title_cand.lower()
            if t_low.endswith(tax_low) and len(title_cand) > len(tax_title):
                boundary_char = title_cand[-len(tax_title)-1:-len(tax_title)]
                if boundary_char in " \t-–—|,":
                    prefix = title_cand[:-len(tax_title)].strip(" \t-–—|,")
                    _ROLE_MODIFIERS = {
                        "junior", "senior", "lead", "chief", "head", "assistant", "associate",
                        "apprentice", "trainee", "general", "executive", "site", "field",
                        "project", "staff", "plant", "counter", "kitchen", "dining", "retail",
                        "branch", "warehouse", "operations", "production", "maintenance",
                        "marketing", "sales", "regional", "national", "corporate", "technical",
                        "clinical", "medical", "ward", "icu", "audit", "tax", "billing",
                        "payroll", "recruitment", "inbound", "outbound", "chat", "email",
                        "desk", "front", "back", "full", "part", "remote", "outsourced",
                        "contract", "seasonal", "reliever", "acting", "deputy", "vice",
                        "it", "hr", "qa", "qc", "cloud", "software", "data", "network",
                        "database", "systems", "security", "quality",
                    }
                    if (
                        len(prefix) >= 3
                        and not _is_address_or_location(prefix)
                        and not _JOB_TITLE_KEYWORDS_RE.search(prefix)
                        and prefix.lower() not in _ROLE_MODIFIERS
                        and (
                            len(prefix.split()) >= 2
                            or _has_company_signals(prefix)
                            or _spacy_looks_like_org(prefix)
                            or any(c.lower() == prefix.lower() for c in _PHIL_COMPANY_NAMES)
                        )
                    ):
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
    return (
        clean in headers
        or any(clean.startswith(h + ":") for h in headers)
        or detect_section_label(line) is not None
        or split_dual_column_header(line) is not None
    )


def _extract_experience_blocks(text: str) -> List[str]:
    """
    Extracts all sections corresponding to Work Experience and OJT/Internship.
    """
    exp_headers = [
        "EXPERIENCE", "EXPERIENCES", "WORK EXPERIENCE", "WORK EXPERIENCES",
        "WORKING EXPERIENCE", "EMPLOYMENT HISTORY", "EMPLOYMENT",
        "PROFESSIONAL EXPERIENCE", "PROFESSIONAL EXPERIENCES",
        "RELEVANT EXPERIENCE", "WORK HISTORY", "CAREER HISTORY", "JOB EXPERIENCE",
        "CAREER SUMMARY", "CAREER EXPERIENCE", "CAREER OVERVIEW", "CAREER TRACK",
        "PROFESSIONAL CAREER", "CAREER TIMELINE", "EMPLOYMENT TIMELINE",
        "POSITIONS HELD", "WORK RECORD", "INDUSTRY EXPERIENCE",
        "PROFESSIONAL HISTORY", "WORK AND EXPERIENCE",
        "RELEVANT WORK EXPERIENCE", "RELEVANT WORK HISTORY", "PROFESSIONAL WORK EXPERIENCE",
        "EMPLOYMENT RECORD", "EMPLOYMENT DETAILS", "EMPLOYMENT SUMMARY", "WORK SUMMARY",
        "WORK BACKGROUND", "OCCUPATIONAL HISTORY", "EMPLOYMENT BACKGROUND", "CAREER BACKGROUND",
        "RELEVANT EMPLOYMENT", "JOB HISTORY", "JOBS HELD", "PREVIOUS EMPLOYMENT",
        "PAST EXPERIENCE", "CURRENT & PREVIOUS EMPLOYMENT", "WORK ENGAGEMENTS",
        "OTHER EXPERIENCE", "ADDITIONAL EXPERIENCE", "RELATED EXPERIENCE", "PRIOR EXPERIENCE",
        "VOLUNTEER EXPERIENCE", "PRACTICAL EXPERIENCE", "INDUSTRIAL EXPERIENCE",
        "FIELD EXPERIENCE", "CLINICAL EXPERIENCE", "TEACHING EXPERIENCE",
        "CORPORATE EXPERIENCE", "MILITARY EXPERIENCE", "FREELANCE EXPERIENCE",
        "CONSULTING EXPERIENCE", "LEADERSHIP & WORK EXPERIENCE",
        "ON-THE-JOB TRAINING (OJT)", "ON-THE-JOB TRAINING",
        "ON THE JOB TRAINING", "OJT", "OJT EXPERIENCE", "INTERNSHIP", "INTERNSHIPS",
        "INTERNSHIP EXPERIENCE", "PRACTICUM", "ON-THE-JOB TRAINING EXPERIENCE",
        "ON-THE-JOB TRAINING / INTERNSHIP", "ON-THE-JOB TRAINING (OJT) / INTERNSHIP / PRACTICUM",
        "PRACTICUM / INTERNSHIP", "INTERNSHIP / PRACTICUM", "APPRENTICESHIP",
        "WORK & INTERNSHIP EXPERIENCE", "WORK AND INTERNSHIP EXPERIENCE",
        "EXPERIENCE & INTERNSHIP", "WORK / OJT EXPERIENCE",
    ]
    stop_headers = [
        "EDUCATION", "SKILLS", "CERTIFICATIONS", "PROJECTS", "QUALIFICATIONS",
        "ACHIEVEMENTS", "AFFILIATIONS", "REFERENCES", "CHARACTER REFERENCES",
        "INTERESTS", "AWARDS", "PUBLICATIONS", "HOBBIES", "VOLUNTEER",
        "PERSONAL", "PERSONAL DATA", "BIODATA", "TRAINING", "SEMINARS",
        "SEMINARS/TRAININGS", "TECHNICAL SKILLS", "LANGUAGES"
    ]
    major_stop_labels = {"EDUCATION", "SKILLS", "CERTIFICATIONS", "REFERENCES", "PERSONAL", "LANGUAGES", "INTERESTS", "AFFILIATIONS", "PUBLICATIONS"}

    lines = text.split('\n')
    extracted_blocks = []
    current_block = []
    in_exp = False
    dual_exp_col: Optional[int] = None

    for idx, line in enumerate(lines):
        cleaned = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', line.strip()).upper()
        cleaned_no_num = re.sub(r'^(?:\(?(?:\d{1,2}|[IVXLC]{1,4})\)?[\.\)\-:]\s+)', '', cleaned).strip()
        sec_label = detect_section_label(line)
        dual = None if sec_label else split_dual_column_header(line)

        if dual:
            if in_exp and current_block:
                extracted_blocks.append('\n'.join(current_block))
                current_block = []
            if "EXPERIENCE" in dual:
                in_exp = True
                dual_exp_col = (0 if dual[0] == "EXPERIENCE" else 1) if '|' in line else None
            else:
                in_exp = False
                dual_exp_col = None
            continue

        is_exp_hdr = (
            any(cleaned == h or cleaned.startswith(h + ":") or cleaned_no_num == h or cleaned_no_num.startswith(h + ":") for h in exp_headers)
            or sec_label == "EXPERIENCE"
        )
        if is_exp_hdr:
            if current_block:
                extracted_blocks.append('\n'.join(current_block))
                current_block = []
            in_exp = True
            dual_exp_col = None
            if not any(cleaned == h or cleaned.startswith(h + ":") or cleaned_no_num == h or cleaned_no_num.startswith(h + ":") for h in exp_headers):
                for delim in (':', '|'):
                    d_idx = line.find(delim)
                    if d_idx > 0:
                        inline_exp = line[d_idx + 1:].strip()
                        if inline_exp:
                            current_block.append(inline_exp)
                        break
            continue
        elif (
            not line.lstrip().startswith(('•', '-', '*', '▪', '►', '✓'))
            and (
                any(cleaned == h or cleaned.startswith(h + ":") for h in stop_headers)
                or (sec_label is not None and sec_label != "EXPERIENCE")
            )
            and not (
                ':' in line
                and _is_likely_responsibility_or_sentence(line.split(':', 1)[1].strip())
            )
        ):
            # Guard against sub-labels ("Projects:", "Achievements:", "Training:") inside an experience block
            # when another dated experience entry still follows before the next major section.
            if in_exp and (':' in line or not current_block) and (sec_label not in major_stop_labels):
                has_more_exp = False
                for fwd_l in lines[idx + 1:idx + 25]:
                    fwd_lbl = detect_section_label(fwd_l)
                    if fwd_lbl in major_stop_labels:
                        break
                    if _DATE_RANGE_REGEX.search(fwd_l):
                        has_more_exp = True
                        break
                if has_more_exp:
                    continue

            if in_exp and current_block:
                extracted_blocks.append('\n'.join(current_block))
                current_block = []
            in_exp = False
            dual_exp_col = None
            continue

        if in_exp:
            if dual_exp_col is not None and '|' in line and '@' not in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 2:
                    if parts[dual_exp_col]:
                        current_block.append(parts[dual_exp_col])
                    continue
            current_block.append(line)

    if current_block:
        extracted_blocks.append('\n'.join(current_block))

    if extracted_blocks:
        return extracted_blocks

    # If other section headers (like EDUCATION, SKILLS, etc.) exist in the document,
    # but NO experience header was found, then there is NO work experience section!
    def _is_other_exp_stop(l: str) -> bool:
        c = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', l.strip()).upper()
        if any(c == sh or c.startswith(sh + ":") for sh in stop_headers):
            return True
        lbl = detect_section_label(l)
        if lbl not in (None, "EXPERIENCE"):
            return True
        d = None if lbl else split_dual_column_header(l)
        return d is not None and "EXPERIENCE" not in d

    if any(_is_other_exp_stop(l) for l in lines):
        return []

    return [text]


# ─── 6. Primary Structured Extractor ─────────────────────────────────────────

_BULLET_PREFIXES = ('•', '-', '*', '▪', '►', '✓')


def _is_academic_degree_title(raw_title: str, company_or_loc: str = "") -> bool:
    """Return True only when a title is an academic degree/schooling entry rather than a job title."""
    if not raw_title:
        return False
    if re.search(
        r'\b(?:bachelor(?:\'?s)?|master(?:\'?s)?\s+(?:of|in|degree)|doctor(?:ate)?\s+(?:of|in)|'
        r'ph\.?d|associate(?:\'?s)?\s+(?:degree|of|in)|diploma\s+(?:in|of)|'
        r'elementary|high\s+school|senior\s+high|junior\s+high)\b',
        raw_title,
        re.I,
    ):
        return True
    if re.search(r'\b(?:university|college|polytechnic|academy|school)\b', company_or_loc or "", re.I) and re.search(
        r'\b(?:bachelor|master|degree|course|bs|ba|ab|bba|bsba|bscpe|bsit|bscs)\b',
        raw_title,
        re.I,
    ):
        return True
    return False


def _is_upcoming_role_header(lines: List[str], curr_idx: int) -> bool:
    """Return True when lines[curr_idx] starts a subsequent multi-line role header."""
    curr_l = lines[curr_idx]
    stripped = curr_l.lstrip('•-*▪►✓ ').strip()
    if not stripped:
        return False
    if curr_l.startswith(_BULLET_PREFIXES):
        # Only treat a bulleted line as a new role header if it looks like a concise title/company and precedes a date
        if len(stripped) > 65 or _is_likely_responsibility_or_sentence(stripped):
            return False
        if not (_has_job_signals(stripped) or _has_company_signals(stripped)):
            return False
    elif _is_likely_responsibility_or_sentence(curr_l):
        return False
    for fwd in range(1, 5):
        if curr_idx + fwd >= len(lines):
            break
        fwd_l = lines[curr_idx + fwd]
        if _is_section_header(fwd_l):
            break
        if fwd_l.startswith(_BULLET_PREFIXES):
            fwd_clean = fwd_l.lstrip('•-*▪►✓ ').strip()
            if _is_likely_responsibility_or_sentence(fwd_clean) or len(fwd_clean) > 65:
                break
        if _DATE_RANGE_REGEX.search(fwd_l) or _STANDALONE_DATE_OR_DUR_RE.match(fwd_l.strip()) or _INLINE_DURATION_OR_YEAR_RE.search(fwd_l):
            return True
    return False


def _collect_responsibilities(lines: List[str], start_idx: int) -> Tuple[List[str], int]:
    """Collect job duty/responsibility lines starting at start_idx until next role or section."""
    responsibilities: List[str] = []
    curr_idx = start_idx
    while curr_idx < len(lines):
        next_l = lines[curr_idx]
        if (
            _DATE_RANGE_REGEX.search(next_l)
            or _STANDALONE_DATE_OR_DUR_RE.match(next_l.strip())
            or _INLINE_DURATION_OR_YEAR_RE.search(next_l)
            or _is_section_header(next_l)
        ):
            break
        if _is_upcoming_role_header(lines, curr_idx):
            break

        d_match = re.match(r'^(?:Duties|Responsibilities|Key\s+Tasks)\s*[:.\-]\s*(.+)', next_l, re.IGNORECASE)
        if d_match:
            responsibilities.append(d_match.group(1).strip())
            curr_idx += 1
            continue
        elif next_l.startswith(_BULLET_PREFIXES):
            duty_text = next_l.lstrip('•-*▪►✓ ').strip()
            if duty_text:
                responsibilities.append(duty_text)
            curr_idx += 1
            continue
        elif not any(comp.lower() in next_l.lower() for comp in _PHIL_COMPANY_NAMES):
            if len(next_l) > 15 and not _is_address_or_location(next_l):
                responsibilities.append(next_l)
                curr_idx += 1
                continue
        break
    return responsibilities, curr_idx


def _ym_to_index(ym_str: Optional[str]) -> Optional[int]:
    """Convert 'YYYY-MM' or 'Present' into a monotonic month index (year*12 + month - 1)."""
    if not ym_str:
        return None
    if ym_str == "Present":
        now = datetime.now()
        return now.year * 12 + (now.month - 1)
    m = re.fullmatch(r'(\d{4})-(\d{2})', ym_str.strip())
    if not m:
        return None
    return int(m.group(1)) * 12 + (int(m.group(2)) - 1)


def _compute_merged_experience_months(work_experiences: List[Dict[str, Any]]) -> int:
    """
    Compute total experience in months by merging overlapping calendar intervals
    for dated roles (avoiding double-counting concurrent jobs) and adding undated durations.
    Preserves exact explicit durations when an entry is non-overlapping (e.g. '2020 - 2024 (4 years)' = 48 mos).
    """
    dated_intervals: List[Tuple[int, int, int]] = []
    undated_months = 0

    for exp in work_experiences:
        dur = int(exp.get("duration_months") or 0)
        s_idx = _ym_to_index(exp.get("start_date"))
        e_idx = _ym_to_index(exp.get("end_date"))
        if s_idx is not None and e_idx is not None and e_idx >= s_idx:
            raw_span = e_idx - s_idx + 1
            eff_end = (s_idx + dur - 1) if (0 < dur < raw_span) else e_idx
            dated_intervals.append((s_idx, eff_end, dur))
        elif dur > 0:
            undated_months += dur

    if not dated_intervals:
        return undated_months

    dated_intervals.sort(key=lambda x: (x[0], x[1]))
    merged: List[List[int]] = []
    for s_idx, e_idx, _ in dated_intervals:
        if not merged or s_idx > merged[-1][1]:
            merged.append([s_idx, e_idx])
        else:
            merged[-1][1] = max(merged[-1][1], e_idx)

    dated_total = sum(e - s + 1 for s, e in merged)
    return dated_total + undated_months


def _is_parent_company_header(lines: List[str], idx: int) -> Optional[Tuple[str, Optional[str], int]]:
    """
    Detect LinkedIn/grouped parent company headers that precede multiple sub-roles:
      - 'Accenture Philippines\\n4 yrs 2 mos\\nSenior Developer\\nJan 2022 - Present'
      - 'Accenture Philippines (2020 - 2024)\\nSenior Developer (2022 - 2024)'
    Returns (company_name, location, lines_to_skip) or None.
    """
    line = lines[idx]
    if line.startswith(_BULLET_PREFIXES) or _is_likely_responsibility_or_sentence(line):
        return None

    # Pattern 1: Company line followed by standalone duration line ('3 yrs 5 mos'), then sub-role with date
    if idx + 2 < len(lines):
        next_l = lines[idx + 1].strip()
        if (
            _STANDALONE_DATE_OR_DUR_RE.match(next_l)
            and not _DATE_RANGE_REGEX.search(next_l)
            and _parse_duration_text(next_l) > 0
            and not _has_job_signals(line)
            and (_has_company_signals(line) or _spacy_looks_like_org(line))
        ):
            for fwd in range(idx + 2, min(idx + 5, len(lines))):
                if _DATE_RANGE_REGEX.search(lines[fwd]):
                    comp, loc = _split_company_and_location(line)
                    if comp:
                        return comp, loc, 2

    # Pattern 2: 'Company (2020 - 2024)' followed immediately by sub-role(s) with dates
    dm = _DATE_RANGE_REGEX.search(line)
    if dm and idx + 1 < len(lines):
        before = re.sub(r'[\s\-–—,|(\[]+$', '', line[:dm.start()]).strip()
        if before and not _has_job_signals(before) and (_has_company_signals(before) or _spacy_looks_like_org(before)):
            # Check if next 1-2 lines start a sub-role with a date range
            for fwd in (idx + 1, idx + 2):
                if fwd < len(lines) and _DATE_RANGE_REGEX.search(lines[fwd]) and not _is_section_header(lines[fwd]):
                    comp, loc = _split_company_and_location(before)
                    if comp:
                        return comp, loc, 1

    return None


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
    current_company_context: Optional[Tuple[str, Optional[str]]] = None
    i = 0

    while i < len(lines):
        line = lines[i]

        if _is_section_header(line) or line.strip().lower() in _RESUME_SECTION_HEADERS or any(line.strip().lower().startswith(h) for h in _RESUME_SECTION_HEADERS):
            current_company_context = None
            i += 1
            continue

        parent_comp = _is_parent_company_header(lines, i)
        if parent_comp:
            current_company_context = (parent_comp[0], parent_comp[1])
            i += parent_comp[2]
            continue

        # ── Case A: Inline or Date-First entry format ─────────────────────────
        dm = _DATE_RANGE_REGEX.search(line)
        if dm:
            prose_m = _PROSE_ROLE_RE.match(line)
            if prose_m:
                raw_title = (prose_m.group("title") or "").strip()
                comp_loc_str = (prose_m.group("company") or "").strip()
                date_str = line[dm.start():dm.end()].strip()
                norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
                consumed_header = 1
            else:
                before_date = re.sub(r'[\s\-–—,|(\[:]+$', '', line[:dm.start()]).strip()
                before_date = re.sub(r'\s+(?:from|between|during)\s*$', '', before_date, flags=re.IGNORECASE).strip()
                after_date = re.sub(r'^[\s\-–—,|)\]:]+|[\s\-–—,|(\[]+$', '', line[dm.end():]).strip()

                if not before_date:
                    # Standalone date or Date-First line (e.g. "2021 - Present" or "2021 - Present | Senior Developer | Tech Mahindra")
                    date_str = line[dm.start():dm.end()].strip()
                    if after_date:
                        if '|' in after_date or '•' in after_date:
                            sep = '|' if '|' in after_date else '•'
                            segs = [s.strip() for s in after_date.split(sep) if s.strip()]
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
                        if i + 1 < len(lines) and not _is_section_header(lines[i + 1]) and not lines[i + 1].startswith(_BULLET_PREFIXES) and not _DATE_RANGE_REGEX.search(lines[i + 1]):
                            raw_title = lines[i + 1]
                            consumed_header = 2
                            if i + 2 < len(lines) and not _is_section_header(lines[i + 2]) and not lines[i + 2].startswith(_BULLET_PREFIXES) and not _DATE_RANGE_REGEX.search(lines[i + 2]):
                                comp_loc_str = lines[i + 2]
                                consumed_header = 3
                                if i + 3 < len(lines) and not _is_section_header(lines[i + 3]) and not lines[i + 3].startswith(_BULLET_PREFIXES) and not _DATE_RANGE_REGEX.search(lines[i + 3]) and _is_address_or_location(lines[i + 3]):
                                    comp_loc_str = f"{comp_loc_str} - {lines[i + 3]}"
                                    consumed_header = 4
                    norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
                elif '|' in line or ('•' in line and not line.lstrip().startswith('•') and line.count('•') >= 2):
                    sep = '|' if '|' in line else '•'
                    segments = [s.strip() for s in line.split(sep)]
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
                    consumed_header = 1
                    after_is_emp_marker = bool(after_date) and any(rx.search(after_date) for rx, _ in _EMPLOYMENT_TYPE_RULES)
                    if (
                        not company
                        and (not after_date or after_is_emp_marker)
                        and i + 1 < len(lines)
                        and not _is_section_header(lines[i + 1])
                        and not lines[i + 1].startswith(_BULLET_PREFIXES)
                        and not _DATE_RANGE_REGEX.search(lines[i + 1])
                        and not _STANDALONE_DATE_OR_DUR_RE.match(lines[i + 1].strip())
                        and not _INLINE_DURATION_OR_YEAR_RE.search(lines[i + 1])
                        and not _is_likely_responsibility_or_sentence(lines[i + 1])
                        and len(lines[i + 1]) <= 70
                        and (
                            _has_company_signals(lines[i + 1])
                            or _spacy_looks_like_org(lines[i + 1])
                            or not _JOB_TITLE_KEYWORDS_RE.search(lines[i + 1])
                        )
                    ):
                        norm_title, company, location = _extract_title_company_location(title_comp_str, lines[i + 1])
                        consumed_header = 2
                    comp_loc_str = company + (f" - {location}" if location else "")

            if not company and current_company_context:
                company, ctx_loc = current_company_context
                location = location or ctx_loc
            elif company and current_company_context and company.lower() != current_company_context[0].lower():
                current_company_context = None

            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_str)
            responsibilities, curr_idx = _collect_responsibilities(lines, i + consumed_header)

            emp_type = _detect_employment_type(raw_title, company + (f" - {location}" if location else ""), date_str, responsibilities)
            # Reject academic degrees / schooling mistaken as employment roles
            if _is_academic_degree_title(raw_title, (company or "") + " " + (location or "")):
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
        if not _INLINE_DURATION_OR_YEAR_RE.search(line):
            for offset in range(1, min(5, len(lines) - i)):
                cand_l = lines[i + offset]
                if _is_section_header(cand_l):
                    break
                if cand_l.startswith(_BULLET_PREFIXES):
                    cand_clean = cand_l.lstrip('•-*▪►✓ ').strip()
                    if _is_likely_responsibility_or_sentence(cand_clean) or len(cand_clean) > 65:
                        break
                if _DATE_RANGE_REGEX.search(cand_l) or _STANDALONE_DATE_OR_DUR_RE.match(cand_l.strip()):
                    if _PROSE_ROLE_RE.match(cand_l):
                        break
                    has_date_ahead = True
                    date_offset = offset
                    break

        if has_date_ahead:
            raw_title = line
            date_line = lines[i + date_offset]
            if date_offset == 4:
                comp_loc_str = f"{lines[i + 1]} - {lines[i + 2]}"
                consumed_header = 5
            elif date_offset == 3:
                comp_loc_str = f"{lines[i + 1]} - {lines[i + 2]}"
                consumed_header = 4
            elif date_offset == 2:
                comp_loc_str = lines[i + 1]
                consumed_header = 3
            elif date_offset == 1:
                dm_b = _DATE_RANGE_REGEX.search(date_line)
                before_dm = re.sub(r'[\s\-–—,|(\[:]+$', '', date_line[:dm_b.start()]).strip() if dm_b else ""
                after_dm = re.sub(r'^[\s\-–—,|)\]:]+|[\s\-–—,|(\[]+$', '', date_line[dm_b.end():]).strip() if dm_b else ""
                inline_comp_loc = before_dm or after_dm
                next_after_date = lines[i + 2] if i + 2 < len(lines) else ""
                if inline_comp_loc and not _is_likely_responsibility_or_sentence(inline_comp_loc):
                    comp_loc_str = inline_comp_loc
                    consumed_header = 2
                elif (
                    next_after_date
                    and not next_after_date.startswith(_BULLET_PREFIXES)
                    and not _is_section_header(next_after_date)
                    and not _DATE_RANGE_REGEX.search(next_after_date)
                    and not _is_likely_responsibility_or_sentence(next_after_date)
                    and (
                        _has_company_signals(next_after_date)
                        or _spacy_looks_like_org(next_after_date)
                        or (len(next_after_date) <= 50 and not _JOB_TITLE_KEYWORDS_RE.search(next_after_date))
                        or (
                            (_has_company_signals(raw_title) or _spacy_looks_like_org(raw_title))
                            and not _has_job_signals(raw_title)
                            and _has_job_signals(next_after_date)
                        )
                    )
                ):
                    comp_loc_str = next_after_date
                    consumed_header = 3
                else:
                    comp_loc_str = ""
                    consumed_header = 2

            if '|' in raw_title:
                parts = [p.strip() for p in raw_title.split('|', 1)]
                raw_title = parts[0]
                if not comp_loc_str and len(parts) > 1:
                    comp_loc_str = parts[1]

            norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
            if not company and current_company_context:
                company, ctx_loc = current_company_context
                location = location or ctx_loc
            elif company and current_company_context and company.lower() != current_company_context[0].lower():
                current_company_context = None

            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_line)
            responsibilities, curr_idx = _collect_responsibilities(lines, i + consumed_header)

            emp_type = _detect_employment_type(raw_title, comp_loc_str, date_line, responsibilities)
            # Reject academic degrees / schooling mistaken as employment roles
            if _is_academic_degree_title(raw_title, comp_loc_str or company or ""):
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

        # ── Case C: Inline duration/year on a single role line (no date range) ─
        dur_m = _INLINE_DURATION_OR_YEAR_RE.search(line)
        if dur_m and not line.startswith(_BULLET_PREFIXES) and not _is_likely_responsibility_or_sentence(line):
            dur_str = (dur_m.group("paren_dur") or dur_m.group("pipe_dur") or "").strip()
            dur_months = _parse_duration_text(dur_str)
            single_yr_m = re.fullmatch(r'(19|20)\d{2}', dur_str)
            if dur_months > 0 or single_yr_m:
                before_dur = re.sub(r'[\s\-–—,|(\[]+$', '', line[:dur_m.start()]).strip()
                if '|' in before_dur:
                    segs = [s.strip() for s in before_dur.split('|') if s.strip()]
                    raw_title = segs[0] if segs else ""
                    comp_loc_str = " | ".join(segs[1:]) if len(segs) > 1 else ""
                else:
                    raw_title = before_dur
                    comp_loc_str = ""
                norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
                consumed_header = 1
                if (
                    not company
                    and i + 1 < len(lines)
                    and not _is_section_header(lines[i + 1])
                    and not lines[i + 1].startswith(_BULLET_PREFIXES)
                    and not _DATE_RANGE_REGEX.search(lines[i + 1])
                    and not _is_likely_responsibility_or_sentence(lines[i + 1])
                    and (_has_company_signals(lines[i + 1]) or _spacy_looks_like_org(lines[i + 1]) or not _JOB_TITLE_KEYWORDS_RE.search(lines[i + 1]))
                ):
                    norm_title, company, location = _extract_title_company_location(raw_title, lines[i + 1])
                    consumed_header = 2

                responsibilities, curr_idx = _collect_responsibilities(lines, i + consumed_header)
                if norm_title and not _is_address_or_location(norm_title) and not _is_academic_degree_title(raw_title, company or ""):
                    s_iso = f"{dur_str}-01" if single_yr_m else None
                    e_iso = f"{dur_str}-12" if single_yr_m else None
                    emp_type = _detect_employment_type(raw_title, company, dur_str, responsibilities)
                    work_experiences.append({
                        "job_title": norm_title,
                        "role": norm_title,
                        "title": norm_title,
                        "raw_job_title": raw_title,
                        "company_name": company,
                        "company": company,
                        "location": location,
                        "employment_type": emp_type,
                        "start_date": s_iso,
                        "end_date": e_iso,
                        "duration_months": dur_months,
                        "responsibilities": responsibilities,
                        "highlights": responsibilities,
                    })
                i = curr_idx
                continue

        # ── Case D: Prose line with explicit duration (e.g. "Worked as Welder at ABC Corp for 3 years") ─
        prose_m = _PROSE_ROLE_RE.match(line)
        if prose_m and _parse_duration_text(line) > 0:
            raw_title = (prose_m.group("title") or "").strip()
            comp_loc_str = (prose_m.group("company") or "").strip()
            norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
            dur_months = _parse_duration_text(line)
            if norm_title and not _is_address_or_location(norm_title) and not _is_academic_degree_title(raw_title, company or ""):
                emp_type = _detect_employment_type(raw_title, company, line, [])
                work_experiences.append({
                    "job_title": norm_title,
                    "role": norm_title,
                    "title": norm_title,
                    "raw_job_title": raw_title,
                    "company_name": company,
                    "company": company,
                    "location": location,
                    "employment_type": emp_type,
                    "start_date": None,
                    "end_date": None,
                    "duration_months": dur_months,
                    "responsibilities": [],
                    "highlights": [],
                })
            i += 1
            continue

        i += 1

    # ── Undated fallback ONLY when an explicit EXPERIENCE section had roles without dates ──
    if not work_experiences and blocks and not (len(blocks) == 1 and blocks[0] == text):
        j = 0
        while j < len(lines):
            l_curr = lines[j]
            if (
                not _is_section_header(l_curr)
                and not l_curr.startswith(_BULLET_PREFIXES)
                and not _is_likely_responsibility_or_sentence(l_curr)
                and len(l_curr) <= 75
                and _has_job_signals(l_curr)
            ):
                comp_cand = ""
                consumed = 1
                if (
                    j + 1 < len(lines)
                    and not _is_section_header(lines[j + 1])
                    and not lines[j + 1].startswith(_BULLET_PREFIXES)
                    and not _is_likely_responsibility_or_sentence(lines[j + 1])
                    and len(lines[j + 1]) <= 70
                    and (_has_company_signals(lines[j + 1]) or _spacy_looks_like_org(lines[j + 1]) or not _has_job_signals(lines[j + 1]))
                ):
                    comp_cand = lines[j + 1]
                    consumed = 2
                norm_title, company, location = _extract_title_company_location(l_curr, comp_cand)
                if norm_title and company and not _is_academic_degree_title(l_curr, company):
                    resps, next_j = _collect_responsibilities(lines, j + consumed)
                    emp_type = _detect_employment_type(l_curr, company, "", resps)
                    work_experiences.append({
                        "job_title": norm_title,
                        "role": norm_title,
                        "title": norm_title,
                        "raw_job_title": l_curr,
                        "company_name": company,
                        "company": company,
                        "location": location,
                        "employment_type": emp_type,
                        "start_date": None,
                        "end_date": None,
                        "duration_months": 0,
                        "responsibilities": resps,
                        "highlights": resps,
                    })
                    j = next_j
                    continue
            j += 1

    total_months = _compute_merged_experience_months(work_experiences)
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


_EXPLICIT_DISQUALIFIER_BEFORE_RE = re.compile(
    r'\b(?:company|firm|organization|enterprise|client|clients|customer|customers|'
    r'team|staff|associates|employees|candidates|applicants|workers|developers|engineers|'
    r'minimum|must\s+have|required|requires|age|aged)\s*'
    r'(?:has|with|of|having|at\s+least|over|more\s+than)?\s*$',
    re.IGNORECASE,
)
_EXPLICIT_DISQUALIFIER_AFTER_RE = re.compile(
    r'^\s*(?:old|of\s+age|warranty|heritage|history|in\s+business|established|founded|'
    r'degree|diploma|course|study|college|university|high\s+school)\b',
    re.IGNORECASE,
)


def _extract_explicit_experience_months(text: str) -> int:
    """
    Extract explicit total experience duration (in months) from summary statements or
    explicit 'Experience:' / 'Years of Experience:' labels, ignoring false positives
    such as age ('18 years old'), company heritage ('25 years in business'), or education length.
    """
    if not text:
        return 0

    best_months = 0
    sections = split_into_sections(text)

    # 1. Explicit label lines anywhere in raw text outside Education/Certifications/References
    # (Scan raw lines before split_into_sections strips prefixes like 'Experience:')
    label_re = re.compile(
        r'^(?:total\s+(?:work\s+|relevant\s+|professional\s+)?)?'
        r'(?:years?\s+of\s+)?(?:work\s+|relevant\s+|professional\s+)?'
        r'(?:experience|tenure|length\s+of\s+service)\s*(?:\(\s*years?\s*\))?\s*[:\-–=]\s*(.+)$',
        re.IGNORECASE,
    )
    skip_lbls = {"EDUCATION", "CERTIFICATIONS", "REFERENCES", "INTERESTS"}
    curr_sec = "HEADER"
    for raw_line in text.split('\n'):
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue
        m = label_re.match(stripped_line)
        if m and curr_sec not in skip_lbls:
            rhs = m.group(1).strip()
            dur_m = _parse_duration_text(rhs)
            if dur_m > 0:
                best_months = max(best_months, dur_m)
                continue
            bare_num = re.match(r'^(\d+(?:\.\d+)?)\+?\s*$', rhs)
            if bare_num:
                yrs = float(bare_num.group(1))
                if 0 < yrs < 50:
                    best_months = max(best_months, max(1, round(yrs * 12.0)))
        lbl = detect_section_label(stripped_line)
        if lbl:
            curr_sec = lbl

    # 2. Candidate narrative statements in HEADER, SUMMARY, or EXPERIENCE intro
    narrative_parts = []
    for lbl in ("HEADER", "SUMMARY", "EXPERIENCE"):
        if sections.get(lbl):
            narrative_parts.append(sections[lbl])
    narrative_text = "\n".join(narrative_parts) if narrative_parts else text

    def _is_disqualified(src: str, start: int, end: int) -> bool:
        before = src[max(0, start - 50):start]
        after = src[end:min(len(src), end + 40)]
        if _EXPLICIT_DISQUALIFIER_BEFORE_RE.search(before):
            return True
        if _EXPLICIT_DISQUALIFIER_AFTER_RE.search(after):
            return True
        # Reject 'with 2 years of experience' when preceded by a plural/role noun ('mentored juniors with ...')
        if re.search(r'\b(?:juniors?|freshers?|graduates?|interns?|trainees?|hires?|peers?)\s+with\s*$', before, re.IGNORECASE):
            return True
        return False

    # Pattern A: Numeric years (+ optional range, + optional months) + experience keyword
    pat_a = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:[-–to]+\s*(\d+(?:\.\d+)?)\s*)?\+?\s*(?:years?|yrs?)'
        r'(?:\s*(?:and|,)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?))?\s+'
        r'(?:of\s+)?(?:(?:proven|hands-on|solid|extensive|broad|strong|rich|combined|total|overall|professional|relevant|related|work|working|industry|practical|direct|field)\s+)*'
        r'(?:experience|exp\.?|expertise|background|work|service)\b',
        re.IGNORECASE,
    )
    for m in pat_a.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        y1 = float(m.group(1))
        y2 = float(m.group(2)) if m.group(2) else None
        extra_mo = float(m.group(3)) if m.group(3) else 0.0
        yrs = ((y1 + y2) / 2.0) if (y2 is not None and y2 > y1 and (y2 - y1) <= 5) else y1
        if 0 <= yrs < 50:
            mos = round(yrs * 12.0 + extra_mo)
            if mos > 0:
                best_months = max(best_months, mos)

    # Pattern B: Qualifier + years ('over 5 years', 'more than 3.5 years', 'at least 4 years')
    pat_b = re.compile(
        r'\b(?:over|more\s+than|at\s+least|nearly|almost|about|around|approx\.?|approximately)\s+'
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)'
        r'(?:\s+(?:of\s+)?(?:(?:work|working|professional|relevant|related|industry|practical)\s+)?(?:experience|exp\.?|practice|service|career))?\b',
        re.IGNORECASE,
    )
    for m in pat_b.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    # Pattern C: 'X years in <industry/field>' or 'X years as a <role>'
    pat_c = re.compile(
        r'\b(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+'
        r'(?:in\s+(?:the\s+)?(?:industry|field|practice|IT|tech|software|manufacturing|construction|sales|retail|hospitality|healthcare|finance|accounting|engineering|customer\s+service|BPO)|as\s+(?:a|an)\s+[A-Za-z])',
        re.IGNORECASE,
    )
    for m in pat_c.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    # Pattern D: Months-only explicit experience ('18 months of experience', '6 mos work experience')
    pat_d = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:months?|mos?)\s+(?:of\s+)?(?:(?:work|working|relevant|related|professional|hands-on|practical)\s+)?(?:experience|exp\.?)\b',
        re.IGNORECASE,
    )
    for m in pat_d.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        mos = float(m.group(1))
        if 0 < mos < 600:
            best_months = max(best_months, max(1, round(mos)))

    # Pattern E: Word numbers ('five years of experience', 'two and a half years of experience', 'three (3) years')
    word_pat = '|'.join(sorted(_WORD_NUM_MAP.keys(), key=len, reverse=True))
    pat_e = re.compile(
        rf'\b(?P<w>{word_pat})(?:\s*\(\s*\d+\s*\))?(?P<half>\s+and\s+a\s+half)?\+?\s*(?:years?|yrs?)\s+'
        rf'(?:of\s+)?(?:(?:proven|hands-on|professional|relevant|related|work|industry|practical)\s+)*(?:experience|exp\.?|expertise|work)\b',
        re.IGNORECASE,
    )
    for m in pat_e.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = _WORD_NUM_MAP.get(m.group("w").lower(), 0.0) + (0.5 if m.group("half") else 0.0)
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    return best_months


def extract_experience_years_float(text: str) -> float:
    """
    Return total years of work experience as a float rounded to 1 decimal place
    (e.g. 2.5 years for 30 months), reconciling structured timeline with explicit summary mentions.
    """
    if not text:
        return 0.0

    structured = extract_structured_experience(text)
    structured_months = int(structured.get("total_experience_months", 0) or 0)
    explicit_months = _extract_explicit_experience_months(text)
    total_months = max(structured_months, explicit_months)
    if total_months <= 0:
        return 0.0
    return round(total_months / 12.0, 1)


def extract_years_experience(text: str) -> int:
    """
    Calculates total years of experience by reconciling merged structured duration months
    from work history with validated explicit summary/label mentions.
    """
    if not text:
        return 0

    structured = extract_structured_experience(text)
    structured_months = int(structured.get("total_experience_months", 0) or 0)
    explicit_months = _extract_explicit_experience_months(text)
    total_months = max(structured_months, explicit_months)
    if total_months > 0:
        return max(1, (total_months + 6) // 12)

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
        if _is_address_or_location(line) or _is_likely_responsibility_or_sentence(line):
            continue
        # Avoid matching educational degrees or school institutions as a job title
        if re.search(r'\b(?:bachelor|master|doctor|phd|diploma|associate|elementary|high\s+school|university|college|institute|polytechnic|campus)\b', line, re.I):
            continue
        has_role_signal = bool(
            _JOB_TITLE_KEYWORDS_RE.search(line)
            or (_KEYWORD_PROCESSOR and _KEYWORD_PROCESSOR.extract_keywords(line))
        )
        if not has_role_signal:
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
            if (
                comp
                and len(comp) > 2
                and not _is_address_or_location(comp)
                and not _is_likely_responsibility_or_sentence(comp)
                and not _DATE_RANGE_REGEX.search(comp)
            ):
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
            if (
                len(line_str) > 3
                and not _is_address_or_location(line_str)
                and not _is_likely_responsibility_or_sentence(line_str)
                and not _DATE_RANGE_REGEX.search(line_str)
                and not _JOB_TITLE_KEYWORDS_RE.search(line_str)
            ):
                if _COMPANY_LEGAL_SUFFIXES_RE.search(line_str):
                    c_clean, _ = _split_company_and_location(line_str)
                    if c_clean:
                        return c_clean

    # Fallback: search for 'at <Company>' pattern
    at_m = re.search(r'\b(?:at|@)\s+([A-Za-z0-9\s&.,\'-]+?)(?:\s*\(|\s*[-–—|,]|\s*[\r\n]|$)', comb, re.I)
    if at_m:
        cand = at_m.group(1).strip()
        if (
            len(cand) > 2
            and not _is_address_or_location(cand)
            and not _is_likely_responsibility_or_sentence(cand)
            and not _DATE_RANGE_REGEX.search(cand)
            and not _JOB_TITLE_KEYWORDS_RE.search(cand)
        ):
            return cand

    # Fallback: scan candidate company lines in experience blocks
    for block in blocks:
        block_lines = [l.strip() for l in block.split('\n') if l.strip()]
        for line_str in block_lines:
            if 2 < len(line_str) < 60:
                if not _is_section_header(line_str) and not line_str.startswith(('•', '-', '*', '▪', '►', '✓')):
                    if (
                        not _DATE_RANGE_REGEX.search(line_str)
                        and not _is_address_or_location(line_str)
                        and not _is_likely_responsibility_or_sentence(line_str)
                    ):
                        if not _JOB_TITLE_KEYWORDS_RE.search(line_str):
                            c_cand, _ = _split_company_and_location(line_str)
                            if (
                                c_cand
                                and len(c_cand) > 2
                                and not _is_address_or_location(c_cand)
                                and not _is_likely_responsibility_or_sentence(c_cand)
                                and not _JOB_TITLE_KEYWORDS_RE.search(c_cand)
                            ):
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