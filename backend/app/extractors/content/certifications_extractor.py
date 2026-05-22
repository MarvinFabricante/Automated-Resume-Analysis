import re

# ─── Section Headers ─────────────────────────────────────────────────────────

_CERT_HEADERS = [
    "CERTIFICATIONS", "CERTIFICATES", "CERTIFICATION", "CERTIFICATE",
    "LICENSES", "LICENSURE", "PROFESSIONAL CERTIFICATIONS",
    "PROFESSIONAL LICENSES", "CERTIFICATIONS AND LICENSES",
    "LICENSES AND CERTIFICATIONS", "CREDENTIALS",
    "PROFESSIONAL CREDENTIALS", "ACCREDITATIONS",
    "TRAININGS AND CERTIFICATIONS", "CERTIFICATIONS AND TRAINING",
]

_STOP_HEADERS = [
    "EXPERIENCE", "SKILLS", "EDUCATION", "PROJECTS", "WORK",
    "EMPLOYMENT", "AFFILIATIONS", "REFERENCES", "INTERESTS",
    "ACHIEVEMENTS", "AWARDS", "HOBBIES", "VOLUNTEER",
    "PERSONAL", "ACTIVITIES", "PUBLICATIONS", "LANGUAGES",
    "TECHNICAL SKILLS", "CORE COMPETENCIES",
    "TRAINING", "TRAININGS", "SEMINARS", "WORKSHOPS",
    "PROFESSIONAL DEVELOPMENT", "SUMMARY", "OBJECTIVE",
]

# ─── Well-known certifications for pattern matching ──────────────────────────

_KNOWN_CERTIFICATIONS = [
    # Cloud
    r"AWS\s+(?:Certified|Solutions?\s+Architect|Developer|SysOps|DevOps)",
    r"AWS\s+Cloud\s+Practitioner",
    r"Azure\s+(?:Administrator|Developer|Solutions?\s+Architect|Fundamentals|Data\s+Engineer)",
    r"(?:AZ|AI|DP|SC|PL|MS|MB)[-\s]?\d{2,4}",
    r"Google\s+Cloud\s+(?:Professional|Associate|Certified)",
    r"GCP\s+(?:Professional|Associate)",
    r"Certified\s+Kubernetes\s+(?:Administrator|Application\s+Developer)",
    r"\bCKA\b", r"\bCKAD\b", r"\bCKS\b",
    
    # Programming / Development
    r"Oracle\s+Certified\s+(?:Professional|Associate|Java)",
    r"\bOCJP\b", r"\bOCA\b", r"\bOCP\b",
    r"Microsoft\s+Certified\s+(?:Professional|Solutions?|Developer|Azure)",
    r"Certified\s+Scrum\s+(?:Master|Developer|Product\s+Owner)",
    r"\bCSM\b", r"\bCSD\b", r"\bCSPO\b",
    r"\bPMP\b", r"Project\s+Management\s+Professional",
    r"\bPRINCE2\b",
    r"ITIL\s+(?:v?\d|Foundation|Practitioner|Expert)?",
    r"\bITIL\b",
    
    # Data / AI
    r"TensorFlow\s+(?:Developer\s+)?Certific",
    r"Databricks\s+(?:Certified|Lakehouse)",
    r"Snowflake\s+(?:SnowPro|Certified)",
    r"Certified\s+(?:Data\s+(?:Analyst|Engineer|Scientist))",
    r"(?:IBM|SAS|Tableau|Power\s+BI)\s+Certif",
    r"Google\s+Data\s+Analytics",
    r"Microsoft\s+(?:Power\s+Platform|Data|AI)\s+Fundamentals",
    
    # Security
    r"CISSP", r"CISM", r"CEH", r"CompTIA\s+Security\+",
    r"CompTIA\s+(?:A\+|Network\+|Cloud\+|Linux\+|Server\+|CySA\+|PenTest\+)",
    r"Certified\s+Information\s+(?:Security|Systems)",
    r"Certified\s+Ethical\s+Hacker",
    r"\bOSCP\b", r"\bGIAC\b",
    
    # Networking
    r"CCNA", r"CCNP", r"CCIE",
    r"Cisco\s+Certified\s+(?:Network|Internetwork)",
    
    # Agile / Process
    r"SAFe\s+(?:\d\.?\d?\s+)?(?:Agilist|Practitioner|Scrum\s+Master)",
    r"Lean\s+Six\s+Sigma\s+(?:Green|Black|Yellow|White)\s+Belt",
    r"Six\s+Sigma",
    r"\bPMI[\s-]ACP\b",
    
    # Philippine-specific
    r"Civil\s+Service\s+(?:Eligible|Eligibility|Professional|Sub-?Professional)",
    r"\bCSE\b(?=\s+(?:Professional|Sub))",
    r"Philippine\s+(?:Board|Professional)\s+",
    r"\bPRC\b\s+(?:License|Board|Registered)",
    r"Board\s+(?:Passer|Exam|Certified)",
    r"Licensed\s+(?:Professional|Electrical|Mechanical|Civil|Chemical)\s+Engineer",
    r"Registered\s+(?:Nurse|Pharmacist|Accountant|Architect|Engineer)",
    r"\bCPA\b", r"Certified\s+Public\s+Accountant",
    r"\bRN\b(?=\s)", r"Registered\s+Nurse",
    
    # General
    r"Certified\s+\w+\s+(?:Professional|Specialist|Expert|Practitioner|Analyst|Manager)",
    r"Certificate\s+(?:in|of|for)\s+\w+",
]


def _is_header(line: str, keywords: list[str]) -> bool:
    """Check if a line is a section header."""
    clean = line.strip().upper()
    if not clean or len(clean.split()) >= 6:
        return False
    stripped = re.sub(r'^[\s\-–—=_*#•►:]+', '', clean)
    stripped = re.sub(r'[\s\-–—=_*#•►:]+$', '', stripped)
    for kw in keywords:
        if stripped == kw or stripped.startswith(kw + ":") or clean == kw:
            return True
    return False


def extract_certifications(text: str) -> str:
    """
    Extracts certifications from resume text.
    
    Strategy:
    1. Find the certifications section and extract entries.
    2. Scan the entire document for known certification patterns.
    3. Merge and deduplicate.
    
    Returns pipe-separated list of certifications.
    """
    if not text:
        return ""

    lines = text.split('\n')

    # ── Step 1: Section-based extraction ──────────────────────────────────────
    section_certs = []
    found_section = False

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if _is_header(clean_line, _CERT_HEADERS):
            found_section = True
            # Check for inline content after colon
            colon_idx = clean_line.find(':')
            if colon_idx >= 0:
                after = clean_line[colon_idx + 1:].strip()
                if after:
                    section_certs.extend(_split_cert_items(after))
            continue

        if found_section:
            if _is_header(clean_line, _STOP_HEADERS):
                break
            # Skip very short or decorative lines
            if len(clean_line) > 3:
                section_certs.append(clean_line.lstrip('•-–▪►✓* ').strip())

    # ── Step 2: Pattern-based scan of full document ───────────────────────────
    pattern_certs = []
    for cert_pattern in _KNOWN_CERTIFICATIONS:
        matches = re.finditer(cert_pattern, text, re.IGNORECASE)
        for m in matches:
            cert = m.group(0).strip()
            if cert and len(cert) > 2:
                pattern_certs.append(cert)

    # ── Step 3: Merge and deduplicate ─────────────────────────────────────────
    seen_lower = set()
    unique_certs = []

    def _add_cert(cert: str):
        cleaned = cert.strip()
        if not cleaned or len(cleaned) < 3:
            return
        key = cleaned.lower()
        # Skip noise
        if key in {'and', 'or', 'the', 'with', 'for', 'etc', 'n/a', 'none'}:
            return
        if key not in seen_lower:
            seen_lower.add(key)
            unique_certs.append(cleaned)

    # Section certs take priority (preserves resume phrasing)
    for c in section_certs:
        _add_cert(c)

    # Add pattern-matched certs
    for c in pattern_certs:
        _add_cert(c)

    return " | ".join(unique_certs[:15]) if unique_certs else ""


def _split_cert_items(text: str) -> list[str]:
    """Split a certification string into individual items."""
    # Split by common delimiters
    for d in ['|', '•', '●', '►', ';']:
        text = text.replace(d, ',')
    
    items = []
    for chunk in text.split(','):
        cleaned = chunk.strip().strip('*-–—').strip()
        if cleaned and len(cleaned) > 3:
            items.append(cleaned)
    return items
