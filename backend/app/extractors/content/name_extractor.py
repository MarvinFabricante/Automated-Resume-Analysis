import re
from typing import Optional


# Common resume header words / noise that should NOT be treated as names
_NOISE_WORDS = {
    "resume", "cv", "curriculum", "vitae", "portfolio", "profile",
    "personal", "information", "details", "contact", "objective",
    "summary", "about", "me", "page", "application", "career",
    "statement", "overview", "candidate", "references", "education",
    "experience", "work history", "skills", "projects", "certifications",
}

# Common job role words that disqualify a line from being a candidate's personal name
_ROLE_DISQUALIFIERS = {
    "engineer", "developer", "programmer", "architect", "designer",
    "manager", "lead", "director", "specialist", "consultant", "analyst",
    "officer", "administrator", "coordinator", "supervisor", "intern",
    "trainee", "associate", "assistant", "technician", "scientist",
    "fullstack", "full-stack", "frontend", "backend", "software",
    "web", "mobile", "devops", "cloud", "data", "qa", "tester",
    "product", "project", "marketing", "sales", "executive", "accountant",
}

# Words that strongly suggest a line is NOT a name
_NOT_NAME_PATTERNS = [
    r"@",                              # email
    r"\d{3,}",                         # phone / long numbers
    r"https?://",                      # URL
    r"\b(www\.|linkedin|github|gitlab|portfolio)\b",
    r"\b(street|st\.|city|province|metro|manila|philippines|ave\.|road|blvd|brgy|barangay)\b",  # address
    r"\b(skills|education|experience|work|history|summary|objective|certifications)\b",
    r"\b(years?\s+of\s+experience|curriculum\s+vitae)\b",
]

_HONORIFICS = [
    r"\b(?:Engr\.?|Dr\.?|Atty\.?|Arch\.?|Prof\.?|Mr\.?|Ms\.?|Mrs\.?)\s+",
]

_PARTICLES = {"de", "la", "del", "dela", "van", "der", "von", "di", "da", "san", "santa"}


def _clean_honorifics(text: str) -> str:
    """Remove prefixes like Engr., Dr., Atty. while retaining the actual name."""
    cleaned = text.strip()
    for h in _HONORIFICS:
        cleaned = re.sub(f"^{h}", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _is_plausible_name(text: str) -> bool:
    """Check if a string looks like a human name."""
    if not text:
        return False

    candidate = _clean_honorifics(text.strip())
    # Remove common trailing suffixes for length/word checks
    candidate_base = re.sub(r'[,.\s]+(?:Jr\.?|Sr\.?|II|III|IV|V|CPA|RN|PE|PMP|MD)$', '', candidate, flags=re.IGNORECASE).strip()

    # Length bounds
    if len(candidate_base) < 3 or len(candidate_base) > 50:
        return False

    words = candidate_base.split()
    if len(words) < 1 or len(words) > 5:
        return False

    # Check against noise
    lower = candidate_base.lower()
    if any(nw == lower or f" {nw} " in f" {lower} " for nw in _NOISE_WORDS):
        return False

    # Check if this line is actually a job title (e.g., "Senior Software Engineer")
    word_set = {w.lower().rstrip(',.') for w in words}
    role_matches = word_set.intersection(_ROLE_DISQUALIFIERS)
    if role_matches and len(role_matches) >= 1:
        # If words contain engineer, developer, etc., unless it's clearly a full name
        if any(w in _ROLE_DISQUALIFIERS for w in word_set):
            # Check if it has title words like "Software", "Senior", "Lead", etc.
            if len(role_matches) >= 2 or any(w in {"senior", "junior", "lead", "software", "fullstack", "web"} for w in word_set):
                return False

    # Disqualifying patterns
    for pattern in _NOT_NAME_PATTERNS:
        if re.search(pattern, candidate, re.IGNORECASE):
            return False

    # At least one word should start with an alphabetic character
    alpha_words = [w for w in words if w and w[0].isalpha()]
    if not alpha_words:
        return False

    # Names are mostly alpha characters (allow periods, hyphens, apostrophes, spaces)
    cleaned = re.sub(r"[.\-'\s,]", "", candidate_base)
    if not cleaned:
        return False
    alpha_ratio = sum(1 for c in cleaned if c.isalpha()) / len(cleaned)
    if alpha_ratio < 0.85:
        return False

    return True


def _normalize_name(name: str) -> str:
    """Normalize a name to proper Title Case while handling special cases and particles."""
    if not name:
        return ""

    # Remove leading/trailing special characters
    name = re.sub(r'^[\s\-–—:•|*#]+', '', name)
    name = re.sub(r'[\s\-–—:•|*#]+$', '', name)

    # Clean honorifics at beginning
    name = _clean_honorifics(name)

    # Handle parts
    parts = name.split()
    result = []
    for i, part in enumerate(parts):
        # Suffixes
        clean_part = part.rstrip(',.')
        has_comma = ',' in part
        trailing_comma = ',' if has_comma else ''

        upper_clean = clean_part.upper()
        if upper_clean in {"JR", "SR", "II", "III", "IV", "V", "CPA", "RN", "PE", "PMP", "MD"}:
            if upper_clean in {"JR", "SR"}:
                result.append(f"{upper_clean.capitalize()}.{trailing_comma}")
            else:
                result.append(f"{upper_clean}{trailing_comma}")
            continue

        # Handle hyphenated parts (e.g. Santos-Reyes)
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

        # Handle single letter middle initials (e.g. "M" -> "M.")
        if len(clean_part) == 1 and clean_part.isalpha():
            result.append(f"{clean_part.upper()}.{trailing_comma}")
            continue

        # Handle particles (de, la, van, der, etc.) if not the first word
        # Note: "Dela" and "Del" in Filipino names are conventionally capitalized (Dela Cruz, Del Rosario)
        if i > 0 and clean_part.lower() in {"de", "la", "van", "der", "von", "di", "da"}:
            result.append(clean_part.lower() + trailing_comma)
            continue

        result.append(clean_part.capitalize() + trailing_comma)

    return " ".join(result).strip(' ,')


def extract_fullname(text: str) -> str:
    """
    Extracts the full name from resume text.
    
    Strategy:
    1. Labeled name field: "Name:", "Full Name:", "Candidate Name:".
    2. Header inspection: Scan the first 10 non-empty lines for plausible names.
       Handles multi-item lines separated by '|', '•', or ' - ' by examining the first segment.
    3. spaCy NER PERSON entities in header area (fallback confirmation).
    4. Fallback: First valid plausible line.
    """
    if not text:
        return ""

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""

    # ── Strategy 1: Labeled name field ────────────────────────────────────────
    for line in lines[:15]:
        match = re.match(r'^(?:Full\s*Name|Candidate\s*Name|Applicant\s*Name|Name)\s*[:.\-]\s*(.+)', line, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # If line has separators like "|", take the first part
            candidate = re.split(r'[|•]', candidate)[0].strip()
            if _is_plausible_name(candidate):
                return _normalize_name(candidate)

    # ── Strategy 2: Scan header lines ─────────────────────────────────────────
    for line in lines[:10]:
        if len(line) > 120:
            continue

        upper = line.upper().strip()
        # Skip pure header words
        if upper in {"RESUME", "CV", "CURRICULUM VITAE", "PERSONAL INFORMATION",
                     "CONTACT INFORMATION", "CONTACT DETAILS", "PROFILE", "SUMMARY",
                     "PROFESSIONAL SUMMARY", "ABOUT ME"}:
            continue

        # If line contains '|' or '•', check the first segment (name is almost always first)
        segments = re.split(r'\s*[|•]\s*', line)
        for seg in segments:
            seg_clean = seg.strip()
            if _is_plausible_name(seg_clean):
                return _normalize_name(seg_clean)

        # Check before dashes or colons if present
        if ':' in line:
            _, _, after = line.partition(':')
            cand = after.strip()
            if _is_plausible_name(cand):
                return _normalize_name(cand)

        # Check full line
        if _is_plausible_name(line):
            return _normalize_name(line)

    # ── Strategy 3: spaCy NER PERSON entities in the header ────────────────────
    try:
        from app.extractors.nlp.nlp_engine import get_doc
        doc = get_doc(text[:1200])
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                cand = ent.text.strip()
                if _is_plausible_name(cand):
                    return _normalize_name(cand)
    except Exception:
        pass

    # ── Strategy 4: Fallback — find first plausible candidate in lines ──────────
    for line in lines[:6]:
        clean = re.sub(r'^[^\w]+', '', line).strip()
        first_segment = re.split(r'[|•\-,]', clean)[0].strip()
        if _is_plausible_name(first_segment):
            return _normalize_name(first_segment)

    return ""