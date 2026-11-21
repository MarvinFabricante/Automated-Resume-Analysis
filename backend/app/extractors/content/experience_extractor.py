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
from functools import lru_cache
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

try:
    from number_parser import parse as _np_parse
except ImportError:
    _np_parse = None

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
    (re.compile(r'\b(?:Job\s+Order|Contract\s+of\s+Service|COS|Casual|Coterminous|Freelance(?:r)?|Self[\s\-]Employed)\b', re.IGNORECASE), "Contractual"),
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
    "SM Supermalls", "SM City", "SM Retail", "SM Supermarket", "Puregold", "Ayala Malls",
    "Ayala Land", "DMCI", "DMCI Homes", "DMCI Holdings", "Accenture", "Accenture Philippines",
    "Teleperformance", "Concentrix", "Convergys", "TaskUs", "Alorica", "Foundever", "Sitel",
    "Cognizant", "Globe Telecom", "Smart Communications", "PLDT", "San Miguel Corporation",
    "San Miguel Brewery", "San Miguel Packaging", "BDO", "BPI", "Metrobank",
    "Foodpanda", "Food Panda", "Grab", "Grab Philippines", "Lalamove", "Shopee", "Lazada",
    "Angkas", "Monde Nissin", "Universal Robina", "ChanzIT", "Fourello", "Vaskeappen",
    "Maxim", "Ninja Van", "J&T Express", "Flash Express", "Toktok", "Mariwasa",
    "Mariwasa Siam Ceramics", "Mariwasa Siam Ceramics Inc.", "XYZ Tech Solutions Inc.",
    # Additional Philippine & international employers without legal suffixes
    "7-Eleven", "Starbucks", "Wendy's", "Burger King", "Shakey's", "Pizza Hut",
    "Yellow Cab", "Max's", "Tokyo Tokyo", "Kenny Rogers", "BonChon", "Popeyes",
    "Dunkin'", "Krispy Kreme", "Mary Grace", "Conti's", "Pancake House",
    "S&R", "Landers", "Savemore", "Waltermart", "Mercury Drug", "Watsons",
    "Southstar Drug", "National Book Store", "Abenson", "Wilcon", "Wilcon Depot",
    "Ace Hardware", "Uniqlo", "Bench", "Penshoppe", "Meralco", "Maynilad",
    "Manila Water", "Converge", "Converge ICT", "DITO", "ABS-CBN", "GMA Network", "TV5",
    "LBC", "LBC Express", "2GO", "DHL", "FedEx", "UPS", "Maersk",
    "Philippine Airlines", "Cebu Pacific", "AirAsia", "PNB", "Landbank", "DBP",
    "Security Bank", "UnionBank", "RCBC", "EastWest Bank", "Chinabank", "PSBank",
    "GCash", "Maya", "PayMaya", "Sun Life", "Pru Life UK", "AXA", "Manulife",
    "IBM", "Oracle", "Microsoft", "Google", "Amazon", "Meta", "DXC", "DXC Technology",
    "Infosys", "TCS", "Wipro", "Capgemini", "Genpact", "Sutherland", "VXI",
    "Telus", "Telus International", "Optum", "JPMorgan", "Wells Fargo", "Citibank",
    "HSBC", "Deutsche Bank", "ING", "ANZ", "FactSet", "Reed Elsevier", "Thomson Reuters",
    "Deloitte", "PwC", "SGV & Co.", "KPMG", "Megaworld", "Filinvest", "Vista Land",
    "EEI", "EEI Corporation", "Megawide", "First Balfour", "Makati Development Corporation",
    "Nestlé", "Nestle", "Unilever", "Procter & Gamble", "Coca-Cola", "Pepsi",
    "Del Monte", "Century Pacific", "Rebisco", "Toyota", "Honda", "Mitsubishi", "Nissan",
    "Texas Instruments", "Analog Devices", "Amkor", "onsemi", "STMicroelectronics",
    "Nexperia", "Epson", "Canon", "Brother", "Murata", "Rohm", "Denso", "Yazaki",
    "Sumitomo", "Lear", "Dyson", "Samsung", "St. Luke's", "Makati Medical Center",
    "The Medical City", "Asian Hospital", "Philippine General Hospital",
    "DepEd", "DPWH", "DOH", "DOLE", "BIR", "SSS", "PhilHealth", "Pag-IBIG", "GSIS", "TESDA",
    "Upwork", "Fiverr", "OnlineJobs.ph", "Self-Employed", "Freelance",
]

_PHIL_COMPANY_NAMES_RE = re.compile(
    r'(?<![A-Za-z0-9])(?:'
    + '|'.join(re.escape(c) for c in sorted(_PHIL_COMPANY_NAMES, key=len, reverse=True))
    + r')(?![A-Za-z0-9])',
    re.IGNORECASE,
)

_TAXONOMY_TITLES_RE = re.compile(
    r'(?<![A-Za-z0-9])(?:'
    + '|'.join(
        re.escape(t)
        for t in sorted(
            {v for vars_list in _PHILIPPINE_JOB_TAXONOMY.values() for v in vars_list},
            key=len,
            reverse=True,
        )
    )
    + r')(?![A-Za-z0-9])',
    re.IGNORECASE,
)

_STRICT_LEGAL_SUFFIXES_RE = re.compile(
    r'\b(?:Inc\.?|Corp\.?|Corporation|Co\.?|Ltd\.?|LLP|LLC|PLC|GmbH|OPC|Pte\.?|Sdn\.?\s+Bhd\.?|B\.?V\.?|Pty\.?|'
    r'Incorporated|Limited|Holdings|Enterprises|Industries|Foundation|Cooperative|Coop|'
    r'Authority|Bureau|Commission|Council|Provincial\s+Government|City\s+Hall|'
    r'Manpower|Staffing|Crewing|Manning|Pawnshop|Outsourcing|Shared\s+Services|'
    r'Security\s+Agency|Janitorial|Phils\.?|Philippines)\b',
    re.IGNORECASE,
)

_COMPANY_LEGAL_SUFFIXES_RE = re.compile(
    r'\b(?:Inc\.?|Corp\.?|Corporation|Co\.?|Ltd\.?|LLP|LLC|PLC|GmbH|OPC|Pte\.?|Sdn\.?\s+Bhd\.?|B\.?V\.?|Pty\.?|'
    r'Incorporated|Limited|Foundation|Association|Cooperative|Coop|Authority|Bureau|Commission|Council|'
    r'Provincial\s+Government|City\s+Hall|Holdings|Enterprises|Services|Trading|Foods|Solutions|'
    r'Technologies|Technology|Group|Agency|Branch|Manpower|Staffing|Industries|Manufacturing|'
    r'Ceramics|Construction|Engineering|Builders|Realty|Properties|Studio|Studios|Consultancy|'
    r'Systems|Consulting|Logistics|Ventures|Labs|Media|Networks|Telecom|Distributors?|Distribution|'
    r'Hardware|Motors|Automotive|Airlines|Shipping|Crewing|Manning|Express|Freight|Cargo|'
    r'Energy|Power|Mining|Pharma(?:ceuticals)?|Diagnostics|Laboratories|Packaging|Plastics|'
    r'Semiconductors?|Electronics|Microelectronics|Retail|Pawnshop|Insurance|Capital|Finance|'
    r'Financial|Securities|Investments|Development|Developers|Estates|Residences|Management|'
    r'Partners|Associates|Outsourcing|Shared\s+Services|BPO|Security\s+Agency|Janitorial|'
    r'Recruitment|Phils\.?|Philippines)\b',
    re.IGNORECASE,
)

_COMPANY_PLACE_WORDS_RE = re.compile(
    r'\b(?:Hospital|Medical\s+Center|Clinic|Pharmacy|Drugstore|Supermarket|Hypermarket|Mart|Mall|Department\s+Store|Hotel|Resort|Restaurant|Cafe|Bakeshop|Factory|Plant|Mill|Foundry|Workshop|Bank|Barangay|Municipality|City\s+Government|LGU|Department\s+of)\b',
    re.IGNORECASE
)

_JOB_TITLE_KEYWORDS_RE = re.compile(
    r'\b(?:Engineer|Developer|Programmer|Specialist|Manager|Director|Officer|Analyst|Lead|Leader|Leadman|Foreman|Supervisor|'
    r'Technician|Assistant|Associate|Operator|Representative|Consultant|Architect|Designer|Coordinator|'
    r'Administrator|Secretary|Crew|Cashier|Rider|Driver|Clerk|Intern|Trainee|Nurse|Midwife|Caregiver|Therapist|Dentist|'
    r'Teacher|Instructor|Professor|Lecturer|Tutor|Trainer|Accountant|Auditor|Chemist|Pharmacist|Janitor|Janitress|Cook|Chef|Baker|Butcher|'
    r'Waiter|Waitress|Server|Bartender|Staff|Executive|Practitioner|Worker|Scientist|Researcher|'
    r'Carpenter|Welder|Mason|Electrician|Plumber|Mechanic|Helper|Apprentice|Inspector|Bagger|Promodiser|'
    r'Merchandiser|Warehouseman|Stockman|Guard|Watchman|Barista|Dishwasher|Busboy|Bookkeeper|Encoder|Typist|Receptionist|'
    r'Checker|Packer|Picker|Loader|Sorter|Dispatcher|Assembler|Machinist|Painter|Fabricator|Tailor|'
    r'Writer|Editor|Marketer|Buyer|Purchaser|Broker|Collector|Teller|Moderator|Transcriber|Freelancer|Superintendent|Principal|Head|Chief|'
    r'Aide|Agent|Attendant|Captain|Pilot|Seaman|Seafarer|Cadet|Bosun|Oiler|Wiper|Steward|Messman|'
    r'Counsel|Lawyer|Attorney|Paralegal|Doctor|Physician|Surgeon|Optometrist|Veterinarian|Psychologist|Psychometrician|'
    r'Nutritionist|Dietitian|Technologist|Phlebotomist|Paramedic|EMT|President|Founder|Owner|Proprietor|Partner|'
    r'Controller|Treasurer|Bursar|Actuary|Underwriter|Appraiser|Realtor|Surveyor|Enumerator|Timekeeper|Storekeeper|Toolkeeper|Keeper|'
    r'Fitter|Rigger|Lineman|Splicer|Tiler|Scaffolder|Steelman|Pahinante|Porter|Courier|Messenger|Liaison|Caretaker|'
    r'Stylist|Barber|Cutter|Sewer|Sommelier|Concierge|Housekeeper|Cleaner|Nanny|OIC|SME|RTA|WFM|CEO|CTO|CFO|COO|VP|'
    r'Tester|QA|QC|SRE|DBA|DevOps|SysAdmin|Webmaster|Illustrator|Animator|Photographer|Videographer|Creator|'
    r'Strategist|Planner|Scheduler|Estimator|Draftsman|Drafter|Detailer|Master|Coach|Mentor|Facilitator|Proctor|'
    r'Librarian|Archivist|Curator|Washer|Utility|Personnel|'
    r'Bellboy|Bellhop|Valet|Hostess|Busser|Runner|Expediter|Salesperson|Salesgirl|Salesboy|Handyman|Repairman|'
    r'Serviceman|Installer|Chauffeur|Conductor|Trucker|Hauler|Gardener|Landscaper|Groundskeeper|Seamstress|'
    r'Dressmaker|Upholsterer|Glazier|Roofer|Plasterer|Bricklayer|Boilermaker|Toolmaker|Millwright|Pressman|'
    r'Molder|Grinder|Polisher|Palletizer|Stacker|Labeler|Wrapper|Tallyman|Weigher|Stevedore|Telemarketer|'
    r'Setter|Closer|Coder|Pentester|Copywriter|Ghostwriter|Proofreader|Translator|Interpreter|Artist|Journalist|'
    r'Reporter|Correspondent|Producer|Recruiter|Sourcer|Advisor|Adviser|Ambassador|Custodian|Banker|Trader|'
    r'Adjuster|Examiner|Investigator|Firefighter|Deckhand|Motorman|Pumpman|Mate|Mariner|Counselor|Educator|'
    r'Registrar|Dean|Fellow|Postdoc|Economist|Statistician|Geologist|Biologist|Microbiologist|MedTech|RadTech|'
    r'Sonographer|Radiographer|Orderly|Carer|Generalist|Front-End|Back-End|Full-Stack|DevSecOps|MLOps|AIOps)\b',
    re.IGNORECASE
)

_RESPONSIBILITY_VERB_START_RE = re.compile(
    r'^(?:[•\-*▪►✓·]\s*)?(?:duties|responsibilities|key\s+tasks|tasks|achievements|'
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


_LOWERCASE_SENTENCE_START_RE = re.compile(
    r'^(?:and|or|with|for|to|of|in|on|by|from|that|which|who|where|when|while|'
    r'using|including|such\s+as|as\s+well\s+as|during|through|via)\b'
)


def _is_likely_responsibility_or_sentence(text: str) -> bool:
    """Detect whether a line is a job duty/responsibility sentence rather than a title or company name."""
    if not text:
        return False
    clean = text.strip()
    if not clean:
        return False
    if _RESPONSIBILITY_VERB_START_RE.match(clean):
        return True
    if clean[0].islower():
        if _LOWERCASE_SENTENCE_START_RE.match(clean):
            return True
        words_cnt = len(clean.split())
        if words_cnt > 6 and not _STRICT_LEGAL_SUFFIXES_RE.search(clean):
            return True
        if words_cnt >= 4 and not _has_job_signals(clean) and not _has_company_signals(clean):
            return True
    if re.search(r'\bwith\s+\d+\+?\s*(?:years?|yrs?)\s+of\s+experience\b', clean, re.IGNORECASE):
        return True
    if len(clean) > 70 and not _STRICT_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if len(clean.split()) > 12 and not _STRICT_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if clean.endswith('.') and len(clean.split()) >= 6 and not _STRICT_LEGAL_SUFFIXES_RE.search(clean):
        return True
    if (';' in clean or clean.count(',') >= 3) and not _STRICT_LEGAL_SUFFIXES_RE.search(clean):
        return True
    return False

# Philippine Locations
_PHIL_LOCATIONS_SET = {
    "manila", "quezon city", "makati", "makati city", "taguig", "taguig city", "bgc",
    "bonifacio global city", "pasig", "pasig city", "ortigas", "ortigas center", "mandaluyong",
    "mandaluyong city", "san juan", "san juan city", "marikina", "marikina city", "pasay",
    "pasay city", "parañaque", "paranaque", "muntinlupa", "muntinlupa city", "alabang",
    "las piñas", "las pinas", "caloocan", "caloocan city", "malabon", "navotas", "valenzuela",
    "valenzuela city", "cubao", "eastwood", "binondo", "ermita", "malate",
    "intramuros", "sampaloc", "tondo", "mckinley", "rizal", "antipolo", "antipolo city",
    "taytay", "cainta", "teresa", "binangonan", "san mateo", "rodriguez", "laguna",
    "calamba", "calamba city", "santa rosa", "santa rosa city", "sta. rosa", "biñan",
    "binan", "san pedro", "cabuyao", "los baños", "los banos", "cavite", "bacoor",
    "dasmarinas", "dasmariñas", "imus", "general trias", "tagaytay", "batangas",
    "batangas city", "lipa", "lipa city", "tanauan", "sto. tomas", "sto tomas", "santo tomas",
    "san pablo", "san pablo city", "lucena", "lucena city", "naga", "naga city",
    "legazpi", "legazpi city", "tacloban", "tacloban city", "zamboanga", "zamboanga city",
    "butuan", "butuan city", "iligan", "iligan city", "cotabato", "cotabato city",
    "olongapo", "olongapo city", "tarlac", "tarlac city", "dagupan", "dagupan city",
    "laoag", "laoag city", "tuguegarao", "tuguegarao city", "cabanatuan", "cabanatuan city",
    "dumaguete", "dumaguete city", "tagbilaran", "tagbilaran city", "roxas", "roxas city",
    "kalibo", "puerto princesa", "bulacan", "malolos", "meycauayan", "san jose del monte",
    "pampanga", "angeles", "angeles city", "san fernando", "clark", "subic",
    "bataan", "nueva ecija", "pangasinan", "la union", "benguet", "ilocos", "ilocos norte",
    "ilocos sur", "cagayan", "isabela", "zambales", "quezon", "albay", "camarines",
    "camarines sur", "camarines norte", "sorsogon", "mindoro", "palawan", "aklan",
    "capiz", "negros", "negros occidental", "negros oriental", "bohol", "leyte", "samar",
    "misamis", "misamis oriental", "misamis occidental", "bukidnon", "south cotabato",
    "north cotabato", "cebu", "cebu city", "mandaue", "lapu-lapu", "davao", "davao city",
    "iloilo", "iloilo city", "baguio", "baguio city", "cagayan de oro", "bacolod",
    "bacolod city", "general santos",
    "national capital region", "central luzon", "central visayas", "western visayas",
    "eastern visayas", "davao region", "northern mindanao", "bicol", "bicol region",
    "cordillera", "cordillera administrative region", "mimaropa", "soccsksargen",
    "caraga", "barmm",
}

_LOCATION_ONLY_TERMS = {
    "ncr", "metro manila", "calabarzon", "philippines", "luzon", "visayas", "mindanao",
    "diliman", "remote", "hybrid", "on-site", "onsite", "wfh", "work from home",
    # Major OFW / remote international locations
    "singapore", "united states", "usa", "u.s.", "u.s.a.", "united kingdom", "uk",
    "canada", "australia", "japan", "tokyo", "south korea", "seoul", "taiwan",
    "hong kong", "china", "malaysia", "kuala lumpur", "thailand", "bangkok",
    "vietnam", "indonesia", "india", "dubai", "abu dhabi", "uae", "united arab emirates",
    "saudi arabia", "riyadh", "jeddah", "dammam", "qatar", "doha", "kuwait",
    "bahrain", "oman", "israel", "germany", "france", "italy", "spain",
    "netherlands", "norway", "drøbak", "sweden", "switzerland", "ireland",
    "new zealand", "london", "new york", "california", "texas", "sydney",
    "melbourne", "toronto", "vancouver",
}

_ALL_LOCATIONS_SET = _PHIL_LOCATIONS_SET | _LOCATION_ONLY_TERMS

_ALL_LOCATIONS_RE = re.compile(
    r'(?<![A-Za-z0-9])(?:'
    + '|'.join(re.escape(loc) for loc in sorted(_ALL_LOCATIONS_SET, key=len, reverse=True))
    + r')(?![A-Za-z0-9])',
    re.IGNORECASE,
)


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


@lru_cache(maxsize=512)
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


@lru_cache(maxsize=512)
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
    r'(?:Jan(?:uary|uary|uray|vier|uar)?|Janaury|1an|'
    r'Feb(?:ruary|ruary|uary|rero|ruar)?|Febraury|F[eé]vrier|Peb(?:rero)?|'
    r'Mar(?:ch|so|z)?|Mrach|Apr(?:il)?|Apirl|Abr(?:il)?|Avr(?:il)?|May|Mayo|Mai|'
    r'Jun(?:e|io|i)?|Juen|Juin|Jul(?:y|io|i)?|Juillet|Hunyo|Hulyo|'
    r'Aug(?:ust|st)?|Agust|Ago(?:sto)?|Août|Aout|'
    r'Sep(?:t(?:ember|mber|iembre)?)?|Set(?:ember|yembre)?|Spetember|'
    r'Oct(?:ober|ber|ubre)?|Okt(?:ubre|ober)?|Ocotober|'
    r'Nov(?:ember|emeber|embre|iembre)?|Novmber|Nob(?:yembre)?|'
    r'Dec(?:ember|emeber|embre)?|Decmber|Dic(?:iembre)?|Dez(?:ember)?|Dis(?:yembre)?|'
    r'Enero|Pebrero|Disyembre)'
)
_YEAR_RE = r'(?:19|20)\d{2}'
_SHORT_YEAR_RE = r'(?:[0-3]\d|[5-9]\d)'
_SEASON_RE = r'(?:Spring|Summer|Fall|Autumn|Winter)'
_APPROX_QUAL_RE = r'(?:Early|Mid|Late)'
_ROMAN_MONTH_RE = r'(?-i:XII|XI|IX|X|VIII|VII|VI|IV|V|III|II|I)'
_PRESENT_RE = (
    r'(?:Pres(?:e?nt|net)|Preesnt|Pres\.?(?!\w)|Current(?:ly)?|Currenly|Curr\.?(?!\w)|Presently|'
    r'Now|To\s+Present|To-Present|To\s+the\s+present|To\s+Date|To-Date|'
    r'Up\s+to\s+(?:present|date|now|this\s+date)|Until\s+(?:present|date|now|today)|As\s+of\s+(?:present|date|today|now)|'
    r'Till?\s+(?:date|present|now)|At\s+present|On-?going|On\s+going|Today|Onwards|Continuing|'
    r'Current\s+(?:Position|Role)|Present\s+Time|Active|Still\s+(?:employed|working|here|active)|Incumbent|'
    r'(?:Hanggang\s+(?:sa\s+)?|Sa\s+)?Kasalukuyan|Presente|Actualidad)'
)
_ORDINAL_DAY_RE = r'\d{1,2}(?:st|nd|rd|th)?'

_DATE_TOKEN_RE = (
    rf'(?:'
    rf'{_ORDINAL_DAY_RE}(?:[-/\s]+|\s+of\s+){_MONTHS_NAMES}\.?[-/,\s]+{_YEAR_RE}'
    rf'|\b{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE}\s*,?)?\s*(?:[,. /-]\s*)?{_YEAR_RE}'
    rf'|{_YEAR_RE}\s*[-/\s]\s*{_MONTHS_NAMES}\.?'
    rf'|{_MONTHS_NAMES}\.?\s*[\'’]{_SHORT_YEAR_RE}'
    rf'|(?:Q[1-4]|(?:1st|2nd|3rd|4th)\s+Quarter)\s*{_YEAR_RE}'
    rf'|{_SEASON_RE}\s+{_YEAR_RE}'
    rf'|{_APPROX_QUAL_RE}[\s\-]+{_YEAR_RE}'
    rf'|\b{_ROMAN_MONTH_RE}[./-]{_YEAR_RE}\b'
    rf'|\d{{4}}[-/.](?:0?[1-9]|1[0-2])(?:[-/.]\d{{1,2}})?\b'
    rf'|\b\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}}\b'
    rf'|\b\d{{1,2}}[./-]\d{{1,2}}[./-]{_SHORT_YEAR_RE}\b'
    rf'|\b(?:0?[1-9]|1[0-2])(?:\s*/\s*|[./-])\d{{4}}\b'
    rf'|(?<!v)(?<!\d\.)\b(?:0[1-9]|1[0-2])[./-]{_SHORT_YEAR_RE}\b'
    rf'|\b(?:0?[1-9]|1[0-2])\s*/\s*{_SHORT_YEAR_RE}\b'
    rf'|{_YEAR_RE}'
    rf')'
)

_RANGE_CONNECTOR_RE = r'(?:[-–—~→]|->|\b(?:to|until|up\s+to|thru|through|till?|hanggang)\b|\'til)'

_DATE_RANGE_REGEX = re.compile(
    rf'(?:'
    rf'(?:between)\s+(?P<btw_start>{_DATE_TOKEN_RE})\s+and\s+(?P<btw_end>{_DATE_TOKEN_RE}|{_PRESENT_RE})'
    rf'|(?P<myr_short_s>\b{_MONTHS_NAMES}\.?\s*[,.]?\s*{_YEAR_RE})\s*[-–—]\s*(?P<myr_short_e>\d{{2}})\b(?![-/.]\d)'
    rf'|(?P<start>{_DATE_TOKEN_RE})\s*{_RANGE_CONNECTOR_RE}\s*(?P<end>{_DATE_TOKEN_RE}|{_PRESENT_RE})(?!\w)'
    rf'|(?P<yr_short_s>(?:19|20)\d{{2}})\s*[-–—]\s*(?P<yr_short_e>\d{{2}})\b(?![-/.]\d)'
    rf'|(?P<sm_start>(?:{_ORDINAL_DAY_RE}(?:[-/\s]+|\s+of\s+))?{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?)\s*(?:[-–—~]|\b(?:to|until|thru|through|hanggang)\b)\s*(?P<sm_end>(?:{_ORDINAL_DAY_RE}(?:[-/\s]+|\s+of\s+))?{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*(?:{_YEAR_RE}|[\'’]{_SHORT_YEAR_RE}))'
    rf'|(?P<my_short_s>\b{_MONTHS_NAMES}\.?\s+{_SHORT_YEAR_RE})\s*{_RANGE_CONNECTOR_RE}\s*(?P<my_short_e>\b{_MONTHS_NAMES}\.?\s+{_SHORT_YEAR_RE}|{_PRESENT_RE})(?!\s*,?\s*(?:19|20)\d{{2}})(?!\w)'
    rf'|(?:Since|From|Started|Effective)\s+(?P<open_start>{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*{_YEAR_RE}|(?:0?[1-9]|1[0-2])\s*[/-]\s*\d{{4}}|{_YEAR_RE})(?!\s*{_RANGE_CONNECTOR_RE})'
    rf'|(?P<trail_start>{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*{_YEAR_RE}|(?:0?[1-9]|1[0-2])\s*[/-]\s*\d{{4}})\s*[-–—]\s*(?=$|[)\]|,])'
    rf')',
    re.IGNORECASE,
)

_HOURS_REGEX = re.compile(r'\(?(\d+)\s*(?:Hours?|Hrs?)\)?', re.IGNORECASE)

_WORD_NUM_MAP = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0,
    "fifteen": 15.0, "sixteen": 16.0, "seventeen": 17.0, "eighteen": 18.0,
    "nineteen": 19.0, "twenty": 20.0, "thirty": 30.0, "forty": 40.0,
    "fifty": 50.0, "sixty": 60.0, "seventy": 70.0, "eighty": 80.0, "ninety": 90.0,
    "half": 0.5, "a": 1.0, "an": 1.0,
}

_NUMBER_WORDS_ONLY = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "and",
}

_TAGALOG_NUM_MAP = {
    "isang": 1, "isa": 1, "dalawang": 2, "dalawa": 2, "tatlong": 3, "tatlo": 3,
    "apat na": 4, "apat": 4, "limang": 5, "lima": 5, "anim na": 6, "anim": 6,
    "pitong": 7, "pito": 7, "walong": 8, "walo": 8, "siyam na": 9, "siyam": 9,
    "sampung": 10, "sampu": 10,
}

_STANDALONE_DATE_OR_DUR_RE = re.compile(
    rf'^\(?\s*(?:{_MONTHS_NAMES}\.?\s*[,.]?\s*{_YEAR_RE}'
    rf'|{_SEASON_RE}\s+{_YEAR_RE}'
    rf'|(?:Q[1-4]|(?:1st|2nd|3rd|4th)\s+Quarter)\s*{_YEAR_RE}'
    rf'|(?:19|20)\d{{2}}'
    rf'|\d+(?:\.\d+)?\s*(?:years?|yrs?)(?:\s*(?:and|,)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?'
    rf'|\d+(?:\.\d+)?\s*\+?\s*(?:months?|mos?|weeks?|wks?|hours?|hrs?)'
    rf'|\d+(?:\.\d+)?\s*y\s*\+?(?:\s*\d+(?:\.\d+)?\s*m)?)\s*\)?$',
    re.IGNORECASE,
)

_INLINE_DURATION_OR_YEAR_RE = re.compile(
    r'(?:\(\s*(?P<paren_dur>(?:\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|hours?|hrs?)(?:\s*(?:and|,|&)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?)|(?:\d+(?:\.\d+)?\s*y\s*\+?(?:\s*\d+(?:\.\d+)?\s*m)?)|(?:19|20)\d{2})\s*\)'
    r'|\|\s*(?P<pipe_dur>(?:\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?|months?|mos?|hours?|hrs?)(?:\s*(?:and|,|&)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?)|(?:\d+(?:\.\d+)?\s*y\s*\+?(?:\s*\d+(?:\.\d+)?\s*m)?))\s*$'
    r'|(?:\s+[-–—]\s+|,\s*)(?P<dash_dur>(?:\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|hours?|hrs?)(?:\s*(?:and|,|&)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?)|(?:\d+(?:\.\d+)?\s*y\s*\+?(?:\s*\d+(?:\.\d+)?\s*m)?))\s*$)',
    re.IGNORECASE,
)


def _words_to_number(phrase: str) -> Optional[float]:
    """Deterministically convert English number phrases (0-999) to float, optionally using number-parser."""
    if not phrase:
        return None
    cleaned = re.sub(r'[-]+', ' ', phrase.strip().lower())
    tokens = [t for t in cleaned.split() if t]
    if not tokens or not all(t in _NUMBER_WORDS_ONLY for t in tokens):
        return None
    if tokens == ["and"]:
        return None
    if _np_parse is not None:
        try:
            parsed_str = _np_parse(cleaned)
            if re.fullmatch(r'\d+(?:\.\d+)?', str(parsed_str).strip()):
                return float(parsed_str)
        except Exception:
            pass
    total = 0.0
    current = 0.0
    for tok in tokens:
        if tok == "and":
            continue
        if tok == "hundred":
            current = (current or 1.0) * 100.0
        elif tok in _WORD_NUM_MAP:
            current += _WORD_NUM_MAP[tok]
        else:
            return None
    total += current
    return total if total > 0 else None


def _normalize_written_numbers(text: str) -> str:
    """
    Normalize written numbers, fractions, and decades near experience/duration units
    into clean numeric strings without mutating unrelated prose numbers.
    """
    if not text:
        return ""
    res = text
    # Unicode fractions (e.g., 2½ -> 2.5, ½ year -> 0.5 year)
    for frac, dec in (("½", ".5"), ("¼", ".25"), ("¾", ".75")):
        res = re.sub(rf'(\d)\s*{frac}', rf'\1{dec}', res)
        res = res.replace(frac, f"0{dec}")

    # "three (3) years" or "five (5)+ years" -> "3 years" / "5+ years"
    res = re.sub(
        r'\b[a-z]+\s*\(\s*(\d+(?:\.\d+)?)\s*\)\s*(\+?)(?=\s*[-–]?\s*(?:years?|yrs?|months?|mos?)\b)',
        r'\1\2',
        res,
        flags=re.I,
    )

    # Decades ("a decade" -> "10 years", "two decades" -> "20 years")
    res = re.sub(r'\b(?:a|an|one)\s+decade\b', '10 years', res, flags=re.I)
    def _repl_decades(m):
        val = _words_to_number(m.group(1))
        if val is not None and val < 10:
            return f"{int(round(val * 10))} years"
        return m.group(0)
    res = re.sub(r'\b([a-z-]+)\s+decades\b', _repl_decades, res, flags=re.I)

    # Half-year / "one and a half" / "a year and a half" / "a year and 6 months"
    res = re.sub(r'\b(?:a|an|one|1)\s+year\s+and\s+a\s+half\b', '1.5 years', res, flags=re.I)
    res = re.sub(r'\b(?:a|an)\s+(year|yr)\s+and\s+(\d+(?:\.\d+)?)\s+(months?|mos?)\b', r'1 \1 and \2 \3', res, flags=re.I)
    res = re.sub(r'\b(\d+)\s+and\s+a\s+half\b', lambda m: f"{int(m.group(1)) + 0.5}", res, flags=re.I)
    def _repl_word_half(m):
        val = _words_to_number(m.group(1))
        if val is not None:
            return f"{val + 0.5}"
        return m.group(0)
    res = re.sub(r'\b([a-z-]+(?:\s+[a-z-]+)?)\s+and\s+a\s+half(?=\s*(?:years?|yrs?)\b)', _repl_word_half, res, flags=re.I)
    res = re.sub(r'\b(?:half\s+(?:a|an)|a\s+half)\s*(years?|yrs?)\b', r'0.5 \1', res, flags=re.I)

    # Tagalog number words before taon/taong/buwan/buwang
    _tl_pat = '|'.join(sorted(_TAGALOG_NUM_MAP.keys(), key=len, reverse=True))
    res = re.sub(
        rf'\b({_tl_pat})\s+(taon(?:g)?|buwan(?:g)?)\b',
        lambda m: f"{_TAGALOG_NUM_MAP[m.group(1).lower()]} {m.group(2)}",
        res,
        flags=re.I,
    )

    # "over a year" / "more than a year" / "a year of experience"
    res = re.sub(r'\b(over|more\s+than|at\s+least|nearly|almost|about|around)\s+(?:a|an)\s+(year|yr)\b', r'\1 1 \2', res, flags=re.I)
    res = re.sub(r'\b(?:a|an)\s+(year|yr)\s+(?=(?:of\s+)?(?:[a-z]+\s+){0,3}(?:experience|exp\.?)\b)', r'1 \1 ', res, flags=re.I)

    # Compound written numbers immediately before duration units or "-year"
    def _repl_unit_num(m):
        phrase = m.group(1)
        sep = m.group(2)
        unit = m.group(3)
        val = _words_to_number(phrase)
        if val is not None:
            val_str = str(int(val)) if val == int(val) else str(val)
            return f"{val_str}{sep}{unit}"
        return m.group(0)

    _num_word_alt = (
        r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|'
        r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|'
        r'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)'
    )
    res = re.sub(
        rf'\b({_num_word_alt}(?:(?:[\s-]+and)?[\s-]+{_num_word_alt}){{0,3}})([\s-]+)(years?|yrs?|months?|mos?|weeks?|wks?|hours?|hrs?|yoe)\b',
        _repl_unit_num,
        res,
        flags=re.I,
    )
    return res


def _expand_short_year(yy: int) -> int:
    max_2digit = (datetime.now().year + 2) % 100
    return (2000 + yy) if yy <= max(max_2digit, 40) else (1900 + yy)


def _month_name_to_num(month_str: str) -> int:
    m = re.sub(r'[^a-z0-9]', '', month_str.strip().lower())
    mapping = {
        'jan': 1, 'january': 1, 'janaury': 1, 'januray': 1, 'enero': 1, 'janvier': 1, 'januar': 1, '1an': 1,
        'feb': 2, 'february': 2, 'febraury': 2, 'febuary': 2, 'pebrero': 2, 'peb': 2, 'febrero': 2, 'fevrier': 2, 'fvrier': 2, 'februar': 2,
        'mar': 3, 'march': 3, 'mrach': 3, 'marso': 3, 'marzo': 3, 'mars': 3, 'marz': 3,
        'apr': 4, 'april': 4, 'apirl': 4, 'abril': 4, 'avril': 4,
        'may': 5, 'mayo': 5, 'mai': 5,
        'jun': 6, 'june': 6, 'juen': 6, 'hunyo': 6, 'junio': 6, 'juin': 6, 'juni': 6,
        'jul': 7, 'july': 7, 'hulyo': 7, 'julio': 7, 'juillet': 7, 'juli': 7,
        'aug': 8, 'august': 8, 'augst': 8, 'agust': 8, 'agosto': 8, 'ago': 8, 'aout': 8,
        'sep': 9, 'sept': 9, 'september': 9, 'septmber': 9, 'setember': 9, 'spetember': 9, 'setyembre': 9, 'septiembre': 9,
        'oct': 10, 'october': 10, 'octber': 10, 'ocotober': 10, 'oktubre': 10, 'octubre': 10, 'oktober': 10,
        'nov': 11, 'november': 11, 'novemeber': 11, 'novmber': 11, 'nobyembre': 11, 'nob': 11, 'noviembre': 11, 'novembre': 11,
        'dec': 12, 'december': 12, 'decemeber': 12, 'decmber': 12, 'disyembre': 12, 'dis': 12, 'diciembre': 12, 'decembre': 12, 'dezember': 12, 'dez': 12,
    }
    if m in mapping:
        return mapping[m]
    if rapidfuzz_process is not None and len(m) >= 3:
        best = rapidfuzz_process.extractOne(m, list(mapping.keys()), scorer=rapidfuzz_fuzz.ratio, score_cutoff=80)
        if best:
            return mapping[best[0]]
    return 1


def _parse_duration_text(text: str) -> int:
    """Parse explicit duration expressions like '2 yrs 6 mos', '3y 4m', '1.5 years', '486 hours', or 'two years' into months."""
    if not text:
        return 0
    clean = _normalize_written_numbers(text.strip())

    # 1. Combined years + months: "2 years 6 months", "1 yr, 3 mos", "2 yrs & 4 mos"
    ym_match = re.search(
        r'\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?\.?)\s*(?:and|,|&)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?\.?)\b',
        clean,
        re.IGNORECASE,
    )
    if ym_match:
        yrs = float(ym_match.group(1))
        mos = float(ym_match.group(2))
        if 0 <= yrs < 50 and 0 <= mos < 60:
            return max(1, round(yrs * 12.0 + mos))

    # 1b. Compact '3y 4m', '2y 6m', '1y+ 2m'
    c_ym = re.search(r'(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*y(?:rs?)?\+?\s*(?:and|,|&)?\s*(\d+(?:\.\d+)?)\s*m(?:os?)?(?![A-Za-z])', clean, re.IGNORECASE)
    if c_ym:
        yrs = float(c_ym.group(1))
        mos = float(c_ym.group(2))
        if 0 <= yrs < 50 and 0 <= mos < 60:
            return max(1, round(yrs * 12.0 + mos))

    # 1c. Tagalog combined or single ("2 taon at 6 buwan", "3 taong")
    tl_ym = re.search(r'\b(\d+(?:\.\d+)?)\s*taon(?:g)?\s*(?:at\s+(\d+(?:\.\d+)?)\s*(?:na\s+)?buwan(?:g)?)?\b', clean, re.IGNORECASE)
    if tl_ym:
        yrs = float(tl_ym.group(1))
        mos = float(tl_ym.group(2)) if tl_ym.group(2) else 0.0
        if 0 < yrs < 50 and 0 <= mos < 60:
            return max(1, round(yrs * 12.0 + mos))

    # 2. Numeric years (including "5-year" and compact "5y+" / "3.5y")
    yr_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:\+?\s*|[-–])(?:years?|yrs?\.?|year\b)', clean, re.IGNORECASE)
    if not yr_match:
        yr_match = re.search(r'\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?\.?)\b', clean, re.IGNORECASE)
    if not yr_match:
        yr_match = re.search(r'(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)\s*y\+?(?![A-Za-z])', clean, re.IGNORECASE)
    if yr_match:
        yrs = float(yr_match.group(1))
        if 0 < yrs < 50:
            return max(1, round(yrs * 12.0))

    # 3. Numeric months ("6+ months", "18 mos", "6 na buwan")
    mo_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:\+\s*|[-–]\s*)?(?:months?|mos?\.?|(?:na\s+)?buwan(?:g)?)\b', clean, re.IGNORECASE)
    if mo_match:
        mos = float(mo_match.group(1))
        if 0 < mos < 600:
            return max(1, round(mos))

    # 4. Weeks
    wk_match = re.search(r'\b(\d+)\s*(?:weeks?|wks?\.?)\b', clean, re.IGNORECASE)
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

    # 6. Word-number durations fallback
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


_ROMAN_MONTH_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
}


def _parse_single_date(d_str: str, is_end: bool = False, prefer_day_first: bool = False) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Parse string like 'June 2023', '15 June 2020', '06/2023', 'Jan \'20', 'Early 2021', 'Summer 2022', 'Q2 2023', 'VI/2020', '2023'."""
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

    # Approximate qualifiers: Early / Mid / Late YYYY
    approx_m = re.search(rf'\b({_APPROX_QUAL_RE})[\s\-]+({_YEAR_RE})\b', d_clean, re.IGNORECASE)
    if approx_m:
        qual = approx_m.group(1).lower()
        yr = int(approx_m.group(2))
        m_num = 2 if qual == "early" else (6 if qual == "mid" else 10)
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # Season: Spring/Summer/Fall/Autumn/Winter YYYY
    season_m = re.search(rf'\b(Spring|Summer|Fall|Autumn|Winter)\s+({_YEAR_RE})\b', d_clean, re.IGNORECASE)
    if season_m:
        s_name = season_m.group(1).lower()
        yr = int(season_m.group(2))
        if s_name == "spring":
            m_num = 5 if is_end else 3
        elif s_name == "summer":
            m_num = 8 if is_end else 6
        elif s_name in ("fall", "autumn"):
            m_num = 11 if is_end else 9
        else:
            if is_end:
                m_num = 2
                yr += 1
            else:
                m_num = 12
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "DD[-/ ]Month[.] [,] YYYY"
    dmy_word = re.search(
        rf'\b{_ORDINAL_DAY_RE}(?:[-/\s]+|\s+of\s+)({_MONTHS_NAMES})\.?[-/,\s]+({_YEAR_RE})\b',
        d_clean,
        re.IGNORECASE,
    )
    if dmy_word:
        m_num = _month_name_to_num(dmy_word.group(1))
        yr = int(dmy_word.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "Month[.] [DD,] YYYY" and glued "Jan2020"
    m_match = re.search(
        rf'\b({_MONTHS_NAMES})\.?(?:\s+{_ORDINAL_DAY_RE}\s*,?)?\s*(?:[,. /-]\s*)?({_YEAR_RE})\b',
        d_clean,
        re.IGNORECASE,
    )
    if m_match:
        m_num = _month_name_to_num(m_match.group(1))
        yr = int(m_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "YYYY Month"
    ym_word = re.search(rf'\b({_YEAR_RE})\s*[-/\s]\s*({_MONTHS_NAMES})\.?\b', d_clean, re.IGNORECASE)
    if ym_word:
        yr = int(ym_word.group(1))
        m_num = _month_name_to_num(ym_word.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # "Month 'YY" or "Month YY"
    m_short_y = re.search(rf'\b({_MONTHS_NAMES})\.?\s*[\'’]?({_SHORT_YEAR_RE})\b', d_clean, re.IGNORECASE)
    if m_short_y:
        m_num = _month_name_to_num(m_short_y.group(1))
        yr = _expand_short_year(int(m_short_y.group(2)))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # Roman numeral month: VI/2020, XII.2023 (strictly uppercase)
    roman_match = re.search(rf'\b(XII|XI|IX|X|VIII|VII|VI|IV|V|III|II|I)[./-]({_YEAR_RE})\b', d_clean)
    if roman_match and roman_match.group(1) in _ROMAN_MONTH_MAP:
        m_num = _ROMAN_MONTH_MAP[roman_match.group(1)]
        yr = int(roman_match.group(2))
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

    # MM/DD/YY or DD/MM/YY (slash, hyphen, or dot)
    mdy_short_match = re.search(rf'\b(\d{{1,2}})[./-](\d{{1,2}})[./-]({_SHORT_YEAR_RE})\b', d_clean)
    if mdy_short_match:
        p1, p2, yr2 = int(mdy_short_match.group(1)), int(mdy_short_match.group(2)), int(mdy_short_match.group(3))
        yr = _expand_short_year(yr2)
        if p1 > 12 and 1 <= p2 <= 12:
            m_num = p2
        elif prefer_day_first and 1 <= p2 <= 12:
            m_num = p2
        elif 1 <= p1 <= 12:
            m_num = p1
        else:
            m_num = max(1, min(12, p2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # MM / YYYY, MM-YYYY, MM.YYYY
    slash_match = re.search(r'\b(0?[1-9]|1[0-2])(?:\s*/\s*|[./-])(\d{4})\b', d_clean)
    if slash_match:
        m_num = max(1, min(12, int(slash_match.group(1))))
        yr = int(slash_match.group(2))
        return f"{yr:04d}-{m_num:02d}", yr, m_num

    # MM/YY, MM-YY, MM.YY
    short_slash = re.search(rf'\b(0?[1-9]|1[0-2])(?:\s*/\s*|[./-])({_SHORT_YEAR_RE})\b', d_clean)
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

    # Fallback to dateparser (strictly requiring year part, multilingual EN/TL/ES)
    if dateparser is not None and re.search(_YEAR_RE, d_clean):
        try:
            parsed = dateparser.parse(d_clean, languages=['en', 'tl', 'es'], settings={'REQUIRE_PARTS': ['year']})
            if parsed and 1950 <= parsed.year <= datetime.now().year + 2:
                return f"{parsed.year:04d}-{parsed.month:02d}", parsed.year, parsed.month
        except Exception:
            pass

    return None, None, None


def _parse_date_and_duration(text: str) -> Tuple[Optional[str], Optional[str], int, str]:
    """
    Extracts start_date (YYYY-MM), end_date (YYYY-MM | Present), duration_months, and extra status string.
    """
    raw_text = text or ""
    match = _DATE_RANGE_REGEX.search(raw_text)
    now = datetime.now()
    now_ym = (now.year, now.month)

    # Validate yr_short_s/e match so standalone ISO YYYY-MM (e.g. "2020-06") is never misread as 2020-2006
    if match and match.groupdict().get("yr_short_s"):
        s_yr_chk = int(match.group("yr_short_s"))
        ey_chk = int(match.group("yr_short_e"))
        has_ws = bool(re.search(r'\s', match.group(0)))
        if not has_ws and 1 <= ey_chk <= 12 and (s_yr_chk % 100) >= ey_chk:
            match = None
        elif not has_ws and 1 <= ey_chk <= 12 and ey_chk <= 12:
            # e.g. "2010-12" without spaces is ambiguous with ISO YYYY-MM; reject unless spaces present
            match = None

    # Validate myr_short_s/e ("Jan 2020 - 23")
    if match and match.groupdict().get("myr_short_s"):
        _, s_yr_chk, _ = _parse_single_date(match.group("myr_short_s"), is_end=False)
        ey2 = int(match.group("myr_short_e"))
        if s_yr_chk:
            e_yr_chk = (s_yr_chk // 100) * 100 + ey2
            if e_yr_chk < s_yr_chk and (s_yr_chk % 100) >= 80 and ey2 <= 30:
                e_yr_chk += 100
            if e_yr_chk <= s_yr_chk or (1 <= ey2 <= 12 and ey2 <= (s_yr_chk % 100)):
                match = None

    # Validate no-apostrophe Mon YY ranges ("Jan 20 - Dec 23", "Jun 21 - Present")
    if match and match.groupdict().get("my_short_s"):
        ms_s = match.group("my_short_s").strip()
        ms_e = match.group("my_short_e").strip()
        m1 = re.search(rf'({_MONTHS_NAMES})\.?\s+(\d{{2}})', ms_s, re.I)
        if not m1:
            match = None
        else:
            s_mo_chk = _month_name_to_num(m1.group(1))
            sy2 = int(m1.group(2))
            cur_yy = now.year % 100
            if re.match(rf'^{_PRESENT_RE}$', ms_e, re.I):
                if not (80 <= sy2 <= 99 or 10 <= sy2 <= cur_yy + 1):
                    match = None
            else:
                m2 = re.search(rf'({_MONTHS_NAMES})\.?\s+(\d{{2}})', ms_e, re.I)
                if not m2:
                    match = None
                else:
                    e_mo_chk = _month_name_to_num(m2.group(1))
                    ey2 = int(m2.group(2))
                    s_yr_exp = _expand_short_year(sy2)
                    e_yr_exp = _expand_short_year(ey2)
                    if e_yr_exp <= s_yr_exp or (s_mo_chk == e_mo_chk and 1 <= sy2 <= 31 and 1 <= ey2 <= 31):
                        match = None

    if not match:
        clean_t = raw_text.strip()
        # Standalone season (e.g. "Summer 2022") -> 3 months
        season_only = re.search(rf'\b({_SEASON_RE}\s+{_YEAR_RE})\b', clean_t, re.IGNORECASE)
        if season_only:
            s_iso, s_yr, s_mo = _parse_single_date(season_only.group(1), is_end=False)
            e_iso, e_yr, e_mo = _parse_single_date(season_only.group(1), is_end=True)
            if s_yr and e_yr and s_mo and e_mo:
                if (s_yr, s_mo) > now_ym:
                    return s_iso, e_iso, 0, ""
                if (e_yr, e_mo) > now_ym:
                    e_yr, e_mo = now.year, now.month
                    e_iso = f"{e_yr:04d}-{e_mo:02d}"
                dur = max(1, (e_yr - s_yr) * 12 + (e_mo - s_mo) + 1)
                extra = (clean_t[:season_only.start()] + " " + clean_t[season_only.end():]).strip()
                return s_iso, e_iso, dur, extra

        # Standalone quarter (e.g. "Q1 2022") -> 3 months
        quarter_only = re.search(rf'\b((?:Q[1-4]|[1-4](?:st|nd|rd|th)\s+Quarter)\s*{_YEAR_RE})\b', clean_t, re.IGNORECASE)
        if quarter_only:
            s_iso, s_yr, s_mo = _parse_single_date(quarter_only.group(1), is_end=False)
            e_iso, e_yr, e_mo = _parse_single_date(quarter_only.group(1), is_end=True)
            if s_yr and e_yr and s_mo and e_mo:
                if (s_yr, s_mo) > now_ym:
                    return s_iso, e_iso, 0, ""
                if (e_yr, e_mo) > now_ym:
                    e_yr, e_mo = now.year, now.month
                    e_iso = f"{e_yr:04d}-{e_mo:02d}"
                dur = max(1, (e_yr - s_yr) * 12 + (e_mo - s_mo) + 1)
                extra = (clean_t[:quarter_only.start()] + " " + clean_t[quarter_only.end():]).strip()
                return s_iso, e_iso, dur, extra

        dur_only = _parse_duration_text(clean_t)
        if dur_only > 0:
            # Check single date + explicit duration (e.g., "2022 (6 months)", "June 2023 (486 hours)")
            date_part = re.sub(r'\([^)]*\)', '', clean_t).strip()
            has_single_date = bool(
                re.search(rf'\b(?:{_MONTHS_NAMES}\.?\s*[,.]?\s*{_YEAR_RE}|{_YEAR_RE})\b', date_part, re.I)
            )
            if has_single_date:
                s_iso, s_yr, s_mo = _parse_single_date(date_part, is_end=False)
                if s_iso and s_yr and s_mo:
                    s_idx = s_yr * 12 + (s_mo - 1)
                    now_idx = now.year * 12 + (now.month - 1)
                    if s_idx > now_idx:
                        return s_iso, s_iso, 0, ""
                    e_idx = min(now_idx, s_idx + dur_only - 1)
                    e_yr, e_mo = e_idx // 12, (e_idx % 12) + 1
                    e_iso = f"{e_yr:04d}-{e_mo:02d}"
                    eff_dur = max(1, e_idx - s_idx + 1)
                    return s_iso, e_iso, eff_dur, clean_t
            if _STANDALONE_DATE_OR_DUR_RE.match(clean_t) or _INLINE_DURATION_OR_YEAR_RE.search(clean_t):
                return None, None, dur_only, clean_t
        if _STANDALONE_DATE_OR_DUR_RE.match(clean_t):
            iso, _, _ = _parse_single_date(clean_t)
            if iso:
                return iso, iso, 0, ""
        return None, None, 0, ""

    gd = match.groupdict()
    is_yr_short = False
    if gd.get("open_start") or gd.get("trail_start"):
        raw_start = (gd.get("open_start") or gd.get("trail_start") or "").strip()
        raw_end = "Present"
    elif gd.get("sm_start") and gd.get("sm_end"):
        raw_start = gd["sm_start"].strip()
        raw_end = gd["sm_end"].strip()
    elif gd.get("my_short_s") and gd.get("my_short_e"):
        raw_start = gd["my_short_s"].strip()
        raw_end = gd["my_short_e"].strip()
    elif gd.get("btw_start") and gd.get("btw_end"):
        raw_start = gd["btw_start"].strip()
        raw_end = gd["btw_end"].strip()
    elif gd.get("myr_short_s") and gd.get("myr_short_e"):
        raw_start = gd["myr_short_s"].strip()
        _, s_yr_tmp, _ = _parse_single_date(raw_start, is_end=False)
        ey_2 = int(gd["myr_short_e"])
        e_yr_full = ((s_yr_tmp or 2000) // 100) * 100 + ey_2
        if s_yr_tmp and e_yr_full < s_yr_tmp and (s_yr_tmp % 100) >= 80 and ey_2 <= 30:
            e_yr_full += 100
        raw_end = f"{e_yr_full:04d}"
    elif gd.get("yr_short_s") and gd.get("yr_short_e"):
        raw_start = gd["yr_short_s"].strip()
        s_yr_tmp = int(raw_start)
        ey_2 = int(gd["yr_short_e"])
        e_yr_full = (s_yr_tmp // 100) * 100 + ey_2
        if e_yr_full < s_yr_tmp and (s_yr_tmp % 100) >= 80 and ey_2 <= 30:
            e_yr_full += 100
        raw_end = f"{e_yr_full:04d}"
        is_yr_short = True
    else:
        raw_start = (gd.get("start") or "").strip()
        raw_end = (gd.get("end") or "").strip()

    # Detect unambiguous DD/MM/YYYY or DD/MM/YY in either endpoint so the partner endpoint parses consistently
    prefer_day_first = False
    for ep in (raw_start, raw_end):
        dmy_check = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](?:\d{4}|\d{2})\b', ep)
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

    # Clamp future dates to current month/year so future years are never counted as earned experience
    if end_iso != "Present" and e_yr and e_mo and (e_yr, e_mo) > now_ym:
        if s_yr and s_mo and (s_yr, s_mo) > now_ym:
            return start_iso, end_iso, 0, ""
        e_yr, e_mo = now.year, now.month
        end_iso = f"{e_yr:04d}-{e_mo:02d}"

    duration = 0
    if s_yr and s_mo:
        if end_iso == "Present" or not e_yr:
            target_yr, target_mo = now.year, now.month
            if (s_yr, s_mo) <= (target_yr, target_mo):
                duration = max(1, (target_yr - s_yr) * 12 + (target_mo - s_mo) + 1)
        elif e_yr and e_mo:
            duration = max(1, (e_yr - s_yr) * 12 + (e_mo - s_mo) + 1)

    # Check if hours mentioned (e.g. 486 Hours) when calendar duration is zero
    hrs_match = _HOURS_REGEX.search(raw_text)
    if hrs_match and duration == 0:
        hrs = int(hrs_match.group(1))
        duration = max(1, round(hrs / 160.0))

    # Extra text (status info outside date range)
    extra_text = raw_text[:match.start()] + " " + raw_text[match.end():]
    extra_text = re.sub(r'[\s\-–—()|·]+', ' ', extra_text).strip()

    # Honor explicit year/month duration annotations on year-only ranges like "2020 - 2024 (4 years)"
    if (re.fullmatch(r'\d{4}', raw_start.strip()) and (re.fullmatch(r'\d{4}', raw_end.strip()) or is_yr_short)) and extra_text:
        explicit_dur = _parse_duration_text(extra_text)
        if 0 < explicit_dur < 600:
            duration = explicit_dur

    if duration > 600:
        duration = 0

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
    "career progression", "sea service", "research experience", "service record",
    "karanasan sa trabaho", "experience summary", "employment record",
    "education", "educational background", "academic background", "qualifications",
    "skills", "technical skills", "core competencies", "certifications", "licenses",
    "licenses and eligibility", "trainings", "seminars", "projects", "references",
    "character references", "personal information", "contact information",
    "summary", "professional summary", "career objective", "objective"
}


_ADDRESS_PATTERNS = re.compile(
    r'\b(?:Avenue|Ave\.?|Street|Barangay|Brgy\.?|Subdivision|Subd\.?|Boulevard|Blvd\.?|Road|Rd\.?|Highway|Hwy\.?|Bldg\.?|Building|Block|Blk\.?|Lot|Compound|Phase|Sitio|Purok)\b|'
    r'(?:(?<=\d)|(?<=[A-Za-z]))\s+St\.?\b',
    re.IGNORECASE
)

_KV_PREFIX_ROLE_RE = re.compile(r'^(?:position(?:\s+title)?|job\s*title|role|designation|occupation|post)\s*[:\-–]\s*', re.IGNORECASE)
_KV_PREFIX_COMP_RE = re.compile(r'^(?:company(?:\s+name)?|employer(?:\s+name)?|organization|firm|agency|establishment|workplace)\s*[:\-–]\s*', re.IGNORECASE)
_KV_PREFIX_DATE_RE = re.compile(r'^(?:inclusive\s+dates?|dates?\s*(?:of\s+employment)?|period|duration|employment\s+dates?|tenure|years?)\s*[:\-–]\s*', re.IGNORECASE)
_KV_PREFIX_LOC_RE = re.compile(r'^(?:location|address|work\s+location|branch|site|place\s+of\s+work)\s*[:\-–]\s*', re.IGNORECASE)

_PURE_EMP_ONLY_RE = re.compile(
    r'^(?:full[\s\-]?time|part[\s\-]?time|regular|permanent|contract(?:ual)?|temporary|seasonal|'
    r'freelance(?:r)?|self[\s\-]?employed|outsourced|project[\s\-]?based|job\s+order|contract\s+of\s+service|'
    r'cos|casual|coterminous|ojt|intern(?:ship)?|practicum|endo|end\s+of\s+contract|reliever)$',
    re.IGNORECASE,
)

_PURE_METADATA_SEG_RE = re.compile(
    r'^(?:full[\s\-]?time|part[\s\-]?time|regular|permanent|contract(?:ual)?|temporary|seasonal|'
    r'freelance(?:r)?|self[\s\-]?employed|outsourced|project[\s\-]?based|job\s+order|contract\s+of\s+service|'
    r'cos|casual|coterminous|probationary|endo|end\s+of\s+contract|reliever|'
    r'ojt|internship|practicum|remote|hybrid|on[\s\-]?site|onsite|wfh|work\s+from\s+home|'
    r'\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?|months?|mos?|weeks?|wks?|hours?|hrs?)'
    r'(?:\s*(?:and|,|&)?\s*\d+(?:\.\d+)?\s*(?:months?|mos?))?|\d+(?:\.\d+)?\s*y\s*\+?(?:\s*\d+(?:\.\d+)?\s*m)?)$',
    re.IGNORECASE,
)


def _is_pure_metadata_seg(text: str) -> bool:
    """Return True if segment (optionally wrapped in parens/brackets) is purely employment/duration metadata."""
    if not text:
        return False
    s = text.strip()
    if (s.startswith("(") and s.endswith(")")) or (s.startswith("[") and s.endswith("]")):
        s = s[1:-1].strip()
    return bool(s and _PURE_METADATA_SEG_RE.match(s))

_PDS_NOISE_SEG_RE = re.compile(
    r'^(?:(?:₱|PHP|Php|P)?\s*\d{1,3}(?:,\d{3})+(?:\.\d{2})?|(?:SG|Salary\s+Grade)[\s\-:]?\d{1,2}(?:[-/]\d)?|\d{2}[-/]\d|[YN]|Yes|No)$',
    re.IGNORECASE,
)


def _is_pds_noise_segment(text: str) -> bool:
    if not text:
        return False
    return bool(_PDS_NOISE_SEG_RE.match(text.strip()))


def _strip_kv_prefix(text: str) -> Tuple[str, Optional[str]]:
    """Strip common Biodata/CV key-value field labels and return (clean_value, kind)."""
    if not text:
        return "", None
    s = text.strip()
    for rx, kind in (
        (_KV_PREFIX_ROLE_RE, "ROLE"),
        (_KV_PREFIX_COMP_RE, "COMPANY"),
        (_KV_PREFIX_DATE_RE, "DATE"),
        (_KV_PREFIX_LOC_RE, "LOCATION"),
    ):
        m = rx.match(s)
        if m:
            return s[m.end():].strip(), kind
    return s, None


def _strip_linkedin_metadata(text: str) -> Tuple[str, str]:
    """
    Remove LinkedIn-style middle-dot metadata segments (e.g. '· Full-time', '· Hybrid', '· 2 yrs 3 mos')
    while preserving them in the second return element for employment-type detection.
    """
    if not text:
        return "", ""
    if '·' not in text:
        clean = text.strip()
        if _is_pure_metadata_seg(clean):
            return "", clean
        return clean, ""
    parts = [p.strip() for p in text.split('·')]
    kept = []
    meta = []
    for p in parts:
        if not p:
            continue
        if _is_pure_metadata_seg(p):
            meta.append(p)
        else:
            kept.append(p)
    return " · ".join(kept).strip(), " ".join(meta).strip()


def _is_address_or_location(text: str) -> bool:
    """Detect if text is an address or location rather than job title or company."""
    if not text:
        return False
    clean, kv_kind = _strip_kv_prefix(text)
    if kv_kind == "LOCATION":
        return True
    clean, _ = _strip_linkedin_metadata(clean)
    if not clean:
        return False
    lower = clean.lower().strip()
    if lower in ("philippines", "metro manila", "ncr", "remote", "hybrid", "on-site", "onsite", "wfh", "work from home"):
        return True
    if _has_job_signals(clean) or _has_company_signals(clean):
        return False
    if _ADDRESS_PATTERNS.search(clean):
        return True
    if lower in _ALL_LOCATIONS_SET or re.fullmatch(r'car', clean.strip()):
        return True
    if ',' in lower:
        parts = [p.strip() for p in lower.split(',') if p.strip()]
        if parts and any(
            any(loc == p or p == f"{loc} city" for loc in _ALL_LOCATIONS_SET)
            for p in parts
        ):
            loc_hits = sum(
                1 for p in parts
                if any(loc == p or p == f"{loc} city" for loc in _ALL_LOCATIONS_SET)
                or bool(_ALL_LOCATIONS_RE.search(p))
                or bool(_ADDRESS_PATTERNS.search(p))
            )
            first_is_loc = (
                parts[0] in _ALL_LOCATIONS_SET
                or bool(_ADDRESS_PATTERNS.search(parts[0]))
                or any(parts[0] == f"{loc} city" for loc in _ALL_LOCATIONS_SET)
            )
            if first_is_loc or (len(parts) >= 3 and loc_hits >= 2):
                return True
    return False


_PRESERVE_UPPER_TOKENS = {
    "IT", "HR", "QA", "QC", "UI", "UX", "CNC", "BOSH", "COSH", "HSE", "OSH",
    "CI", "CD", "API", "SQL", "PHP", "AWS", "GCP", "SAP", "ERP", "CRM", "POS",
    "CSR", "TSR", "VA", "OJT", "BPO", "LPT", "CPA", "ECE", "RN", "MD", "RCE",
    "RMP", "RME", "REE", "OIC", "SME", "RTA", "WFM", "CEO", "CTO", "CFO", "COO",
    "VP", "AVP", "SVP", "EVP", "GM", "PM", "BA", "BI", "AI", "ML", "DL", "NLP",
    "SRE", "DBA", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "CAD", "BIM", "PLC", "HVAC", "LED", "CCTV", "ATM", "LTO", "PRC", "TESDA",
    "DOLE", "ISO", "R&D", "F&B",
}
_PRESERVE_LOWER_WORDS = {"of", "and", "or", "in", "on", "at", "to", "for", "with", "by", "the", "a", "an"}
_SPECIAL_CASE_TOKENS = {
    "ios": "iOS", "nodejs": "Node.js", "node.js": "Node.js", ".net": ".NET",
    "c#": "C#", "c++": "C++", "devops": "DevOps", "devsecops": "DevSecOps",
    "mlops": "MLOps", "aiops": "AIOps", "sysadmin": "SysAdmin",
    "medtech": "MedTech", "radtech": "RadTech",
}


def _smart_title_case_token(tok: str, is_first: bool = False) -> str:
    if not tok:
        return ""
    low = tok.lower()
    if low in _SPECIAL_CASE_TOKENS:
        return _SPECIAL_CASE_TOKENS[low]
    up = tok.upper()
    if up in _PRESERVE_UPPER_TOKENS:
        return up
    if '/' in tok:
        sub_parts = [p.strip() for p in tok.split('/')]
        norm_subs = [_smart_title_case_token(sp, is_first=True) for sp in sub_parts]
        if all(len(sp) <= 3 or sp.upper() in _PRESERVE_UPPER_TOKENS for sp in sub_parts):
            return "/".join(norm_subs)
        return " / ".join(norm_subs)
    if '-' in tok:
        return "-".join(_smart_title_case_token(hp, is_first=True) for hp in tok.split('-'))
    if not is_first and low in _PRESERVE_LOWER_WORDS:
        return low
    return tok[:1].upper() + tok[1:].lower()


def _smart_title_case(text: str) -> str:
    words = text.split()
    return " ".join(_smart_title_case_token(w, is_first=(idx == 0)) for idx, w in enumerate(words))


def _normalize_job_title(raw_title: str) -> str:
    """
    Normalizes raw job title to clean, standardized title string:
    - Strips noisy annotations like (OJT), (Kitchen / Grill), (Full-time), etc.
    - Strips leading/trailing symbols, bullets, or separators.
    - Normalizes casing to Title Case while preserving acronyms & compact slashes.
    - Standardizes known abbreviations where appropriate (e.g., CSR -> Customer Service Representative).
    """
    if not raw_title:
        return ""

    clean, kv_kind = _strip_kv_prefix(raw_title)
    if kv_kind in ("COMPANY", "LOCATION", "DATE"):
        return ""
    clean, _ = _strip_linkedin_metadata(clean)
    clean = re.sub(r'\s*\([^)]*\)', '', clean).strip()
    clean = re.sub(r'\s*\|\s*.*$', '', clean).strip()
    clean = re.sub(r'^(?:\(?\d{1,2}\)?[\.\)]\s+|[•\-\*▪►✓\s:·]+)|[•\-\*▪►✓\s:·]+$', '', clean).strip()

    if not clean or _PURE_METADATA_SEG_RE.match(clean) or _is_pds_noise_segment(clean):
        return ""

    clean_low = clean.lower()
    if clean_low in _RESUME_SECTION_HEADERS or (
        any(clean_low.startswith(h + ":") for h in _RESUME_SECTION_HEADERS)
        and not _JOB_TITLE_KEYWORDS_RE.search(clean)
    ):
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
        compact_slash = all(len(p) <= 3 or p.upper() in _PRESERVE_UPPER_TOKENS for p in parts)
        if compact_slash and ' ' not in clean:
            norm_parts = [_smart_title_case_token(p, is_first=True) for p in parts]
            return "/".join(norm_parts)
        norm_parts = []
        for p in parts:
            if p.upper() in acronym_map:
                norm_parts.append(acronym_map[p.upper()])
            elif p.isupper() or p.islower():
                norm_parts.append(_smart_title_case(p))
            else:
                norm_parts.append(p)
        dedup = []
        for np in norm_parts:
            if np not in dedup:
                dedup.append(np)
        return " / ".join(dedup)

    if clean.isupper() or clean.islower():
        return _smart_title_case(clean)

    # If already a concise role title (<= 6 words with a recognized job keyword), preserve full title
    if len(clean.split()) <= 6 and _JOB_TITLE_KEYWORDS_RE.search(clean):
        return clean

    # Check spaCy POS / entity fallback for longer or out-of-vocabulary strings
    spacy_cand = _extract_title_with_spacy(clean)
    if spacy_cand:
        return _smart_title_case(spacy_cand) if (spacy_cand.isupper() or spacy_cand.islower()) else spacy_cand

    return clean


def _split_company_and_location(raw_text: str) -> Tuple[str, Optional[str]]:
    """
    Splits company string into (company_name, location).
    """
    clean, kv_kind = _strip_kv_prefix(raw_text.strip())
    if kv_kind == "LOCATION":
        return "", clean or None
    clean, _ = _strip_linkedin_metadata(clean)
    # Strip parenthetical agency remarks from company name
    clean = re.sub(r'\(via\s+[^)]+\)', '', clean, flags=re.IGNORECASE).strip()
    if not clean or _is_pure_metadata_seg(clean) or _is_pds_noise_segment(clean):
        return "", None
    if clean.islower():
        clean = _smart_title_case(clean)

    def _clean_loc(loc_val: Optional[str]) -> Optional[str]:
        if not loc_val:
            return None
        lv = loc_val.strip(' ,-–—|')
        if not lv or _PURE_EMP_ONLY_RE.match(lv) or _is_pure_metadata_seg(lv) or _is_pds_noise_segment(lv):
            return None
        return lv

    # Case 0: Trailing parenthetical location e.g. 'Rizal Packaging & Industrial Solutions Inc. (Taytay, Rizal)'
    paren_loc_m = re.search(r'^(.+?)\s*\(([^()]+)\)\s*$', clean)
    if paren_loc_m:
        base_comp = paren_loc_m.group(1).strip(' ,-–—|')
        inside_paren = paren_loc_m.group(2).strip()
        if _ALL_LOCATIONS_RE.search(inside_paren) or _is_address_or_location(inside_paren):
            return base_comp, _clean_loc(inside_paren)

    # Case 1: Pipe separator 'Accenture Philippines | BGC, Taguig City'
    if '|' in clean:
        parts = [p.strip() for p in clean.split('|', 1)]
        return parts[0], _clean_loc(parts[1]) if len(parts) > 1 and parts[1] else None

    # Case 2: Dash separator 'Chowking - SM City Taytay' or 'Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna'
    if ' - ' in clean or ' – ' in clean or ' — ' in clean:
        parts = re.split(r'\s+[-–—]\s+', clean, maxsplit=1)
        comp = parts[0].strip()
        loc = _clean_loc(parts[1]) if len(parts) > 1 else None
        return comp, loc

    # Case 3: Comma separator outside parentheses 'XYZ Tech Solutions Inc., Makati City'
    comma_parts = re.split(r',(?![^()]*\))', clean, maxsplit=1)
    if len(comma_parts) == 2:
        first = comma_parts[0].strip()
        rest = comma_parts[1].strip()
        if _COMPANY_LEGAL_SUFFIXES_RE.search(first) or _PHIL_COMPANY_NAMES_RE.search(first):
            return first, _clean_loc(rest)
        if _ALL_LOCATIONS_RE.search(rest) or _is_address_or_location(rest):
            return first, _clean_loc(rest)

    # Case 4: No separator, check if location is trailing (never break 'Municipality of X', 'University of Manila', '<Company> Philippines')
    for loc in sorted(_PHIL_LOCATIONS_SET, key=len, reverse=True):
        if clean.lower().endswith(loc) and (len(clean) == len(loc) or clean[-len(loc) - 1] in " \t"):
            idx = clean.lower().rfind(loc)
            comp = clean[:idx].strip(' ,-–—')
            found_loc = clean[idx:].strip(' ,-–—')
            if comp and not comp.lower().endswith(("of", "the", "in", "at", "de", "del", "san", "sta", "sta.", "santo", "new")):
                return comp, _clean_loc(found_loc)

    return clean, None


def _has_company_signals(text: str) -> bool:
    if not text:
        return False
    if _COMPANY_LEGAL_SUFFIXES_RE.search(text) or _COMPANY_PLACE_WORDS_RE.search(text):
        return True
    if _PHIL_COMPANY_NAMES_RE.search(text):
        return True
    return False


def _has_strong_company_signals(text: str) -> bool:
    """Return True when text contains unambiguous legal/entity/known-company signals (not mere industry nouns)."""
    if not text:
        return False
    return bool(
        _STRICT_LEGAL_SUFFIXES_RE.search(text)
        or _COMPANY_PLACE_WORDS_RE.search(text)
        or _PHIL_COMPANY_NAMES_RE.search(text)
    )


def _has_job_signals(text: str) -> bool:
    if not text:
        return False
    if _JOB_TITLE_KEYWORDS_RE.search(text):
        return True
    if _KEYWORD_PROCESSOR and _KEYWORD_PROCESSOR.extract_keywords(text):
        return True
    return bool(_TAXONOMY_TITLES_RE.search(text))


def _extract_title_company_location(title_cand: str, comp_cand: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Decouples raw title, company, and location strings even when written on the same line,
    swapped, or combined (e.g. 'Food Panda Delivery Rider', 'Delivery Rider at Food Panda').
    Returns (job_title, company_name, location).
    """
    title_cand = title_cand.strip() if title_cand else ""
    comp_cand = comp_cand.strip() if comp_cand else ""

    # Strip leading bullet/list markers before splitting so bullets never leak into company/title
    title_cand = re.sub(r'^(?:\(?\d{1,2}\)?[\.\)]\s+|[•\-\*▪►✓]+\s+)', '', title_cand).strip()
    comp_cand = re.sub(r'^(?:\(?\d{1,2}\)?[\.\)]\s+|[•\-\*▪►✓]+\s+)', '', comp_cand).strip()

    title_cand, kv_title_kind = _strip_kv_prefix(title_cand)
    comp_cand, kv_comp_kind = _strip_kv_prefix(comp_cand)
    title_cand, _ = _strip_linkedin_metadata(title_cand)
    comp_cand, _ = _strip_linkedin_metadata(comp_cand)

    if kv_title_kind == "COMPANY" and kv_comp_kind == "ROLE":
        title_cand, comp_cand = comp_cand, title_cand
    elif kv_title_kind == "COMPANY" and not comp_cand:
        comp_cand = title_cand
        title_cand = ""

    if _is_likely_responsibility_or_sentence(title_cand):
        return "", "", None

    if comp_cand and (_is_likely_responsibility_or_sentence(comp_cand) or _DATE_RANGE_REGEX.search(comp_cand) or _is_pure_metadata_seg(comp_cand) or _is_pds_noise_segment(comp_cand)):
        comp_cand = ""

    # Check if comp_cand is actually an address or country/location
    loc_override = None
    if comp_cand and (kv_comp_kind == "LOCATION" or _is_address_or_location(comp_cand) or comp_cand.lower() in ("philippines", "metro manila", "ncr", "remote", "hybrid", "on-site", "onsite")):
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
    if comp_cand and kv_title_kind != "ROLE":
        title_has_comp_signals = _has_strong_company_signals(title_cand) or (
            _has_company_signals(title_cand) and not _has_job_signals(title_cand)
        )
        comp_has_comp_signals = _has_strong_company_signals(comp_cand) or (
            _has_company_signals(comp_cand) and not _has_job_signals(comp_cand)
        )

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

    # 2. Check ' - ' or ' – ' or ' — ' (including multi-dash 'Title - Company - Location' or 'Company - Location - Title')
    if re.search(r'\s+[-–—]\s+', title_cand):
        dash_parts = [p.strip() for p in re.split(r'\s+[-–—]\s+', title_cand) if p.strip()]
        if len(dash_parts) >= 3:
            if _has_job_signals(dash_parts[0]) and not _has_strong_company_signals(dash_parts[0]):
                comp, loc = _split_company_and_location(" - ".join(dash_parts[1:]))
                return _normalize_job_title(dash_parts[0]), comp, loc or loc_override
            if _has_job_signals(dash_parts[-1]) and not _has_strong_company_signals(dash_parts[-1]):
                comp, loc = _split_company_and_location(" - ".join(dash_parts[:-1]))
                return _normalize_job_title(dash_parts[-1]), comp, loc or loc_override
        parts = re.split(r'\s+[-–—]\s+', title_cand, maxsplit=1)
        p1, p2 = parts[0].strip(), parts[1].strip()
        p1_job = _has_job_signals(p1)
        p2_job = _has_job_signals(p2)
        p1_comp = _has_strong_company_signals(p1) or _spacy_looks_like_org(p1) or (_has_company_signals(p1) and not p1_job)
        p2_comp = _has_strong_company_signals(p2) or _spacy_looks_like_org(p2) or (_has_company_signals(p2) and not p2_job)
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
            seg1_job = _has_job_signals(seg1)
            seg1_comp = _has_strong_company_signals(seg1) or _spacy_looks_like_org(seg1) or (_has_company_signals(seg1) and not seg1_job)
            seg0_comp = _has_strong_company_signals(seg0) or _spacy_looks_like_org(seg0) or (_has_company_signals(seg0) and not seg0_job)
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
        sorted_tax_titles = sorted(all_taxonomy_titles, key=len, reverse=True)
        for tax_title in sorted_tax_titles:
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
                            or bool(_PHIL_COMPANY_NAMES_RE.fullmatch(prefix))
                        )
                    ):
                        comp, loc = _split_company_and_location(prefix)
                        return _normalize_job_title(tax_title), comp, loc or loc_override

        # 4b. Check known job taxonomy prefix followed by company suffix/ORG (e.g. 'Production Operator Acme Plastic Moulding Corp.')
        for tax_title in sorted_tax_titles:
            tax_low = tax_title.lower()
            t_low = title_cand.lower()
            if t_low.startswith(tax_low) and len(title_cand) > len(tax_title):
                boundary_char = title_cand[len(tax_title):len(tax_title)+1]
                if boundary_char in " \t-–—|,":
                    rem = title_cand[len(tax_title):].strip(" \t-–—|,")
                    if (
                        len(rem) >= 3
                        and not _is_address_or_location(rem)
                        and not _JOB_TITLE_KEYWORDS_RE.search(rem)
                        and (_has_strong_company_signals(rem) or _spacy_looks_like_org(rem))
                    ):
                        comp, loc = _split_company_and_location(rem)
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


_NESTED_EXP_SUBHEADINGS = {
    "KEY ACHIEVEMENTS", "ACHIEVEMENTS", "ACCOMPLISHMENTS", "NOTABLE ACHIEVEMENTS",
    "KEY PROJECTS", "SELECTED PROJECTS", "NOTABLE PROJECTS",
    "KEY RESPONSIBILITIES", "CORE RESPONSIBILITIES", "DUTIES & RESPONSIBILITIES",
    "ROLE SUMMARY", "TOOLS USED", "TECH STACK", "TECHNOLOGIES USED",
}


def _extract_experience_blocks_with_mode(text: str) -> Tuple[List[str], str]:
    """
    Extracts all sections corresponding to Work Experience and OJT/Internship,
    along with extraction mode: 'explicit', 'sectionless', 'unlabeled_rescue', or 'none'.
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
        "WHERE I'VE WORKED", "WHERE I HAVE WORKED", "PROFESSIONAL JOURNEY", "CAREER JOURNEY",
        "MY EXPERIENCE", "MY WORK EXPERIENCE", "GOVERNMENT SERVICE",
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
            for delim in (':', '|'):
                d_idx = line.find(delim)
                if d_idx > 0:
                    prefix_hdr = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', line[:d_idx]).upper()
                    prefix_no_num = re.sub(r'^(?:\(?(?:\d{1,2}|[IVXLC]{1,4})\)?[\.\)\-:]\s+)', '', prefix_hdr).strip()
                    if (
                        prefix_hdr in exp_headers
                        or prefix_no_num in exp_headers
                        or detect_section_label(line[:d_idx]) == "EXPERIENCE"
                    ):
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
            # Guard against nested job subheadings ("Key Achievements", "Selected Projects", "Training:", etc.)
            # inside an active experience block when bullets or another dated role follows before a major stop section.
            cleaned_sub_key = cleaned.split(':', 1)[0].strip()
            if in_exp and (cleaned_sub_key in _NESTED_EXP_SUBHEADINGS or ':' in line or not current_block) and (sec_label not in major_stop_labels):
                has_more_exp = False
                for fwd_l in lines[idx + 1:idx + 45]:
                    fwd_s = fwd_l.strip()
                    if not fwd_s:
                        continue
                    fwd_lbl = detect_section_label(fwd_s)
                    if fwd_lbl in major_stop_labels:
                        break
                    if _DATE_RANGE_REGEX.search(fwd_s) or (
                        cleaned_sub_key in _NESTED_EXP_SUBHEADINGS and fwd_s.startswith(('•', '-', '*', '▪', '►', '✓'))
                    ):
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
        return extracted_blocks, "explicit"

    # If other section headers (like EDUCATION, SKILLS, etc.) exist in the document
    # and NO experience header was found, collect unlabeled HEADER/SUMMARY lines for
    # strict verified rescue (unlabeled_rescue) without bleeding EDUCATION/SKILLS/CERTS.
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
        secs = split_into_sections(text)
        excluded_secs = {
            "EDUCATION", "SKILLS", "CERTIFICATIONS", "TRAINING", "AWARDS",
            "PROJECTS", "REFERENCES", "PERSONAL", "LANGUAGES", "INTERESTS",
            "AFFILIATIONS", "PUBLICATIONS",
        }
        rescue_chunks = [
            body.strip()
            for lbl, body in secs.items()
            if lbl not in excluded_secs and body and body.strip()
        ]
        if rescue_chunks:
            return rescue_chunks, "unlabeled_rescue"
        return [], "none"

    return [text], "sectionless"


def _extract_experience_blocks(text: str) -> List[str]:
    """
    Extracts all sections corresponding to Work Experience and OJT/Internship.
    """
    blocks, _ = _extract_experience_blocks_with_mode(text)
    return blocks


# ─── 6. Primary Structured Extractor ─────────────────────────────────────────

_BULLET_PREFIXES = ('•', '-', '*', '▪', '►', '✓')


def _is_academic_degree_title(raw_title: str, company_or_loc: str = "") -> bool:
    """Return True only when a title is an academic degree/schooling entry rather than a job title."""
    if not raw_title:
        return False
    if re.search(
        r'\b(?:bachelor(?:\'?s)?|master(?:\'?s)?\s+(?:of|in|degree)|doctor(?:ate)?\s+(?:of|in)|'
        r'ph\.?d|associate(?:\'?s)?\s+(?:degree|of|in)|diploma\s+(?:in|of)|'
        r'elementary|high\s+school|senior\s+high|junior\s+high|'
        r'tesda\s+nc\s*[ivx1-4]*|vocational\s+(?:course|track|diploma)|'
        r'bscs|bsit|bscpe|bsce|bsis|bsme|bsee|bsie|bsba|bsa|bsn|bsed)\b',
        raw_title,
        re.I,
    ):
        return True
    if re.match(
        r'^(?:B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|M\.?B\.?A\.?|A\.?B\.?)\s+(?:in\s+)?'
        r'(?:Computer|Information|Civil|Mechanical|Electrical|Electronics|Industrial|Chemical|Materials|'
        r'Accountancy|Business|Nursing|Education|Psychology|Biology|Mathematics|Engineering|'
        r'Architecture|Science|Arts|Commerce|Management|Tourism|Hospitality|Criminology)\b',
        raw_title.strip(),
        re.I,
    ):
        return True
    if re.search(
        r'\b(?:university|college|polytechnic|academy|school|institute|campus|pup|up|dlsu|ust|feu|admu|sti|map[uú]a|tip|ue|nu)\b',
        company_or_loc or "",
        re.I,
    ) and re.search(
        r'\b(?:bachelor|master|degree|course|bs|ba|ab|ms|ma|mba|bba|bsba|bscpe|bsit|bscs|stem|abm|humss|tvl|student)\b',
        raw_title,
        re.I,
    ):
        return True
    return False


def _is_certification_or_award_entry(raw_title: str, company_or_loc: str = "") -> bool:
    """Return True when an entry is clearly a certification, license, or academic award rather than a job."""
    combined = f"{raw_title or ''} {company_or_loc or ''}".strip()
    if not combined:
        return False
    return bool(
        re.search(
            r'\b(?:(?:aws|azure|gcp|google\s+cloud|microsoft|cisco|oracle|comptia|red\s+hat|itil|pmp|scrum|istqb)\s+certified|'
            r'certified\s+(?:scrum|cloud|solutions|ethical|public\s+accountant\s+exam)|'
            r'prc\s+(?:board|license|licensure)|civil\s+service\s+(?:eligibility|exam|professional|sub-?professional)|'
            r'dean\'?s\s+list(?:er)?|(?:summa|magna)?\s*cum\s+laude|valedictorian|salutatorian|'
            r'honorable\s+mention|scholarship|national\s+certificate|driver\'?s\s+license)\b',
            combined,
            re.I,
        )
    )


def _is_contact_or_identity_line(line: str) -> bool:
    """Return True if line contains contact info (email, phone, URL) unlikely to be a role header."""
    if not line:
        return False
    if re.search(r'@|https?://|www\.|(?:\+63|09)\d[\d\s\-]{7,}', line, re.I):
        return True
    return False


def _is_bullet_sub_role_header(line: str) -> bool:
    """Return True if a bulleted line with a date/duration is a concise sub-role header (e.g. '• Senior Engineer (2022 - 2024)') rather than a responsibility mentioning years."""
    if not line.startswith(_BULLET_PREFIXES):
        return False
    stripped = line.lstrip('•-*▪►✓ ').strip()
    m = _DATE_RANGE_REGEX.search(stripped) or _INLINE_DURATION_OR_YEAR_RE.search(stripped)
    if not m:
        return False
    before = re.sub(r'[\s\-–—,|(\[:]+$', '', stripped[:m.start()]).strip()
    if not before or len(before) > 55:
        return False
    if _is_likely_responsibility_or_sentence(before):
        return False
    return _has_job_signals(before)


def _is_upcoming_role_header(lines: List[str], curr_idx: int) -> bool:
    """Return True when lines[curr_idx] starts a subsequent multi-line role header."""
    curr_l = lines[curr_idx]
    stripped = curr_l.lstrip('•-*▪►✓ ').strip()
    if not stripped or _is_contact_or_identity_line(stripped):
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
        if _is_section_header(fwd_l) or _is_contact_or_identity_line(fwd_l):
            break
        if fwd_l.startswith(_BULLET_PREFIXES):
            fwd_clean = fwd_l.lstrip('•-*▪►✓ ').strip()
            if _is_likely_responsibility_or_sentence(fwd_clean) or len(fwd_clean) > 65:
                break
            if (
                _DATE_RANGE_REGEX.search(fwd_l)
                or _STANDALONE_DATE_OR_DUR_RE.match(fwd_clean)
                or _INLINE_DURATION_OR_YEAR_RE.search(fwd_l)
            ) and not _is_bullet_sub_role_header(fwd_l):
                break
        if _DATE_RANGE_REGEX.search(fwd_l) or _STANDALONE_DATE_OR_DUR_RE.match(fwd_l.strip()) or _INLINE_DURATION_OR_YEAR_RE.search(fwd_l):
            return True
    return False


def _collect_responsibilities(
    lines: List[str],
    start_idx: int,
    blank_before: Optional[List[bool]] = None,
) -> Tuple[List[str], int, Optional[str]]:
    """Collect job duty/responsibility lines starting at start_idx until next role or section."""
    responsibilities: List[str] = []
    captured_location: Optional[str] = None
    curr_idx = start_idx
    while curr_idx < len(lines):
        next_l = lines[curr_idx]
        if _is_section_header(next_l):
            break
        has_date_or_dur = bool(
            _DATE_RANGE_REGEX.search(next_l)
            or _STANDALONE_DATE_OR_DUR_RE.match(next_l.strip())
            or _INLINE_DURATION_OR_YEAR_RE.search(next_l)
        )
        if has_date_or_dur:
            if next_l.startswith(_BULLET_PREFIXES) and not _is_bullet_sub_role_header(next_l):
                duty_text = next_l.lstrip('•-*▪►✓ ').strip()
                if duty_text:
                    responsibilities.append(duty_text)
                curr_idx += 1
                continue
            break
        if _is_upcoming_role_header(lines, curr_idx):
            break

        # Capture a standalone location/work-mode line placed right below the date header
        if not responsibilities and captured_location is None and not next_l.startswith(_BULLET_PREFIXES):
            loc_clean, kv_kind = _strip_kv_prefix(next_l)
            loc_clean, _ = _strip_linkedin_metadata(loc_clean)
            if kv_kind == "LOCATION" or _is_address_or_location(next_l):
                if loc_clean:
                    captured_location = loc_clean
                curr_idx += 1
                continue

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
        else:
            # Join soft-wrapped continuation line onto the previous bullet/responsibility when appropriate
            is_blank_gap = bool(blank_before and curr_idx < len(blank_before) and blank_before[curr_idx])
            if (
                responsibilities
                and not is_blank_gap
                and not _is_address_or_location(next_l)
                and not _PHIL_COMPANY_NAMES_RE.search(next_l)
                and (
                    next_l[0].islower()
                    or (
                        not responsibilities[-1].rstrip().endswith(('.', '!', '?', ';'))
                        and not _has_company_signals(next_l)
                        and not _has_job_signals(next_l)
                    )
                )
            ):
                responsibilities[-1] = f"{responsibilities[-1].rstrip()} {next_l.strip()}"
                curr_idx += 1
                continue

            if not _PHIL_COMPANY_NAMES_RE.search(next_l) and not _is_address_or_location(next_l):
                if len(next_l) > 15 or (
                    len(next_l) >= 6
                    and (
                        _RESPONSIBILITY_VERB_START_RE.match(next_l)
                        or (not _has_company_signals(next_l) and not _has_job_signals(next_l))
                    )
                ):
                    responsibilities.append(next_l)
                    curr_idx += 1
                    continue
        break
    return responsibilities, curr_idx, captured_location


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
        if dur > 0 and s_idx is not None and e_idx is not None and e_idx >= s_idx:
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
      - 'Accenture Philippines\\nTaguig City\\n4 yrs 2 mos\\nSenior Developer\\nJan 2022 - Present'
      - 'Accenture Philippines (2020 - 2024)\\nSenior Developer (2022 - 2024)'
      - 'Accenture Philippines - Taguig City\\nSenior Developer (2022 - 2024)\\nDeveloper (2020 - 2022)'
      - 'Accenture Philippines\\nSenior Developer\\nJan 2023 - Dec 2024\\n• ...\\nDeveloper\\nJan 2021 - Dec 2022'
    Returns (company_name, location, lines_to_skip) or None.
    """
    line = lines[idx]
    if line.startswith(_BULLET_PREFIXES) or _is_likely_responsibility_or_sentence(line) or _is_contact_or_identity_line(line):
        return None
    if _is_academic_degree_title(line) or _is_certification_or_award_entry(line):
        return None

    clean_line, kv_kind = _strip_kv_prefix(line)
    if kv_kind == "ROLE":
        return None

    # Pattern 1: Company line followed by optional location/work-mode + standalone duration line ('3 yrs 5 mos'), then sub-role with date
    if idx + 2 < len(lines) and not _has_job_signals(clean_line) and not _is_address_or_location(clean_line):
        for dur_off, skip_cnt in ((1, 2), (2, 3)):
            if idx + dur_off + 1 >= len(lines):
                continue
            if dur_off == 2:
                mid_l = lines[idx + 1].strip()
                mid_clean, _ = _strip_linkedin_metadata(mid_l)
                if not (_is_address_or_location(mid_l) or _PURE_METADATA_SEG_RE.match(mid_l) or (mid_l and not mid_clean)):
                    continue
            dur_l = lines[idx + dur_off].strip()
            if (
                _STANDALONE_DATE_OR_DUR_RE.match(dur_l)
                and not _DATE_RANGE_REGEX.search(dur_l)
                and _parse_duration_text(dur_l) > 0
            ):
                for fwd in range(idx + skip_cnt, min(idx + skip_cnt + 3, len(lines))):
                    if _DATE_RANGE_REGEX.search(lines[fwd]):
                        comp, loc = _split_company_and_location(line)
                        if comp:
                            if dur_off == 2 and not loc:
                                loc_cand, _ = _strip_linkedin_metadata(lines[idx + 1].strip())
                                if loc_cand and _is_address_or_location(loc_cand):
                                    loc = loc_cand
                            return comp, loc, skip_cnt

    # Pattern 2: 'Company (2020 - 2024)' followed immediately by sub-role(s) with dates
    dm = _DATE_RANGE_REGEX.search(line)
    if dm and idx + 1 < len(lines):
        before = re.sub(r'[\s\-–—,|(\[]+$', '', line[:dm.start()]).strip()
        before_clean, _ = _strip_kv_prefix(before)
        if before_clean and not _has_job_signals(before_clean) and not _is_address_or_location(before_clean):
            for fwd in (idx + 1, idx + 2):
                if fwd < len(lines) and not _is_section_header(lines[fwd]):
                    sub_l = lines[fwd].lstrip('•-*▪►✓ ').strip()
                    sub_dm = _DATE_RANGE_REGEX.search(sub_l)
                    if sub_dm:
                        sub_before = re.sub(r'[\s\-–—,|(\[]+$', '', sub_l[:sub_dm.start()]).strip()
                        if (sub_before and _has_job_signals(sub_before)) or _has_company_signals(before_clean) or _spacy_looks_like_org(before_clean):
                            comp, loc = _split_company_and_location(before_clean)
                            if comp:
                                return comp, loc, 1

    # Pattern 3: 'Company [- Location]' without date, followed directly by 2+ dated sub-roles (inline OR multi-line)
    if not dm and not _has_job_signals(clean_line) and not _is_address_or_location(clean_line) and idx + 2 < len(lines):
        if _has_company_signals(clean_line) or _spacy_looks_like_org(clean_line):
            sub_1 = lines[idx + 1].lstrip('•-*▪►✓ ').strip()
            dm_1 = _DATE_RANGE_REGEX.search(sub_1)
            if dm_1:
                sub1_before = re.sub(r'[\s\-–—,|(\[]+$', '', sub_1[:dm_1.start()]).strip()
                if sub1_before and _has_job_signals(sub1_before):
                    for fwd in range(idx + 2, min(idx + 10, len(lines))):
                        if _is_section_header(lines[fwd]):
                            break
                        if lines[fwd].startswith(_BULLET_PREFIXES) and not _is_bullet_sub_role_header(lines[fwd]):
                            continue
                        sub_k = lines[fwd].lstrip('•-*▪►✓ ').strip()
                        dm_k = _DATE_RANGE_REGEX.search(sub_k)
                        if dm_k:
                            subk_before = re.sub(r'[\s\-–—,|(\[]+$', '', sub_k[:dm_k.start()]).strip()
                            if subk_before and _has_job_signals(subk_before):
                                comp, loc = _split_company_and_location(line)
                                if comp:
                                    return comp, loc, 1
                            break
                        elif not _is_likely_responsibility_or_sentence(sub_k) and not _is_address_or_location(sub_k):
                            if _has_job_signals(sub_k) and not _has_strong_company_signals(sub_k) and fwd + 1 < len(lines) and _DATE_RANGE_REGEX.search(lines[fwd + 1]):
                                comp, loc = _split_company_and_location(line)
                                if comp:
                                    return comp, loc, 1
                            break
            elif (
                not lines[idx + 1].startswith(_BULLET_PREFIXES)
                and _has_job_signals(sub_1)
                and not _has_strong_company_signals(sub_1)
                and _DATE_RANGE_REGEX.search(lines[idx + 2])
            ):
                dm_2 = _DATE_RANGE_REGEX.search(lines[idx + 2])
                d2_before = re.sub(r'[\s\-–—,|(\[]+$', '', lines[idx + 2][:dm_2.start()]).strip()
                if not d2_before or _PURE_METADATA_SEG_RE.match(d2_before):
                    for fwd in range(idx + 3, min(idx + 16, len(lines))):
                        if _is_section_header(lines[fwd]) or _is_contact_or_identity_line(lines[fwd]):
                            break
                        cand_l = lines[fwd]
                        if cand_l.startswith(_BULLET_PREFIXES) and not _is_bullet_sub_role_header(cand_l):
                            continue
                        cand_s = cand_l.lstrip('•-*▪►✓ ').strip()
                        if _is_likely_responsibility_or_sentence(cand_s) or _is_address_or_location(cand_s):
                            continue
                        dm_next = _DATE_RANGE_REGEX.search(cand_s)
                        if dm_next:
                            nb = re.sub(r'[\s\-–—,|(\[]+$', '', cand_s[:dm_next.start()]).strip()
                            if nb and _has_job_signals(nb) and not _has_strong_company_signals(nb):
                                comp, loc = _split_company_and_location(line)
                                if comp:
                                    return comp, loc, 1
                            break
                        if _has_job_signals(cand_s) and not _has_strong_company_signals(cand_s) and fwd + 1 < len(lines) and _DATE_RANGE_REGEX.search(lines[fwd + 1]):
                            dm_n2 = _DATE_RANGE_REGEX.search(lines[fwd + 1])
                            dn2_b = re.sub(r'[\s\-–—,|(\[]+$', '', lines[fwd + 1][:dm_n2.start()]).strip()
                            if not dn2_b or _PURE_METADATA_SEG_RE.match(dn2_b):
                                comp, loc = _split_company_and_location(line)
                                if comp:
                                    return comp, loc, 1
                        break

    return None


_COMPLETE_DATE_RANGE_NO_TRAIL_RE = re.compile(
    rf'(?:'
    rf'(?:between)\s+{_DATE_TOKEN_RE}\s+and\s+(?:{_DATE_TOKEN_RE}|{_PRESENT_RE})'
    rf'|{_DATE_TOKEN_RE}\s*{_RANGE_CONNECTOR_RE}\s*(?:{_DATE_TOKEN_RE}|{_PRESENT_RE})'
    rf'|(?:19|20)\d{{2}}\s*[-–—]\s*\d{{2}}\b(?![-/.]\d)'
    rf'|{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*(?:[-–—~]|\b(?:to|until|thru|through|hanggang)\b)\s*{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*(?:{_YEAR_RE}|[\'’]{_SHORT_YEAR_RE})'
    rf'|(?:Since|From|Started|Effective)\s+(?:{_MONTHS_NAMES}\.?(?:\s+{_ORDINAL_DAY_RE})?\s*[,.]?\s*{_YEAR_RE}|(?:0?[1-9]|1[0-2])\s*[/-]\s*\d{{4}}|{_YEAR_RE})'
    rf')',
    re.IGNORECASE,
)


def _repair_ocr_dates_in_line(line: str) -> str:
    """Fix common OCR digit/letter confusions strictly inside date-like tokens."""
    def _fix_year(m):
        raw = m.group(1)
        fixed = raw.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
        if re.fullmatch(r'(?:19|20)\d{2}', fixed):
            return fixed
        return raw

    res = re.sub(r'\b([12][09Oo][0-9OoIl]{2})\b', _fix_year, line)
    res = re.sub(r'(?<![A-Za-z0-9])[Oo](\d[./-](?:19|20)\d{2})\b', r'0\1', res)
    res = re.sub(r'(?<=[./-])[Oo](\d)(?=[./-](?:19|20)\d{2}\b)', r'0\1', res)
    res = re.sub(r'\b0ct\b', 'Oct', res, flags=re.IGNORECASE)
    res = re.sub(r'\b1an\b', 'Jan', res, flags=re.IGNORECASE)
    res = re.sub(r'\b5ep\b', 'Sep', res, flags=re.IGNORECASE)
    res = re.sub(r'\bPr[3e]s[3e]n[t1l]\b', 'Present', res, flags=re.IGNORECASE)
    return res


def _preprocess_experience_text(text: str) -> str:
    """Normalize dashes, quotes, bullets, whitespace, letter-spaced headings, OCR dates, and strip page footers."""
    if not text:
        return ""
    t = text.replace('\xa0', ' ').replace('\u202f', ' ').replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015]', '-', t)
    t = re.sub(r'[\u2018\u2019]', "'", t)
    t = re.sub(r'[\u201c\u201d]', '"', t)
    t = re.sub(r'[\u2022\u2023\u25e6\u2043\u2219\u25cb\u25cf\u25a0\u25aa]', '•', t)
    out_lines = []
    for ln in t.split('\n'):
        s = ln.strip()
        if not s:
            out_lines.append("")
            continue
        if re.fullmatch(r'page\s+\d+(?:\s*(?:of|/)\s*\d+)?', s, re.IGNORECASE):
            continue
        m_ls = re.match(r"^(?:[A-Z]\s){3,}[A-Z](?:\s{2,}(?:[A-Z]\s)+[A-Z])*$", s)
        if m_ls:
            s = " ".join(re.sub(r"\s+", "", wg) for wg in re.split(r"\s{2,}", s))
        s = re.sub(r'^·\s+', '• ', s)
        s = re.sub(r'[\t ]+', ' ', s)
        out_lines.append(_repair_ocr_dates_in_line(s))
    return "\n".join(out_lines)


def _preprocess_lines_with_blanks(text: str) -> Tuple[List[str], List[bool]]:
    """Split text into non-empty stripped lines while tracking preceding blank lines."""
    lines: List[str] = []
    blank_before: List[bool] = []
    saw_blank = False
    for raw_l in text.split('\n'):
        s = raw_l.strip()
        if not s:
            if lines:
                saw_blank = True
            continue
        lines.append(s)
        blank_before.append(saw_blank)
        saw_blank = False
    return lines, blank_before


def _merge_wrapped_date_lines(
    lines: List[str],
    blank_before: Optional[List[bool]] = None,
) -> Tuple[List[str], List[bool]]:
    """Join wrapped date lines, From:/To: pairs, and CSC PDS dual-date pipes while preserving blank boundaries."""
    blanks = blank_before if (blank_before and len(blank_before) == len(lines)) else [False] * len(lines)
    merged: List[str] = []
    merged_blanks: List[bool] = []
    k = 0
    while k < len(lines):
        curr = lines[k]
        curr_b = blanks[k]

        # 0a. Inline 'From: <date> To: <date|Present>' -> '<date> - <date|Present>'
        m_from_to_inline = re.match(
            r'^(?:from|inclusive\s+dates?)\s*[:\-]\s*(.+?)\s+\bto\b\s*[:\-]?\s*(.+)$',
            curr,
            re.IGNORECASE,
        )
        if m_from_to_inline:
            d1_s = m_from_to_inline.group(1).strip()
            d2_s = m_from_to_inline.group(2).strip()
            if _parse_single_date(d1_s, is_end=False)[0] is not None and _parse_single_date(d2_s, is_end=True)[0] is not None:
                merged.append(f"{d1_s} - {d2_s}")
                merged_blanks.append(curr_b)
                k += 1
                continue

        # 0b. CSC PDS pipe row with separate From | To columns ('01/15/2020 | 12/31/2023 | Role | Agency ...')
        if '|' in curr and not _DATE_RANGE_REGEX.search(curr):
            pipe_segs = [p.strip() for p in curr.split('|')]
            if len(pipe_segs) >= 3:
                s0, s1 = pipe_segs[0], pipe_segs[1]
                if (
                    s0 and s1
                    and not _JOB_TITLE_KEYWORDS_RE.search(s0)
                    and not _JOB_TITLE_KEYWORDS_RE.search(s1)
                    and _parse_single_date(s0, is_end=False)[0] is not None
                    and _parse_single_date(s1, is_end=True)[0] is not None
                ):
                    rest_segs = " | ".join(pipe_segs[2:])
                    merged.append(f"{s0} - {s1} | {rest_segs}" if rest_segs else f"{s0} - {s1}")
                    merged_blanks.append(curr_b)
                    k += 1
                    continue

        if (
            k + 1 < len(lines)
            and not _is_section_header(curr)
            and not curr.startswith(_BULLET_PREFIXES)
            and not _COMPLETE_DATE_RANGE_NO_TRAIL_RE.search(curr)
        ):
            nxt = lines[k + 1]
            if not _is_section_header(nxt) and not nxt.startswith(_BULLET_PREFIXES):
                # 0c. Multi-line 'From: <date>\nTo: <date|Present>'
                m_from = re.match(r'^from\s*[:\-]\s*(.+)$', curr, re.IGNORECASE)
                m_to = re.match(r'^to\s*[:\-]\s*(.+)$', nxt, re.IGNORECASE)
                if m_from and m_to:
                    d1_s = m_from.group(1).strip()
                    d2_s = m_to.group(1).strip()
                    if _parse_single_date(d1_s, is_end=False)[0] is not None and _parse_single_date(d2_s, is_end=True)[0] is not None:
                        merged.append(f"{d1_s} - {d2_s}")
                        merged_blanks.append(curr_b)
                        k += 2
                        continue

                if (
                    re.search(rf'(?:{_DATE_TOKEN_RE})\s*(?:[-–—~→]|->|\b(?:to|until|up\s+to|thru|through|till?|hanggang)\b)\s*$', curr, re.I)
                    and re.match(rf'^(?:{_DATE_TOKEN_RE}|{_PRESENT_RE})(?:$|\s|[\)·|,(\[])', nxt, re.I)
                ):
                    merged.append(f"{curr} {nxt}")
                    merged_blanks.append(curr_b)
                    k += 2
                    continue
                if re.fullmatch(rf'{_DATE_TOKEN_RE}', curr, re.I):
                    if (
                        k + 2 < len(lines)
                        and re.fullmatch(r'(?:[-–—~→]|->|to|until|up\s+to|thru|through|till?|hanggang)', nxt, re.I)
                        and re.match(rf'^(?:{_DATE_TOKEN_RE}|{_PRESENT_RE})(?:$|\s|[\)·|,(\[])', lines[k + 2], re.I)
                    ):
                        merged.append(f"{curr} {nxt} {lines[k + 2]}")
                        merged_blanks.append(curr_b)
                        k += 3
                        continue
                    if re.match(rf'^(?:[-–—~→]|->|\b(?:to|until|up\s+to|thru|through|till?|hanggang)\b)\s*(?:{_DATE_TOKEN_RE}|{_PRESENT_RE})', nxt, re.I):
                        merged.append(f"{curr} {nxt}")
                        merged_blanks.append(curr_b)
                        k += 2
                        continue
        merged.append(curr)
        merged_blanks.append(curr_b)
        k += 1
    return merged, merged_blanks


def _split_semicolon_multi_roles(
    lines: List[str],
    blank_before: Optional[List[bool]] = None,
) -> Tuple[List[str], List[bool]]:
    """Split semicolon-delimited multi-role lines when 2+ segments carry dates or durations."""
    blanks = blank_before if (blank_before and len(blank_before) == len(lines)) else [False] * len(lines)
    out: List[str] = []
    out_blanks: List[bool] = []
    for ln, b_flag in zip(lines, blanks):
        if (
            ';' in ln
            and not ln.startswith(_BULLET_PREFIXES)
            and not _RESPONSIBILITY_VERB_START_RE.match(ln)
        ):
            parts = [p.strip() for p in ln.split(';') if p.strip()]
            dated_parts = sum(1 for p in parts if _DATE_RANGE_REGEX.search(p) or _INLINE_DURATION_OR_YEAR_RE.search(p))
            if len(parts) >= 2 and dated_parts >= 2:
                for p_idx, p_val in enumerate(parts):
                    out.append(p_val)
                    out_blanks.append(b_flag if p_idx == 0 else True)
                continue
        out.append(ln)
        out_blanks.append(b_flag)
    return out, out_blanks


def _resolve_header_lines(header_lines: List[str]) -> Tuple[str, str, str, Optional[str], str]:
    """
    Unified header slot resolver for 1-4 header lines / segments in any order
    (Harvard/Overleaf, LinkedIn, CSC PDS, Biodata KV, inline pipes/bullets).
    Returns (norm_title, raw_title, company, location, meta_extra).
    """
    role_segs: List[str] = []
    comp_segs: List[str] = []
    loc_segs: List[str] = []
    other_segs: List[str] = []
    meta_parts: List[str] = []

    def _consume_segment(raw_seg: str, forced_kind: Optional[str] = None) -> None:
        seg = re.sub(r'^(?:\(?\d{1,2}\)?[\.\)]\s+|[•\-\*▪►✓]+\s+)', '', raw_seg.strip()).strip()
        if not seg:
            return
        if forced_kind is None:
            seg, forced_kind = _strip_kv_prefix(seg)
        if forced_kind == "DATE":
            if not seg:
                return
        cleaned, seg_meta = _strip_linkedin_metadata(seg)
        if seg_meta:
            meta_parts.append(seg_meta)
        if not cleaned or _is_pure_metadata_seg(cleaned) or _is_pds_noise_segment(cleaned):
            return
        if _DATE_RANGE_REGEX.fullmatch(cleaned) or _STANDALONE_DATE_OR_DUR_RE.match(cleaned):
            return
        if forced_kind == "ROLE":
            role_segs.append(cleaned)
        elif forced_kind == "COMPANY":
            comp_segs.append(cleaned)
        elif forced_kind == "LOCATION":
            loc_segs.append(cleaned)
        elif _is_address_or_location(cleaned) and not _has_job_signals(cleaned) and not _has_company_signals(cleaned):
            loc_segs.append(cleaned)
        else:
            other_segs.append(cleaned)

    for ln in header_lines:
        s = (ln or "").strip()
        if not s:
            continue
        kv_val, kv_kind = _strip_kv_prefix(s)
        if kv_kind in ("ROLE", "COMPANY", "LOCATION") and '|' not in s:
            _consume_segment(kv_val, forced_kind=kv_kind)
            continue
        pipe_pieces = [p.strip() for p in s.split('|')] if '|' in s else [s]
        for piece in pipe_pieces:
            if not piece:
                continue
            if '•' in piece and not piece.lstrip().startswith('•'):
                for bp in piece.split('•'):
                    _consume_segment(bp)
            else:
                _consume_segment(piece)

    if role_segs or comp_segs:
        t_str = role_segs[0] if role_segs else (other_segs[0] if other_segs else "")
        rem_other = other_segs if role_segs else other_segs[1:]
        c_str = comp_segs[0] if comp_segs else (" | ".join(rem_other) if rem_other else "")
    elif len(other_segs) == 0:
        t_str, c_str = "", ""
    elif len(other_segs) == 1:
        t_str, c_str = other_segs[0], ""
    elif len(other_segs) == 2:
        t_str, c_str = other_segs[0], other_segs[1]
    else:
        def _role_score(seg: str) -> int:
            s_job = _has_job_signals(seg)
            s_strong_comp = _has_strong_company_signals(seg) or _spacy_looks_like_org(seg)
            s_comp = _has_company_signals(seg)
            if s_job and not s_strong_comp:
                return 3
            if s_job:
                return 2
            if s_comp or s_strong_comp:
                return 0
            return 1

        best_idx = max(range(len(other_segs)), key=lambda idx: (_role_score(other_segs[idx]), -idx))
        t_str = other_segs[best_idx]
        c_str = " | ".join(seg for idx, seg in enumerate(other_segs) if idx != best_idx)

    norm_title, company, loc = _extract_title_company_location(t_str, c_str)
    if loc_segs:
        joined_loc = ", ".join(dict.fromkeys(loc_segs))
        if loc:
            if joined_loc.lower() not in loc.lower() and loc.lower() not in joined_loc.lower():
                loc = f"{loc}, {joined_loc}"
        else:
            loc = joined_loc

    raw_title = t_str or norm_title
    return norm_title, raw_title, company, loc, " ".join(meta_parts).strip()


def _resolve_three_header_lines(l0: str, l1: str, l2: str) -> Tuple[str, str, Optional[str]]:
    """Resolve 3 pre-date lines (title, company, location in any order) into (norm_title, company, location)."""
    norm_title, _, company, loc, _ = _resolve_header_lines([l0, l1, l2])
    return norm_title, company, loc


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
        return {
            "total_experience_months": 0,
            "explicit_experience_months": 0,
            "reconciled_experience_months": 0,
            "years_experience_float": 0.0,
            "work_experiences": [],
        }

    clean_text = _preprocess_experience_text(text)
    blocks, exp_mode = _extract_experience_blocks_with_mode(clean_text)
    combined_exp_text = "\n\n".join(blocks)

    raw_lines, raw_blanks = _preprocess_lines_with_blanks(combined_exp_text)
    lines, blank_before = _merge_wrapped_date_lines(raw_lines, raw_blanks)
    lines, blank_before = _split_semicolon_multi_roles(lines, blank_before)
    if not lines:
        explicit_months = _extract_explicit_experience_months(clean_text)
        return {
            "total_experience_months": 0,
            "explicit_experience_months": explicit_months,
            "reconciled_experience_months": explicit_months,
            "years_experience_float": round(explicit_months / 12.0, 1) if explicit_months > 0 else 0.0,
            "work_experiences": [],
        }

    work_experiences = []
    current_company_context: Optional[Tuple[str, Optional[str]]] = None
    consumed_indices: set[int] = set()
    i = 0

    def _passes_mode_gate(norm_t: str, comp_v: str, dur_v: int, s_iso: Optional[str], e_iso: Optional[str], resps_v: List[str]) -> bool:
        if exp_mode != "unlabeled_rescue":
            return True
        has_real_date_or_dur = dur_v > 0 or (bool(s_iso) and bool(e_iso))
        return has_real_date_or_dur and _has_job_signals(norm_t) and (bool(comp_v) or bool(resps_v))

    def _should_peek_next_for_case_a(norm_t: str, raw_t: str, comp_v: str, next_line: str, after_d: str = "") -> bool:
        if _is_section_header(next_line) or next_line.startswith(_BULLET_PREFIXES) or _DATE_RANGE_REGEX.search(next_line):
            return False
        if _STANDALONE_DATE_OR_DUR_RE.match(next_line.strip()) or _INLINE_DURATION_OR_YEAR_RE.search(next_line):
            return False
        if _is_likely_responsibility_or_sentence(next_line) or _is_academic_degree_title(next_line) or len(next_line) > 70:
            return False
        if not comp_v:
            after_ok = (not after_d) or any(rx.search(after_d) for rx, _ in _EMPLOYMENT_TYPE_RULES) or _is_pure_metadata_seg(after_d)
            if not after_ok:
                return False
            return bool(_has_company_signals(next_line) or _spacy_looks_like_org(next_line) or not _JOB_TITLE_KEYWORDS_RE.search(next_line))
        if not norm_t or (not _has_job_signals(norm_t) and (_has_company_signals(raw_t) or _spacy_looks_like_org(raw_t))):
            return bool(_has_job_signals(next_line))
        return False

    while i < len(lines):
        line = lines[i]
        line_low = line.strip().lower()

        if _is_section_header(line) or line_low in _RESUME_SECTION_HEADERS or (
            any(line_low.startswith(h + ":") for h in _RESUME_SECTION_HEADERS)
            and not _JOB_TITLE_KEYWORDS_RE.search(line)
        ):
            current_company_context = None
            consumed_indices.add(i)
            i += 1
            continue

        if _is_contact_or_identity_line(line):
            consumed_indices.add(i)
            i += 1
            continue

        parent_comp = _is_parent_company_header(lines, i)
        if parent_comp:
            current_company_context = (parent_comp[0], parent_comp[1])
            consumed_indices.update(range(i, i + parent_comp[2]))
            i += parent_comp[2]
            continue

        # ── Case A: Inline or Date-First entry format ─────────────────────────
        dm = _DATE_RANGE_REGEX.search(line)
        if dm:
            prose_m = _PROSE_ROLE_RE.match(line)
            meta_extra = ""
            if prose_m:
                raw_title = (prose_m.group("title") or "").strip()
                comp_loc_str = (prose_m.group("company") or "").strip()
                date_str = line[dm.start():dm.end()].strip()
                norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
                consumed_header = 1
            else:
                before_date = re.sub(r'[\s\-–—,|(\[:]+$', '', line[:dm.start()]).strip()
                before_date = re.sub(r'\s+(?:from|between|during)\s*$', '', before_date, flags=re.IGNORECASE).strip()
                before_clean, before_kv = _strip_kv_prefix(before_date)
                if before_kv == "DATE" and not before_clean:
                    before_date = ""
                after_date = re.sub(r'^[\s\-–—,|)\]:·]+|[\s\-–—,|(\[]+$', '', line[dm.end():]).strip()

                if not before_date:
                    # Standalone date or Date-First line (e.g. "2021 - Present" or "2021 - Present | Senior Developer | Tech Mahindra")
                    date_str = line[dm.start():dm.end()].strip()
                    if after_date and not _is_pure_metadata_seg(after_date):
                        norm_title, raw_title, company, location, meta_extra = _resolve_header_lines([after_date])
                        consumed_header = 1
                        if i + 1 < len(lines) and _should_peek_next_for_case_a(norm_title, raw_title, company, lines[i + 1]):
                            norm_title, raw_title, company, location, extra_m = _resolve_header_lines([after_date, lines[i + 1]])
                            if extra_m:
                                meta_extra = f"{meta_extra} {extra_m}".strip()
                            consumed_header = 2
                    else:
                        if after_date:
                            meta_extra = after_date
                        consumed_header = 1
                        peek_lines: List[str] = []
                        if i + 1 < len(lines) and not _is_section_header(lines[i + 1]) and not lines[i + 1].startswith(_BULLET_PREFIXES) and not _DATE_RANGE_REGEX.search(lines[i + 1]):
                            peek_lines.append(lines[i + 1])
                            consumed_header = 2
                            _, _, pre_comp_chk, _, _ = _resolve_header_lines(peek_lines)
                            if (
                                not pre_comp_chk
                                and i + 2 < len(lines)
                                and not _is_section_header(lines[i + 2])
                                and not lines[i + 2].startswith(_BULLET_PREFIXES)
                                and not _DATE_RANGE_REGEX.search(lines[i + 2])
                                and not _is_likely_responsibility_or_sentence(lines[i + 2])
                                and not _is_academic_degree_title(lines[i + 2])
                            ):
                                peek_lines.append(lines[i + 2])
                                consumed_header = 3
                                if i + 3 < len(lines) and not _is_section_header(lines[i + 3]) and not lines[i + 3].startswith(_BULLET_PREFIXES) and not _DATE_RANGE_REGEX.search(lines[i + 3]) and _is_address_or_location(lines[i + 3]):
                                    peek_lines.append(lines[i + 3])
                                    consumed_header = 4
                        norm_title, raw_title, company, location, extra_m = _resolve_header_lines(peek_lines)
                        if extra_m:
                            meta_extra = f"{meta_extra} {extra_m}".strip()
                elif '|' in line or ('•' in line and not line.lstrip().startswith('•') and line.count('•') >= 2):
                    sep = '|' if '|' in line else '•'
                    segments = [s.strip() for s in line.split(sep)]
                    date_idx = next((idx for idx, s in enumerate(segments) if _DATE_RANGE_REGEX.search(s)), -1)
                    if date_idx >= 0:
                        date_str = segments[date_idx]
                        other_segs = [s for idx, s in enumerate(segments) if idx != date_idx]
                    else:
                        other_segs = segments[:2]
                        date_str = segments[2] if len(segments) > 2 else ""

                    norm_title, raw_title, company, location, meta_extra = _resolve_header_lines(other_segs)
                    consumed_header = 1
                    if i + 1 < len(lines) and _should_peek_next_for_case_a(norm_title, raw_title, company, lines[i + 1]):
                        norm_title, raw_title, company, location, extra_m = _resolve_header_lines(other_segs + [lines[i + 1]])
                        if extra_m:
                            meta_extra = f"{meta_extra} {extra_m}".strip()
                        consumed_header = 2
                else:
                    title_comp_str = before_date
                    date_str = line[dm.start():].strip(' ()')
                    raw_title = title_comp_str
                    norm_title, company, location = _extract_title_company_location(title_comp_str)
                    consumed_header = 1
                    if i + 1 < len(lines) and _should_peek_next_for_case_a(norm_title, raw_title, company, lines[i + 1], after_d=after_date):
                        norm_title, raw_title_res, company, location, extra_m = _resolve_header_lines([title_comp_str, lines[i + 1]])
                        if raw_title_res:
                            raw_title = raw_title_res
                        if extra_m:
                            meta_extra = f"{meta_extra} {extra_m}".strip()
                        consumed_header = 2

            if not company and current_company_context:
                company, ctx_loc = current_company_context
                location = location or ctx_loc
            elif company and current_company_context and company.lower() != current_company_context[0].lower():
                current_company_context = None

            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_str)
            responsibilities, curr_idx, cap_loc = _collect_responsibilities(lines, i + consumed_header, blank_before=blank_before)
            if cap_loc and not location:
                location = cap_loc

            emp_type = _detect_employment_type(
                raw_title,
                f"{company} {location or ''} {meta_extra} {line}".strip(),
                f"{date_str} {extra_status}".strip(),
                responsibilities,
            )
            # Reject academic degrees / schooling or certifications mistaken as employment roles
            if _is_academic_degree_title(raw_title, (company or "") + " " + (location or "")) or _is_certification_or_award_entry(raw_title, company or ""):
                consumed_indices.update(range(i, curr_idx))
                i = curr_idx
                continue

            if norm_title and not _is_address_or_location(norm_title) and _passes_mode_gate(norm_title, company, duration, start_iso, end_iso, responsibilities):
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
                consumed_indices.update(range(i, curr_idx))
            i = curr_idx
            continue

        # ── Case B: Multi-line block format (Template 1 & Template 3) ─────────
        has_date_ahead = False
        date_offset = -1
        if not _INLINE_DURATION_OR_YEAR_RE.search(line) and not _is_likely_responsibility_or_sentence(line):
            for offset in range(1, min(5, len(lines) - i)):
                cand_l = lines[i + offset]
                if _is_section_header(cand_l) or _is_contact_or_identity_line(cand_l):
                    break
                if cand_l.startswith(_BULLET_PREFIXES):
                    cand_clean = cand_l.lstrip('•-*▪►✓ ').strip()
                    if _is_likely_responsibility_or_sentence(cand_clean) or len(cand_clean) > 65:
                        break
                    if (
                        _DATE_RANGE_REGEX.search(cand_l)
                        or _STANDALONE_DATE_OR_DUR_RE.match(cand_clean)
                    ) and not _is_bullet_sub_role_header(cand_l):
                        break
                if _DATE_RANGE_REGEX.search(cand_l) or _STANDALONE_DATE_OR_DUR_RE.match(cand_l.strip()):
                    if _PROSE_ROLE_RE.match(cand_l):
                        break
                    has_date_ahead = True
                    date_offset = offset
                    break

        if has_date_ahead:
            date_line = lines[i + date_offset]
            dm_b = _DATE_RANGE_REGEX.search(date_line)
            before_dm = re.sub(r'[\s\-–—,|(\[:]+$', '', date_line[:dm_b.start()]).strip() if dm_b else ""
            after_dm = re.sub(r'^[\s\-–—,|)\]:·]+|[\s\-–—,|(\[]+$', '', date_line[dm_b.end():]).strip() if dm_b else ""
            before_dm_clean, before_dm_kv = _strip_kv_prefix(before_dm)
            if before_dm_kv == "DATE" and not before_dm_clean:
                before_dm = ""

            pre_header_lines = list(lines[i : i + date_offset])
            if before_dm and not _is_pure_metadata_seg(before_dm) and not _is_likely_responsibility_or_sentence(before_dm):
                pre_header_lines.append(before_dm)
            if after_dm and not _is_pure_metadata_seg(after_dm) and not _is_likely_responsibility_or_sentence(after_dm):
                pre_header_lines.append(after_dm)
            consumed_header = date_offset + 1

            norm_title, raw_title, company, location, meta_extra = _resolve_header_lines(pre_header_lines)
            if len(pre_header_lines) == 1 and '|' not in pre_header_lines[0] and _strip_kv_prefix(pre_header_lines[0])[1] is None:
                raw_title = pre_header_lines[0]

            # Early reject degree/certification blocks before peeking past date_line
            if (
                any(_is_academic_degree_title(pl) for pl in pre_header_lines)
                or _is_academic_degree_title(raw_title, f"{company or ''} {location or ''}")
                or _is_certification_or_award_entry(raw_title, company or "")
            ):
                consumed_indices.update(range(i, i + consumed_header))
                i += consumed_header
                continue

            # Peek one line after the date if either company or role title is still missing
            next_after_date = lines[i + consumed_header] if (i + consumed_header) < len(lines) else ""
            if (
                next_after_date
                and not next_after_date.startswith(_BULLET_PREFIXES)
                and not _is_section_header(next_after_date)
                and not _DATE_RANGE_REGEX.search(next_after_date)
                and not _STANDALONE_DATE_OR_DUR_RE.match(next_after_date.strip())
                and not _is_likely_responsibility_or_sentence(next_after_date)
                and not _is_academic_degree_title(next_after_date)
            ):
                need_comp = not company and not _is_address_or_location(next_after_date) and (
                    _has_company_signals(next_after_date)
                    or _spacy_looks_like_org(next_after_date)
                    or (len(next_after_date) <= 50 and not _JOB_TITLE_KEYWORDS_RE.search(next_after_date))
                )
                need_role = (
                    (not norm_title or (not _has_job_signals(norm_title) and (_has_company_signals(" ".join(pre_header_lines)) or _spacy_looks_like_org(" ".join(pre_header_lines)))))
                    and _has_job_signals(next_after_date)
                )
                if need_comp or need_role:
                    norm_title, raw_title, company, location, extra_m = _resolve_header_lines(pre_header_lines + [next_after_date])
                    if extra_m:
                        meta_extra = f"{meta_extra} {extra_m}".strip()
                    consumed_header += 1

            if not company and current_company_context:
                company, ctx_loc = current_company_context
                location = location or ctx_loc
            elif company and current_company_context and company.lower() != current_company_context[0].lower():
                current_company_context = None

            start_iso, end_iso, duration, extra_status = _parse_date_and_duration(date_line)
            responsibilities, curr_idx, cap_loc = _collect_responsibilities(lines, i + consumed_header, blank_before=blank_before)
            if cap_loc and not location:
                location = cap_loc

            emp_type = _detect_employment_type(
                raw_title,
                f"{company} {location or ''} {meta_extra} {' '.join(pre_header_lines)}".strip(),
                f"{date_line} {extra_status}".strip(),
                responsibilities,
            )
            # Reject academic degrees / schooling or certifications mistaken as employment roles
            if _is_academic_degree_title(raw_title, f"{company or ''} {location or ''}") or _is_certification_or_award_entry(raw_title, company or ""):
                consumed_indices.update(range(i, curr_idx))
                i = curr_idx
                continue

            if norm_title and not _is_address_or_location(norm_title) and _passes_mode_gate(norm_title, company, duration, start_iso, end_iso, responsibilities):
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
                consumed_indices.update(range(i, curr_idx))

            i = curr_idx
            continue

        # ── Case C: Inline duration/year on a single role line (no date range) ─
        dur_m = _INLINE_DURATION_OR_YEAR_RE.search(line)
        if dur_m and not line.startswith(_BULLET_PREFIXES) and not _is_likely_responsibility_or_sentence(line):
            dur_str = (dur_m.group("paren_dur") or dur_m.group("pipe_dur") or dur_m.group("dash_dur") or "").strip()
            dur_months = _parse_duration_text(dur_str)
            single_yr_m = re.fullmatch(r'(19|20)\d{2}', dur_str)
            if dur_months > 0 or single_yr_m:
                before_dur = re.sub(r'[\s\-–—,|(\[]+$', '', line[:dur_m.start()]).strip()
                date_seg = None
                if '|' in before_dur:
                    segs = [s.strip() for s in before_dur.split('|') if s.strip()]
                    kept_segs = []
                    for s_idx_seg, s_val in enumerate(segs):
                        if s_idx_seg > 0 and _STANDALONE_DATE_OR_DUR_RE.match(s_val) and _parse_single_date(s_val)[0] is not None and not date_seg:
                            date_seg = s_val
                        else:
                            kept_segs.append(s_val)
                    header_segs = kept_segs
                else:
                    header_segs = [before_dur]
                norm_title, raw_title, company, location, meta_extra = _resolve_header_lines(header_segs)
                consumed_header = 1
                if i + 1 < len(lines) and _should_peek_next_for_case_a(norm_title, raw_title, company, lines[i + 1]):
                    norm_title, raw_title, company, location, extra_m = _resolve_header_lines(header_segs + [lines[i + 1]])
                    if extra_m:
                        meta_extra = f"{meta_extra} {extra_m}".strip()
                    consumed_header = 2

                responsibilities, curr_idx, cap_loc = _collect_responsibilities(lines, i + consumed_header, blank_before=blank_before)
                if cap_loc and not location:
                    location = cap_loc
                if (
                    norm_title
                    and (company or _has_job_signals(raw_title))
                    and not _is_address_or_location(norm_title)
                    and not _is_academic_degree_title(raw_title, company or "")
                    and not _is_certification_or_award_entry(raw_title, company or "")
                    and _passes_mode_gate(norm_title, company, dur_months, None, None, responsibilities)
                ):
                    if date_seg and not single_yr_m:
                        s_iso, e_iso, eff_dur, _ = _parse_date_and_duration(f"{date_seg} ({dur_str})")
                        if eff_dur > 0:
                            dur_months = eff_dur
                    else:
                        s_iso = f"{dur_str}-01" if single_yr_m else None
                        e_iso = f"{dur_str}-12" if single_yr_m else None
                    emp_type = _detect_employment_type(raw_title, f"{company} {meta_extra}".strip(), dur_str, responsibilities)
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
                    consumed_indices.update(range(i, curr_idx))
                i = curr_idx
                continue

        # ── Case D: Prose line with explicit duration (e.g. "Worked as Welder at ABC Corp for 3 years") ─
        prose_m = _PROSE_ROLE_RE.match(line)
        if prose_m and _parse_duration_text(line) > 0:
            raw_title = (prose_m.group("title") or "").strip()
            comp_loc_str = (prose_m.group("company") or "").strip()
            norm_title, company, location = _extract_title_company_location(raw_title, comp_loc_str)
            dur_months = _parse_duration_text(line)
            if (
                norm_title
                and not _is_address_or_location(norm_title)
                and not _is_academic_degree_title(raw_title, company or "")
                and not _is_certification_or_award_entry(raw_title, company or "")
                and _passes_mode_gate(norm_title, company, dur_months, None, None, [])
            ):
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
                consumed_indices.add(i)
            i += 1
            continue

        i += 1

    # ── Undated role rescue for explicit EXPERIENCE sections (supports mixed dated + undated roles) ─
    if exp_mode == "explicit" and blocks:
        j = 0
        while j < len(lines):
            if j in consumed_indices:
                j += 1
                continue
            l_curr = lines[j]
            if (
                not _is_section_header(l_curr)
                and not l_curr.startswith(_BULLET_PREFIXES)
                and not _is_likely_responsibility_or_sentence(l_curr)
                and not _is_contact_or_identity_line(l_curr)
                and len(l_curr) <= 75
                and _has_job_signals(l_curr)
            ):
                header_cands = [l_curr]
                consumed = 1
                if (
                    j + 1 < len(lines)
                    and (j + 1) not in consumed_indices
                    and not _is_section_header(lines[j + 1])
                    and not lines[j + 1].startswith(_BULLET_PREFIXES)
                    and not _DATE_RANGE_REGEX.search(lines[j + 1])
                    and not _is_likely_responsibility_or_sentence(lines[j + 1])
                    and len(lines[j + 1]) <= 70
                    and (_has_company_signals(lines[j + 1]) or _spacy_looks_like_org(lines[j + 1]) or not _has_job_signals(lines[j + 1]))
                ):
                    header_cands.append(lines[j + 1])
                    consumed = 2
                norm_title, raw_title, company, location, meta_extra = _resolve_header_lines(header_cands)
                if not company and len(header_cands) == 2:
                    # Fallback if single-line already held company and second line wasn't company
                    norm_title, raw_title, company, location, meta_extra = _resolve_header_lines([l_curr])
                    consumed = 1
                if norm_title and company and not _is_academic_degree_title(raw_title, company) and not _is_certification_or_award_entry(raw_title, company):
                    resps, next_j, cap_loc = _collect_responsibilities(lines, j + consumed, blank_before=blank_before)
                    if cap_loc and not location:
                        location = cap_loc
                    emp_type = _detect_employment_type(raw_title, f"{company} {meta_extra}".strip(), "", resps)
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
                        "duration_months": 0,
                        "responsibilities": resps,
                        "highlights": resps,
                    })
                    consumed_indices.update(range(j, next_j))
                    j = next_j
                    continue
            j += 1

    # Deduplicate identical and near-duplicate entries while preserving order
    deduped: List[Dict[str, Any]] = []
    seen_idx: Dict[Tuple[str, str, str, str], int] = {}
    seen_title_dates: Dict[Tuple[str, str, str], int] = {}
    for exp in work_experiences:
        t_key = (exp.get("job_title") or "").strip().lower()
        c_key = (exp.get("company_name") or "").strip().lower()
        s_key = exp.get("start_date") or ""
        e_key = exp.get("end_date") or ""
        key = (t_key, c_key, s_key, e_key)

        match_idx = seen_idx.get(key)
        if match_idx is None and s_key:
            td_key = (t_key, s_key, e_key)
            prev_i = seen_title_dates.get(td_key)
            if prev_i is not None:
                prev_c = (deduped[prev_i].get("company_name") or "").strip().lower()
                if not prev_c or not c_key or prev_c == c_key:
                    match_idx = prev_i

        if match_idx is None:
            new_i = len(deduped)
            seen_idx[key] = new_i
            if s_key:
                seen_title_dates.setdefault((t_key, s_key, e_key), new_i)
            deduped.append(exp)
        else:
            existing = deduped[match_idx]
            if not existing.get("company_name") and exp.get("company_name"):
                existing["company_name"] = exp["company_name"]
                existing["company"] = exp["company_name"]
            if len(exp.get("responsibilities") or []) > len(existing.get("responsibilities") or []):
                existing["responsibilities"] = exp["responsibilities"]
                existing["highlights"] = exp["highlights"]
            if not existing.get("location") and exp.get("location"):
                existing["location"] = exp["location"]
            if not existing.get("duration_months") and exp.get("duration_months"):
                existing["duration_months"] = exp["duration_months"]

    total_months = _compute_merged_experience_months(deduped)
    explicit_months = _extract_explicit_experience_months(clean_text)
    reconciled_months = max(total_months, explicit_months)
    years_float = round(reconciled_months / 12.0, 1) if reconciled_months > 0 else 0.0
    return {
        "total_experience_months": total_months,
        "explicit_experience_months": explicit_months,
        "reconciled_experience_months": reconciled_months,
        "years_experience_float": years_float,
        "work_experiences": deduped,
    }


# ─── 7. Backward Compatibility Functions ─────────────────────────────────────

def extract_experience_entries(text: str, structured: Optional[Dict[str, Any]] = None) -> list[dict]:
    """
    Parses structured experience entries from resume text.
    Provides backward compatibility with legacy dict format while including new structured fields.
    """
    if structured is None:
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


def extract_experience(text: str, structured: Optional[Dict[str, Any]] = None) -> str:
    """
    Extracts work experience from resume text with structured parsing.
    Returns pipe-separated entries: "Role at Company (Dates) - Responsibilities: ..."
    """
    entries = extract_experience_entries(text, structured=structured)
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
    r'minimum|must\s+have|required|requires|age|aged|'
    r'lived|living|resided|residing|born|graduated|ago|saved|reduced|data|logs|records|history|founded|established|'
    r'mentored|supervised|managed|led|trained|coached|hired|recruited|'
    r'valid|expires?|remaining)\s*'
    r'(?:a\s+team\s+of\s+\d+\s+\w+\s+|in\s+[A-Za-z\s]{2,25}\s+for\s+|here\s+for\s+|for\s+|has|with|of|having|at\s+least|over|more\s+than|in)?\s*$',
    re.IGNORECASE,
)
_WORKED_AT_COMPANY_FOR_RE = re.compile(
    r'\b(?:worked|working|employed|served|serving)\s+(?:at|with|for)\s+[^.!?\n]{1,45}\bfor\s+$',
    re.IGNORECASE,
)
_EXPLICIT_DISQUALIFIER_AFTER_RE = re.compile(
    r'^\s*(?:old|of\s+age|ago|warranty|validity|remaining|left|heritage|history|in\s+business|established|founded|'
    r'data|logs|records|degree|diploma|course|coursework|program|study|studies|college|university|school|high\s+school|'
    r'bachelor|master|phd|training\s+bond)\b',
    re.IGNORECASE,
)

_MOD_WORD = (
    r'(?!years?\b|yrs?\b|months?\b|mos?\b|old\b|ago\b|age\b|degree\b|diploma\b|'
    r'school\b|college\b|university\b|heritage\b|history\b|data\b|logs?\b|records?\b|warranty\b|validity\b|business\b)'
    r'[A-Za-z0-9&/\-]+'
)


def _extract_explicit_experience_months(text: str) -> int:
    """
    Extract explicit total experience duration (in months) from summary statements or
    explicit 'Experience:' / 'Years of Experience:' labels, ignoring false positives
    such as age ('18 years old'), residence duration, company heritage, or education length.
    """
    if not text:
        return 0

    clean_text = _preprocess_experience_text(text)
    best_months = 0

    # 1. Explicit label lines anywhere in raw text outside Education/Certifications/References
    label_re = re.compile(
        r'^(?:(?:total|overall|combined)\s+)?'
        r'(?:(?:work|working|relevant|related|professional|industry|manufacturing|production|software|it|sales|retail|bpo|engineering|hospitality|nursing|teaching|accounting|finance|logistics|warehouse|customer\s+service|[A-Za-z&/\-]{2,20})\s+){0,2}'
        r'(?:years?\s+of\s+)?'
        r'(?:experience(?:\s+summary)?|work\s+exp\.?|exp\.?|tenure|length\s+of\s+service|yoe)\s*(?:\(\s*years?\s*\))?\s*[:\-–=|]\s*(.+)$',
        re.IGNORECASE,
    )
    split_label_re = re.compile(
        r'^(?:(?:total|overall|combined)\s+)?'
        r'(?:(?:work|working|relevant|related|professional|industry|[A-Za-z&/\-]{2,20})\s+){0,2}'
        r'(?:years?\s+of\s+)?'
        r'(?:experience(?:\s+summary)?|work\s+exp\.?|exp\.?|tenure|length\s+of\s+service|yoe)\s*[:\-–=]?\s*$',
        re.IGNORECASE,
    )
    skip_lbls = {"EDUCATION", "CERTIFICATIONS", "REFERENCES", "INTERESTS", "PUBLICATIONS"}
    raw_lines = [ln.strip() for ln in clean_text.split('\n') if ln.strip()]
    curr_sec = "HEADER"
    curr_raw_hdr = ""
    narrative_lines: List[str] = []

    for idx, stripped_line in enumerate(raw_lines):
        # Check explicit single-line label (full line or inline pipe/bullet/semicolon segment)
        if curr_sec not in skip_lbls:
            segs = [stripped_line]
            if any(d in stripped_line for d in ('|', ';', '•')):
                segs.extend(p.strip() for p in re.split(r'[|;•]', stripped_line) if p.strip())
            for seg in segs:
                if re.match(r'^(?:minimum|required|desired|preferred|expected)\b', seg, re.IGNORECASE):
                    continue
                m = label_re.match(seg)
                if m:
                    rhs = m.group(1).strip()
                    dur_m = _parse_duration_text(rhs)
                    if dur_m > 0:
                        best_months = max(best_months, dur_m)
                    else:
                        bare_num = re.match(r'^(\d+(?:\.\d+)?)\+?\s*$', rhs)
                        if bare_num:
                            yrs = float(bare_num.group(1))
                            if 0 < yrs < 50:
                                best_months = max(best_months, max(1, round(yrs * 12.0)))

        # Check 2-line split explicit label (e.g. "Total Work Experience\n5 years 6 months")
        if split_label_re.match(stripped_line) and curr_sec not in skip_lbls and idx + 1 < len(raw_lines):
            next_rhs = raw_lines[idx + 1]
            if not _DATE_RANGE_REGEX.search(next_rhs) and not re.match(r'^(?:19|20)\d{2}\b', next_rhs):
                dur_m = _parse_duration_text(next_rhs)
                if dur_m > 0:
                    best_months = max(best_months, dur_m)
                else:
                    bare_num = re.match(r'^(\d+(?:\.\d+)?)\+?\s*$', next_rhs)
                    if bare_num:
                        yrs = float(bare_num.group(1))
                        if 0 < yrs < 50:
                            best_months = max(best_months, max(1, round(yrs * 12.0)))

        lbl = detect_section_label(stripped_line)
        if lbl:
            curr_sec = lbl
            curr_raw_hdr = stripped_line.upper()
            # Keep inline text after colon if not skip section
            if lbl not in skip_lbls and ':' in stripped_line:
                after_col = stripped_line.split(':', 1)[1].strip()
                if after_col:
                    narrative_lines.append(after_col)
            continue

        include_for_narrative = (
            curr_sec in ("HEADER", "SUMMARY", "EXPERIENCE")
            or (
                curr_sec not in skip_lbls
                and any(k in curr_raw_hdr for k in ("QUALIFICATION", "HIGHLIGHT", "PROFILE", "ABOUT", "OBJECTIVE"))
            )
        )
        if include_for_narrative:
            narrative_lines.append(stripped_line)

    raw_narrative = "\n".join(narrative_lines) if narrative_lines else clean_text
    narrative_text = _normalize_written_numbers(raw_narrative)

    def _is_disqualified(src: str, start: int, end: int) -> bool:
        before = src[max(0, start - 75):start]
        after = src[end:min(len(src), end + 45)]
        if _EXPLICIT_DISQUALIFIER_AFTER_RE.search(after):
            return True
        if _EXPLICIT_DISQUALIFIER_BEFORE_RE.search(before):
            if not _WORKED_AT_COMPANY_FOR_RE.search(before):
                return True
        if re.search(
            r'\b(?:juniors?|freshers?|graduates?|interns?|trainees?|hires?|peers?|students?|members?|subordinates?|colleagues?)\s+with\s*$',
            before,
            re.IGNORECASE,
        ):
            return True
        return False

    # Pattern 1: Numeric years (+ optional range, + optional months) + 0-6 domain words + experience keyword
    pat_1 = re.compile(
        rf'\b(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?)\s*|\bto\b\s*(\d+(?:\.\d+)?)\s*)?\+?\s*(?:[-–]\s*year\b|(?:years?|yrs?\.?)[\'’]?)'
        rf'(?:\s*(?:and|,|&)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?\.?))?\s+'
        rf'(?:of\s+)?(?:{_MOD_WORD},?\s+){{0,6}}'
        rf'(?:experience|exp\.?|expertise|background|service|track\s+record|career|tenure|proficiency|work\s+history)\b',
        re.IGNORECASE,
    )
    for m in pat_1.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        y1 = float(m.group(1))
        y2_str = m.group(2) or m.group(3)
        y2 = float(y2_str) if y2_str else None
        extra_mo = float(m.group(4)) if m.group(4) else 0.0
        if y1 >= 50 or (y2 is not None and y2 >= 50):
            continue
        yrs = ((y1 + y2) / 2.0) if (y2 is not None and y2 > y1 and (y2 - y1) <= 5) else y1
        if 0 <= yrs < 50:
            mos = round(yrs * 12.0 + extra_mo)
            if 0 < mos < 600:
                best_months = max(best_months, mos)

    # Pattern 1b: Gerund/role phrasing ('Over 5 years working as a Production Operator', '6+ years developing backend systems')
    pat_gerund = re.compile(
        r'\b(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?\.?)\s+(?:of\s+)?'
        r'(?:working|serving|practicing|operating|managing|developing|building|leading|'
        r'designing|teaching|nursing|coding|programming|testing|engineering|maintaining|'
        r'supervising|selling|driving|delivering|welding|assembling|inspecting|handling|'
        r'supporting|assisting|auditing|accounting|encoding|cooking|baking)\b',
        re.IGNORECASE,
    )
    for m in pat_gerund.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    # Pattern 2: YoE shorthand ('6+ YoE', '4.5 YoE')
    pat_2 = re.compile(r'\b(\d+(?:\.\d+)?)\+?\s*yoe\b', re.IGNORECASE)
    for m in pat_2.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    # Pattern 3: Reversed phrasing ('experience of 7 years', 'experienced in QA for over 4 years')
    pat_3a = re.compile(
        r'\b(?:experience|exp\.?|career|tenure|background|service)\s+(?:of|spanning|totaling|totalling|exceeding)\s+'
        r'(?:over|more\s+than|at\s+least|nearly|almost|about|around|approx\.?|approximately)?\s*'
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?\.?)(?:\s*(?:and|,|&)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?\.?))?\b',
        re.IGNORECASE,
    )
    for m in pat_3a.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        extra_mo = float(m.group(2)) if m.group(2) else 0.0
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0 + extra_mo)))

    pat_3b = re.compile(
        r'\b(?:experienced|working|employed|practicing|serving|operating)\s+'
        r'(?:(?:as\s+(?:a|an)\s+|in\s+|for\s+)[A-Za-z0-9&/\-,\s]{2,40}\s+)?for\s+'
        r'(?:over|more\s+than|at\s+least|nearly|almost|about|around|approx\.?|approximately)?\s*'
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?\.?)(?:\s*(?:and|,|&)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?\.?))?\b',
        re.IGNORECASE,
    )
    for m in pat_3b.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        extra_mo = float(m.group(2)) if m.group(2) else 0.0
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0 + extra_mo)))

    # Pattern 4: 'X years in <industry/field>' or 'X years as a/an <role>'
    pat_4 = re.compile(
        r'\b(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?\.?)\s+'
        r'(?:in\s+(?:the\s+)?(?:[A-Za-z0-9&/\-]+\s+){0,2}'
        r'(?:industry|field|practice|sector|IT|tech|software|engineering|manufacturing|production|'
        r'construction|sales|marketing|retail|hospitality|resort\s+operations|food\s+service|culinary|'
        r'healthcare|nursing|clinical|finance|accounting|banking|audit|tax|customer\s+service|BPO|'
        r'logistics|supply\s+chain|warehouse|operations|quality\s+control|quality\s+assurance|QA|QC|'
        r'maintenance|administration|HR|human\s+resources|education|teaching|procurement|legal|'
        r'design|media|data|cloud|cybersecurity|maritime|aviation|automotive|telecommunications|real\s+estate|'
        r'management|project\s+management|hotel\s+management|customer\s+support|call\s+center|fast\s+food|'
        r'food\s+and\s+beverage|f&b|electronics|semiconductor|e-commerce|ecommerce|merchandising|security|'
        r'housekeeping|electrical|mechanical|civil|chemical|industrial|materials|architecture|pharmacy|'
        r'medical|analytics|devops|testing|support|helpdesk|virtual\s+assistance|freelancing|consulting|'
        r'training|recruitment|payroll|bookkeeping|purchasing|inventory|shipping|driving|delivery|'
        r'welding|fabrication|machining|packaging|plastics|ceramics|agriculture)'
        r'|as\s+(?:a|an)\s+[A-Za-z])',
        re.IGNORECASE,
    )
    for m in pat_4.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        if 0 < yrs < 50:
            best_months = max(best_months, max(1, round(yrs * 12.0)))

    # Pattern 5: Months-only explicit ('18 months of experience', '6-month internship experience', '22 months in resort operations')
    pat_5 = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:[-–]\s*month\s+(?:[A-Za-z0-9&/\-]+\s+){0,3}(?:experience|exp\.?|internship|ojt|practicum)'
        r'|(?:months?|mos?\.?)\s+(?:of\s+(?:[A-Za-z0-9&/\-]+\s+){0,5}(?:experience|exp\.?)|in\s+(?:[A-Za-z0-9&/\-]+\s+){0,3}(?:operations|industry|field|manufacturing|retail|sales|IT|software|BPO|hospitality|resort\s+operations|nursing|teaching|accounting|finance|logistics|warehouse|customer\s+service|management|support)))\b',
        re.IGNORECASE,
    )
    for m in pat_5.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        mos = float(m.group(1))
        if 0 < mos < 600:
            best_months = max(best_months, max(1, round(mos)))

    # Pattern 6: Career start in summary ('Working as a Software Engineer since January 2020', 'Software Engineer since 2020', 'Career spanning 2018 - Present')
    now = datetime.now()
    pat_6 = re.compile(
        rf'\b(?:working|employed|practicing|freelancing|developing|operating|serving|in\s+the\s+(?:industry|field))'
        rf'(?:\s+(?:as\s+(?:a|an)\s+|in\s+)[A-Za-z0-9/&\-\s]{{2,40}})?\s+since\s+'
        rf'((?:{_MONTHS_NAMES}\.?\s*[,.]?\s*)?(?:19|20)\d{{2}})\b',
        re.IGNORECASE,
    )
    for m in pat_6.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        _, s_yr, s_mo = _parse_single_date(m.group(1), is_end=False)
        if s_yr and s_mo and (s_yr, s_mo) <= (now.year, now.month):
            mos = max(1, (now.year - s_yr) * 12 + (now.month - s_mo) + 1)
            if 0 < mos < 600:
                best_months = max(best_months, mos)

    pat_6_title_since = re.compile(
        rf'\b([A-Za-z][A-Za-z0-9/&\-\s]{{1,40}})\s+since\s+((?:{_MONTHS_NAMES}\.?\s*[,.]?\s*)?(?:19|20)\d{{2}})\b',
        re.IGNORECASE,
    )
    _SINCE_DISQUAL_RE = re.compile(
        r'\b(?:living|residing|resided|lived|member|founded|established|graduated|born|married|schooling|student|incorporated)\b',
        re.IGNORECASE,
    )
    for m in pat_6_title_since.finditer(narrative_text):
        prefix_phrase = m.group(1).strip()
        if _SINCE_DISQUAL_RE.search(prefix_phrase) or _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        if _JOB_TITLE_KEYWORDS_RE.search(prefix_phrase):
            _, s_yr, s_mo = _parse_single_date(m.group(2), is_end=False)
            if s_yr and s_mo and (s_yr, s_mo) <= (now.year, now.month):
                mos = max(1, (now.year - s_yr) * 12 + (now.month - s_mo) + 1)
                if 0 < mos < 600:
                    best_months = max(best_months, mos)

    pat_6_span = re.compile(
        rf'\b(?:career|experience|tenure|work\s+history)\s+(?:spanning|from)\s+([^\n.;]+)',
        re.IGNORECASE,
    )
    for m in pat_6_span.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        _, _, span_mos, _ = _parse_date_and_duration(m.group(1))
        if 0 < span_mos < 600:
            best_months = max(best_months, span_mos)

    # Pattern 7: Tagalog explicit ('5 taong karanasan sa trabaho', '2 taon at 6 buwan na karanasan', '6 na buwang karanasan')
    pat_7_yr = re.compile(
        r'\b(\d+(?:\.\d+)?)\+?\s*taon(?:g)?(?:\s+at\s+(\d+(?:\.\d+)?)\s*(?:na\s+)?buwan(?:g)?)?\s+(?:na\s+)?(?:karanasan|sa\s+trabaho)\b',
        re.IGNORECASE,
    )
    for m in pat_7_yr.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        yrs = float(m.group(1))
        extra_mo = float(m.group(2)) if m.group(2) else 0.0
        if 0 < yrs < 50 and 0 <= extra_mo < 60:
            best_months = max(best_months, max(1, round(yrs * 12.0 + extra_mo)))

    pat_7_mo = re.compile(
        r'\b(\d+(?:\.\d+)?)\+?\s*(?:na\s+)?buwan(?:g)?\s+(?:na\s+)?(?:karanasan|sa\s+trabaho)\b',
        re.IGNORECASE,
    )
    for m in pat_7_mo.finditer(narrative_text):
        if _is_disqualified(narrative_text, m.start(), m.end()):
            continue
        mos = float(m.group(1))
        if 0 < mos < 600:
            best_months = max(best_months, max(1, round(mos)))

    return best_months


def extract_experience_years_float(text: str, structured: Optional[Dict[str, Any]] = None) -> float:
    """
    Return total years of work experience as a float rounded to 1 decimal place
    (e.g. 2.5 years for 30 months), reconciling structured timeline with explicit summary mentions.
    """
    if not text:
        return 0.0

    if structured is None:
        structured = extract_structured_experience(text)
    structured_months = int(structured.get("total_experience_months", 0) or 0)
    explicit_months = int(structured.get("explicit_experience_months") or _extract_explicit_experience_months(text))
    total_months = max(structured_months, explicit_months)
    if total_months <= 0:
        return 0.0
    return round(total_months / 12.0, 1)


def extract_years_experience(text: str, structured: Optional[Dict[str, Any]] = None) -> int:
    """
    Calculates total years of experience by reconciling merged structured duration months
    from work history with validated explicit summary/label mentions.
    """
    if not text:
        return 0

    if structured is None:
        structured = extract_structured_experience(text)
    structured_months = int(structured.get("total_experience_months", 0) or 0)
    explicit_months = int(structured.get("explicit_experience_months") or _extract_explicit_experience_months(text))
    total_months = max(structured_months, explicit_months)
    if total_months > 0:
        return max(1, (total_months + 6) // 12)

    return 0


def _order_entries_by_recency(entries: list[dict]) -> list[dict]:
    """
    Return entries ordered by recency (Present first, then latest end/start date,
    non-OJT preferred on equal recency, preserving document order on ties).
    """
    if not entries:
        return []
    has_any_date = any(e.get("start_date") or e.get("end_date") for e in entries)
    if not has_any_date:
        return list(entries)

    def _recency_key(item: Tuple[int, dict]) -> Tuple[int, int, int, int, int, int]:
        idx, e = item
        s_ym = _ym_to_index(e.get("start_date"))
        e_ym = _ym_to_index(e.get("end_date"))
        has_d = 1 if (s_ym is not None or e_ym is not None) else 0
        is_pres = 1 if e.get("end_date") == "Present" else 0
        non_ojt = 0 if e.get("employment_type") == "OJT" else 1
        return (has_d, is_pres, e_ym if e_ym is not None else -1, s_ym if s_ym is not None else -1, non_ojt, -idx)

    return [e for _, e in sorted(enumerate(entries), key=_recency_key, reverse=True)]


def _select_most_recent_entry(entries: list[dict]) -> Optional[dict]:
    ordered = _order_entries_by_recency(entries)
    return ordered[0] if ordered else None


def extract_job_title(text: str, entries: Optional[list[dict]] = None) -> str:
    """
    Extracts the candidate's primary job title from resume.
    Prefers most recent work experience role, falling back to header role tag.
    """
    if not text:
        return ""

    if entries is None:
        entries = extract_experience_entries(text)

    # 1. Most recent work experience role (highest confidence if available)
    if entries:
        for ent in _order_entries_by_recency(entries):
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
        for e in _order_entries_by_recency(entries):
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
        if re.search(rf'(?<![A-Za-z0-9]){re.escape(c)}(?![A-Za-z0-9])', comb, re.I):
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