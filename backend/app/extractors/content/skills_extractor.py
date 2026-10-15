"""
Philippine Resume Skills Extraction Engine
==========================================
Principal NLP & Information Extraction Architecture for the Philippine workforce:
- Full-Document Multi-Pass Extraction:
  - Pass 1: Exact & Alias Gazetteer Matching via FlashText + spaCy PhraseMatcher
  - Pass 2: Linguistic Pattern & Dependency Extraction via spaCy Matcher,
            Action Verb + Object Noun Chunks, Filipino Workplace Traits,
            Driver's License, PRC Licensure, and TESDA Certificates
  - Pass 3: Fuzzy Normalization & Canonical Deduplication via RapidFuzz
- Exhaustive Philippine Taxonomy across 9 Workforce Domains:
  1. Service, F&B & Hospitality (Jollibee/McDo Crew, Janitors, Stewards, Baristas)
  2. Janitorial, Maintenance & Skilled Trades (Industrial Cleaning, SMAW/TIG, HVAC, EIM)
  3. Logistics, Driving, Warehouse & Security (Riders, LTO DL, Forklift, SOSIA Guard)
  4. BPO, Customer Service & Administrative (CSR, TSR, WPM, Avaya/Zendesk, SSS/BIR)
  5. Software Development & IT (Java, C#, NestJS, Supabase, Cloud, QA Automation)
  6. Engineering, Construction & Architecture (AutoCAD, STAAD.Pro, BOSH/COSH SO2, BOQ)
  7. Healthcare, Education & Finance (RN, Caregiving, ESL, CPA, Tax Compliance)
  8. Soft Skills & Filipino Workplace Traits ("Pakikisama", "Can work under pressure")
  9. Philippine Licenses, Eligibility & Languages (PRC, CSC, TESDA NC, Filipino/Dialects)
- External Dataset Ingestion Hook for ESCO, O*NET, and TESDA datasets.
- Deterministic, local Python execution without external LLM dependencies.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple

# Local deterministic NLP libraries
try:
    from flashtext import KeywordProcessor
except ImportError:
    KeywordProcessor = None

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

from app.extractors.nlp.nlp_engine import get_doc, get_verb_object_pairs
from app.extractors.content.skills_taxonomy import (
    PHILIPPINE_SKILLS_TAXONOMY,
    load_external_skill_datasets as taxonomy_load_external,
)

# ─── Backward-Compatibility Knowledge Base Symbols ───────────────────────────
# Some modules (e.g. nlp_engine, spacy_extractor) import COMMON_SKILLS and _format_skill

_UPPER_CASE_SKILLS = {
    "html", "html5", "css", "css3", "php", "sql", "mysql", "seo", "sem",
    "ui/ux", "aws", "gcp", "api", "rest", "rest api", "restful", "grpc",
    "graphql", "nosql", "json", "xml", "yaml", "csv", "ci/cd", "devops",
    "qa", "tdd", "bdd", "etl", "elt", "bi", "ai", "ml", "nlp", "cnn",
    "rnn", "lstm", "gan", "llm", "gpt", "jwt", "sso", "oauth", "ssl/tls",
    "iam", "gdpr", "hipaa", "pci dss", "iso 27001", "soc 2", "rpa",
    "iot", "nft", "erp", "crm", "pwa", "saas", "paas", "iaas",
    "sass", "scss", "less", "npm", "yarn", "pnpm", "pip",
    "k8s", "ec2", "s3", "eks", "ecs", "smaw", "tig", "mig", "haccp",
    "fifo", "pos", "wpm", "bosh", "cosh", "staad.pro", "etabs", "boq",
    "plc", "cctv", "bls", "cpr", "esl", "prc", "csc", "tesda", "lto",
}

_TITLE_CASE_OVERRIDES = {
    "node.js": "Node.js", "nodejs": "Node.js",
    "react.js": "React.js", "vue.js": "Vue.js",
    "next.js": "Next.js", "nuxt.js": "Nuxt.js", "express.js": "Express.js",
    "nest.js": "Nest.js", "angular.js": "Angular.js", "ember.js": "Ember.js",
    "backbone.js": "Backbone.js", "three.js": "Three.js",
    "d3.js": "D3.js", "p5.js": "p5.js",
    "asp.net": "ASP.NET", "asp.net core": "ASP.NET Core",
    ".net": ".NET", ".net core": ".NET Core",
    "vb.net": "VB.NET", "f#": "F#", "c#": "C#", "c++": "C++",
    "objective-c": "Objective-C",
    "scikit-learn": "Scikit-learn", "xgboost": "XGBoost",
    "lightgbm": "LightGBM", "catboost": "CatBoost",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "opencv": "OpenCV", "fastapi": "FastAPI",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "dynamodb": "DynamoDB",
    "supabase": "Supabase", "firebase": "Firebase",
    "github": "GitHub", "gitlab": "GitLab",
    "kubernetes": "Kubernetes", "docker": "Docker",
    "salesforce": "Salesforce", "hubspot": "HubSpot",
    "quickbooks": "QuickBooks", "typescript": "TypeScript",
    "javascript": "JavaScript", "powershell": "PowerShell",
    "android": "Android", "ios": "iOS",
    "autocad": "AutoCAD", "staad.pro": "STAAD.Pro",
    "sketchup": "SketchUp", "zendesk": "Zendesk",
    "freshdesk": "Freshdesk", "avaya": "Avaya",
}


def _format_skill(skill: str) -> str:
    """Apply proper capitalization and standard casing to a skill string."""
    clean = skill.strip()
    lower = clean.lower()
    if not lower:
        return ""
    if lower in _TITLE_CASE_OVERRIDES:
        return _TITLE_CASE_OVERRIDES[lower]
    if lower in _UPPER_CASE_SKILLS:
        return clean.upper()
    return clean.title()


# Populate COMMON_SKILLS with all canonical and alias terms in uppercase
COMMON_SKILLS: Set[str] = set()
for _canon, _meta in PHILIPPINE_SKILLS_TAXONOMY.items():
    COMMON_SKILLS.add(_canon.upper())
    for _al in _meta.get("aliases", []):
        COMMON_SKILLS.add(_al.upper())


# ─── Resume Section Regexes ──────────────────────────────────────────────────
_SECTION_HEADERS = {
    "Skills": re.compile(
        r'^(?:technical\s+skills?|core\s+competencies|skills?\s*(?:&|and)\s*traits?|'
        r'skills?\s*(?:&|and)\s*abilities|skills?\s*(?:&|and)\s*expertise|key\s+skills?|'
        r'skills?|competencies|proficiencies|areas?\s+of\s+expertise|qualifications?|'
        r'technical\s+&\s+engineering\s+skills?|skills\s+&\s+proficiencies)\b',
        re.IGNORECASE
    ),
    "Work Experience": re.compile(
        r'^(?:work\s+experience|professional\s+experience|employment\s+history|'
        r'career\s+history|experience|work\s+history|relevant\s+experience)\b',
        re.IGNORECASE
    ),
    "Education": re.compile(
        r'^(?:education|educational\s+background|educational\s+attainment|'
        r'academic\s+background|academic\s+qualifications?)\b',
        re.IGNORECASE
    ),
    "Certifications": re.compile(
        r'^(?:certifications?|licenses?\s*(?:&|and)\s*certifications?|eligibility|'
        r'trainings?\s*(?:&|and)\s*seminars?|credentials?|accreditations?|'
        r'licenses?\s*(?:&|and)\s*eligibility)\b',
        re.IGNORECASE
    ),
    "Summary": re.compile(
        r'^(?:objective|career\s+objective|summary|professional\s+summary|'
        r'career\s+summary|profile|about\s+me)\b',
        re.IGNORECASE
    ),
}

# Context constraints for short keywords (e.g. single letters or common english words)
_SHORT_KEYWORDS_REQUIRING_CONTEXT = {
    "C": {"PROGRAMMING", "LANGUAGES", "DEVELOPER", "C++", "C#", "JAVA", "PYTHON", "CODE", "SOFTWARE"},
    "R": {"PROGRAMMING", "LANGUAGES", "DATA", "STATISTICS", "PYTHON", "MACHINE LEARNING", "ANALYSIS"},
    "GO": {"GOLANG", "PROGRAMMING", "BACKEND", "DEVELOPER", "DOCKER", "KUBERNETES"},
    "IT": {"SUPPORT", "INFORMATION TECHNOLOGY", "BSIT", "BS IT", "HARDWARE", "SYSTEMS", "ADMIN"},
    "AI": {"ARTIFICIAL INTELLIGENCE", "MACHINE LEARNING", "ML", "DEEP LEARNING", "DATA"},
    "ML": {"MACHINE LEARNING", "AI", "DEEP LEARNING", "DATA SCIENCE", "ALGORITHMS"},
    "QA": {"QUALITY ASSURANCE", "TESTING", "MANUAL TESTING", "AUTOMATION", "TESTER"},
    "UI": {"USER INTERFACE", "UX", "FRONTEND", "DESIGN", "FIGMA"},
    "UX": {"USER EXPERIENCE", "UI", "FRONTEND", "DESIGN", "RESEARCH"},
    "PM": {"PROJECT MANAGER", "MAINTENANCE", "PREVENTIVE MAINTENANCE", "SCRUM"},
}

# Filipino Soft Skills & Workplace Traits Trigger Patterns
_SOFT_SKILL_PATTERNS = [
    (
        re.compile(r'\b(?:can\s+work\s+under\s+pressure|willing\s+to\s+learn\s+and\s+work\s+under\s+pressure|works?\s+well\s+under\s+pressure|stress\s+tolerance|handles?\s+pressure)\b', re.IGNORECASE),
        "Stress Tolerance (Can Work Under Pressure)"
    ),
    (
        re.compile(r'\b(?:willing\s+to\s+render\s+overtime|render\s+overtime|willing\s+to\s+work\s+overtime|work\s+on\s+holidays|amenable\s+to\s+shifting\s+schedules?|shifting\s+schedules?|night\s+shift|graveyard\s+shift|rotational\s+shifts?)\b', re.IGNORECASE),
        "Overtime & Shifting Flexibility"
    ),
    (
        re.compile(r'\b(?:can\s+work\s+with\s+minimal\s+supervision|minimal\s+supervision|works?\s+independently|without\s+supervision|autonomous\s+worker)\b', re.IGNORECASE),
        "Autonomy (Can Work With Minimal Supervision)"
    ),
    (
        re.compile(r'\b(?:fast\s+learner(?:\s+and\s+willing\s+to\s+be\s+trained)?|quick\s+learner|willing\s+to\s+be\s+trained|eager\s+to\s+learn)\b', re.IGNORECASE),
        "Fast Learner & Willing to be Trained"
    ),
    (
        re.compile(r'\b(?:team\s+player|team-player|works?\s+well\s+in\s+a\s+team|teamwork(?:\s+&\s+collaboration)?|pakikisama)\b', re.IGNORECASE),
        "Teamwork & Collaboration"
    ),
    (
        re.compile(r'\b(?:interpersonal\s+skills?|good\s+interpersonal\s+skills?)\b', re.IGNORECASE),
        "Interpersonal Skills"
    ),
    (
        re.compile(r'\b(?:active\s+listening|empathetic\s+listening)\b', re.IGNORECASE),
        "Active Listening"
    ),
    (
        re.compile(r'\b(?:conflict\s+de[\s\-]escalation|customer\s+de[\s\-]escalation|de[\s\-]escalation)\b', re.IGNORECASE),
        "Conflict De-escalation"
    ),
    (
        re.compile(r'\b(?:problem\s+solving|problem-solving(?:\s+skills?)?)\b', re.IGNORECASE),
        "Problem Solving"
    ),
    (
        re.compile(r'\b(?:time\s+management|multitasking|multi[\s\-]tasking)\b', re.IGNORECASE),
        "Time Management & Multitasking"
    ),
    (
        re.compile(r'\b(?:honesty\s+(?:&|and)\s+integrity|honest\s+and\s+trustworthy)\b', re.IGNORECASE),
        "Honesty & Integrity"
    ),
]

# Specialized Regexes
_TYPING_SPEED_RE = re.compile(r'\b(\d{2,3})\s*WPM(?:\s+typing(?:\s+speed)?)?\b', re.IGNORECASE)
_DRIVER_LICENSE_RE = re.compile(r'\b(?:Professional|Non-Professional)?\s*Driver\'?s?\s*License(?:\s*(?:Restriction|DL\s*Code)\s*([A-Za-z0-9,\s]+))?\b', re.IGNORECASE)
_TESDA_CERT_RE = re.compile(r'\b(?:TESDA\s+)?([A-Za-z0-9\s/()\-]+?)\s*(?:NC\s*(?:I|II|III|IV)|National\s*Certificate\s*(?:I|II|III|IV))\b', re.IGNORECASE)
_PRC_LICENSE_RE = re.compile(r'\b(?:PRC\s+)?(?:Registered|Licensed)?\s*([A-Za-z\s]+?)(?:Board\s*Exam\s*Passer|Licensure\s*Exam\s*Passer)\b', re.IGNORECASE)

# Competency Trigger Prefixes
_COMPETENCY_PREFIX_RE = re.compile(
    r'\b(?:proficient\s+in|knowledgeable\s+in|skilled\s+in|experienced\s+in|background\s+in|'
    r'familiar\s+with|ability\s+to\s+(?:operate|handle|perform|conduct)|good\s+command\s+of|'
    r'strong\s+background\s+in|hands[\s\-]on\s+experience\s+in|well[\s\-]versed\s+in|'
    r'competent\s+in|specializing\s+in|expertise\s+in)\s+([^.\n;:•]+)',
    re.IGNORECASE
)

# Compound skill variations mapping
_COMPOUND_SKILL_MAP = {
    "ms word/excel/powerpoint": ["Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", "Microsoft Office Suite"],
    "ms word, excel, powerpoint": ["Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", "Microsoft Office Suite"],
    "word, excel, powerpoint": ["Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", "Microsoft Office Suite"],
    "excel vlookup & pivot tables": ["Advanced Excel (VLOOKUP & Pivot Tables)", "Microsoft Excel"],
    "excel vlookup and pivot tables": ["Advanced Excel (VLOOKUP & Pivot Tables)", "Microsoft Excel"],
    "smaw ncii": ["Shielded Metal Arc Welding (SMAW)", "TESDA National Certificate (NC II)"],
    "smaw nc ii": ["Shielded Metal Arc Welding (SMAW)", "TESDA National Certificate (NC II)"],
    "bosh so2": ["Basic Occupational Safety and Health (BOSH)"],
    "cosh so2": ["Construction Occupational Safety and Health (COSH)"],
    "css nc ii": ["PC Troubleshooting & Hardware Repair", "TESDA National Certificate (NC II)"],
    "food preparation and kitchen sanitation": ["Food Preparation", "Kitchen Sanitation"],
    "floor buffing and housekeeping": ["Floor Polishing & Buffing", "Housekeeping & Room Makeup"],
}


class PhilippineSkillsExtractor:
    """
    High-precision multi-pass Philippine resume skills extraction engine.
    """

    def __init__(self):
        self.taxonomy = PHILIPPINE_SKILLS_TAXONOMY
        self.keyword_processor = KeywordProcessor(case_sensitive=False) if KeywordProcessor else None
        self.alias_to_canonical: Dict[str, str] = {}
        self.canonical_choices: List[str] = []
        self._build_index()

    def _build_index(self):
        """Indexes all canonical skills and aliases into FlashText and alias maps."""
        if KeywordProcessor is not None:
            self.keyword_processor = KeywordProcessor(case_sensitive=False)
        self.alias_to_canonical = {}
        self.canonical_choices = list(self.taxonomy.keys())

        for canonical, info in self.taxonomy.items():
            if self.keyword_processor is not None:
                self.keyword_processor.add_keyword(canonical, canonical)
            self.alias_to_canonical[canonical.lower()] = canonical

            for alias in info.get("aliases", []):
                clean_alias = alias.strip()
                if clean_alias:
                    if self.keyword_processor is not None:
                        self.keyword_processor.add_keyword(clean_alias, canonical)
                    self.alias_to_canonical[clean_alias.lower()] = canonical

    def load_external_datasets(
        self,
        esco_csv_path: Optional[str] = None,
        onet_txt_path: Optional[str] = None,
        tesda_json_path: Optional[str] = None
    ) -> int:
        """Loads external ESCO, O*NET, or TESDA datasets and dynamically updates the index."""
        added = taxonomy_load_external(esco_csv_path, onet_txt_path, tesda_json_path)
        if added > 0:
            self._build_index()
        return added

    def _segment_sections(self, text: str) -> List[Tuple[int, int, str]]:
        """Segments resume text into typed sections based on headers."""
        spans: List[Tuple[int, int, str]] = []
        lines = text.split('\n')
        current_section = "General"
        section_start = 0
        char_offset = 0

        for line in lines:
            line_len = len(line) + 1  # newline length
            clean_line = line.strip()

            if clean_line:
                matched_header = None
                for sec_name, pattern in _SECTION_HEADERS.items():
                    if pattern.match(clean_line):
                        matched_header = sec_name
                        break

                if matched_header:
                    if char_offset > section_start:
                        spans.append((section_start, char_offset, current_section))
                    current_section = matched_header
                    section_start = char_offset

            char_offset += line_len

        if char_offset > section_start:
            spans.append((section_start, char_offset, current_section))

        return spans

    def _get_section(self, offset: int, spans: List[Tuple[int, int, str]]) -> str:
        """Returns the section name for a character offset."""
        for start, end, name in spans:
            if start <= offset < end:
                return name
        return "General"

    def _is_valid_short_mention(self, raw: str, start: int, end: int, text: str) -> bool:
        """Filters out ambiguous short tokens to prevent false positives."""
        raw_upper = raw.strip().upper()
        if raw_upper not in _SHORT_KEYWORDS_REQUIRING_CONTEXT:
            return True

        exact_snippet = text[start:end].strip()
        if not exact_snippet.isupper() and len(exact_snippet) <= 2:
            return False

        window_start = max(0, start - 100)
        window_end = min(len(text), end + 100)
        window = text[window_start:window_end].upper()

        context_words = _SHORT_KEYWORDS_REQUIRING_CONTEXT[raw_upper]
        return any(w in window for w in context_words)

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Executes the full multi-pass skills extraction pipeline:
          - Pass 1: FlashText exact & alias gazetteer extraction
          - Pass 2: spaCy Matcher, dependency verb-object pairs, and Filipino trait patterns
          - Pass 3: RapidFuzz fuzzy normalization and canonical deduplication
        """
        if not text or not text.strip():
            return {
                "total_unique_skills": 0,
                "skill_summary_by_type": {
                    "hard_skills_count": 0,
                    "soft_skills_count": 0,
                    "certifications_and_licenses_count": 0,
                    "languages_count": 0
                },
                "extracted_skills": [],
                "categorized_view": {
                    "hard_skills": [],
                    "soft_skills": [],
                    "tools_and_technologies": [],
                    "certifications_and_eligibility": [],
                    "languages": []
                }
            }

        section_spans = self._segment_sections(text)
        candidates: List[Dict[str, Any]] = []

        # ─── Pass 1: FlashText Exact & Alias Gazetteer ────────────────────────
        if self.keyword_processor is not None:
            matches = self.keyword_processor.extract_keywords(text, span_info=True)
            for canonical, start, end in matches:
                raw_mention = text[start:end].strip()
                if not self._is_valid_short_mention(raw_mention, start, end, text):
                    continue

                sec = self._get_section(start, section_spans)
                candidates.append({
                    "canonical_skill": canonical,
                    "raw_mention": raw_mention,
                    "source_section": sec,
                    "extraction_method": "Gazetteer_Exact",
                    "confidence_score": 0.98,
                    "offset": start
                })

        # ─── Pass 2: Linguistic Patterns & Dependency Parsing ─────────────────
        # 2a. Compound Skill Variations (e.g. MS Word/Excel/Powerpoint, SMAW NCII)
        text_lower = text.lower()
        for compound_key, mapped_canonicals in _COMPOUND_SKILL_MAP.items():
            if compound_key in text_lower:
                idx = text_lower.find(compound_key)
                sec = self._get_section(idx, section_spans)
                for mapped in mapped_canonicals:
                    candidates.append({
                        "canonical_skill": mapped,
                        "raw_mention": text[idx:idx + len(compound_key)],
                        "source_section": sec,
                        "extraction_method": "Regex_Pattern",
                        "confidence_score": 0.95,
                        "offset": idx
                    })

        # 2b. Filipino Soft Skills & Workplace Traits
        for pattern, canonical in _SOFT_SKILL_PATTERNS:
            for m in pattern.finditer(text):
                sec = self._get_section(m.start(), section_spans)
                candidates.append({
                    "canonical_skill": canonical,
                    "raw_mention": m.group(0).strip(),
                    "source_section": sec,
                    "extraction_method": "Regex_Pattern",
                    "confidence_score": 0.95,
                    "offset": m.start()
                })

        # 2b. Typing Speed Pattern
        for m in _TYPING_SPEED_RE.finditer(text):
            sec = self._get_section(m.start(), section_spans)
            candidates.append({
                "canonical_skill": "Typing Speed (WPM)",
                "raw_mention": m.group(0).strip(),
                "source_section": sec,
                "extraction_method": "Regex_Pattern",
                "confidence_score": 0.96,
                "offset": m.start()
            })

        # 2c. Professional Driver's License Pattern
        for m in _DRIVER_LICENSE_RE.finditer(text):
            sec = self._get_section(m.start(), section_spans)
            candidates.append({
                "canonical_skill": "Professional Driver's License (LTO)",
                "raw_mention": m.group(0).strip(),
                "source_section": sec,
                "extraction_method": "Regex_Pattern",
                "confidence_score": 0.96,
                "offset": m.start()
            })

        # 2d. TESDA Certification Pattern
        for m in _TESDA_CERT_RE.finditer(text):
            sec = self._get_section(m.start(), section_spans)
            raw = m.group(0).strip()
            raw_lower = raw.lower()
            if "smaw" in raw_lower or "welding" in raw_lower:
                candidates.append({
                    "canonical_skill": "Shielded Metal Arc Welding (SMAW)",
                    "raw_mention": raw,
                    "source_section": sec,
                    "extraction_method": "Regex_Pattern",
                    "confidence_score": 0.95,
                    "offset": m.start()
                })
            candidates.append({
                "canonical_skill": "TESDA National Certificate (NC II)",
                "raw_mention": raw,
                "source_section": sec,
                "extraction_method": "Regex_Pattern",
                "confidence_score": 0.95,
                "offset": m.start()
            })

        # 2e. PRC Licensure Exam Pattern
        for m in _PRC_LICENSE_RE.finditer(text):
            sec = self._get_section(m.start(), section_spans)
            field = m.group(1).strip().lower()
            if "civil" in field:
                canonical = "PRC Registered Civil Engineer"
            elif "mechanical" in field:
                canonical = "PRC Registered Mechanical Engineer"
            elif "electrical" in field:
                canonical = "PRC Registered Electrical Engineer"
            elif "nurse" in field or "nursing" in field:
                canonical = "PRC Registered Nurse"
            elif "cpa" in field or "accountant" in field:
                canonical = "PRC Certified Public Accountant (CPA)"
            elif "teacher" in field or "education" in field:
                canonical = "PRC Licensed Professional Teacher (LPT)"
            else:
                canonical = f"PRC Licensed {m.group(1).strip().title()}"
            candidates.append({
                "canonical_skill": canonical,
                "raw_mention": m.group(0).strip(),
                "source_section": sec,
                "extraction_method": "Regex_Pattern",
                "confidence_score": 0.95,
                "offset": m.start()
            })

        # 2f. Competency Prefixes ("Proficient in...", "Skilled in...")
        for m in _COMPETENCY_PREFIX_RE.finditer(text):
            sec = self._get_section(m.start(), section_spans)
            phrase = m.group(1).strip()
            items = re.split(r'[,;|]|\band\b|\bwith\b', phrase)
            for item in items:
                clean_item = item.strip().strip("-•*►▪()")
                if not clean_item or len(clean_item) < 3:
                    continue

                item_lower = clean_item.lower()
                if item_lower in _COMPOUND_SKILL_MAP:
                    for mapped_canonical in _COMPOUND_SKILL_MAP[item_lower]:
                        candidates.append({
                            "canonical_skill": mapped_canonical,
                            "raw_mention": clean_item,
                            "source_section": sec,
                            "extraction_method": "Regex_Pattern",
                            "confidence_score": 0.92,
                            "offset": m.start()
                        })
                    continue

                if item_lower in self.alias_to_canonical:
                    candidates.append({
                        "canonical_skill": self.alias_to_canonical[item_lower],
                        "raw_mention": clean_item,
                        "source_section": sec,
                        "extraction_method": "Regex_Pattern",
                        "confidence_score": 0.92,
                        "offset": m.start()
                    })
                elif fuzz and len(clean_item) >= 4:
                    best_match = process.extractOne(
                        clean_item,
                        list(self.alias_to_canonical.keys()),
                        scorer=fuzz.token_sort_ratio
                    )
                    if best_match and best_match[1] >= 85:
                        matched_canonical = self.alias_to_canonical[best_match[0]]
                        candidates.append({
                            "canonical_skill": matched_canonical,
                            "raw_mention": clean_item,
                            "source_section": sec,
                            "extraction_method": "Fuzzy_Normalized",
                            "confidence_score": round(0.75 + (best_match[1] - 85) / 100 * 0.20, 2),
                            "offset": m.start()
                        })

        # 2g. Action Verb + Object Noun Phrases via Dependency Parsing
        try:
            doc = get_doc(text)
            action_verbs = {
                "operate", "maintain", "perform", "handle", "conduct", "execute",
                "prepare", "develop", "build", "manage", "supervise", "monitor",
                "install", "configure", "fabricate", "weld", "inspect", "draft", "encode"
            }
            for verb, obj in get_verb_object_pairs(doc):
                if verb.lower() in action_verbs:
                    obj_clean = obj.strip()
                    if len(obj_clean) >= 4:
                        obj_lower = obj_clean.lower()
                        if obj_lower in _COMPOUND_SKILL_MAP:
                            for mapped in _COMPOUND_SKILL_MAP[obj_lower]:
                                candidates.append({
                                    "canonical_skill": mapped,
                                    "raw_mention": f"{verb} {obj}",
                                    "source_section": "Work Experience",
                                    "extraction_method": "Syntactic_Dependency",
                                    "confidence_score": 0.90,
                                    "offset": text.lower().find(obj_lower) if obj_lower in text.lower() else 0
                                })
                        elif obj_lower in self.alias_to_canonical:
                            candidates.append({
                                "canonical_skill": self.alias_to_canonical[obj_lower],
                                "raw_mention": f"{verb} {obj}",
                                "source_section": "Work Experience",
                                "extraction_method": "Syntactic_Dependency",
                                "confidence_score": 0.90,
                                "offset": text.lower().find(obj_lower) if obj_lower in text.lower() else 0
                            })
                        elif fuzz and len(obj_clean) >= 5:
                            match = process.extractOne(
                                obj_clean,
                                list(self.alias_to_canonical.keys()),
                                scorer=fuzz.token_sort_ratio
                            )
                            if match and match[1] >= 85:
                                candidates.append({
                                    "canonical_skill": self.alias_to_canonical[match[0]],
                                    "raw_mention": f"{verb} {obj}",
                                    "source_section": "Work Experience",
                                    "extraction_method": "Syntactic_Dependency",
                                    "confidence_score": round(0.75 + (match[1] - 85) / 100 * 0.20, 2),
                                    "offset": text.lower().find(obj_lower) if obj_lower in text.lower() else 0
                                })
        except Exception:
            pass

        # ─── Pass 3: Fuzzy Normalization, Prioritization & Deduplication ──────
        section_priority = {
            "Skills": 5,
            "Work Experience": 4,
            "Certifications": 4,
            "Summary": 3,
            "Education": 2,
            "General": 1
        }

        grouped_skills: Dict[str, Dict[str, Any]] = {}
        for cand in candidates:
            c_skill = cand["canonical_skill"]
            meta = self.taxonomy.get(c_skill, {})

            skill_type = meta.get("type", "Hard Skill")
            domain_category = meta.get("domain", "General Technical & Professional")
            is_tool = meta.get("is_tool", False)

            entry = {
                "canonical_skill": c_skill,
                "raw_mention": cand["raw_mention"],
                "skill_type": skill_type,
                "domain_category": domain_category,
                "source_section": cand["source_section"],
                "extraction_method": cand["extraction_method"],
                "confidence_score": cand["confidence_score"],
                "is_tool": is_tool,
                "_priority": section_priority.get(cand["source_section"], 1),
                "_offset": cand.get("offset", 0)
            }

            if c_skill not in grouped_skills:
                grouped_skills[c_skill] = entry
            else:
                existing = grouped_skills[c_skill]
                # Prioritize higher section relevance or higher confidence
                if (entry["_priority"] > existing["_priority"] or
                   (entry["_priority"] == existing["_priority"] and entry["confidence_score"] > existing["confidence_score"])):
                    grouped_skills[c_skill] = entry

        final_skills = []
        hard_skills_set = set()
        soft_skills_set = set()
        tools_set = set()
        certs_set = set()
        languages_set = set()

        for c_skill, data in sorted(grouped_skills.items(), key=lambda x: x[0]):
            stype = data["skill_type"]
            is_tool = data["is_tool"]

            clean_entry = {
                "canonical_skill": data["canonical_skill"],
                "raw_mention": data["raw_mention"],
                "skill_type": stype,
                "domain_category": data["domain_category"],
                "source_section": data["source_section"],
                "extraction_method": data["extraction_method"],
                "confidence_score": data["confidence_score"]
            }
            final_skills.append(clean_entry)

            if is_tool:
                tools_set.add(c_skill)

            if stype == "Hard Skill":
                if not is_tool:
                    hard_skills_set.add(c_skill)
                else:
                    tools_set.add(c_skill)
            elif stype == "Soft Skill":
                soft_skills_set.add(c_skill)
            elif stype == "Certification / License":
                certs_set.add(c_skill)
            elif stype == "Language":
                languages_set.add(c_skill)

        hard_count = len([s for s in final_skills if s["skill_type"] == "Hard Skill"])
        soft_count = len([s for s in final_skills if s["skill_type"] == "Soft Skill"])
        cert_count = len([s for s in final_skills if s["skill_type"] == "Certification / License"])
        lang_count = len([s for s in final_skills if s["skill_type"] == "Language"])

        return {
            "total_unique_skills": len(final_skills),
            "skill_summary_by_type": {
                "hard_skills_count": hard_count,
                "soft_skills_count": soft_count,
                "certifications_and_licenses_count": cert_count,
                "languages_count": lang_count
            },
            "extracted_skills": final_skills,
            "categorized_view": {
                "hard_skills": sorted(list(hard_skills_set)),
                "soft_skills": sorted(list(soft_skills_set)),
                "tools_and_technologies": sorted(list(tools_set)),
                "certifications_and_eligibility": sorted(list(certs_set)),
                "languages": sorted(list(languages_set))
            }
        }


# ─── Singleton & Public Interface ─────────────────────────────────────────────
_SKILLS_EXTRACTOR = PhilippineSkillsExtractor()


def extract_structured_skills(text: str) -> Dict[str, Any]:
    """
    Extracts structured skills across the entire Philippine workforce spectrum.
    Returns the comprehensive JSON schema dictionary.
    """
    return _SKILLS_EXTRACTOR.extract(text)


def extract_skills(text: str) -> str:
    """
    Extracts skills and returns a clean pipe-separated string.
    Maintains backward compatibility with the existing parsing pipeline.
    """
    structured = _SKILLS_EXTRACTOR.extract(text)
    names = [s["canonical_skill"] for s in structured.get("extracted_skills", [])]
    return " | ".join(names[:50]) if names else ""


def extract_skills_list(text: str) -> List[str]:
    """
    Extracts skills and returns a clean list of canonical skill names.
    Maintains backward compatibility with the existing parsing pipeline.
    """
    structured = _SKILLS_EXTRACTOR.extract(text)
    return [s["canonical_skill"] for s in structured.get("extracted_skills", [])]


def load_external_skill_datasets(
    esco_csv_path: Optional[str] = None,
    onet_txt_path: Optional[str] = None,
    tesda_json_path: Optional[str] = None
) -> int:
    """
    Ingests external skill datasets (ESCO, O*NET, TESDA) and dynamically
    re-indexes the keyword processor.
    """
    return _SKILLS_EXTRACTOR.load_external_datasets(esco_csv_path, onet_txt_path, tesda_json_path)


# ─── Verification & Demonstration Block ───────────────────────────────────────
if __name__ == "__main__":
    p1_jollibee = """
OBJECTIVE
Seeking a Service Crew or Janitor position where I can utilize my skills in food preparation,
kitchen sanitation, and customer service. Willing to learn and work under pressure.

WORK EXPERIENCE
Service Crew
Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna
June 2023 - December 2023
- Food preparation and kitchen sanitation in frying and grill stations.
- Handled POS cashiering, cash handling, and customer order taking.
- Performed dining area table bussing, tray cleaning, and dishwashing.

Utility Personnel / Janitor
Robinsons Place Antipolo
January 2022 - May 2023
- Floor buffing and housekeeping using heavy-duty rotary floor polisher.
- Restroom sanitation, trash segregation, and chemical handling.

Delivery Rider
Lalamove Philippines / Self-Employed
2021 - 2022
- Single motorcycle driving with Professional Driver's License Restriction 1, 2.
- Defensive driving and mobile GPS navigation across Metro Manila and Rizal.

SKILLS & TRAITS
- Fast learner and willing to be trained
- Can work under pressure and willing to render overtime
- Team player with good interpersonal skills
- Fluent in Tagalog and basic English
"""

    p2_bpo = """
CAREER SUMMARY
Dedicated Customer Service Representative with 2+ years of BPO experience handling inbound technical support and customer care accounts.

CORE COMPETENCIES & SKILLS
- Customer service & active listening
- Conflict de-escalation & complaint resolution
- 45 WPM typing speed
- Inbound call handling & email correspondence
- Ticketing systems: Zendesk, Freshdesk, Jira Service Desk
- CRM & VoIP tools: Salesforce, Avaya One-X, Cisco IP Phone
- Proficient in Microsoft Office (Excel VLOOKUP & Pivot Tables, Word, PowerPoint)
- 201 file management and data encoding
- Amenable to shifting schedules, night shift, and holiday overtime
- Languages: Fluent in English and Filipino / Tagalog

WORK EXPERIENCE
Technical Support Representative (TSR)
Concentrix Philippines - Pasig City
March 2022 - Present
- Handled 50+ inbound customer inquiries daily regarding internet connectivity and account billing.
- Utilized Zendesk and Avaya for real-time call logging and customer de-escalation.
"""

    p3_dev = """
SOFTWARE ENGINEER
Makati City, Metro Manila | 09171234567 | dev@gmail.com

TECHNICAL SKILLS
Languages: Java, C#, TypeScript, JavaScript, Python, SQL, HTML5, CSS3
Frameworks & Libraries: Spring Boot, NestJS, Node.js, Express.js, React.js, Next.js, Tailwind CSS
Databases & Cloud: PostgreSQL, Supabase, MongoDB Atlas, Redis, Docker, AWS (S3, EC2)
Tools & Testing: Git, GitHub Actions, Postman, Jest, Cypress, CI/CD, Linux

PROFESSIONAL EXPERIENCE
Full Stack Software Developer
Accenture Philippines | BGC, Taguig City
August 2023 - Present
- Developed scalable RESTful APIs using NestJS and PostgreSQL with Supabase.
- Built responsive UI components using React and Tailwind CSS.
- Performed manual regression testing and automated API testing using Postman.
- Collaborated in an Agile Scrum environment with daily standups and sprint planning.
"""

    p4_engineer = """
REGISTERED CIVIL ENGINEER / SITE ENGINEER
Binangonan, Rizal | 09181234567 | civil_eng@gmail.com

LICENSES & CERTIFICATIONS
- PRC Registered Civil Engineer (Civil Engineering Board Exam Passer)
- BOSH SO2 Certified (Basic Occupational Safety and Health)
- TESDA Shielded Metal Arc Welding (SMAW) NC II Certified
- COSH Certified (Construction Occupational Safety and Health)

TECHNICAL & ENGINEERING SKILLS
- AutoCAD (2D & 3D), STAAD.Pro, ETABS, Revit, SketchUp, MS Project
- Structural analysis and design
- Site supervision and construction management
- Concrete pouring and rebar inspection
- Quantity surveying, cost estimation, and Bill of Quantities (BOQ) preparation
- Blueprint reading and architectural plan interpretation
- TIG/MIG welding and metal fabrication

WORK EXPERIENCE
Project Site Engineer
DMCI Homes - Quezon City
March 2023 - Present
- Conducted daily site supervision and reinforced concrete quality inspection.
- Prepared daily accomplishment reports and monitored subcontractor manpower.
- Ensured strict compliance with construction safety and ISO 9001 quality standards.
"""

    resumes = [
        ("Resume 1: Blue-Collar & Service Worker (Jollibee / Janitor / Rider)", p1_jollibee),
        ("Resume 2: BPO CSR & Admin Assistant", p2_bpo),
        ("Resume 3: Full Stack Software Developer", p3_dev),
        ("Resume 4: Site Civil Engineer & TESDA Welder", p4_engineer)
    ]

    for title, resume_text in resumes:
        print(f"\n{'='*80}\n{title}\n{'='*80}")
        result = extract_structured_skills(resume_text)
        print(json.dumps(result, indent=2))
