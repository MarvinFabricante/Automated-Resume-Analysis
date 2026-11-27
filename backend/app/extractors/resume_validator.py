"""
Strict Resume / CV Document Gatekeeper
--------------------------------------
Deterministic, zero-LLM classifier that verifies whether an uploaded document
is genuinely a Resume, Curriculum Vitae (CV), or Philippine Biodata — and
rejects random PDFs/DOCX/TXT files (user manuals, theses, invoices, receipts,
certificates, clearances, transcripts, contracts, job postings, cover letters,
syllabi, articles, blank/unreadable/password-protected files, etc.).

Pure function module: no database access, no network calls, fast local execution.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ─── Non-Personal / Corporate / Document Word Filters ────────────────────────

_NON_PERSON_NAME_WORDS: Set[str] = {
    "inc", "incorporated", "corp", "corporation", "ltd", "limited", "llc", "co",
    "company", "enterprises", "enterprise", "industries", "solutions", "services",
    "technologies", "technology", "systems", "system", "software", "portal",
    "platform", "manual", "guide", "handbook", "playbook", "documentation",
    "document", "reference", "quickstart", "quick", "start", "operations",
    "operating", "procedure", "sop", "policy", "privacy", "terms", "conditions",
    "agreement", "contract", "memorandum", "memo", "notice", "letter", "report",
    "proposal", "thesis", "capstone", "manuscript", "abstract", "chapter",
    "section", "appendix", "invoice", "receipt", "billing", "statement",
    "quotation", "voucher", "payslip", "payroll", "order", "purchase",
    "certificate", "certification", "diploma", "transcript", "clearance",
    "license", "passport", "registration", "enrollment", "syllabus", "schedule",
    "outline", "agenda", "presentation", "slides", "brochure", "flyer", "menu",
    "catalog", "catalogue", "recipe", "article", "newsletter", "journal",
    "magazine", "book", "novel", "story", "poem", "lyrics", "form",
    "questionnaire", "survey", "checklist", "worksheet", "template", "sample",
    "university", "college", "school", "institute", "academy", "department",
    "office", "ministry", "bureau", "commission", "authority", "republic",
    "government", "municipality", "barangay", "province", "city", "hospital",
    "clinic", "church", "foundation", "association", "organization", "committee",
    "council", "board", "agency", "bank", "group", "holdings", "ceramics",
    "ceramic", "mariwasa", "siam", "manufacturing", "trading", "logistics",
    "posting", "vacancy", "hiring", "recruitment", "screening", "analysis",
    "automated", "matching", "description", "overview", "summary", "introduction",
    "table", "contents", "figure", "page", "part", "volume", "edition", "version",
    "confidential", "restricted", "internal", "copyright", "wikipedia",
}

_INSTITUTIONAL_EMAIL_PREFIXES: Set[str] = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "support", "help",
    "helpdesk", "info", "information", "admin", "administrator", "webmaster",
    "sales", "billing", "accounts", "accounting", "finance", "cashier",
    "treasury", "registrar", "admissions", "dean", "faculty", "office",
    "secretary", "guidance", "library", "contact", "inquiry", "inquiries",
    "customercare", "customerservice", "feedback", "hello", "team", "careers",
    "career", "jobs", "recruitment", "recruiting", "talent", "hr",
    "humanresources", "legal", "compliance", "privacy", "security", "press",
    "media", "marketing", "newsletter", "notifications", "alerts", "system",
    "automated", "mailer", "postmaster", "root",
}

# ─── Standalone Section Headings (English + Filipino/Tagalog) ────────────────

_CORE_HEADING_PATTERNS: Dict[str, re.Pattern] = {
    "EXPERIENCE": re.compile(
        r"^(?:work\s+experience|work\s+experiences|working\s+experience|"
        r"professional\s+experience|professional\s+experiences|employment\s+history|"
        r"work\s+history|career\s+history|career\s+experience|career\s+summary|"
        r"employment\s+record|employment\s+background|employment\s+details|"
        r"relevant\s+experience|relevant\s+work\s+experience|job\s+experience|"
        r"job\s+history|positions?\s+held|work\s+record|industry\s+experience|"
        r"experience|experiences|employment|internship|internships|"
        r"internship\s+experience|on[\s\-]the[\s\-]job\s+training(?:\s*\(ojt\))?|"
        r"ojt(?:\s+experience)?|practicum(?:\s+experience)?|apprenticeship|"
        r"work\s*(?:&|and|/)\s*internship(?:\s+experience)?|"
        r"experience\s*(?:&|and|/)\s*internships?|"
        r"experience\s*(?:&|and|/)\s*employment|work\s+background|"
        r"academic\s+appointments|professional\s+appointments|teaching\s+experience|"
        r"research\s+experience|clinical\s+experience|sea\s+service(?:\s+record)?|"
        r"karanasan\s+sa\s+trabaho|mga\s+karanasan\s+sa\s+trabaho|"
        r"kasaysayan\s+ng\s+trabaho|karanasan)$",
        re.IGNORECASE,
    ),
    "EDUCATION": re.compile(
        r"^(?:education|educational\s+background|educational\s+attainment|"
        r"educational\s+history|educational\s+qualifications?|"
        r"academic\s+background|academic\s+qualifications?|academic\s+history|"
        r"academic\s+record|academic\s+credentials?|schooling|scholastic\s+record|"
        r"education\s*(?:&|and|/)\s*training|degrees?|"
        r"edukasyon|pinag[\s\-]aralan|antas\s+ng\s+edukasyon|kasaysayan\s+ng\s+edukasyon)$",
        re.IGNORECASE,
    ),
    "SKILLS": re.compile(
        r"^(?:skills|technical\s+skills|core\s+competencies|key\s+skills|"
        r"professional\s+skills|relevant\s+skills|core\s+skills|hard\s+skills|"
        r"soft\s+skills|hard\s*(?:&|and|/)\s*soft\s+skills|"
        r"technical\s*(?:&|and|/)\s*soft\s+skills|skills?\s*(?:&|and|/)\s*competencies|"
        r"competencies\s*(?:&|and|/)\s*skills|skills?\s*(?:&|and|/)\s*abilities|"
        r"skills?\s*(?:&|and|/)\s*expertise|skills?\s*(?:&|and|/)\s*qualifications|"
        r"skills?\s*(?:&|and|/)\s*proficiencies|skills?\s*(?:&|and|/)\s*tools|"
        r"skills?\s*(?:&|and|/)\s*certifications?|technical\s+competencies|"
        r"technical\s+proficiency|technical\s+expertise|areas?\s+of\s+expertise|"
        r"competencies|proficiencies|skill\s*set|skills?\s+summary|"
        r"skills?\s+inventory|skills?\s+profile|computer\s+skills|it\s+skills|"
        r"office\s+skills|engineering\s+skills|tech\s+stack|tools\s*(?:&|and|/)\s*technologies|"
        r"summary\s+of\s+qualifications|key\s+qualifications|core\s+qualifications|"
        r"kasanayan|mga\s+kasanayan|kakayahan|mga\s+kakayahan)$",
        re.IGNORECASE,
    ),
}

_SUPPORTING_HEADING_PATTERNS: Dict[str, re.Pattern] = {
    "CERTIFICATIONS": re.compile(
        r"^(?:certifications?|certificates?|licenses?|licensure|"
        r"professional\s+certifications?|professional\s+licenses?|"
        r"certifications?\s*(?:&|and|/)\s*licenses?|"
        r"licenses?\s*(?:&|and|/)\s*certifications?|"
        r"licenses?\s*(?:&|and|/)\s*eligibilit(?:y|ies)|"
        r"eligibilit(?:y|ies)|government\s+eligibilit(?:y|ies)|"
        r"trainings?\s*(?:&|and|/)\s*certifications?|"
        r"certifications?\s*(?:&|and|/)\s*trainings?|"
        r"certifications?\s*(?:&|and|/)\s*awards?|"
        r"certifications?\s*(?:&|and|/)\s*achievements?|"
        r"professional\s+credentials?|accreditations?|"
        r"mga\s+sertipikasyon|sertipiko|lisensya)$",
        re.IGNORECASE,
    ),
    "TRAINING": re.compile(
        r"^(?:trainings?|seminars?|workshops?|seminars?\s*(?:&|and|/)\s*trainings?|"
        r"trainings?\s*(?:&|and|/)\s*seminars?|seminars?\s+attended|"
        r"trainings?\s+attended|professional\s+development|pagsasanay|mga\s+pagsasanay)$",
        re.IGNORECASE,
    ),
    "PROJECTS": re.compile(
        r"^(?:projects?|personal\s+projects?|academic\s+projects?|"
        r"relevant\s+projects?|key\s+projects?|work\s+projects?|portfolio|"
        r"featured\s+projects?|notable\s+projects?|project\s+highlights?)$",
        re.IGNORECASE,
    ),
    "RESUME_SUMMARY": re.compile(
        r"^(?:professional\s+summary|career\s+objective|career\s+summary|"
        r"career\s+profile|personal\s+profile|personal\s+statement|about\s+me|"
        r"professional\s+profile|objective|layunin|layunin\s+sa\s+trabaho|tungkol\s+sa\s+akin)$",
        re.IGNORECASE,
    ),
    "PERSONAL": re.compile(
        r"^(?:personal\s+information|personal\s+details|personal\s+data|"
        r"contact\s+information|contact\s+details|contact|biodata|bio[\s\-]data|"
        r"applicant\s+information|candidate\s+information|"
        r"impormasyong\s+personal|personal\s+na\s+impormasyon|datos\s+personal)$",
        re.IGNORECASE,
    ),
    "RESUME_REFERENCES": re.compile(
        r"^(?:character\s+references?|professional\s+references?|"
        r"personal\s+references?|list\s+of\s+references|mga\s+sanggunian)$",
        re.IGNORECASE,
    ),
    "AWARDS": re.compile(
        r"^(?:awards?|achievements?|honors?|honors?\s*(?:&|and|/)\s*awards?|"
        r"awards?\s*(?:&|and|/)\s*achievements?|accomplishments?|recognitions?)$",
        re.IGNORECASE,
    ),
    "VOLUNTEER": re.compile(
        r"^(?:volunteer(?:\s+experience|\s+work)?|community\s+service|civic\s+activities|"
        r"extra[\s\-]?curricular\s+activities|leadership(?:\s*(?:&|and|/)\s*activities)?)$",
        re.IGNORECASE,
    ),
    "LANGUAGES": re.compile(
        r"^(?:languages?|language\s+proficiency|language\s+skills)$",
        re.IGNORECASE,
    ),
    "AFFILIATIONS": re.compile(
        r"^(?:affiliations?|professional\s+affiliations?|memberships?|"
        r"professional\s+memberships?|organizations?)$",
        re.IGNORECASE,
    ),
    "PUBLICATIONS": re.compile(
        r"^(?:publications?|research\s+publications?|selected\s+publications?)$",
        re.IGNORECASE,
    ),
}

_DECORATION_STRIP_RE = re.compile(
    r"^[\s\-–—=_*#•►◆■□▪▸▹:│┃><~«»|()\[\]]+|[\s\-–—=_*#•►◆■□▪▸▹:│┃><~«»|()\[\]]+$"
)
_LEADING_INDEX_RE = re.compile(r"^(?:(?:\d{1,2}|[ivxlc]{1,4})[\.\)\-:]\s+)", re.IGNORECASE)

# Explicit standalone resume / CV / biodata document header
_EXPLICIT_RESUME_TITLE_RE = re.compile(
    r"^(?:curriculum\s+vitae|r[eé]sum[eé]|bio[\s\-]?data|personal\s+data\s+sheet|"
    r"c\.?\s*v\.?|(?:[A-Z][A-Za-zÀ-ÿ.\-\s]{2,40}\s*[-–—|:]\s*(?:r[eé]sum[eé]|curriculum\s+vitae|bio[\s\-]?data|cv))|"
    r"(?:(?:r[eé]sum[eé]|curriculum\s+vitae)\s+of\s+[A-Z][A-Za-zÀ-ÿ.\-\s]{2,40}))$",
    re.IGNORECASE,
)

# Phrases that mean "resume" is being talked ABOUT (a tool/manual/guide), NOT that the doc IS a resume
_META_RESUME_SYSTEM_RE = re.compile(
    r"\b(?:resume\s+(?:analysis|parser|parsing|screening|scanner|scanning|builder|checker|"
    r"upload|guide|tips|system|platform|database|storage|repository|management)|"
    r"automated\s+resume|upload\s+your\s+resume|send\s+your\s+resume|submit\s+your\s+resume)\b",
    re.IGNORECASE,
)

# ─── Contact, Identity, Biodata & Content Patterns ───────────────────────────

_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+\-]+)@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?:\+?63[\s\-().]*9\d{2}[\s\-().]*\d{3}[\s\-().]*\d{4}|"
    r"\b09\d{2}[\s\-().]*\d{3}[\s\-().]*\d{4}\b|"
    r"(?:\+?\d{1,3}[\s\-().]+)?\(?\d{2,4}\)?[\s\-().]+\d{3,4}[\s\-().]+\d{4})"
)
_PROFILE_URL_RE = re.compile(
    r"\b(?:linkedin\.com/in/|github\.com/[A-Za-z0-9_\-]+|gitlab\.com/[A-Za-z0-9_\-]+|"
    r"behance\.net/|dribbble\.com/|portfolio\s*:)",
    re.IGNORECASE,
)

_BIODATA_FIELD_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:date\s+of\s+birth|birth\s*date|birthday|petsa\s+ng\s+kapanganakan)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:place\s+of\s+birth|birth\s*place|lugar\s+ng\s+kapanganakan)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:civil\s+status|marital\s+status|katayuang\s+sibil)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:nationality|citizenship|pagkamamamayan)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:religion|relihiyon)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:height|weight|taas|timbang)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:sex|gender|kasarian)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:age|edad)\s*[:\-]\s*\d{1,2}\b", re.IGNORECASE),
    re.compile(r"\b(?:present\s+address|permanent\s+address|home\s+address|residential\s+address|tirahan)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\b(?:father'?s?\s+name|mother'?s?\s+name|language[s]?\s+spoken)\s*[:\-]", re.IGNORECASE),
]

_DEGREE_RE = re.compile(
    r"\b(?:bachelor(?:'?s)?\s+(?:of|in)\s+[a-z]+|master(?:'?s)?\s+(?:of|in)\s+[a-z]+|"
    r"doctor\s+of\s+[a-z]+|ph\.?d\.?|m\.?b\.?a\.?|associate\s+(?:of|in|degree)|"
    r"b\.?s\.?\s+(?:in\s+)?(?:computer|information|civil|mechanical|electrical|industrial|"
    r"chemical|electronics|materials|accountancy|business|nursing|psychology|education|"
    r"hospitality|tourism|architecture|engineering|biology|mathematics|management|economics|finance)|"
    r"bsit|bscs|bscpe|bsce|bsis|bsme|bsee|bsie|bsba|bsa|bsn|bshm|bstm|bsed|beed|abm|humss|stem|tvl|"
    r"senior\s+high\s+school|high\s+school\s+(?:diploma|graduate)|secondary\s+education|"
    r"vocational(?:\s+diploma|\s+course|\s*/\s*technical)?|technical[\s\-]vocational|"
    r"diploma\s+in\s+[a-z]+|tesda\s+(?:nc\s*[i1-4]+|national\s+certificate|training)|"
    r"undergraduate|college\s+graduate|fresh\s+graduate)\b",
    re.IGNORECASE,
)

_SCHOOL_RE = re.compile(
    r"\b(?:university|polytechnic|state\s+college|colleges?\b|institute\s+of\s+technology|"
    r"national\s+high\s+school|high\s+school|academy|tesda|sti\s+college|ama\s+computer|"
    r"de\s+la\s+salle|ateneo|map[uú]a|far\s+eastern|santo\s+tomas|adamson|lyceum|"
    r"feati|cebu\s+institute|silliman|san\s+beda|let[r]an|arellano|centro\s+escolar)\b",
    re.IGNORECASE,
)

_DATE_RANGE_RE = re.compile(
    r"(?:\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s*(?:19|20)\d{2}|\b(?:19|20)\d{2})\s*(?:-|–|—|~|\bto\b)\s*"
    r"(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s*(?:19|20)\d{2}|(?:19|20)\d{2}|present|current|now|ongoing)\b",
    re.IGNORECASE,
)

_RESUME_ACTION_BULLET_RE = re.compile(
    r"^\s*(?:[•\-*▪►✓·]\s*)?"
    r"(?:managed|developed|built|designed|created|implemented|maintained|operated|"
    r"supervised|assisted|handled|performed|conducted|prepared|coordinated|led|"
    r"inspected|monitored|executed|delivered|engineered|analyzed|analysed|processed|"
    r"encoded|answered|updated|resolved|trained|taught|supported|organized|organised|"
    r"streamlined|optimized|optimised|collaborated|administered|audited|reconciled|"
    r"assembled|fabricated|repaired|troubleshot|installed|configured|tested|verified|"
    r"checked|packaged|packed|loaded|unloaded|cleaned|sanitized|served|transported|"
    r"responsible\s+for|duties\s+include)\b",
    re.IGNORECASE,
)

_CAREER_OBJECTIVE_RE = re.compile(
    r"\b(?:seeking\s+(?:a|an)\s+(?:challenging\s+)?(?:position|role|opportunity|career|job)|"
    r"to\s+obtain\s+(?:a|an)\s+(?:challenging\s+)?(?:position|role|opportunity)|"
    r"looking\s+for\s+(?:a|an)\s+(?:challenging\s+)?(?:position|role|opportunity|job)|"
    r"aiming\s+to\s+(?:leverage|contribute|apply|utilize)|"
    r"to\s+contribute\s+my\s+(?:skills|knowledge|experience)|"
    r"with\s+(?:over\s+)?\d+\+?\s*(?:years?|yrs?)\s+of\s+(?:professional\s+|work\s+|industry\s+|relevant\s+|hands[\s\-]on\s+)?experience|"
    r"dedicated\s+(?:recent\s+)?(?:[a-z]+\s+){0,3}(?:graduate|professional|engineer|developer|technician|specialist|operator|worker)|"
    r"motivated\s+and\s+(?:hardworking|detail[\s\-]oriented|results[\s\-]driven|dedicated)|"
    r"character\s+references?|references?\s+(?:are\s+)?(?:available|furnished)\s+upon\s+request)\b",
    re.IGNORECASE,
)

_RESUME_CERT_RE = re.compile(
    r"\b(?:tesda|nc\s*[i1-4]{1,3}|prc\s+(?:license|board|registered)|board\s+passer|"
    r"civil\s+service\s+(?:eligibility|professional|sub[\s\-]?professional)|"
    r"bosh\s*(?:so[1-4])?|cosh|certified\s+public\s+accountant|registered\s+nurse|"
    r"registered\s+(?:civil|electrical|mechanical|master)\s+(?:engineer|plumber)|"
    r"aws\s+certified|cisco\s+certified|ccna|ccnp|comptia|pmp|lean\s+six\s+sigma|"
    r"lto\s+(?:professional\s+)?driver'?s?\s+license|basic\s+life\s+support)\b",
    re.IGNORECASE,
)

_EXPLICIT_SKILLS_LIST_RE = re.compile(
    r"\b(?:proficient\s+in|skilled\s+in|knowledgeable\s+in|experienced\s+in|"
    r"expertise\s+in|well[\s\-]versed\s+in|competent\s+in|"
    r"(?:technical\s+|core\s+|key\s+|computer\s+)?skills\s*[:\-])\s*[^\n]{4,}",
    re.IGNORECASE,
)

_GARBAGE_EXP_ORG_RE = re.compile(
    r"^(?:chapter|section|part|step|module|unit|lesson|week|figure|table|appendix|"
    r"manual|guide|system|portal|page|slide|item|article|clause|thesis|capstone|"
    r"manuscript|abstract|methodology|literature|study|research|respondent|adviser|advisor)\b",
    re.IGNORECASE,
)

_GARBAGE_EXP_TITLE_RE = re.compile(
    r"\b(?:user\s+manual|recruiter\s+guide|quick\s+start|operations\s+manual|"
    r"admin\s+guide|step[\s\-]by[\s\-]step|table\s+of\s+contents|chapter\s+\d+|"
    r"thesis\s+(?:adviser|advisor|manuscript|committee|proposal|defense)|"
    r"capstone\s+(?:adviser|advisor|manuscript|project|documentation)|"
    r"panel\s+of\s+examiners|research\s+methodology|statement\s+of\s+the\s+problem|"
    r"review\s+of\s+related\s+(?:literature|studies))\b",
    re.IGNORECASE,
)

_ACADEMIC_YEAR_PREFIX_RE = re.compile(
    r"\b(?:s\.?\s*y\.?|a\.?\s*y\.?|school\s+year|academic\s+year|semester|term|batch)\s*[:\-]?\s*$",
    re.IGNORECASE,
)

_ACADEMIC_PROSE_LINE_RE = re.compile(
    r"\b(?:the\s+researchers?|respondents?|proponents?|adviser|advisor|panelist|"
    r"panel\s+member|critic\s+reader|this\s+study|this\s+research|this\s+thesis|"
    r"this\s+paper|likert\s+scale|weighted\s+mean|iso(?:/iec)?\s*25010|"
    r"alpha\s+and\s+beta\s+testing|survey\s+questionnaire|data\s+gathering|"
    r"partial\s+fulfillment|presented\s+to\s+the\s+faculty|submitted\s+to\s+the\s+faculty|"
    r"waterfall\s+model|agile\s+scrum\s+methodology|developmental\s+research)\b",
    re.IGNORECASE,
)

_THESIS_DEGREE_BOILERPLATE_RE = re.compile(
    r"\b(?:partial\s+fulfillment|requirements?\s+for\s+the\s+degree|"
    r"presented\s+to\s+the\s+faculty|submitted\s+to\s+the\s+faculty|"
    r"approval\s+sheet|degree\s+of\s+bachelor|degree\s+of\s+master)\b",
    re.IGNORECASE,
)

# Job-role cue for validating work experience without dates (e.g. messy/undated resumes)
_ROLE_KEYWORD_RE = re.compile(
    r"\b(?:engineer|developer|programmer|architect|designer|manager|supervisor|"
    r"director|specialist|analyst|consultant|officer|coordinator|administrator|"
    r"technician|operator|assistant|associate|representative|agent|clerk|cashier|"
    r"accountant|auditor|bookkeeper|nurse|teacher|instructor|professor|intern|"
    r"trainee|crew|attendant|driver|rider|helper|worker|welder|electrician|"
    r"mechanic|machinist|inspector|checker|encoder|receptionist|staff|lead|head|"
    r"housekeeper|janitor|guard|merchandiser|salesperson|barista|cook|chef|baker|"
    r"pharmacist|therapist|writer|editor|recruiter|generalist|planner|buyer|packer)\b",
    re.IGNORECASE,
)

_ORG_SUFFIX_RE = re.compile(
    r"\b(?:inc\.?|corp\.?|corporation|ltd\.?|llc|co\.?|company|enterprises?|"
    r"industries|solutions|services|systems|technologies|holdings|group|"
    r"manufacturing|trading|bank|hospital|hotel|restaurant|foods|ceramics|"
    r"construction|logistics|motors|retail|supply|studio|agency|builders|phils\.?|"
    r"philippines|branch|plant|factory)\b",
    re.IGNORECASE,
)

# ─── Negative (Non-Resume) Document Classifiers ──────────────────────────────

_NON_RESUME_RULES: Dict[str, Dict[str, Any]] = {
    "manual_or_guide": {
        "label": "User Manual / Guide / Documentation",
        "title_patterns": [
            (re.compile(r"\b(?:user(?:'?s)?\s+manual|end[\s\-]user\s+(?:product\s+)?manual|"
                        r"operations\s+manual|technical\s+(?:operations\s+)?manual|"
                        r"system\s+(?:administrator\s+)?manual|product\s+(?:&|and)\s+technical\s+(?:operations\s+)?manual|"
                        r"instruction\s+manual|training\s+manual|quick\s*start(?:\s+reference)?\s+(?:guide|manual)|"
                        r"reference\s+guide|user\s+guide|installation\s+guide|setup\s+guide|"
                        r"administrator\s+guide|developer\s+(?:&|and)\s+system\s+administrator\s+manual|"
                        r"standard\s+operating\s+procedure|employee\s+handbook|student\s+handbook|"
                        r"troubleshooting\s+guide|api\s+documentation|system\s+documentation|"
                        r"software\s+requirements?\s+specification|software\s+design\s+document|"
                        r"system\s+architecture\s+document|functional\s+specification|"
                        r"technical\s+specification|deployment\s+guide|configuration\s+guide|"
                        r"release\s+notes|enterprise\s+user\s+manual)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\btable\s+of\s+contents\b", re.IGNORECASE), 3.0),
            (re.compile(r"\b(?:document\s+reference|document\s+control|revision\s+history|"
                        r"software\s+version|target\s+audience|security\s+classification|"
                        r"effective\s+date|restricted\s*/\s*internal)\b", re.IGNORECASE), 2.5),
            (re.compile(r"\b(?:step[\s\-]by[\s\-]step\s+(?:operations?\s+)?guide|"
                        r"how\s+to\s+(?:use|install|start|configure|log\s*in)|"
                        r"frequently\s+asked\s+questions|\bfaq\b|troubleshooting)\b", re.IGNORECASE), 2.5),
            (re.compile(r"\b(?:click\s+(?:the|on)\s+[\"'\w]|navigate\s+to\s+https?://|"
                        r"log\s*in\s+with|sign\s*in\s+with|role[\s\-]based\s+access\s+control)\b", re.IGNORECASE), 2.5),
            (re.compile(r"\b(?:chapter\s+[1-9]\b|part\s+[1-9]\b|appendix\s+[a-z]\b)", re.IGNORECASE), 2.0),
            (re.compile(r"(?:©\s*(?:19|20)\d{2}|\ball\s+rights\s+reserved\b)", re.IGNORECASE), 2.0),
        ],
    },
    "academic_paper": {
        "label": "Thesis Manuscript / Academic Paper / Report",
        "title_patterns": [
            (re.compile(r"\b(?:submitted\s+in\s+partial\s+fulfillment|"
                        r"in\s+partial\s+fulfillment\s+of\s+the\s+requirements|"
                        r"partial\s+fulfillment\s+of\s+the\s+requirements|"
                        r"presented\s+to\s+the\s+faculty\s+of|submitted\s+to\s+the\s+faculty\s+of|"
                        r"thesis\s+manuscript|capstone\s+manuscript|research\s+manuscript|"
                        r"project\s+manuscript|final\s+manuscript|"
                        r"bachelor'?s\s+thesis|master'?s\s+thesis|undergraduate\s+thesis|"
                        r"graduate\s+thesis|doctoral\s+dissertation|dissertation\s+manuscript|"
                        r"capstone\s+project\s+(?:documentation|manuscript|paper|report|proposal)|"
                        r"thesis\s+proposal|capstone\s+proposal|research\s+proposal|"
                        r"research\s+paper|term\s+paper|laboratory\s+report|lab\s+report|"
                        r"feasibility\s+study|business\s+plan|project\s+proposal|"
                        r"annual\s+report|financial\s+report|incident\s+report|"
                        r"ojt\s+narrative\s+report|practicum\s+(?:narrative\s+)?report|"
                        r"narrative\s+report|accomplishment\s+report|progress\s+report|"
                        r"case\s+study\s+report|book\s+report|reflection\s+paper|"
                        r"reaction\s+paper|position\s+paper|approval\s+sheet|"
                        r"certificate\s+of\s+originality|certification\s+of\s+originality)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:statement\s+of\s+the\s+problem|review\s+of\s+related\s+literature|"
                        r"related\s+literature\s+and\s+studies|conceptual\s+framework|"
                        r"theoretical\s+framework|scope\s+and\s+(?:delimitation|limitation)s?|"
                        r"significance\s+of\s+the\s+study|background\s+of\s+the\s+study|"
                        r"objectives\s+of\s+the\s+study|definition\s+of\s+terms|"
                        r"research\s+methodology|research\s+design|results?\s+and\s+discussion|"
                        r"summary\s+of\s+findings|conclusions?\s+and\s+recommendations?)\b", re.IGNORECASE), 3.5),
            (re.compile(r"^\s*(?:chapter\s+(?:[1-9]|1[0-5]|i{1,3}|iv|v|vi{0,3}|ix|x)\b.*|"
                        r"abstract|introduction|methodology|bibliography|works\s+cited|"
                        r"list\s+of\s+tables|list\s+of\s+figures|acknowledgements?|dedication)\s*$",
                        re.IGNORECASE | re.MULTILINE), 3.0),
            (re.compile(r"\b(?:figure\s+\d+[\.:\-]|fig\.\s*\d+[\.:\-]|table\s+(?:\d+|[ivx]+)[\.:\-]|"
                        r"et\s+al\.|doi\s*:\s*10\.)", re.IGNORECASE), 2.0),
        ],
    },
    "financial_document": {
        "label": "Invoice / Receipt / Financial Statement",
        "title_patterns": [
            (re.compile(r"\b(?:official\s+receipt|sales\s+invoice|tax\s+invoice|commercial\s+invoice|"
                        r"service\s+invoice|billing\s+statement|statement\s+of\s+account|"
                        r"purchase\s+order|delivery\s+receipt|acknowledg(?:e)?ment\s+receipt|"
                        r"proforma\s+invoice|price\s+quotation|bank\s+statement|"
                        r"credit\s+card\s+statement|pay\s*slip|payroll\s+summary|"
                        r"check\s+voucher|disbursement\s+voucher|income\s+tax\s+return|"
                        r"balance\s+sheet|income\s+statement|cash\s+flow\s+statement|"
                        r"trial\s+balance|budget\s+proposal|liquidation\s+report|expense\s+report|"
                        r"bir\s+form\s+(?:2316|1700|1701|2307)|certificate\s+of\s+compensation)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:invoice\s*(?:no\.?|number|#)|receipt\s*(?:no\.?|number|#)|"
                        r"o\.?r\.?\s*(?:no\.?|#)|p\.?o\.?\s*(?:no\.?|#)|vat\s+reg\.?\s*tin)\b", re.IGNORECASE), 3.0),
            (re.compile(r"\b(?:bill\s+to|ship\s+to|sold\s+to|payment\s+terms|due\s+date)\s*[:\-]?", re.IGNORECASE), 2.0),
            (re.compile(r"\b(?:sub[\s\-]?total|grand\s+total|total\s+amount\s+due|amount\s+due|"
                        r"balance\s+due|vatable\s+sales?|vat\s+amount|unit\s+price|change\s+due)\b", re.IGNORECASE), 2.5),
            (re.compile(r"\b(?:gross\s+pay|net\s+pay|basic\s+pay|withholding\s+tax|"
                        r"total\s+deductions|sss\s+contribution|philhealth\s+contribution|"
                        r"pag[\s\-]?ibig\s+contribution)\b", re.IGNORECASE), 3.0),
        ],
    },
    "certificate_or_official_record": {
        "label": "Certificate / Clearance / Transcript / Official Record",
        "title_patterns": [
            (re.compile(r"\b(?:certificate\s+of\s+(?:completion|appreciation|recognition|attendance|"
                        r"participation|achievement|employment|graduation|good\s+moral|indigency|"
                        r"residency|live\s+birth|marriage|registration|matriculation|grades|enrollment|no\s+marriage)|"
                        r"barangay\s+clearance|police\s+clearance|nbi\s+clearance|medical\s+certificate|"
                        r"birth\s+certificate|marriage\s+certificate|death\s+certificate|cenomar|"
                        r"transcript\s+of\s+records|official\s+transcript|report\s+card|"
                        r"grade\s+slip|assessment\s+of\s+fees|enrollment\s+form|registration\s+form|"
                        r"philippine\s+statistics\s+authority|national\s+bureau\s+of\s+investigation|"
                        r"philippine\s+identification\s+card|driver'?s\s+license\s+receipt|"
                        r"social\s+security\s+system\s+member|philhealth\s+member\s+data\s+record)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:this\s+is\s+to\s+certify\s+that|is\s+hereby\s+awarded\s+to|"
                        r"hereby\s+certifies\s+that|is\s+presented\s+to|in\s+grateful\s+recognition\s+of|"
                        r"for\s+having\s+successfully\s+completed|given\s+this\s+\d{1,2}(?:st|nd|rd|th)?\s+day\s+of)\b", re.IGNORECASE), 9.0),
            (re.compile(r"\b(?:office\s+of\s+the\s+registrar|university\s+registrar|"
                        r"general\s+weighted\s+average|grading\s+system|tuition\s+fee|"
                        r"miscellaneous\s+fee|subject\s+code|course\s+code|units\s+earned|"
                        r"remarks\s*:\s*passed)\b", re.IGNORECASE), 3.5),
        ],
    },
    "presentation_or_slides": {
        "label": "Presentation / Slide Deck",
        "title_patterns": [
            (re.compile(r"\b(?:slide\s+deck|presentation\s+slides|powerpoint\s+presentation|"
                        r"defense\s+presentation|capstone\s+defense\s+presentation|"
                        r"thesis\s+defense\s+presentation|project\s+pitch\s+deck)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"^\s*slide\s+\d+\b", re.IGNORECASE | re.MULTILINE), 3.5),
            (re.compile(r"\b(?:thank\s+you\s+for\s+listening|questions\s*\?\s*$|q\s*&\s*a\s*$|presented\s+by\s*:)\b", re.IGNORECASE | re.MULTILINE), 3.5),
            (re.compile(r"^\s*(?:agenda|outline|learning\s+objectives|discussion\s+points)\s*$", re.IGNORECASE | re.MULTILINE), 2.5),
        ],
    },
    "school_or_course_document": {
        "label": "School / Course Document (Syllabus, Module, Exam, or Assignment)",
        "title_patterns": [
            (re.compile(r"\b(?:course\s+syllabus|course\s+outline|class\s+schedule|"
                        r"exam\s+schedule|examination\s+paper|quiz\s+paper|answer\s+key|"
                        r"learning\s+module|self[\s\-]learning\s+module|activity\s+sheet|"
                        r"worksheet|laboratory\s+exercise|lab\s+exercise|homework\s+assignment|"
                        r"lesson\s+plan|lecture\s+notes|study\s+guide|class\s+handout)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:course\s+description|learning\s+outcomes|grading\s+criteria|"
                        r"midterm\s+exam|final\s+exam|credit\s+units|pre[\s\-]?requisite|"
                        r"instructor\s*:|professor\s*:|course\s+code\s*:)\b", re.IGNORECASE), 3.0),
            (re.compile(r"\b(?:directions\s*:\s*(?:choose|encircle|select|write|read|answer)|"
                        r"multiple\s+choice|true\s+or\s+false|fill\s+in\s+the\s+blanks?|"
                        r"score\s*:\s*___|\d+\s+points\s*\))\b", re.IGNORECASE), 4.0),
        ],
    },
    "legal_or_correspondence": {
        "label": "Contract / Agreement / Policy / Letter",
        "title_patterns": [
            (re.compile(r"\b(?:memorandum\s+of\s+agreement|memorandum\s+of\s+understanding|"
                        r"non[\s\-]?disclosure\s+agreement|confidentiality\s+agreement|"
                        r"employment\s+contract|service\s+agreement|lease\s+(?:agreement|contract)|"
                        r"terms\s+and\s+conditions|terms\s+of\s+(?:service|use)|privacy\s+policy|"
                        r"data\s+privacy\s+(?:policy|notice)|company\s+policy|deed\s+of\s+sale|"
                        r"affidavit\s+of|special\s+power\s+of\s+attorney|office\s+memorandum|"
                        r"inter[\s\-]?office\s+memorandum|memorandum\s+order|office\s+order|"
                        r"board\s+resolution|letter\s+of\s+intent|permission\s+letter|"
                        r"transmittal\s+letter|endorsement\s+letter|recommendation\s+letter|"
                        r"resignation\s+letter|notice\s+to\s+explain)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:know\s+all\s+men\s+by\s+these\s+presents|witnesseth|"
                        r"party\s+of\s+the\s+first\s+part|party\s+of\s+the\s+second\s+part|"
                        r"in\s+witness\s+whereof|hereby\s+agree\s+as\s+follows|"
                        r"indemnify\s+and\s+hold\s+harmless|force\s+majeure|notary\s+public)\b", re.IGNORECASE), 4.5),
            (re.compile(r"\b(?:whereas,\s+|shall\s+be\s+governed\s+by|doc\.?\s*no\.?\s*\d+.*page\s*no\.?)\b", re.IGNORECASE), 3.0),
            (re.compile(r"^\s*memorandum\s*$", re.IGNORECASE | re.MULTILINE), 4.5),
        ],
    },
    "job_posting": {
        "label": "Job Description / Job Posting",
        "title_patterns": [
            (re.compile(r"\b(?:job\s+description|job\s+posting|job\s+vacancy|job\s+announcement|"
                        r"job\s+opening|we\s+are\s+hiring|now\s+hiring|career\s+opportunity\s+notice)\b", re.IGNORECASE), 7.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:we\s+are\s+looking\s+for|join\s+our\s+team|about\s+the\s+role|"
                        r"the\s+ideal\s+candidate|successful\s+candidate\s+will|"
                        r"equal\s+opportunity\s+employer|how\s+to\s+apply|apply\s+now|"
                        r"send\s+your\s+(?:resume|cv)|what\s+we\s+offer|benefits\s+and\s+perks|"
                        r"salary\s+range|compensation\s+and\s+benefits|reports\s+to\s*:|"
                        r"you\s+will\s+be\s+responsible\s+for)\b", re.IGNORECASE), 3.0),
            (re.compile(r"\b(?:minimum\s+qualifications|required\s+qualifications|preferred\s+qualifications|"
                        r"position\s+overview|job\s+summary)\b", re.IGNORECASE), 2.5),
        ],
    },
    "misc_non_resume": {
        "label": "Non-Resume Document",
        "title_patterns": [
            (re.compile(r"\b(?:survey\s+questionnaire|product\s+catalog(?:ue)?|"
                        r"price\s+list|restaurant\s+menu|event\s+program|minutes\s+of\s+the\s+meeting|"
                        r"meeting\s+agenda|from\s+wikipedia,\s+the\s+free\s+encyclopedia)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:for\s+office\s+use\s+only|do\s+not\s+write\s+below\s+this\s+line|"
                        r"please\s+check\s+the\s+appropriate\s+box|strongly\s+agree.*strongly\s+disagree)\b", re.IGNORECASE), 4.0),
            (re.compile(r"\b(?:preheat\s+oven|tablespoons?|teaspoons?|nutrition\s+facts|"
                        r"once\s+upon\s+a\s+time|lorem\s+ipsum|this\s+page\s+was\s+last\s+edited|"
                        r"citation\s+needed)\b", re.IGNORECASE), 4.5),
            (re.compile(r"^\s*ingredients\s*:?\s*$", re.IGNORECASE | re.MULTILINE), 5.0),
        ],
    },
}

_LETTER_SALUTATION_RE = re.compile(
    r"^\s*(?:dear\s+(?:sir|madam|hiring|recruiter|hr|mr\.?|ms\.?|mrs\.?|dr\.?|team|selection)|"
    r"to\s+whom\s+it\s+may\s+concern)\b",
    re.IGNORECASE | re.MULTILINE,
)
_LETTER_CLOSING_RE = re.compile(
    r"^\s*(?:sincerely(?:\s+yours)?|respectfully(?:\s+yours)?|yours\s+(?:truly|sincerely|faithfully)|"
    r"best\s+regards|warm\s+regards|kind\s+regards|cordially(?:\s+yours)?)\s*,?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_ACADEMIC_CITATION_RE = re.compile(
    r"(?:\[\d{1,3}\]|\bet\s+al\.|\bdoi\s*:|\bisbn\b|\bvol\.\s*\d|\bpp\.\s*\d|"
    r"\bjournal\s+of\b|\bproceedings\s+of\b|\(\d{4}\)\.)",
    re.IGNORECASE,
)

# ─── Dedicated Thesis / Academic Manuscript Structural Patterns ──────────────

_THESIS_UNMISTAKABLE_BOILERPLATE_RE = re.compile(
    r"\b(?:submitted\s+in\s+partial\s+fulfillment|"
    r"in\s+partial\s+fulfillment\s+of\s+the\s+requirements|"
    r"partial\s+fulfillment\s+of\s+the\s+requirements|"
    r"presented\s+to\s+the\s+faculty\s+of|submitted\s+to\s+the\s+faculty\s+of|"
    r"thesis\s+manuscript|capstone\s+manuscript|research\s+manuscript|"
    r"project\s+manuscript|final\s+manuscript|"
    r"approval\s+sheet|certificate\s+of\s+originality|certification\s+of\s+originality|"
    r"endorsement\s+for\s+(?:oral\s+)?defense|recommendation\s+for\s+oral\s+examination|"
    r"panel\s+of\s+examiners|board\s+of\s+examiners|thesis\s+committee|"
    r"curriculum\s+vitae\s+of\s+the\s+researchers?|researchers?'?\s+curriculum\s+vitae|"
    r"researchers?'?\s+profiles?|proponents?'?\s+profiles?|"
    r"about\s+the\s+researchers?|biographical\s+sketch\s+of\s+the\s+researchers?)\b",
    re.IGNORECASE,
)

_THESIS_COVER_LINE_RE = re.compile(
    r"^(?:a\s+thesis(?:\s+(?:manuscript|proposal|paper|study|presented|submitted|entitled).*)?|"
    r"(?:an\s+)?undergraduate\s+thesis(?:\s+(?:manuscript|proposal|paper|presented|submitted).*)?|"
    r"(?:a\s+)?(?:bachelor'?s|master'?s|graduate)\s+thesis(?:\s+(?:manuscript|proposal|paper|presented|submitted).*)?|"
    r"(?:a\s+)?(?:doctoral\s+)?dissertation(?:\s+(?:manuscript|proposal|presented|submitted).*)?|"
    r"(?:a\s+)?capstone\s+project(?:\s+(?:documentation|manuscript|paper|report|proposal|presented|submitted).*)?|"
    r"(?:a\s+)?(?:research\s+paper|research\s+study|thesis\s+proposal|capstone\s+proposal|"
    r"research\s+proposal|feasibility\s+study|case\s+study\s+report|ojt\s+narrative\s+report|"
    r"practicum\s+narrative\s+report|narrative\s+report))$",
    re.IGNORECASE,
)

_CHAPTER_HEADING_RE = re.compile(
    r"^\s*(?:chapter|kabanata)\s+(?P<num>1[0-5]|[1-9]|i{1,3}|iv|v|vi{0,3}|ix|x|"
    r"one|two|three|four|five|six|seven|eight|nine|ten)\b"
    r"(?:\s*[:\-–—\.]\s*.*|\s+[A-Z0-9].*|\s*)$",
    re.IGNORECASE,
)

_CHAPTER_NUM_MAP: Dict[str, str] = {
    "i": "1", "one": "1", "ii": "2", "two": "2", "iii": "3", "three": "3",
    "iv": "4", "four": "4", "v": "5", "five": "5", "vi": "6", "six": "6",
    "vii": "7", "seven": "7", "viii": "8", "eight": "8", "ix": "9", "nine": "9",
    "x": "10", "ten": "10",
}

_DISTINCT_THESIS_SECTION_CUES: List[Tuple[str, re.Pattern]] = [
    ("statement_of_the_problem", re.compile(r"\b(?:statement\s+of\s+the\s+problem|paglalahad\s+ng\s+suliranin)\b", re.IGNORECASE)),
    ("background_of_the_study", re.compile(r"\b(?:background\s+of\s+the\s+study|the\s+problem\s+and\s+its\s+(?:background|setting)|kaligiran\s+ng\s+pag[\s\-]aaral)\b", re.IGNORECASE)),
    ("objectives_of_the_study", re.compile(r"\b(?:general\s+and\s+specific\s+objectives|objectives\s+of\s+the\s+study|research\s+objectives|layunin\s+ng\s+pag[\s\-]aaral)\b", re.IGNORECASE)),
    ("review_of_related_literature", re.compile(r"\b(?:review\s+of\s+related\s+(?:literature|studies)|related\s+literature\s+and\s+studies|review\s+of\s+literature|kaugnay\s+na\s+literatura(?:\s+at\s+pag[\s\-]aaral)?)\b", re.IGNORECASE)),
    ("conceptual_theoretical_framework", re.compile(r"\b(?:conceptual\s+framework|theoretical\s+framework|research\s+paradigm|input[\s\-]process[\s\-]output\s+(?:model|framework|diagram)|balangkas\s+(?:konseptwal|teoretikal))\b", re.IGNORECASE)),
    ("scope_and_delimitation", re.compile(r"\b(?:scope\s+and\s+(?:delimitation|limitation)s?|limitations?\s+of\s+the\s+study|saklaw\s+at\s+(?:limitasyon|delimitasyon))\b", re.IGNORECASE)),
    ("significance_of_the_study", re.compile(r"\b(?:significance\s+of\s+the\s+study|kahalagahan\s+ng\s+pag[\s\-]aaral)\b", re.IGNORECASE)),
    ("definition_of_terms", re.compile(r"\b(?:(?:operational\s+)?definition\s+of\s+terms|katuturan\s+ng\s+mga\s+talakay)\b", re.IGNORECASE)),
    ("hypothesis_of_the_study", re.compile(r"\b(?:null\s+hypothesis|alternative\s+hypothesis|hypothes(?:is|es)\s+of\s+the\s+study|research\s+hypothes(?:is|es))\b", re.IGNORECASE)),
    ("research_methodology", re.compile(r"\b(?:research\s+methodology|research\s+design|research\s+locale|locale\s+of\s+the\s+study|research\s+instrument|data\s+gathering\s+procedure|sampling\s+(?:technique|method|design)|population\s+and\s+sampling|respondents?\s+of\s+the\s+study|statistical\s+treatment\s+of\s+data|materials\s+and\s+methods|disenyo\s+ng\s+pananaliksik|metodolohiya\s+ng\s+pananaliksik)\b", re.IGNORECASE)),
    ("results_and_discussion", re.compile(r"\b(?:results?\s+and\s+discussion|presentation,?\s+analysis,?\s+and\s+interpretation\s+of\s+data|findings\s+and\s+discussion|experimental\s+results?|evaluation\s+results?|resulta\s+at\s+diskusyon)\b", re.IGNORECASE)),
    ("summary_conclusions_recommendations", re.compile(r"\b(?:summary\s+of\s+findings|summary,?\s+conclusions?,?\s+and\s+recommendations?|conclusions?\s+and\s+recommendations?|buod,?\s+konklusyon\s+at\s+rekomendasyon|konklusyon\s+at\s+rekomendasyon)\b", re.IGNORECASE)),
    ("thesis_evaluation_metrics", re.compile(r"\b(?:likert\s+scale|weighted\s+mean|slovins?\s+formula|cronbach'?s?\s+alpha|iso(?:/iec)?\s*25010|system\s+usability\s+scale)\b", re.IGNORECASE)),
    ("academic_front_back_matter", re.compile(r"^\s*(?:list\s+of\s+tables|list\s+of\s+figures|list\s+of\s+appendices|dedication|acknowledgements?|pasasalamat|paghahandog|bibliography|talasanggunian|works\s+cited|appendices|appendix\s+[a-z](?:\s*[:\-–—].*)?)\s*$", re.IGNORECASE | re.MULTILINE)),
]

_IMRAD_SECTION_PATTERNS: Dict[str, re.Pattern] = {
    "abstract": re.compile(r"^\s*abstract(?:\s*[:\-–—]\s*\S.*|\s*)$", re.IGNORECASE),
    "keywords": re.compile(r"^\s*(?:keywords?|index\s+terms)\s*[:\-–—]\s*\S+", re.IGNORECASE),
    "introduction": re.compile(r"^\s*(?:(?:[1-9]|i{1,3})[\.\)]\s*)?introduction\s*$", re.IGNORECASE),
    "related_work": re.compile(r"^\s*(?:(?:[1-9]|i{1,3}|iv|v)[\.\)]\s*)?(?:related\s+works?|literature\s+review|review\s+of\s+related\s+(?:literature|studies))\s*$", re.IGNORECASE),
    "methodology": re.compile(r"^\s*(?:(?:[1-9]|i{1,3}|iv|v)[\.\)]\s*)?(?:proposed\s+)?(?:methodology|methods?|materials\s+and\s+methods|research\s+methodology|system\s+architecture)\s*$", re.IGNORECASE),
    "results": re.compile(r"^\s*(?:(?:[1-9]|i{1,3}|iv|v)[\.\)]\s*)?(?:experimental\s+|evaluation\s+)?results?(?:\s+and\s+discussion)?\s*$", re.IGNORECASE),
    "conclusion": re.compile(r"^\s*(?:(?:[1-9]|i{1,3}|iv|v)[\.\)]\s*)?conclusions?(?:\s+and\s+(?:recommendations?|future\s+work))?\s*$", re.IGNORECASE),
}

_ACADEMIC_PROSE_RE = re.compile(
    r"\b(?:this\s+(?:study|research|paper|thesis|capstone)\s+"
    r"(?:aims?|seeks?|presents?|investigates?|examines?|focuses?|proposes?|evaluates?|explores?|addresses?|describes?)|"
    r"the\s+researchers?\s+(?:used|utilized|conducted|developed|designed|aimed|found|concluded|recommended|gathered|surveyed|interviewed|implemented|evaluated)|"
    r"based\s+on\s+the\s+findings|"
    r"in\s+this\s+(?:paper|study|research|thesis),?\s+we\s+(?:propose|present|introduce|evaluate|investigate|develop|analyze))\b",
    re.IGNORECASE,
)

_FIGURE_TABLE_CAPTION_RE = re.compile(
    r"\b(?:figure|fig\.?|table)\s+(?:\d+(?:\.\d+)?|[ivx]+)\s*[\.:\-–—]",
    re.IGNORECASE,
)

_ADVISER_OR_PROPONENT_RE = re.compile(
    r"\b(?:thesis\s+adviser|capstone\s+adviser|research\s+adviser|technical\s+adviser|"
    r"subject\s+adviser|project\s+adviser|critic\s+reader|panel\s+of\s+examiners|"
    r"oral\s+defense|thesis\s+defense|capstone\s+defense)\b|"
    r"^\s*(?:adviser|advisor|panelist|submitted\s+by|prepared\s+by|proponents?|researchers?)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)

_APPENDIX_HEADING_RE = re.compile(
    r"^\s*(?:appendices|appendix\s+[a-z0-9](?:\s*[:\-–—].*)?)\s*$",
    re.IGNORECASE,
)

_NON_RESUME_FILENAME_HINTS: List[Tuple[str, re.Pattern]] = [
    ("academic_paper", re.compile(r"\b(?:thesis|manuscript|dissertation|capstone|research[\s_\-]?paper|term[\s_\-]?paper|chapter[\s_\-]?\d|imrad|feasibility)\b", re.IGNORECASE)),
    ("manual_or_guide", re.compile(r"\b(?:user[\s_\-]?manual|manual|handbook|playbook|srs|sdd|documentation|specification)\b", re.IGNORECASE)),
    ("financial_document", re.compile(r"\b(?:invoice|receipt|payslip|payroll|quotation|billing|statement[\s_\-]?of[\s_\-]?account)\b", re.IGNORECASE)),
    ("certificate_or_official_record", re.compile(r"\b(?:clearance|transcript|diploma|grade[\s_\-]?slip|birth[\s_\-]?cert)\b", re.IGNORECASE)),
    ("legal_or_correspondence", re.compile(r"\b(?:contract|memorandum|affidavit|agreement|moa|mou|nda|resignation)\b", re.IGNORECASE)),
    ("presentation_or_slides", re.compile(r"\b(?:slides?|slide[\s_\-]?deck|presentation|pitch[\s_\-]?deck|powerpoint|defense[\s_\-]?deck)\b", re.IGNORECASE)),
    ("school_or_course_document", re.compile(r"\b(?:syllabus|module|worksheet|assignment|homework|exam|quiz|handout|lecture[\s_\-]?notes)\b", re.IGNORECASE)),
    ("misc_non_resume", re.compile(r"\b(?:questionnaire|survey|recipe|menu|minutes)\b", re.IGNORECASE)),
]

_RESUME_FILENAME_HINT_RE = re.compile(r"\b(?:resume|cv|curriculum|biodata|bio[\s_\-]?data|pds)\b", re.IGNORECASE)


def _analyze_academic_manuscript_signals(
    text: str,
    lines: List[str],
    has_academic_refs: bool,
) -> Dict[str, Any]:
    """
    Deterministic, zero-LLM structural detector specifically tuned to catch Thesis Manuscripts,
    Capstone Documentation, IMRaD / IEEE Papers, Research Proposals, and Academic Reports —
    including manuscripts that embed Researchers' Curriculum Vitae in an Appendix — while
    never falsely rejecting legitimate resumes that mention a student's thesis title or an
    academic CV with a Publications list.
    """
    score = 0.0
    hard_veto = False
    is_thesis_specific = False
    has_embedded_cv_appendix = False
    signals: List[str] = []

    # 1. Unmistakable thesis / dissertation / defense boilerplate anywhere in document
    boilerplate_matches = _THESIS_UNMISTAKABLE_BOILERPLATE_RE.findall(text)
    if boilerplate_matches:
        unique_bp = sorted({m.lower().strip() for m in boilerplate_matches})
        score += 12.0
        hard_veto = True
        is_thesis_specific = True
        signals.append(f"academic_paper:thesis_boilerplate({','.join(unique_bp[:3])})(+12.0)")

    # 2. Cover / front-matter explicit thesis/manuscript line BEFORE any core resume heading
    first_core_line_idx: Optional[int] = None
    first_appendix_line_idx: Optional[int] = None
    cv_title_occurrences = 0
    for idx, ln in enumerate(lines):
        norm = _normalise_heading_candidate(ln)
        if first_core_line_idx is None and norm and len(norm.split()) <= 6:
            if any(pat.match(norm) for pat in _CORE_HEADING_PATTERNS.values()):
                first_core_line_idx = idx
        if first_appendix_line_idx is None and _APPENDIX_HEADING_RE.match(ln):
            first_appendix_line_idx = idx
        if re.match(r"^(?:curriculum\s+vitae|researchers?'?\s+(?:curriculum\s+vitae|profile))$", norm, re.IGNORECASE):
            cv_title_occurrences += 1

    cover_limit = min(len(lines), 45)
    if first_core_line_idx is not None and first_core_line_idx < cover_limit:
        cover_scan_end = first_core_line_idx
    else:
        cover_scan_end = cover_limit

    for ln in lines[:cover_scan_end]:
        norm = _normalise_heading_candidate(ln)
        if norm and len(norm) <= 100 and _THESIS_COVER_LINE_RE.match(norm):
            score += 9.5
            hard_veto = True
            is_thesis_specific = True
            signals.append(f"academic_paper:cover_title({norm[:45]})(+9.5)")
            break

    # 3. Chapter headings (e.g. "CHAPTER 1: THE PROBLEM AND ITS BACKGROUND", "Chapter II - RRL")
    distinct_chapters: Set[str] = set()
    for ln in lines:
        if len(ln) > 130:
            continue
        m_ch = _CHAPTER_HEADING_RE.match(ln)
        if m_ch:
            raw_num = m_ch.group("num").lower()
            distinct_chapters.add(_CHAPTER_NUM_MAP.get(raw_num, raw_num))

    if len(distinct_chapters) >= 2:
        score += 10.5
        hard_veto = True
        is_thesis_specific = True
        signals.append(f"academic_paper:multiple_chapters({len(distinct_chapters)})(+10.5)")
    elif len(distinct_chapters) == 1:
        score += 4.5
        signals.append("academic_paper:chapter_heading(+4.5)")

    # 4. Distinct thesis/academic structural sections (scored individually, not lumped into 1 cap)
    matched_thesis_cues: List[str] = []
    for cue_name, cue_pat in _DISTINCT_THESIS_SECTION_CUES:
        if cue_pat.search(text):
            matched_thesis_cues.append(cue_name)

    if matched_thesis_cues:
        cue_pts = min(16.0, 3.5 * len(matched_thesis_cues))
        score += cue_pts
        signals.append(f"academic_paper:thesis_sections({','.join(matched_thesis_cues[:4])})(+{cue_pts:.1f})")
        if len(matched_thesis_cues) >= 2:
            hard_veto = True
            is_thesis_specific = True
        elif len(matched_thesis_cues) == 1 and len(distinct_chapters) >= 1:
            hard_veto = True
            is_thesis_specific = True

    # 5. IMRaD / IEEE / Conference academic paper headings
    imrad_found: Set[str] = set()
    for ln in lines:
        if len(ln) > 160:
            continue
        for sec_key, sec_pat in _IMRAD_SECTION_PATTERNS.items():
            if sec_pat.match(ln):
                # Guard bare "Abstract" / "Introduction" against long non-abstract lines
                if sec_key == "abstract" and ":" not in ln and "—" not in ln and "-" not in ln and len(ln.split()) > 2:
                    continue
                imrad_found.add(sec_key)
                break

    if len(imrad_found) >= 3:
        score += 10.0
        hard_veto = True
        signals.append(f"academic_paper:imrad_structure({','.join(sorted(imrad_found))})(+10.0)")
    elif len(imrad_found) == 2:
        score += 5.5
        signals.append(f"academic_paper:imrad_partial({','.join(sorted(imrad_found))})(+5.5)")
    elif len(imrad_found) == 1:
        score += 2.5
        signals.append(f"academic_paper:imrad_single({','.join(sorted(imrad_found))})(+2.5)")

    # 6. Academic prose, figure/table captions, adviser/proponent cues
    prose_hits = _ACADEMIC_PROSE_RE.findall(text)
    if len(prose_hits) >= 2:
        score += 5.5
        signals.append(f"academic_paper:academic_prose({len(prose_hits)})(+5.5)")
    elif len(prose_hits) == 1:
        score += 3.0
        signals.append("academic_paper:academic_prose(1)(+3.0)")

    caption_hits = _FIGURE_TABLE_CAPTION_RE.findall(text)
    if len(caption_hits) >= 2:
        score += 4.5
        signals.append(f"academic_paper:figure_table_captions({len(caption_hits)})(+4.5)")
    elif len(caption_hits) == 1:
        score += 2.0
        signals.append("academic_paper:figure_table_caption(1)(+2.0)")

    adviser_hits = _ADVISER_OR_PROPONENT_RE.findall(text)
    if adviser_hits:
        score += 3.5
        signals.append(f"academic_paper:adviser_or_proponent({len(adviser_hits)})(+3.5)")

    # Cross-signal hard vetos for IMRaD / partial thesis / proposal manuscripts
    has_strong_corroborator = bool(
        has_academic_refs
        or len(caption_hits) >= 1
        or len(prose_hits) >= 1
        or len(adviser_hits) >= 1
        or len(matched_thesis_cues) >= 1
        or len(distinct_chapters) >= 1
    )
    if len(imrad_found) >= 2 and has_strong_corroborator:
        hard_veto = True
    if len(prose_hits) >= 1 and (len(distinct_chapters) >= 1 or len(matched_thesis_cues) >= 1 or len(adviser_hits) >= 1 or len(caption_hits) >= 1):
        hard_veto = True
        if len(distinct_chapters) >= 1 or len(matched_thesis_cues) >= 1 or len(adviser_hits) >= 1:
            is_thesis_specific = True
    if len(adviser_hits) >= 1 and (len(distinct_chapters) >= 1 or len(matched_thesis_cues) >= 1 or len(imrad_found) >= 1):
        hard_veto = True
        if len(distinct_chapters) >= 1 or len(matched_thesis_cues) >= 1:
            is_thesis_specific = True

    # 7. Detect embedded Curriculum Vitae in a Thesis Appendix (e.g. "APPENDIX A: CURRICULUM VITAE")
    if (
        (first_appendix_line_idx is not None and first_core_line_idx is not None and first_appendix_line_idx < first_core_line_idx)
        or cv_title_occurrences >= 2
        or (
            first_core_line_idx is not None
            and len(lines) >= 35
            and first_core_line_idx > len(lines) * 0.45
            and (len(distinct_chapters) >= 1 or len(matched_thesis_cues) >= 1 or len(imrad_found) >= 1 or bool(prose_hits))
        )
    ):
        has_embedded_cv_appendix = True
        hard_veto = True
        is_thesis_specific = True
        score += 12.0
        signals.append("academic_paper:embedded_cv_in_appendix(+12.0)")

    return {
        "score": score,
        "hard_veto": hard_veto,
        "is_thesis_specific": is_thesis_specific,
        "has_embedded_cv_appendix": has_embedded_cv_appendix,
        "signals": signals,
    }


def _normalise_heading_candidate(line: str) -> str:
    s = line.strip()
    s = _DECORATION_STRIP_RE.sub("", s).strip()
    s = _LEADING_INDEX_RE.sub("", s).strip()
    s = _DECORATION_STRIP_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _is_valid_person_fullname(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    clean = re.sub(r"\s+", " ", name).strip()
    if len(clean) < 3 or len(clean) > 65:
        return False
    if any(ch in clean for ch in ("@", "/", "\\", "http", ":", "?", "!", ";")):
        return False
    if re.search(r"\d", clean):
        return False
    tokens = [re.sub(r"[^A-Za-zÀ-ÿ'\-]", "", t).lower() for t in clean.split()]
    tokens = [t for t in tokens if t]
    if len(tokens) < 2 or len(tokens) > 6:
        return False
    if any(t in _NON_PERSON_NAME_WORDS for t in tokens):
        return False
    return True


def _extract_personal_emails(text: str) -> List[str]:
    found: List[str] = []
    for m in _EMAIL_RE.finditer(text or ""):
        local_part = m.group(1).lower()
        full = m.group(0).lower()
        if local_part in _INSTITUTIONAL_EMAIL_PREFIXES:
            continue
        if any(local_part.startswith(p + ".") or local_part.startswith(p + "_") for p in ("noreply", "no-reply", "support", "admin", "billing")):
            continue
        if full not in found:
            found.append(full)
    return found


def _detect_strict_resume_headings(text: str) -> Tuple[Set[str], Set[str], bool]:
    """
    Scan lines for genuine standalone resume section headings (and clean non-schema inline headers).
    Returns (core_headings, supporting_headings, has_academic_references).
    """
    core: Set[str] = set()
    supporting: Set[str] = set()
    has_academic_refs = False
    lines = text.splitlines()

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or len(stripped) > 75:
            continue

        # Sentences ending with a period are prose, not standalone section headings
        ends_sentence = stripped.endswith(".") and not re.search(r"\b(?:inc|jr|sr|st|etc)\.$", stripped, re.I)

        # Check standalone heading (single or dual-column separated by '|')
        parts_to_check = [stripped]
        if "|" in stripped and stripped.count("|") == 1:
            left, right = [p.strip() for p in stripped.split("|", 1)]
            if left and right and len(left.split()) <= 5 and len(right.split()) <= 5:
                parts_to_check.extend([left, right])

        matched_standalone = False
        if not ends_sentence and ":" not in stripped:
            for part in parts_to_check:
                norm = _normalise_heading_candidate(part)
                if not norm or len(norm.split()) > 6:
                    continue
                for label, pat in _CORE_HEADING_PATTERNS.items():
                    if pat.match(norm):
                        core.add(label)
                        matched_standalone = True
                for label, pat in _SUPPORTING_HEADING_PATTERNS.items():
                    if pat.match(norm):
                        supporting.add(label)
                        matched_standalone = True
                # Bare "REFERENCES" requires disambiguation (Resume References vs Academic Bibliography)
                if re.match(r"^references?$", norm, re.IGNORECASE):
                    lookahead = "\n".join(lines[idx + 1 : idx + 15])
                    if _ACADEMIC_CITATION_RE.search(lookahead) and not re.search(
                        r"\b(?:available\s+upon\s+request|furnished\s+upon\s+request|"
                        r"character\s+reference|supervisor|manager|09\d{2}|\+63)\b",
                        lookahead,
                        re.IGNORECASE,
                    ):
                        has_academic_refs = True
                    else:
                        supporting.add("RESUME_REFERENCES")
                        matched_standalone = True

        # Clean inline colon header like "Skills: Python, React, SQL" or "Education: BSIT, UST"
        # Explicitly reject prose/schema definitions like "Work Experience: Job titles, employers, employment duration."
        if not matched_standalone and ":" in stripped:
            prefix, rest = stripped.split(":", 1)
            prefix_norm = _normalise_heading_candidate(prefix)
            rest_clean = rest.strip()
            is_schema_definition = bool(
                re.search(
                    r"\b(?:job\s+titles?,\s+employers?|highest\s+degree\s+earned|"
                    r"full\s+name,\s+email|technical\s+competencies,\s+certifications|"
                    r"employment\s+duration,\s+quantified|academic\s+institution,\s+major)\b",
                    rest_clean,
                    re.IGNORECASE,
                )
            )
            if prefix_norm and len(prefix_norm.split()) <= 4 and not is_schema_definition:
                # Bare inline colon header with nothing after colon (e.g. "WORK EXPERIENCE:")
                if not rest_clean:
                    for label, pat in _CORE_HEADING_PATTERNS.items():
                        if pat.match(prefix_norm):
                            core.add(label)
                    for label, pat in _SUPPORTING_HEADING_PATTERNS.items():
                        if pat.match(prefix_norm):
                            supporting.add(label)
                else:
                    # Inline populated header like "Skills: Python, FastAPI" or "Objective: Seeking..."
                    if _CORE_HEADING_PATTERNS["SKILLS"].match(prefix_norm) and not ends_sentence:
                        core.add("SKILLS")
                    elif _SUPPORTING_HEADING_PATTERNS["RESUME_SUMMARY"].match(prefix_norm):
                        supporting.add("RESUME_SUMMARY")
                    elif _SUPPORTING_HEADING_PATTERNS["CERTIFICATIONS"].match(prefix_norm) and not ends_sentence:
                        supporting.add("CERTIFICATIONS")

    return core, supporting, has_academic_refs


def _has_verified_work_experience(
    text: str,
    extracted_data: Dict[str, Any],
    sections: Dict[str, str],
) -> Tuple[bool, bool]:
    """
    Returns (has_dated_or_structured_exp, has_role_plus_org_or_bullets).
    Filters out hallucinated non-resume entries (e.g. company='CHAPTER 4', title='HR Recruiter Guide').
    """
    valid_dated = False
    valid_undated = False

    work_exps = extracted_data.get("work_experiences") or []
    for entry in work_exps:
        if not isinstance(entry, dict):
            continue
        title = (entry.get("job_title") or entry.get("role") or "").strip()
        comp = (entry.get("company_name") or entry.get("company") or "").strip()
        has_dates = bool(entry.get("start_date") or entry.get("end_date") or (entry.get("duration_months") or 0) > 0)

        if comp and _GARBAGE_EXP_ORG_RE.match(comp):
            continue
        if title and _GARBAGE_EXP_TITLE_RE.search(title):
            continue

        title_looks_real = bool(title) and len(title) <= 80 and (
            bool(_ROLE_KEYWORD_RE.search(title)) or bool(comp)
        )
        if title_looks_real and has_dates:
            valid_dated = True
            break
        if title_looks_real and comp and len(comp) >= 3 and not _GARBAGE_EXP_ORG_RE.match(comp):
            valid_undated = True

    if not valid_dated:
        exp_body = (sections.get("EXPERIENCE") or "").strip()
        if exp_body and _DATE_RANGE_RE.search(exp_body):
            valid_dated = True
        elif _DATE_RANGE_RE.search(text) and _ROLE_KEYWORD_RE.search(text):
            # Check if a genuine employment date range appears on the same or adjacent non-prose line as a role keyword
            text_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for idx, ln in enumerate(text_lines):
                if len(ln) > 140 or _ACADEMIC_PROSE_LINE_RE.search(ln):
                    continue
                for dm in _DATE_RANGE_RE.finditer(ln):
                    before_dm = ln[:dm.start()]
                    if _ACADEMIC_YEAR_PREFIX_RE.search(before_dm):
                        continue
                    # Ignore prose ranges like "from August 2025 - February 2026" inside long sentences
                    if re.search(r"\bfrom\s*$", before_dm, re.IGNORECASE) and len(ln.split()) >= 10:
                        continue
                    neighbor_lines = [ln]
                    if idx > 0 and len(text_lines[idx - 1]) <= 120 and not _ACADEMIC_PROSE_LINE_RE.search(text_lines[idx - 1]):
                        neighbor_lines.append(text_lines[idx - 1])
                    if idx + 1 < len(text_lines) and len(text_lines[idx + 1]) <= 120 and not _ACADEMIC_PROSE_LINE_RE.search(text_lines[idx + 1]):
                        neighbor_lines.append(text_lines[idx + 1])
                    if any(
                        _ROLE_KEYWORD_RE.search(nl)
                        and not re.match(r"^\s*(?:adviser|advisor|panelist|dean|chairperson|submitted\s+by|respondents?)\b", nl, re.IGNORECASE)
                        for nl in neighbor_lines
                    ):
                        valid_dated = True
                        break
                if valid_dated:
                    break

    if not valid_undated:
        # Check line-by-line (or adjacent short lines) for "<Role> at/@/- <Company>" — never match unrelated words pages apart
        text_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        role_at_org_re = re.compile(
            r"\b(?:engineer|developer|operator|technician|supervisor|manager|analyst|specialist|"
            r"assistant|coordinator|accountant|nurse|teacher|crew|driver|rider|clerk|cashier|"
            r"attendant|inspector|welder|electrician|mechanic|intern|designer|representative)"
            r"\s+(?:at|@|-|\||,)\s+[A-Z][A-Za-z0-9&.,'\-\s]{2,45}",
            re.IGNORECASE,
        )
        for idx, ln in enumerate(text_lines):
            if len(ln) > 130 or _ACADEMIC_PROSE_LINE_RE.search(ln):
                continue
            if role_at_org_re.search(ln):
                valid_undated = True
                break
            if (
                len(ln) <= 100
                and _ROLE_KEYWORD_RE.search(ln)
                and not re.match(r"^\s*(?:adviser|advisor|panelist|dean|submitted\s+by|respondents?)\b", ln, re.IGNORECASE)
            ):
                if _ORG_SUFFIX_RE.search(ln):
                    valid_undated = True
                    break
                if idx + 1 < len(text_lines):
                    nxt = text_lines[idx + 1]
                    if len(nxt) <= 90 and not _ACADEMIC_PROSE_LINE_RE.search(nxt) and _ORG_SUFFIX_RE.search(nxt):
                        valid_undated = True
                        break

    return valid_dated, valid_undated


def _has_verified_education(
    text: str,
    extracted_data: Dict[str, Any],
    sections: Dict[str, str],
) -> Tuple[bool, bool]:
    """
    Returns (has_strong_education, has_partial_education).
    Requires genuine academic degree or educational institution keywords (never hallucinated manual titles
    or thesis cover-page boilerplate like "In Partial Fulfillment of the Requirements for the Degree...").
    """
    # Strip thesis cover-page boilerplate lines before scanning raw text for degree/school
    filtered_lines: List[str] = []
    skip_next_degree = False
    for ln in text.splitlines():
        if _THESIS_DEGREE_BOILERPLATE_RE.search(ln):
            skip_next_degree = True
            continue
        if skip_next_degree and ln.strip():
            # Line immediately following "In Partial Fulfillment of the Requirements for the Degree"
            skip_next_degree = False
            if _DEGREE_RE.search(ln):
                continue
        filtered_lines.append(ln)
    edu_scan_text = "\n".join(filtered_lines)

    has_degree = bool(_DEGREE_RE.search(edu_scan_text))
    has_school = bool(_SCHOOL_RE.search(edu_scan_text))

    if has_degree and has_school:
        return True, True

    edu_sec = (sections.get("EDUCATION") or "").strip()
    if edu_sec and (bool(_DEGREE_RE.search(edu_sec)) or bool(_SCHOOL_RE.search(edu_sec))):
        return True, True

    # Check structured education entries only if degree_or_course or institution actually matches academic terms
    for edu in extracted_data.get("education_entries") or []:
        if not isinstance(edu, dict):
            continue
        deg = (edu.get("degree_or_course") or "").strip()
        inst = (edu.get("institution_name") or "").strip()
        if _THESIS_DEGREE_BOILERPLATE_RE.search(deg) or _THESIS_DEGREE_BOILERPLATE_RE.search(inst):
            continue
        deg_ok = bool(deg and _DEGREE_RE.search(deg))
        inst_ok = bool(inst and _SCHOOL_RE.search(inst))
        if deg_ok and inst_ok:
            return True, True
        if deg_ok or inst_ok:
            return False, True

    if has_degree:
        return False, True

    return False, False


def _build_rejection_message(
    detected_type: str,
    reason_code: str,
    ai_reason: Optional[str] = None,
    verified_by: Optional[str] = None,
) -> str:
    if reason_code == "password_protected":
        return (
            "Wrong document detected (Password-Protected File). This file is password-protected and cannot be verified as a resume. "
            "Please remove the password and upload an unprotected resume file (PDF, DOCX, DOC, or TXT)."
        )
    if reason_code == "unreadable_or_empty":
        return (
            "Wrong document detected (Unreadable or Blank File). We could not read enough text from this file to verify that it is a resume. "
            "Please upload a clear, text-based resume or CV (PDF, DOCX, DOC, or TXT)."
        )
    if reason_code == "blank_form":
        return (
            "Wrong document detected (Blank Form / Empty Template). This file appears to be a blank form or template with no candidate details filled in. "
            "Please upload your completed resume or CV."
        )

    predictor_prefix = "AI Predicted" if verified_by == "AI" else "Predicted"
    reason_suffix = f" Reason: {ai_reason.strip().rstrip('.')}." if (ai_reason and ai_reason.strip()) else ""

    if reason_code == "detected_thesis_manuscript":
        return (
            f"Wrong document detected ({predictor_prefix}: Thesis / Capstone Manuscript). "
            f"Only resume or CV documents are accepted. The uploaded file appears to be a thesis or "
            f"capstone manuscript, not a resume.{reason_suffix} Please upload a valid resume containing your personal "
            f"details, education, skills, or work experience."
        )

    type_labels = {
        "manual_or_guide": ("User Manual / Guide", "a user manual or guide"),
        "academic_paper": ("Thesis Manuscript / Academic Paper / Report", "a thesis manuscript, academic paper, or report"),
        "financial_document": ("Invoice / Receipt / Financial Statement", "an invoice, receipt, or financial document"),
        "certificate_or_official_record": ("Certificate / Clearance / Official Record", "a certificate, clearance, or official record"),
        "legal_or_correspondence": ("Contract / Policy / Letter", "a contract, policy, or standalone letter"),
        "cover_letter": ("Standalone Cover / Application Letter", "a standalone cover letter or application letter"),
        "presentation_or_slides": ("Presentation / Slide Deck", "a presentation slide deck"),
        "school_or_course_document": ("School / Course Document", "a syllabus, module, exam, or school assignment"),
        "job_posting": ("Job Description / Job Posting", "a job posting or job description"),
        "misc_non_resume": ("Non-Resume Document", "a non-resume document"),
    }
    entry = type_labels.get(detected_type)
    if entry:
        short_label, human_type = entry
        return (
            f"Wrong document detected ({predictor_prefix}: {short_label}). "
            f"Only resume or CV documents are accepted. The uploaded file appears to be {human_type}, "
            f"not a resume.{reason_suffix} Please upload a valid resume containing your personal details, education, "
            f"skills, or work experience."
        )
    return (
        f"Wrong document detected ({predictor_prefix}: Non-Resume Document). "
        f"Only resume or CV documents are accepted. The uploaded file does not appear to be a valid "
        f"resume.{reason_suffix} Please upload your resume or CV containing your contact information, skills, "
        f"education, or work experience."
    )


def validate_resume_document(
    raw_text: str,
    extracted_data: Optional[Dict[str, Any]] = None,
    sections: Optional[Dict[str, str]] = None,
    file_signals: Optional[Dict[str, Any]] = None,
    page_count: Optional[int] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether extracted document text & metadata represent a valid Resume / CV / Biodata.

    Returns a dictionary with:
      - is_resume (bool)
      - confidence (float 0.0-1.0)
      - score (float)
      - positive_score (float)
      - negative_score (float)
      - detected_document_type (str)
      - reason_code (str)
      - message (str)
      - positive_signals (list[str])
      - negative_signals (list[str])
      - metrics (dict)
    """
    signals = file_signals or {}
    data = extracted_data or {}

    # ── Hard Gate 1: Password-protected file ─────────────────────────────────
    if signals.get("password_protected"):
        return {
            "is_resume": False,
            "confidence": 1.0,
            "score": -10.0,
            "positive_score": 0.0,
            "negative_score": 10.0,
            "detected_document_type": "password_protected",
            "reason_code": "password_protected",
            "message": _build_rejection_message("password_protected", "password_protected"),
            "positive_signals": [],
            "negative_signals": ["password_protected_file"],
            "metrics": {"word_count": 0, "page_count": page_count},
        }

    text = (raw_text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", text)
    alpha_words = re.findall(r"[A-Za-zÀ-ÿ]{2,}", text)
    word_count = len(words)
    alpha_word_count = len(alpha_words)

    if page_count is None and isinstance(signals.get("page_count"), int):
        page_count = signals["page_count"]

    # ── Hard Gate 2: Extreme page count even before text length check (e.g. 50-page scanned thesis) ──
    if isinstance(page_count, int) and page_count >= 15:
        return {
            "is_resume": False,
            "confidence": 0.99,
            "score": -12.0,
            "positive_score": 0.0,
            "negative_score": 12.0,
            "detected_document_type": "academic_paper" if _THESIS_UNMISTAKABLE_BOILERPLATE_RE.search(text) or _CHAPTER_HEADING_RE.search(text) else "manual_or_guide",
            "reason_code": "detected_thesis_manuscript" if _THESIS_UNMISTAKABLE_BOILERPLATE_RE.search(text) else "document_too_long",
            "message": _build_rejection_message(
                "academic_paper" if _THESIS_UNMISTAKABLE_BOILERPLATE_RE.search(text) else "manual_or_guide",
                "detected_thesis_manuscript" if _THESIS_UNMISTAKABLE_BOILERPLATE_RE.search(text) else "document_too_long",
            ),
            "positive_signals": [],
            "negative_signals": [f"excessive_pages_hard_limit({page_count})(+12.0)"],
            "metrics": {"word_count": word_count, "alpha_word_count": alpha_word_count, "page_count": page_count},
        }

    # ── Hard Gate 3: Empty / unreadable / far too short ──────────────────────
    if alpha_word_count < 18 or len(text) < 90:
        return {
            "is_resume": False,
            "confidence": 0.98,
            "score": -8.0,
            "positive_score": 0.0,
            "negative_score": 8.0,
            "detected_document_type": "unreadable_or_empty",
            "reason_code": "unreadable_or_empty",
            "message": _build_rejection_message("unreadable_or_empty", "unreadable_or_empty"),
            "positive_signals": [],
            "negative_signals": [f"insufficient_text(alpha_words={alpha_word_count},chars={len(text)})"],
            "metrics": {"word_count": word_count, "alpha_word_count": alpha_word_count, "page_count": page_count},
        }

    if sections is None:
        try:
            from app.extractors.content.section_parser import split_into_sections
            sections = split_into_sections(text)
        except Exception:
            sections = {}

    top_lines = lines[:18]
    top_title_block = "\n".join(top_lines)
    top_region = "\n".join(lines[:35])[:1800]
    personal_block = (sections.get("PERSONAL") or "") + "\n" + (sections.get("HEADER") or "")
    contact_search_region = top_region + "\n" + personal_block[:1200]

    positive_score = 0.0
    negative_score = 0.0
    positive_signals: List[str] = []
    negative_signals: List[str] = []

    # ── 1. Strict Standalone Resume Section Headings ─────────────────────────
    core_headings, supporting_headings, has_academic_refs = _detect_strict_resume_headings(text)

    # Run dedicated Thesis / Academic Manuscript structural analyzer BEFORE positive scoring
    # so embedded Researchers' CVs in a thesis appendix cannot spoof resume signals.
    academic_analysis = _analyze_academic_manuscript_signals(text, lines, has_academic_refs)

    if core_headings and not academic_analysis["has_embedded_cv_appendix"]:
        pts = 3.0 * len(core_headings)
        positive_score += pts
        positive_signals.append(f"core_headings:{','.join(sorted(core_headings))}(+{pts:.1f})")

    if supporting_headings and not academic_analysis["has_embedded_cv_appendix"]:
        pts = min(6.0, 1.5 * len(supporting_headings))
        positive_score += pts
        positive_signals.append(f"supporting_headings:{','.join(sorted(supporting_headings))}(+{pts:.1f})")

    # ── 2. Explicit Standalone Resume / CV / Biodata Title ───────────────────
    has_explicit_cv_title = False
    for ln in top_lines[:10]:
        norm_ln = _normalise_heading_candidate(ln)
        if _EXPLICIT_RESUME_TITLE_RE.match(norm_ln) and not _META_RESUME_SYSTEM_RE.search(ln):
            has_explicit_cv_title = True
            positive_score += 3.5
            positive_signals.append("explicit_resume_title(+3.5)")
            break

    is_explicit_cv = bool(re.search(r"\bcurriculum\s+vitae\b", top_title_block, re.IGNORECASE)) and not academic_analysis["has_embedded_cv_appendix"]

    # ── 3. Top-Anchored Candidate Identity & Contact Signals ─────────────────
    fullname = (data.get("fullname") or data.get("candidate_name") or "").strip()
    valid_name = _is_valid_person_fullname(fullname)
    if valid_name:
        positive_score += 1.5
        positive_signals.append("valid_person_name(+1.5)")

    top_emails = _extract_personal_emails(contact_search_region)
    # Also check extracted primary email if it's personal and appears in top half
    extracted_email = (data.get("email") or "").strip().lower()
    if extracted_email and extracted_email not in top_emails:
        local_p = extracted_email.split("@", 1)[0]
        if local_p not in _INSTITUTIONAL_EMAIL_PREFIXES and extracted_email in text[: max(2000, len(text) // 2)].lower():
            top_emails.append(extracted_email)

    has_personal_email = len(top_emails) > 0
    if has_personal_email:
        positive_score += 2.0
        positive_signals.append("personal_email_in_header(+2.0)")

    has_phone = bool(_PHONE_RE.search(contact_search_region))
    if not has_phone and (data.get("phone") or "").strip():
        ph_digits = re.sub(r"\D", "", data["phone"])
        if len(ph_digits) >= 7:
            has_phone = True
    if has_phone:
        positive_score += 2.0
        positive_signals.append("phone_number(+2.0)")

    has_profile_url = bool(_PROFILE_URL_RE.search(contact_search_region))
    if has_profile_url:
        positive_score += 1.5
        positive_signals.append("profile_url(+1.5)")

    biodata_hits = sum(1 for pat in _BIODATA_FIELD_PATTERNS if pat.search(text))
    has_biodata_fields = biodata_hits >= 3 and not academic_analysis["has_embedded_cv_appendix"]
    if has_biodata_fields:
        positive_score += 3.0
        positive_signals.append(f"biodata_personal_fields({biodata_hits})(+3.0)")

    # ── 4. Verified Education Evidence ───────────────────────────────────────
    strong_edu, partial_edu = _has_verified_education(text, data, sections)
    if strong_edu and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 2.5
        positive_signals.append("verified_education_degree_and_school(+2.5)")
    elif partial_edu and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 1.5
        positive_signals.append("verified_education_partial(+1.5)")

    # ── 5. Verified Work Experience & Action-Bullet Evidence ─────────────────
    dated_exp, undated_exp = _has_verified_work_experience(text, data, sections)
    exp_proj_lines: Set[str] = set()
    for sec_k in ("EXPERIENCE", "PROJECTS", "VOLUNTEER"):
        for sln in (sections.get(sec_k) or "").splitlines():
            if sln.strip():
                exp_proj_lines.add(sln.strip())

    action_bullet_count = sum(
        1
        for ln in lines
        if len(ln) <= 220
        and not _ACADEMIC_PROSE_LINE_RE.search(ln)
        and (ln.startswith(("•", "-", "*", "▪", "►", "✓", "·")) or ln in exp_proj_lines)
        and _RESUME_ACTION_BULLET_RE.match(ln)
    )
    if dated_exp and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 3.0
        positive_signals.append("verified_dated_work_experience(+3.0)")
    elif undated_exp and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 2.0
        positive_signals.append("verified_role_and_employer(+2.0)")

    if action_bullet_count >= 2 and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 1.5
        positive_signals.append(f"resume_action_bullets({action_bullet_count})(+1.5)")

    # ── 6. Verified Skills Evidence ──────────────────────────────────────────
    skills_list = data.get("skills_list") or []
    skills_sec_body = (sections.get("SKILLS") or "").strip()
    has_explicit_skills = bool(_EXPLICIT_SKILLS_LIST_RE.search(text))
    has_skills_in_section = ("SKILLS" in core_headings) and (len(skills_sec_body) >= 5 or len(skills_list) >= 1)

    has_verified_skills = False
    if not academic_analysis["has_embedded_cv_appendix"]:
        if has_skills_in_section or (has_explicit_skills and len(skills_list) >= 2):
            has_verified_skills = True
            positive_score += 2.0
            positive_signals.append("verified_skills_section_or_list(+2.0)")
        elif has_explicit_skills:
            has_verified_skills = True
            positive_score += 1.5
            positive_signals.append("explicit_skills_statement(+1.5)")
        elif (
            len(skills_list) >= 3
            and word_count <= 1500
            and (len(core_headings) >= 1 or has_explicit_cv_title or has_biodata_fields)
            and academic_analysis["score"] < 2.0
            and not _META_RESUME_SYSTEM_RE.search(text)
        ):
            has_verified_skills = True
            positive_score += 1.0
            positive_signals.append(f"concise_doc_skills({len(skills_list)})(+1.0)")

    # ── 7. Career Objective / Summary / Certifications Signals ───────────────
    if _CAREER_OBJECTIVE_RE.search(text) and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 1.5
        positive_signals.append("career_objective_phrase(+1.5)")

    if _RESUME_CERT_RE.search(text) and not academic_analysis["has_embedded_cv_appendix"]:
        positive_score += 1.0
        positive_signals.append("professional_credentials(+1.0)")

    # ── 8. Negative Document-Type Scoring ────────────────────────────────────
    category_scores: Dict[str, float] = {}

    # Determine safe top block BEFORE the first core/certifications resume heading
    # (prevents penalizing a resume that mentions "Certificate of Completion" inside its own Certifications section)
    cert_safe_end = len(top_lines)
    for idx, ln in enumerate(top_lines):
        norm_ln = _normalise_heading_candidate(ln)
        if norm_ln and len(norm_ln.split()) <= 5 and (
            any(p.match(norm_ln) for p in _CORE_HEADING_PATTERNS.values())
            or _SUPPORTING_HEADING_PATTERNS["CERTIFICATIONS"].match(norm_ln)
        ):
            cert_safe_end = idx
            break
    cert_top_block = "\n".join(top_lines[:cert_safe_end])

    for cat_key, cfg in _NON_RESUME_RULES.items():
        cat_pts = 0.0
        title_region = cert_top_block if cat_key == "certificate_or_official_record" else top_title_block
        for pat, weight in cfg["title_patterns"]:
            if pat.search(title_region):
                cat_pts += weight
                negative_signals.append(f"{cat_key}:title_match(+{weight:.1f})")
            elif cat_key in ("manual_or_guide", "academic_paper", "financial_document", "legal_or_correspondence", "misc_non_resume") and pat.search(text[:3500]):
                sub_w = round(weight * 0.85, 1)
                cat_pts += sub_w
                negative_signals.append(f"{cat_key}:early_match(+{sub_w:.1f})")

        for pat, weight in cfg["body_patterns"]:
            if pat.search(text):
                cat_pts += weight
                negative_signals.append(f"{cat_key}:body_match(+{weight:.1f})")

        if cat_pts > 0:
            category_scores[cat_key] = cat_pts

    # Merge dedicated Thesis / Academic Manuscript structural analyzer signals
    if academic_analysis["score"] > 0:
        category_scores["academic_paper"] = max(
            category_scores.get("academic_paper", 0.0),
            academic_analysis["score"],
        )
        negative_signals.extend(academic_analysis["signals"])

    # Academic bibliography references boost academic_paper negative score
    if has_academic_refs:
        category_scores["academic_paper"] = category_scores.get("academic_paper", 0.0) + 3.5
        negative_signals.append("academic_paper:academic_references(+3.5)")

    # Soft filename corroboration (ONLY when filename lacks resume/cv/biodata keywords;
    # never enough alone to reject a real resume, never required to reject a renamed non-resume)
    if filename:
        base_stem = os.path.splitext(os.path.basename(filename))[0]
        base_stem = re.sub(r"^\d{9,13}_", "", base_stem)
        clean_stem = re.sub(r"[_\-]+", " ", base_stem)
        if clean_stem and not _RESUME_FILENAME_HINT_RE.search(clean_stem):
            for fn_cat, fn_pat in _NON_RESUME_FILENAME_HINTS:
                if fn_pat.search(clean_stem):
                    category_scores[fn_cat] = category_scores.get(fn_cat, 0.0) + 2.5
                    negative_signals.append(f"{fn_cat}:filename_hint(+2.5)")
                    break

    # Meta-system mentions (e.g. a document ABOUT a resume analysis system)
    # Do not penalize a genuine candidate's resume (2+ core resume headings + contact info +
    # zero manual/guide cues) that simply lists an "Automated Resume Analysis" project they built.
    meta_resume_hits = len(_META_RESUME_SYSTEM_RE.findall(text))
    has_manual_structural_cues = category_scores.get("manual_or_guide", 0.0) > 0
    is_likely_student_resume_listing_project = (
        len(core_headings) >= 2
        and (has_personal_email or has_phone)
        and not has_manual_structural_cues
        and meta_resume_hits <= 5
    )
    if not is_likely_student_resume_listing_project and (
        meta_resume_hits >= 3 or (meta_resume_hits >= 2 and len(core_headings) < 2)
    ):
        pts = min(8.0, meta_resume_hits * 2.5)
        category_scores["manual_or_guide"] = category_scores.get("manual_or_guide", 0.0) + pts
        negative_signals.append(f"manual_or_guide:meta_resume_system_mentions({meta_resume_hits})(+{pts:.1f})")

    # Standalone Letter / Cover Letter check (only penalize when NOT a cover-letter + resume packet!)
    is_letter_format = bool(_LETTER_SALUTATION_RE.search(text)) and bool(_LETTER_CLOSING_RE.search(text))
    if is_letter_format and len(core_headings) < 2 and not (dated_exp and strong_edu):
        category_scores["legal_or_correspondence"] = category_scores.get("legal_or_correspondence", 0.0) + 8.0
        negative_signals.append("legal_or_correspondence:standalone_letter(+8.0)")

    # Job posting adjustment: if a real candidate uploaded their own resume mentioning "Job Description" as a bullet,
    # only keep high job_posting penalty if employer voice is present or personal contact+experience are absent
    if category_scores.get("job_posting", 0.0) > 0:
        has_employer_voice = bool(
            re.search(
                r"\b(?:we\s+are\s+hiring|now\s+hiring|we\s+are\s+looking\s+for|join\s+our\s+team|"
                r"the\s+ideal\s+candidate|successful\s+candidate|equal\s+opportunity\s+employer|"
                r"how\s+to\s+apply|apply\s+now|send\s+your\s+(?:resume|cv)|you\s+will\s+be\s+responsible)\b",
                text,
                re.IGNORECASE,
            )
        )
        if not has_employer_voice and valid_name and (has_personal_email or has_phone) and len(core_headings) >= 2:
            category_scores["job_posting"] = 0.0

    # Blank un-filled form check (many underscore fill-in blanks and no personal email/experience)
    blank_underscore_lines = len(re.findall(r"_{5,}", text))
    is_blank_form = blank_underscore_lines >= 6 and not has_personal_email and not dated_exp
    if is_blank_form:
        category_scores["misc_non_resume"] = category_scores.get("misc_non_resume", 0.0) + 8.0
        negative_signals.append(f"blank_form:underscores({blank_underscore_lines})(+8.0)")

    # Source code / JSON / SQL / raw log file check
    if len(core_headings) == 0 and not has_explicit_cv_title and len(lines) >= 6:
        code_line_re = re.compile(
            r"^\s*(?:import\s+\w+|from\s+\w+\s+import|def\s+\w+\(|class\s+\w+|"
            r"const\s+\w+\s*=|let\s+\w+\s*=|function\s+\w+\(|public\s+(?:class|static)|"
            r"SELECT\s+.+\s+FROM|INSERT\s+INTO|CREATE\s+TABLE|<!DOCTYPE|<html|<div|"
            r"[\{\}\[\]],?$|\"[^\"]+\"\s*:\s*|"
            r"(?:INFO|DEBUG|WARNING|ERROR|CRITICAL)\s*[:\-\[])",
            re.IGNORECASE,
        )
        code_lines = sum(1 for ln in lines if code_line_re.match(ln))
        if code_lines >= 5 and (code_lines / len(lines)) >= 0.30:
            category_scores["misc_non_resume"] = category_scores.get("misc_non_resume", 0.0) + 7.5
            negative_signals.append(f"misc_non_resume:source_code_or_data({code_lines}/{len(lines)})(+7.5)")

    # Excessive length / page count penalty (allow legitimate multi-page resumes 2-10 pages!)
    has_strong_multipage_resume_structure = (
        len(core_headings) >= 2
        and (valid_name or has_personal_email or has_phone)
        and (not academic_analysis["has_embedded_cv_appendix"])
    )
    length_penalty = 0.0
    if page_count is not None:
        if page_count >= 14 or (page_count >= 11 and not is_explicit_cv and not has_strong_multipage_resume_structure):
            length_penalty += 8.0
            negative_signals.append(f"excessive_pages({page_count})(+8.0)")
        elif page_count >= 9 and not is_explicit_cv and not has_strong_multipage_resume_structure:
            length_penalty += 4.0
            negative_signals.append(f"many_pages({page_count})(+4.0)")

    if word_count >= 5500:
        length_penalty += 8.0
        negative_signals.append(f"excessive_words({word_count})(+8.0)")
    elif word_count >= 3800 and not is_explicit_cv and not has_strong_multipage_resume_structure:
        length_penalty += 3.5
        negative_signals.append(f"high_word_count({word_count})(+3.5)")

    # Dense prose narrative check (articles, essays, stories, emails without resume structure)
    avg_line_len = (sum(len(ln) for ln in lines) / len(lines)) if lines else 0.0
    period_ended_lines = sum(1 for ln in lines if ln.endswith(".") and len(ln.split()) >= 12)
    prose_penalty = 0.0
    if (
        word_count >= 100
        and len(core_headings) == 0
        and not has_explicit_cv_title
        and avg_line_len >= 95.0
        and period_ended_lines >= 4
        and action_bullet_count < 2
    ):
        prose_penalty = 4.0
        negative_signals.append(f"dense_prose_narrative(avg_line={avg_line_len:.0f})(+4.0)")

    # Sum total negative score (take top category cleanly + half of secondary categories + structural penalties)
    sorted_cats = sorted(category_scores.items(), key=lambda kv: kv[1], reverse=True)
    top_neg_cat, top_neg_cat_score = sorted_cats[0] if sorted_cats else ("non_resume_document", 0.0)
    secondary_neg_sum = sum(v * 0.5 for _, v in sorted_cats[1:])
    negative_score = top_neg_cat_score + secondary_neg_sum + length_penalty + prose_penalty

    # ── 9. Five-Pillar Verification & Final Decision ─────────────────────────
    has_identity_pillar = (valid_name and (has_personal_email or has_phone or has_profile_url)) or has_biodata_fields
    has_experience_pillar = (not academic_analysis["has_embedded_cv_appendix"]) and (("EXPERIENCE" in core_headings) or dated_exp or undated_exp)
    has_education_pillar = (not academic_analysis["has_embedded_cv_appendix"]) and (("EDUCATION" in core_headings) or strong_edu)
    has_skills_pillar = (not academic_analysis["has_embedded_cv_appendix"]) and (("SKILLS" in core_headings) or has_verified_skills)
    has_meta_pillar = has_explicit_cv_title or (len(supporting_headings) >= 2 and not academic_analysis["has_embedded_cv_appendix"])

    pillars = {
        "identity_contact": has_identity_pillar,
        "experience": has_experience_pillar,
        "education": has_education_pillar,
        "skills": has_skills_pillar,
        "resume_structure": has_meta_pillar,
    }
    pillar_count = sum(1 for v in pillars.values() if v)
    core_qualification_pillars = sum(
        1 for k in ("experience", "education", "skills") if pillars[k]
    )

    net_score = round(positive_score - negative_score, 2)

    # Decision Rules (Strict Resume-Only Gate)
    is_resume = True
    detected_type = "resume"
    reason_code = "valid_resume"

    if is_blank_form:
        is_resume = False
        detected_type = "misc_non_resume"
        reason_code = "blank_form"
    elif academic_analysis["hard_veto"]:
        is_resume = False
        # Preserve more specific manual/spec label when a Software Requirements Spec / User Manual
        # explicitly matched a manual title without thesis-specific markers.
        if not academic_analysis["is_thesis_specific"] and category_scores.get("manual_or_guide", 0.0) >= 8.0:
            detected_type = "manual_or_guide"
            reason_code = "detected_manual_or_guide"
        else:
            detected_type = "academic_paper"
            reason_code = "detected_thesis_manuscript" if academic_analysis["is_thesis_specific"] else "detected_academic_paper"
    elif top_neg_cat_score >= 6.5:
        is_resume = False
        detected_type = top_neg_cat
        reason_code = f"detected_{top_neg_cat}"
    elif (isinstance(page_count, int) and page_count >= 15) or word_count >= 6000:
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.5 else "academic_paper"
        reason_code = "document_too_long"
    elif length_penalty >= 8.0 and not (is_explicit_cv and len(core_headings) >= 3 and top_neg_cat_score < 2.0):
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.5 else "manual_or_guide"
        reason_code = "document_too_long"
    elif (
        len(core_headings) == 0
        and not has_explicit_cv_title
        and not has_biodata_fields
        and (
            negative_score >= 2.0
            or word_count > 1200
            or positive_score < 7.0
            or not (
                (has_identity_pillar and core_qualification_pillars >= 2)
                or (valid_name and core_qualification_pillars == 3)
            )
        )
    ):
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.0 else "non_resume_document"
        reason_code = "insufficient_resume_evidence"
    elif negative_score >= 4.5 and negative_score >= positive_score * 0.55:
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.0 else "non_resume_document"
        reason_code = f"non_resume_signals_{detected_type}"
    elif core_qualification_pillars < 1 or pillar_count < 2 or positive_score < 5.5 or net_score < 4.0:
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.0 else "non_resume_document"
        reason_code = "insufficient_resume_evidence"

    # Compute bounded confidence [0.0, 1.0]
    if is_resume:
        confidence = round(min(0.99, max(0.55, 0.55 + (net_score / 25.0))), 2)
        message = "Valid resume document verified."
    else:
        confidence = round(min(0.99, max(0.60, 0.60 + (max(negative_score, 6.0 - positive_score) / 20.0))), 2)
        message = _build_rejection_message(detected_type, reason_code)

    return {
        "is_resume": is_resume,
        "confidence": confidence,
        "score": net_score,
        "positive_score": round(positive_score, 2),
        "negative_score": round(negative_score, 2),
        "detected_document_type": detected_type,
        "reason_code": reason_code,
        "message": message,
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "metrics": {
            "word_count": word_count,
            "alpha_word_count": alpha_word_count,
            "page_count": page_count,
            "pillar_count": pillar_count,
            "core_qualification_pillars": core_qualification_pillars,
            "pillars": pillars,
            "core_headings": sorted(core_headings),
            "supporting_headings": sorted(supporting_headings),
        },
    }


def fast_precheck_non_resume(
    raw_text: str,
    file_signals: Optional[Dict[str, Any]] = None,
    page_count: Optional[int] = None,
    filename: Optional[str] = None,
    is_partial_sample: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Millisecond-speed pre-screen run BEFORE expensive PDF/OCR or spaCy NLP extraction.
    Returns a rejection validation dict ONLY when a document is unmistakably
    NOT a resume (e.g. password-protected, oversized manuscript/manual, thesis/academic paper,
    or explicit high-confidence non-resume type like User Manual / Invoice / Certificate / Contract).
    Returns None when full extraction + validation should proceed.
    """
    signals = file_signals or {}
    p_cnt = page_count if page_count is not None else signals.get("page_count")

    if signals.get("password_protected"):
        return validate_resume_document(
            raw_text="",
            extracted_data={},
            file_signals=signals,
            page_count=p_cnt,
            filename=filename,
        )

    text = (raw_text or "").strip()

    # Immediate rejection for extremely long files (e.g. 15+ page scanned/text thesis manuscript or manual)
    # even before running OCR/pdfminer across dozens of pages.
    if isinstance(p_cnt, int) and p_cnt >= 15:
        return validate_resume_document(
            raw_text=text,
            extracted_data={},
            sections={},
            file_signals=signals,
            page_count=p_cnt,
            filename=filename,
        )

    if len(text) < 250:
        return None

    word_count = len(re.findall(r"[A-Za-zÀ-ÿ0-9]+", text))

    # Fast check for huge documents or clear high-confidence non-resume types
    quick = validate_resume_document(
        raw_text=text,
        extracted_data={},
        sections={},
        file_signals=signals,
        page_count=p_cnt,
        filename=filename,
    )
    if not quick["is_resume"] and (
        quick["reason_code"] in (
            "blank_form",
            "document_too_long",
            "detected_thesis_manuscript",
            "detected_manual_or_guide",
            "detected_academic_paper",
            "detected_financial_document",
            "detected_certificate_or_official_record",
            "detected_legal_or_correspondence",
            "detected_job_posting",
            "detected_misc_non_resume",
        )
        or (isinstance(p_cnt, int) and p_cnt >= 12)
        or (not is_partial_sample and word_count >= 4500)
    ):
        return quick

    return None


def extract_text_from_image_file(file_path: str) -> str:
    """
    Extract text from a scanned image file (.png/.jpg/.jpeg/.webp) using PyMuPDF OCR
    so even uploaded image scans can be verified as resumes.
    """
    try:
        import fitz
        img_doc = fitz.open(file_path)
        try:
            pdf_bytes = img_doc.convert_to_pdf()
        finally:
            img_doc.close()

        pdf_doc = fitz.open("pdf", pdf_bytes)
        try:
            parts: List[str] = []
            for page in pdf_doc:
                try:
                    tp = page.get_textpage_ocr(flags=0, dpi=250, full=True)
                    parts.append(tp.extractText() or "")
                except Exception as ocr_err:
                    logger.debug(f"Image OCR page failed: {ocr_err}")
            return "\n".join(parts).strip()
        finally:
            pdf_doc.close()
    except Exception as exc:
        logger.debug(f"Image text extraction failed for {file_path}: {exc}")
        return ""


def validate_resume_file_bytes(file_bytes: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
    """
    End-to-end helper that takes raw uploaded file bytes + filename, writes to a temporary file,
    extracts text & structured content, and verifies whether the document is a genuine resume.

    Used by direct upload endpoints (e.g. /resumes/upload and /hr/physical-resumes/upload)
    that must reject non-resumes before storing files or creating DB records.
    """
    ext = os.path.splitext(filename or "")[1].lower().strip(".")
    tmp_dir = tempfile.mkdtemp()
    safe_name = os.path.basename(filename or f"upload.{ext or 'pdf'}").replace(" ", "_")
    tmp_path = os.path.join(tmp_dir, safe_name)

    try:
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)

        if ext in ("png", "jpg", "jpeg", "webp"):
            from app.extractors.file.file_extractor import clean_raw_text
            raw_text = clean_raw_text(extract_text_from_image_file(tmp_path))
            if not raw_text:
                res = validate_resume_document(raw_text="", file_signals={}, page_count=1, filename=filename)
                return False, res
            from app.extractors.content.content_extractor import extract_content
            extracted = extract_content(raw_text)
            res = validate_resume_document(
                raw_text=raw_text,
                extracted_data=extracted,
                file_signals={},
                page_count=1,
                filename=filename,
            )
            return bool(res["is_resume"]), res

        from app.extractors.resume_processor import process_resume
        extracted = process_resume(tmp_path, ext)
        validation = (extracted or {}).get("resume_validation")
        if not validation:
            validation = validate_resume_document(
                raw_text=(extracted or {}).get("raw_text", ""),
                extracted_data=extracted or {},
                filename=filename,
            )
        return bool(validation.get("is_resume")), validation
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if os.path.isdir(tmp_dir):
                os.rmdir(tmp_dir)
        except OSError:
            pass
