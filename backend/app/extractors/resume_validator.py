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
    r"\b(?:bachelor(?:'?s)?\s+(?:of|in)\s+[a-z]|master(?:'?s)?\s+(?:of|in)\s+[a-z]|"
    r"doctor\s+of\s+[a-z]|ph\.?d\.?|m\.?b\.?a\.?|associate\s+(?:of|in|degree)|"
    r"b\.?s\.?\s+(?:in\s+)?(?:computer|information|civil|mechanical|electrical|industrial|"
    r"chemical|electronics|materials|accountancy|business|nursing|psychology|education|"
    r"hospitality|tourism|architecture|engineering|biology|mathematics|management|economics|finance)|"
    r"bsit|bscs|bscpe|bsce|bsis|bsme|bsee|bsie|bsba|bsa|bsn|bshm|bstm|bsed|beed|abm|humss|stem|tvl|"
    r"senior\s+high\s+school|high\s+school\s+(?:diploma|graduate)|secondary\s+education|"
    r"vocational(?:\s+diploma|\s+course|\s*/\s*technical)?|technical[\s\-]vocational|"
    r"diploma\s+in\s+[a-z]|tesda\s+(?:nc\s*[i1-4]+|national\s+certificate|training)|"
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
    r"manual|guide|system|portal|page|slide|item|article|clause)\b",
    re.IGNORECASE,
)

_GARBAGE_EXP_TITLE_RE = re.compile(
    r"\b(?:user\s+manual|recruiter\s+guide|quick\s+start|operations\s+manual|"
    r"admin\s+guide|step[\s\-]by[\s\-]step|table\s+of\s+contents|chapter\s+\d+)\b",
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
        "label": "Academic Paper / Thesis / Report",
        "title_patterns": [
            (re.compile(r"\b(?:submitted\s+in\s+partial\s+fulfillment|"
                        r"in\s+partial\s+fulfillment\s+of\s+the\s+requirements|"
                        r"bachelor'?s\s+thesis|master'?s\s+thesis|doctoral\s+dissertation|"
                        r"capstone\s+project\s+(?:documentation|manuscript|paper|report)|"
                        r"research\s+paper|term\s+paper|laboratory\s+report|lab\s+report|"
                        r"feasibility\s+study|business\s+plan|project\s+proposal|"
                        r"annual\s+report|financial\s+report|incident\s+report|"
                        r"narrative\s+report|accomplishment\s+report|progress\s+report|"
                        r"case\s+study\s+report|book\s+report|reflection\s+paper|"
                        r"approval\s+sheet)\b", re.IGNORECASE), 8.0),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:statement\s+of\s+the\s+problem|review\s+of\s+related\s+literature|"
                        r"related\s+literature\s+and\s+studies|conceptual\s+framework|"
                        r"theoretical\s+framework|scope\s+and\s+delimitation|significance\s+of\s+the\s+study|"
                        r"definition\s+of\s+terms|research\s+methodology|research\s+design|"
                        r"results\s+and\s+discussion|summary\s+of\s+findings|"
                        r"conclusions?\s+and\s+recommendations?)\b", re.IGNORECASE), 3.5),
            (re.compile(r"^\s*(?:chapter\s+(?:[1-9]|i|ii|iii|iv|v)\b|abstract|introduction|"
                        r"methodology|bibliography|works\s+cited|list\s+of\s+tables|list\s+of\s+figures|"
                        r"acknowledgements?|dedication)\s*$", re.IGNORECASE | re.MULTILINE), 2.5),
            (re.compile(r"\b(?:figure\s+\d+[\.:]|table\s+\d+[\.:]|et\s+al\.|doi\s*:\s*10\.)", re.IGNORECASE), 2.0),
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
                        r"residency|live\s+birth|marriage|registration|matriculation|grades)|"
                        r"barangay\s+clearance|police\s+clearance|nbi\s+clearance|medical\s+certificate|"
                        r"birth\s+certificate|marriage\s+certificate|death\s+certificate|"
                        r"transcript\s+of\s+records|official\s+transcript|report\s+card|"
                        r"grade\s+slip|assessment\s+of\s+fees|enrollment\s+form|registration\s+form|"
                        r"philippine\s+statistics\s+authority|national\s+bureau\s+of\s+investigation|"
                        r"philippine\s+identification\s+card)\b", re.IGNORECASE), 8.5),
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
    "legal_or_correspondence": {
        "label": "Contract / Agreement / Policy / Letter",
        "title_patterns": [
            (re.compile(r"\b(?:memorandum\s+of\s+agreement|memorandum\s+of\s+understanding|"
                        r"non[\s\-]?disclosure\s+agreement|confidentiality\s+agreement|"
                        r"employment\s+contract|service\s+agreement|lease\s+(?:agreement|contract)|"
                        r"terms\s+and\s+conditions|terms\s+of\s+(?:service|use)|privacy\s+policy|"
                        r"data\s+privacy\s+(?:policy|notice)|company\s+policy|deed\s+of\s+sale|"
                        r"affidavit\s+of|special\s+power\s+of\s+attorney|office\s+memorandum|"
                        r"inter[\s\-]?office\s+memorandum)\b", re.IGNORECASE), 8.5),
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
            (re.compile(r"\b(?:course\s+syllabus|course\s+outline|class\s+schedule|"
                        r"exam\s+schedule|survey\s+questionnaire|product\s+catalog(?:ue)?|"
                        r"price\s+list|restaurant\s+menu|event\s+program|minutes\s+of\s+the\s+meeting|"
                        r"meeting\s+agenda|from\s+wikipedia,\s+the\s+free\s+encyclopedia)\b", re.IGNORECASE), 8.5),
        ],
        "body_patterns": [
            (re.compile(r"\b(?:course\s+description|learning\s+outcomes|grading\s+criteria|"
                        r"midterm\s+exam|final\s+exam|credit\s+units|pre[\s\-]?requisite)\b", re.IGNORECASE), 2.5),
            (re.compile(r"\b(?:for\s+office\s+use\s+only|do\s+not\s+write\s+below\s+this\s+line|"
                        r"please\s+check\s+the\s+appropriate\s+box|strongly\s+agree.*strongly\s+disagree)\b", re.IGNORECASE), 4.0),
            (re.compile(r"\b(?:preheat\s+oven|tablespoons?|teaspoons?|nutrition\s+facts|"
                        r"once\s+upon\s+a\s+time|lorem\s+ipsum|this\s+page\s+was\s+last\s+edited|"
                        r"citation\s+needed|thank\s+you\s+for\s+listening)\b", re.IGNORECASE), 4.5),
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
            # Check if a date range appears near a role keyword (within 120 chars)
            for dm in _DATE_RANGE_RE.finditer(text):
                window = text[max(0, dm.start() - 120) : min(len(text), dm.end() + 120)]
                if _ROLE_KEYWORD_RE.search(window):
                    valid_dated = True
                    break

    if not valid_undated:
        # Check for "<Role> at <Company>" or role line + org line in text (supports undated/messy resumes)
        if re.search(
            r"\b(?:engineer|developer|operator|technician|supervisor|manager|analyst|specialist|"
            r"assistant|coordinator|accountant|nurse|teacher|crew|driver|rider|clerk|cashier|"
            r"attendant|inspector|welder|electrician|mechanic|intern|designer|representative)"
            r"\s+(?:at|@|-|\||,)\s+[A-Z][A-Za-z0-9&.,'\-\s]{2,45}",
            text,
            re.IGNORECASE,
        ):
            valid_undated = True
        elif _ROLE_KEYWORD_RE.search(text) and _ORG_SUFFIX_RE.search(text):
            valid_undated = True

    return valid_dated, valid_undated


def _has_verified_education(
    text: str,
    extracted_data: Dict[str, Any],
    sections: Dict[str, str],
) -> Tuple[bool, bool]:
    """
    Returns (has_strong_education, has_partial_education).
    Requires genuine academic degree or educational institution keywords (never hallucinated manual titles).
    """
    has_degree = bool(_DEGREE_RE.search(text))
    has_school = bool(_SCHOOL_RE.search(text))

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
        deg_ok = bool(deg and _DEGREE_RE.search(deg))
        inst_ok = bool(inst and _SCHOOL_RE.search(inst))
        if deg_ok and inst_ok:
            return True, True
        if deg_ok or inst_ok:
            return False, True

    if has_degree:
        return False, True

    return False, False


def _build_rejection_message(detected_type: str, reason_code: str) -> str:
    if reason_code == "password_protected":
        return (
            "This file is password-protected and cannot be verified as a resume. "
            "Please remove the password and upload an unprotected resume file (PDF, DOCX, DOC, or TXT)."
        )
    if reason_code == "unreadable_or_empty":
        return (
            "We could not read enough text from this file to verify that it is a resume. "
            "Please upload a clear, text-based resume or CV (PDF, DOCX, DOC, or TXT)."
        )
    if reason_code == "blank_form":
        return (
            "This file appears to be a blank form or template with no candidate details filled in. "
            "Please upload your completed resume or CV."
        )

    type_labels = {
        "manual_or_guide": "a user manual or guide",
        "academic_paper": "an academic paper, thesis, or report",
        "financial_document": "an invoice, receipt, or financial document",
        "certificate_or_official_record": "a certificate, clearance, or official record",
        "legal_or_correspondence": "a contract, policy, or standalone letter",
        "job_posting": "a job posting or job description",
        "misc_non_resume": "a non-resume document",
    }
    human_type = type_labels.get(detected_type)
    if human_type:
        return (
            f"Only resume or CV documents are accepted. The uploaded file appears to be {human_type}, "
            "not a resume. Please upload a valid resume containing your personal details, education, "
            "skills, or work experience."
        )
    return (
        "Only resume or CV documents are accepted. The uploaded file does not appear to be a valid "
        "resume. Please upload your resume or CV containing your contact information, skills, "
        "education, or work experience."
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

    # ── Hard Gate 2: Empty / unreadable / far too short ──────────────────────
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

    top_lines = lines[:15]
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

    if core_headings:
        pts = 3.0 * len(core_headings)
        positive_score += pts
        positive_signals.append(f"core_headings:{','.join(sorted(core_headings))}(+{pts:.1f})")

    if supporting_headings:
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

    is_explicit_cv = bool(re.search(r"\bcurriculum\s+vitae\b", top_title_block, re.IGNORECASE))

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
    has_biodata_fields = biodata_hits >= 3
    if has_biodata_fields:
        positive_score += 3.0
        positive_signals.append(f"biodata_personal_fields({biodata_hits})(+3.0)")

    # ── 4. Verified Education Evidence ───────────────────────────────────────
    strong_edu, partial_edu = _has_verified_education(text, data, sections)
    if strong_edu:
        positive_score += 2.5
        positive_signals.append("verified_education_degree_and_school(+2.5)")
    elif partial_edu:
        positive_score += 1.5
        positive_signals.append("verified_education_partial(+1.5)")

    # ── 5. Verified Work Experience & Action-Bullet Evidence ─────────────────
    dated_exp, undated_exp = _has_verified_work_experience(text, data, sections)
    action_bullet_count = sum(1 for ln in lines if _RESUME_ACTION_BULLET_RE.match(ln))
    if dated_exp:
        positive_score += 3.0
        positive_signals.append("verified_dated_work_experience(+3.0)")
    elif undated_exp:
        positive_score += 2.0
        positive_signals.append("verified_role_and_employer(+2.0)")

    if action_bullet_count >= 2:
        positive_score += 1.5
        positive_signals.append(f"resume_action_bullets({action_bullet_count})(+1.5)")

    # ── 6. Verified Skills Evidence ──────────────────────────────────────────
    skills_list = data.get("skills_list") or []
    skills_sec_body = (sections.get("SKILLS") or "").strip()
    has_explicit_skills = bool(_EXPLICIT_SKILLS_LIST_RE.search(text))
    has_skills_in_section = ("SKILLS" in core_headings) and (len(skills_sec_body) >= 5 or len(skills_list) >= 1)

    has_verified_skills = False
    if has_skills_in_section or (has_explicit_skills and len(skills_list) >= 2):
        has_verified_skills = True
        positive_score += 2.0
        positive_signals.append("verified_skills_section_or_list(+2.0)")
    elif has_explicit_skills:
        has_verified_skills = True
        positive_score += 1.5
        positive_signals.append("explicit_skills_statement(+1.5)")
    elif len(skills_list) >= 3 and word_count <= 1500 and not _META_RESUME_SYSTEM_RE.search(text):
        has_verified_skills = True
        positive_score += 1.0
        positive_signals.append(f"concise_doc_skills({len(skills_list)})(+1.0)")

    # ── 7. Career Objective / Summary / Certifications Signals ───────────────
    if _CAREER_OBJECTIVE_RE.search(text):
        positive_score += 1.5
        positive_signals.append("career_objective_phrase(+1.5)")

    if _RESUME_CERT_RE.search(text):
        positive_score += 1.0
        positive_signals.append("professional_credentials(+1.0)")

    # ── 8. Negative Document-Type Scoring ────────────────────────────────────
    category_scores: Dict[str, float] = {}
    for cat_key, cfg in _NON_RESUME_RULES.items():
        cat_pts = 0.0
        for pat, weight in cfg["title_patterns"]:
            if pat.search(top_title_block):
                cat_pts += weight
                negative_signals.append(f"{cat_key}:title_match(+{weight:.1f})")
            elif cat_key in ("manual_or_guide", "financial_document", "legal_or_correspondence") and pat.search(text[:2500]):
                sub_w = round(weight * 0.75, 1)
                cat_pts += sub_w
                negative_signals.append(f"{cat_key}:early_match(+{sub_w:.1f})")

        for pat, weight in cfg["body_patterns"]:
            if pat.search(text):
                # Avoid penalizing a real resume that only mentions "NBI Clearance" inside its Certifications section
                cat_pts += weight
                negative_signals.append(f"{cat_key}:body_match(+{weight:.1f})")

        if cat_pts > 0:
            category_scores[cat_key] = cat_pts

    # Academic bibliography references boost academic_paper negative score
    if has_academic_refs:
        category_scores["academic_paper"] = category_scores.get("academic_paper", 0.0) + 3.5
        negative_signals.append("academic_paper:academic_references(+3.5)")

    # Meta-system mentions (e.g. a document ABOUT a resume analysis system)
    meta_resume_hits = len(_META_RESUME_SYSTEM_RE.findall(text))
    if meta_resume_hits >= 2:
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

    # Excessive length / page count penalty
    length_penalty = 0.0
    if page_count is not None:
        if page_count >= 12:
            length_penalty += 8.0
            negative_signals.append(f"excessive_pages({page_count})(+8.0)")
        elif page_count >= 8 and not is_explicit_cv:
            length_penalty += 4.0
            negative_signals.append(f"many_pages({page_count})(+4.0)")

    if word_count >= 4500:
        length_penalty += 8.0
        negative_signals.append(f"excessive_words({word_count})(+8.0)")
    elif word_count >= 3000 and not is_explicit_cv:
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
    has_experience_pillar = ("EXPERIENCE" in core_headings) or dated_exp or undated_exp
    has_education_pillar = ("EDUCATION" in core_headings) or strong_edu
    has_skills_pillar = ("SKILLS" in core_headings) or has_verified_skills
    has_meta_pillar = has_explicit_cv_title or len(supporting_headings) >= 2

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

    # Decision Rules
    is_resume = True
    detected_type = "resume"
    reason_code = "valid_resume"

    if is_blank_form:
        is_resume = False
        detected_type = "misc_non_resume"
        reason_code = "blank_form"
    elif top_neg_cat_score >= 7.0:
        is_resume = False
        detected_type = top_neg_cat
        reason_code = f"detected_{top_neg_cat}"
    elif length_penalty >= 8.0 and not (is_explicit_cv and len(core_headings) >= 3 and top_neg_cat_score < 4.0):
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 3.0 else "manual_or_guide"
        reason_code = "document_too_long"
    elif negative_score >= 5.0 and negative_score >= positive_score * 0.65:
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.5 else "non_resume_document"
        reason_code = f"non_resume_signals_{detected_type}"
    elif core_qualification_pillars < 1 or pillar_count < 2 or positive_score < 5.5 or net_score < 4.0:
        is_resume = False
        detected_type = top_neg_cat if top_neg_cat_score >= 2.5 else "non_resume_document"
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
) -> Optional[Dict[str, Any]]:
    """
    Millisecond-speed pre-screen run BEFORE expensive spaCy / NLP extraction.
    Returns a rejection validation dict ONLY when a document is unmistakably
    NOT a resume (e.g. password-protected, blank/unreadable, huge manual/thesis,
    or explicit high-confidence non-resume type like User Manual / Invoice / Certificate).
    Returns None when full extraction + validation should proceed.
    """
    signals = file_signals or {}
    if signals.get("password_protected"):
        return validate_resume_document(
            raw_text="",
            extracted_data={},
            file_signals=signals,
            page_count=page_count,
            filename=filename,
        )

    text = (raw_text or "").strip()
    if len(text) < 250:
        return None

    p_cnt = page_count if page_count is not None else signals.get("page_count")
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
            "detected_manual_or_guide",
            "detected_academic_paper",
            "detected_financial_document",
            "detected_certificate_or_official_record",
            "detected_legal_or_correspondence",
            "detected_misc_non_resume",
        )
        or (isinstance(p_cnt, int) and p_cnt >= 12)
        or word_count >= 4500
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
