import re
from typing import List, Tuple, Set, Optional


# Common resume header words / noise that should NOT be treated as names
_NOISE_WORDS = {
    "resume", "cv", "curriculum", "vitae", "portfolio", "profile",
    "personal", "information", "details", "contact", "objective",
    "summary", "about", "me", "page", "application", "career",
    "statement", "overview", "candidate", "references", "education",
    "experience", "work history", "skills", "projects", "certifications",
    "certification", "certificate", "certificates", "professional",
    "biodata", "bio-data", "personal data sheet", "pds", "personal profile",
    "professional profile", "employment", "qualifications", "curriculum vitae",
    "cover letter", "applicant", "job application", "application form",
    "firstname", "lastname", "first name", "last name", "firstname lastname",
    "your name", "full name", "sample", "template", "credential", "foundation",
    "scrum", "cyber", "security", "awareness", "awards", "achievements",
    "trainings", "training", "seminars", "workshops", "eligibility", "licenses",
    "postman", "docker", "python", "java", "javascript", "typescript", "react",
    "angular", "vue", "nodejs", "laravel", "django", "flask", "spring",
    "mysql", "postgresql", "mongodb", "redis", "firebase", "supabase", "aws",
    "azure", "gcp", "git", "github", "gitlab", "jira", "selenium", "cypress",
    "playwright", "appium", "figma", "canva", "photoshop", "illustrator",
    "wordpress", "shopify", "salesforce", "zendesk", "hubspot", "kubernetes",
    "terraform", "jenkins", "linux", "ubuntu", "windows", "android", "ios"
}

# Words that strongly disqualify a line from being a candidate's personal name
_ROLE_DISQUALIFIERS = {
    "engineer", "developer", "programmer", "architect", "designer",
    "manager", "lead", "director", "specialist", "consultant", "analyst",
    "officer", "administrator", "coordinator", "supervisor", "intern",
    "trainee", "associate", "assistant", "technician", "scientist",
    "fullstack", "full-stack", "frontend", "backend", "software",
    "web", "mobile", "devops", "cloud", "data", "qa", "tester",
    "product", "project", "marketing", "sales", "executive", "accountant",
    "representative", "clerk", "cashier", "encoder", "operator", "crew",
    "nurse", "teacher", "instructor", "professor", "auditor", "teller",
    "generalist", "receptionist", "staff", "agent", "writer", "editor",
    "underwriter", "adviser", "advisor", "support", "service", "customer",
    "technical", "human", "resources", "virtual", "call", "center",
    "information", "technology", "logistics", "operations", "telecommunications"
}

# Specific compound titles / role phrases common in Philippine resumes
_COMPOUND_ROLES = [
    r"\bcustomer\s+service\s+(?:representative|agent|specialist|associate)\b",
    r"\btechnical\s+support\s+(?:representative|agent|specialist)\b",
    r"\bcall\s+center\s+agent\b",
    r"\bfull\s*stack\s+(?:web\s+)?developer\b",
    r"\bfront\s*end\s+developer\b",
    r"\bback\s*end\s+developer\b",
    r"\bsoftware\s+(?:engineer|developer)\b",
    r"\bhuman\s+resources\s+(?:officer|specialist|generalist|assistant|manager)\b",
    r"\baccounting\s+(?:officer|assistant|clerk|specialist)\b",
    r"\bit\s+supervisor\b",
    r"\bvirtual\s+assistant\b",
    r"\bdata\s+(?:analyst|scientist|engineer)\b",
    r"\bgraphic\s+designer\b",
    r"\bquality\s+assurance\b",
    r"\bcivil\s+engineer\b",
    r"\belectrical\s+engineer\b",
    r"\bmechanical\s+engineer\b",
]

_NOT_NAME_PATTERNS = [
    r"@",                              # email
    r"\d{3,}",                         # phone / long numbers
    r"https?://",                      # URL
    r"\b(www\.|linkedin|github|gitlab|portfolio)\b",
    r"\b(street|st\.|city|province|metro|manila|philippines|ave\.|road|blvd|brgy|barangay|poblacion|subdivision|village)\b",  # address
    r"(?:,\s*|\b(?:province|prov\.)\s+(?:of\s+)?)(?:cavite|laguna|batangas|bulacan|pampanga|bataan|zambales|tarlac|pangasinan|ilocos|isabela|cagayan|albay|camarines|sorsogon|cebu|bohol|iloilo|negros|leyte|samar|davao|bukidnon|misamis|zamboanga|benguet|rizal)\b",  # PH provinces in address context
    r"\b(skills|education|experience|work|history|summary|objective|certifications|references|training)\b",
    r"\b(years?\s+of\s+experience|curriculum\s+vitae|bio[\s-]?data)\b",
]

_HONORIFICS = [
    r"\b(?:Engr\.?|Dr\.?|Atty\.?|Arch\.?|Ar\.?|Prof\.?|Hon\.?|Rev\.?|Mr\.?|Ms\.?|Mrs\.?)\s+",
]

# PRC professional licenses and international post-nominals widely used in the Philippines
_PROFESSIONAL_SUFFIXES = {
    "CPA", "RN", "MD", "ECE", "CE", "ME", "EE", "IE", "LPT", "RMT", "RPh", "RPm",
    "REA", "REB", "CHE", "MIT", "MSIT", "MBA", "PHD", "PMP", "CSP", "UAP", "PIA", "FAP", "CFP",
    "RCE", "RMP", "PECE", "PME", "PEE", "REE", "RME", "ECT", "RPsy", "CHRA", "SO1", "SO2", "SO3", "SO4"
}

_GENERATIONAL_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}

# Filipino particles & prefixes in compound surnames
_FILIPINO_PARTICLES = {"dela", "del", "delos", "de", "san", "santa", "santo"}


_ROLE_WORDS = {
    "specialist", "engineer", "developer", "programmer", "architect", "designer",
    "manager", "lead", "director", "consultant", "analyst", "officer",
    "administrator", "coordinator", "supervisor", "intern", "trainee", "associate",
    "assistant", "technician", "scientist", "fullstack", "full-stack", "frontend", "backend",
    "devops", "cloud", "data", "qa", "tester", "product", "project", "marketing",
    "sales", "executive", "accountant", "representative", "clerk", "cashier",
    "encoder", "operator", "crew", "nurse", "teacher", "instructor", "professor",
    "auditor", "teller", "generalist", "receptionist", "staff", "agent", "writer",
    "editor", "student", "undergraduate", "graduate", "e-commerce", "ecommerce",
    "e-commerse", "virtual", "support", "service", "customer", "operations",
    "specialists", "engineers", "developers", "technicians", "senior", "junior",
    "it", "hr", "full", "stack", "web", "software", "mobile", "digital",
    "human", "resources", "accounting", "electrical", "engineering", "mechanical",
    "civil", "machine", "industrial", "quality", "assurance", "control",
    "technical", "business", "systems", "network", "database", "security",
    "email", "phone", "mobile", "contact", "address", "location", "tel"
}


def _strip_roles_and_titles(text: str) -> str:
    """
    Strips trailing or leading job titles and role words that may be merged
    with candidate names during PDF/DOCX column or line extraction.
    Example: 'John Paul T. Basagre E-commerse Specialist' -> 'John Paul T. Basagre'
             'John Paul T. Basagre - E-commerce Specialist' -> 'John Paul T. Basagre'
             'E-commerce Specialist John Paul T. Basagre' -> 'John Paul T. Basagre'
    """
    if not text:
        return ""
    cleaned = text.strip()

    # If segmented by pipe, bullet, dash, or slash, check each segment
    for sep in ['|', '•', '–', '—', ' - ', ' / ']:
        if sep in cleaned:
            parts = [p.strip() for p in cleaned.split(sep) if p.strip()]
            for p in parts:
                p_words = p.lower().split()
                # If segment contains no role words and looks like a name (2-5 words), return it
                if (
                    2 <= len(p_words) <= 5
                    and not any(w.rstrip('.,') in _ROLE_WORDS for w in p_words)
                    and _is_plausible_name(p)
                ):
                    return p

    # Remove trailing role words
    words = cleaned.split()
    while words and words[-1].lower().rstrip('.,') in _ROLE_WORDS:
        words.pop()
    # Remove leading role words
    while words and words[0].lower().rstrip('.,') in _ROLE_WORDS:
        words.pop(0)

    res = " ".join(words).strip(' -–—:,|')
    return res


def _clean_honorifics(text: str) -> str:
    """Remove prefixes like Engr., Ar., Dr., Atty. while retaining the actual name."""
    cleaned = text.strip()
    for h in _HONORIFICS:
        cleaned = re.sub(f"^{h}", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _invert_surname_first(name: str) -> str:
    """
    Detect and convert Philippine government/academic format 'Surname, Given Name [Middle] [Suffix]'
    to natural order 'Given Name [Middle] Surname [Suffix]'.
    Examples:
      - 'BASAGRE, JOHN PAUL T.' -> 'JOHN PAUL T. BASAGRE'
      - 'DELA CRUZ, JUAN M.' -> 'JUAN M. DELA CRUZ'
      - 'Santos, Maria Theresa G., CPA' -> 'Maria Theresa G. Santos, CPA'
    """
    if ',' not in name:
        return name

    parts = [p.strip() for p in name.split(',') if p.strip()]
    if len(parts) < 2:
        return name

    surname = parts[0]
    given_and_middle = parts[1]

    # Check if part 1 is actually just a suffix (e.g. 'Juan Dela Cruz, Jr.' or 'Maria Santos, CPA')
    clean_p1_upper = re.sub(r'[^A-Za-z]', '', given_and_middle).upper()
    if clean_p1_upper in _GENERATIONAL_SUFFIXES or clean_p1_upper in _PROFESSIONAL_SUFFIXES:
        return name

    # Suffixes in subsequent parts (e.g. ['Dela Cruz', 'Juan M.', 'Jr.'])
    extra_suffix = ""
    if len(parts) > 2:
        suffixes = parts[2:]
        extra_suffix = ", " + ", ".join(suffixes)

    inverted = f"{given_and_middle} {surname}{extra_suffix}".strip()
    return inverted


def _is_plausible_name(text: str, allow_single_word: bool = False) -> bool:
    """Check if a string looks like a human candidate name."""
    if not text or '\n' in text or '\r' in text:
        return False

    candidate = _clean_honorifics(text.strip())
    # Temporarily invert surname-first if comma present
    candidate = _invert_surname_first(candidate)

    # Remove common trailing suffixes for length/word checks
    candidate_base = re.sub(
        r'[,.\s]+(?:Jr\.?|Sr\.?|II|III|IV|V|CPA|RN|PE|PMP|MD|ECE|CE|ME|EE|LPT|RMT|RPh|RPm|UAP)$',
        '',
        candidate,
        flags=re.IGNORECASE
    ).strip()

    # Length bounds
    if len(candidate_base) < 3 or len(candidate_base) > 50:
        return False

    words = candidate_base.split()
    min_words = 1 if allow_single_word else 2
    if len(words) < min_words or len(words) > 6:
        return False

    # Check against noise words
    lower = candidate_base.lower()
    if any(nw == lower or f" {nw} " in f" {lower} " for nw in _NOISE_WORDS):
        return False
    if any(w.lower().rstrip('.,') in _NOISE_WORDS for w in words):
        return False

    # Check for known compound role patterns (e.g. 'Customer Service Representative')
    for crole in _COMPOUND_ROLES:
        if re.search(crole, lower):
            return False

    # Check if this line is actually a job title (e.g., "Senior Software Engineer")
    word_set = {w.lower().rstrip(',.') for w in words}
    role_matches = word_set.intersection(_ROLE_DISQUALIFIERS)
    if role_matches and len(role_matches) >= 1:
        if len(role_matches) >= 2 or any(w in {"senior", "junior", "lead", "software", "fullstack", "web", "customer", "service"} for w in word_set):
            return False
        # If single role match, but line has 1 or 2 words, it's almost certainly a title (e.g. "Developer", "Accountant")
        if len(words) <= 2:
            return False

    # Disqualifying patterns (emails, phone numbers, urls, addresses)
    for pattern in _NOT_NAME_PATTERNS:
        if re.search(pattern, candidate, re.IGNORECASE):
            return False

    # Check alphanumeric characters
    cleaned = re.sub(r"[.\-'\s,]", "", candidate_base)
    if not cleaned:
        return False
    alpha_ratio = sum(1 for c in cleaned if c.isalpha()) / len(cleaned)
    if alpha_ratio < 0.85:
        return False

    return True


def is_valid_name(name: str) -> bool:
    """Public helper to verify if a candidate string is a plausible name."""
    return _is_plausible_name(name)


def _normalize_name(name: str) -> str:
    """Normalize a name to proper Title Case while handling Filipino conventions."""
    if not name:
        return ""

    # Remove leading/trailing special characters
    name = re.sub(r'^[\s\-–—:•|*#]+', '', name)
    name = re.sub(r'[\s\-–—:•|*#]+$', '', name)

    # Invert surname-first if applicable
    name = _invert_surname_first(name)

    # Clean honorifics at beginning (e.g. "Engr.", "Dr.")
    name = _clean_honorifics(name)

    parts = name.split()
    result = []
    for i, part in enumerate(parts):
        clean_part = part.rstrip(',.')
        has_comma = ',' in part
        trailing_comma = ',' if has_comma else ''

        upper_clean = clean_part.upper()

        # Handle 'Ma.' (Maria abbreviation in the Philippines)
        if upper_clean == "MA":
            result.append(f"Ma.{trailing_comma}")
            continue

        # Professional and generational suffixes
        if upper_clean in _GENERATIONAL_SUFFIXES or upper_clean in _PROFESSIONAL_SUFFIXES:
            if upper_clean in {"JR", "SR"}:
                result.append(f"{upper_clean.capitalize()}.{trailing_comma}")
            else:
                result.append(f"{upper_clean}{trailing_comma}")
            continue

        # Handle hyphenated parts (e.g. Santos-Reyes, Mary-Ann)
        if '-' in part:
            subparts = part.split('-')
            norm_subs = [sp.capitalize() for sp in subparts]
            result.append("-".join(norm_subs) + trailing_comma)
            continue

        # Handle apostrophes (e.g. O'Connor, D'Angelo)
        if "'" in part:
            idx = part.index("'")
            result.append(part[:idx+1].capitalize() + part[idx+1:].capitalize() + trailing_comma)
            continue

        # Handle Scottish/Irish Mc...
        if (clean_part.startswith("Mc") or clean_part.startswith("MC") or clean_part.startswith("mc")) and len(clean_part) > 2:
            result.append("Mc" + clean_part[2:].capitalize() + trailing_comma)
            continue

        # Handle single letter middle initials (e.g. "T" -> "T.")
        if len(clean_part) == 1 and clean_part.isalpha():
            result.append(f"{clean_part.upper()}.{trailing_comma}")
            continue

        # Handle Filipino and Spanish compound surname particles
        # "Dela", "Del", "Delos", "De", "San", "Santa", "Santo"
        part_lower = clean_part.lower()
        if part_lower in _FILIPINO_PARTICLES:
            result.append(part_lower.capitalize() + trailing_comma)
            continue

        # Default title case
        result.append(clean_part.capitalize() + trailing_comma)

    return " ".join(result).strip(' ,')


def _score_candidate_name(candidate: str, line_idx: int, email: str = "") -> float:
    """Score candidate name based on line index, email correlation, and Philippine naming signals."""
    score = 100.0 - (line_idx * 15.0)

    clean_base = re.sub(
        r'[,.\s]+(?:Jr\.?|Sr\.?|II|III|IV|V|CPA|RN|PE|PMP|MD|ECE|CE|ME|EE|LPT|RMT|RPh|RPm|UAP)$',
        '',
        candidate,
        flags=re.IGNORECASE
    ).strip()
    words = clean_base.split()

    # Typical Filipino full name has 2 to 4 words (e.g. Given Middle Surname)
    if len(words) in (2, 3, 4):
        score += 30.0

    # Presence of middle initial (e.g. T. or T)
    if any(len(w.rstrip('.')) == 1 and w[0].isalpha() for w in words):
        score += 25.0

    # Presence of Ma. (Maria abbreviation)
    if any(w.lower() in ("ma", "ma.") for w in words):
        score += 35.0

    # Presence of Filipino compound surname particles (Dela, Del, Delos, De, San, Santa)
    if any(w.lower() in _FILIPINO_PARTICLES for w in words):
        score += 30.0

    # Strong correlation with email tokens
    if email:
        email_user = email.split('@')[0].lower()
        email_clean = re.sub(r'[^a-zA-Z]', '', email_user)
        matched_tokens = 0
        for w in words:
            w_clean = re.sub(r'[^a-zA-Z]', '', w).lower()
            if len(w_clean) >= 3 and w_clean in email_clean:
                matched_tokens += 1
        if matched_tokens >= 2:
            score += 120.0
        elif matched_tokens == 1:
            score += 50.0

    return score


def extract_all_name_candidates(text: str, email: str = "") -> List[str]:
    """
    Extracts all plausible candidate names from resume text, ranked by confidence.
    Enforces header-only extraction (top ~10 lines), spaCy PERSON preference,
    role/title word stripping, Last-First-Middle formatting, and multi-line joining.
    """
    if not text:
        return []

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return []

    if not email:
        em_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text[:2000])
        if em_match:
            email = em_match.group(0)

    candidate_scores = {}

    def add_cand(raw: str, line_idx: int, bonus: float = 0.0):
        if not raw or '\n' in raw or '\r' in raw:
            return
        # Clean roles/titles from raw string
        stripped = _strip_roles_and_titles(raw)
        if not stripped or not _is_plausible_name(stripped):
            return
        norm = _normalize_name(stripped)
        if not norm:
            return
        sc = _score_candidate_name(stripped, line_idx, email) + bonus
        if norm not in candidate_scores or sc > candidate_scores[norm]:
            candidate_scores[norm] = sc

    # Strategy 1: spaCy NER PERSON entities in header area (top 10 lines / 1000 chars)
    header_chunk = "\n".join(lines[:12])
    ner_spans: List[str] = []
    try:
        from app.extractors.nlp.nlp_engine import get_doc
        doc = get_doc(header_chunk)
        for ent in doc.ents:
            if ent.label_ == "PERSON" and "\n" not in ent.text:
                ent_clean = _strip_roles_and_titles(ent.text.strip())
                if ent_clean:
                    ner_spans.append(_normalize_name(ent_clean))
                    add_cand(ent_clean, 0, bonus=15.0)
    except Exception:
        pass

    # Strategy 2: Labeled name field (English & Tagalog Bio-data)
    labeled_pattern = re.compile(
        r'^(?:Full\s*Name|Candidate\s*Name|Applicant\s*Name|Pangalan(?:\s*ng\s*Aplikante|\s*ng\s*Empleyado)?|Name)\s*[:.\-–—]\s*(.+)',
        re.IGNORECASE
    )
    for idx, line in enumerate(lines[:15]):
        match = labeled_pattern.match(line)
        if match:
            cand = match.group(1).strip()
            cand = re.split(r'\s*[|•]\s*', cand)[0].strip()
            add_cand(cand, idx, bonus=200.0)

    # Strategy 3: Scan header lines (first ~10 lines)
    header_lines_count = min(12, len(lines))
    for idx in range(header_lines_count):
        line = lines[idx]
        if len(line) > 120:
            continue

        upper = line.upper().strip()
        cleaned_header = re.sub(r'^[\s\-–—=_*#•►:]+|[\s\-–—=_*#•►:]+$', '', upper)

        # Stop scanning header if we reached a major section header
        if any(cleaned_header == sh or cleaned_header.startswith(sh + ":") for sh in {
            "WORK EXPERIENCE", "EXPERIENCE", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE",
            "WORK HISTORY", "EDUCATION", "EDUCATIONAL BACKGROUND", "SKILLS", "TECHNICAL SKILLS",
            "CERTIFICATIONS", "LICENSES", "LICENSES AND ELIGIBILITY", "TRAINING", "SEMINARS",
            "PROJECTS", "REFERENCES", "CHARACTER REFERENCES"
        }):
            break

        if upper in {"RESUME", "CV", "CURRICULUM VITAE", "PERSONAL INFORMATION",
                     "CONTACT INFORMATION", "CONTACT DETAILS", "PROFILE", "SUMMARY",
                     "PROFESSIONAL SUMMARY", "ABOUT ME", "BIODATA", "BIO-DATA"}:
            continue

        # Multi-segment lines: "John Paul T. Basagre | Web Developer"
        segments = re.split(r'\s*[|•/]\s*|\s+-\s+', line)
        for seg in segments:
            add_cand(seg.strip(), idx, bonus=20.0)

        # Colon-separated lines
        if ':' in line:
            _, _, after = line.partition(':')
            add_cand(after.strip(), idx)

        # Whole line with role stripped
        add_cand(line, idx, bonus=25.0)

        # Strategy 4: Check if adjacent lines at top of header are a split name
        # E.g., Line 0: "Basagre" and Line 1: "John Paul T." OR Line 0: "JHESED" and Line 1: "TACADENA"
        if idx <= 3 and idx + 1 < header_lines_count:
            next_line = lines[idx + 1]
            # Only join when neither raw line contains colons, pipes, emails, numbers, or role/noise words
            raw_pair = f"{line} {next_line}"
            raw_tokens = {w.lower().rstrip('.,:') for w in raw_pair.split()}
            has_role_or_noise = bool(
                raw_tokens.intersection(_ROLE_WORDS)
                or raw_tokens.intersection(_ROLE_DISQUALIFIERS)
                or raw_tokens.intersection(_NOISE_WORDS)
            )
            if (
                not has_role_or_noise
                and not any(c in raw_pair for c in ['@', ':', '|', 'http', '+63', '09'])
                and not re.search(r'\d', raw_pair)
                and _is_plausible_name(line, allow_single_word=True)
                and _is_plausible_name(next_line, allow_single_word=True)
            ):
                curr_words = line.split()
                next_words = next_line.split()
                # Case A: Both lines are 1-word (e.g. Line 0: "JHESED", Line 1: "TACADENA")
                if len(curr_words) == 1 and len(next_words) == 1:
                    add_cand(f"{line} {next_line}", idx, bonus=55.0)
                    add_cand(f"{next_line} {line}", idx, bonus=20.0)
                # Case B: One line is a 1-word surname and the other is 2-3 given/middle words
                elif len(curr_words) == 1 and 2 <= len(next_words) <= 3:
                    add_cand(f"{next_line} {line}", idx, bonus=50.0)
                    add_cand(f"{line} {next_line}", idx, bonus=20.0)
                elif len(next_words) == 1 and 2 <= len(curr_words) <= 3:
                    add_cand(f"{line} {next_line}", idx, bonus=50.0)
                    add_cand(f"{next_line} {line}", idx, bonus=20.0)

    # Promote full candidates that contain a partial spaCy NER span (e.g. preserving 'Ma.', inverted surname, or ', CPA')
    if ner_spans and len(candidate_scores) > 1:
        for cand_norm in list(candidate_scores.keys()):
            cand_tokens = {w.lower().rstrip('.,') for w in cand_norm.split()}
            for ner_norm in ner_spans:
                if not ner_norm or cand_norm == ner_norm:
                    continue
                ner_tokens = {w.lower().rstrip('.,') for w in ner_norm.split()}
                if ner_tokens and ner_tokens.issubset(cand_tokens) and len(cand_tokens) > len(ner_tokens):
                    candidate_scores[cand_norm] = max(
                        candidate_scores[cand_norm],
                        candidate_scores.get(ner_norm, 0.0) + 25.0,
                    )

    sorted_names = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    return [name for name, score in sorted_names]


def extract_fullname(text: str, email: str = "") -> str:
    """
    Extracts the candidate's full name from resume text.
    Optimized for Philippine naming structures, PRC licenses, and bio-data formats.
    """
    candidates = extract_all_name_candidates(text, email)
    if candidates:
        return candidates[0]

    # Fallback to first plausible segment in first 8 lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:8]:
        clean = re.sub(r'^[^\w]+', '', line).strip()
        first_segment = re.split(r'\s*[|•]\s*', clean)[0].strip()
        stripped = _strip_roles_and_titles(first_segment)
        if _is_plausible_name(stripped):
            return _normalize_name(stripped)

    return ""