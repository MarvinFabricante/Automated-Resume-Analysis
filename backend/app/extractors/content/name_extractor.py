import re


# Common resume header words / noise that should NOT be treated as names
_NOISE_WORDS = {
    "resume", "cv", "curriculum", "vitae", "portfolio", "profile",
    "personal", "information", "details", "contact", "objective",
    "summary", "about", "me", "page", "application",
}

# Words that strongly suggest a line is NOT a name
_NOT_NAME_PATTERNS = [
    r"@",                              # email
    r"\d{3,}",                         # phone / long numbers
    r"https?://",                      # URL
    r"\b(street|city|province|metro|manila|philippines)\b",  # address
    r"\b(skills|education|experience|work|history)\b",
]


def _is_plausible_name(text: str) -> bool:
    """Check if a string looks like a human name."""
    if not text:
        return False

    # Too short or too long
    if len(text) < 3 or len(text) > 60:
        return False

    words = text.split()
    if len(words) < 1 or len(words) > 6:
        return False

    # Check against noise
    lower = text.lower()
    if any(nw in lower for nw in _NOISE_WORDS):
        return False

    # Check for patterns that disqualify
    for pattern in _NOT_NAME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    # At least one word should start with an uppercase letter
    alpha_words = [w for w in words if w and w[0].isalpha()]
    if not alpha_words:
        return False

    # Names are mostly alpha characters (allow periods, hyphens, apostrophes)
    cleaned = re.sub(r"[.\-'\s,]", "", text)
    if not cleaned:
        return False
    alpha_ratio = sum(1 for c in cleaned if c.isalpha()) / len(cleaned)
    if alpha_ratio < 0.85:
        return False

    return True


def _normalize_name(name: str) -> str:
    """Normalize a name to proper Title Case while handling special cases."""
    if not name:
        return ""

    # Remove leading/trailing special chars
    name = re.sub(r'^[\s\-–—:•|]+', '', name)
    name = re.sub(r'[\s\-–—:•|]+$', '', name)

    # Handle ALL-CAPS or all-lowercase names → title case
    parts = name.split()
    result = []
    for part in parts:
        # Preserve suffixes like Jr., III, IV
        if part.upper() in {"JR", "JR.", "SR", "SR.", "II", "III", "IV", "V"}:
            result.append(part.upper().rstrip('.') + ('.' if '.' in part else ''))
        elif part.startswith("Mc") or part.startswith("MC") or part.startswith("mc"):
            result.append("Mc" + part[2:].capitalize())
        elif "'" in part:
            # O'Brien, D'Angelo
            idx = part.index("'")
            result.append(part[:idx+1].capitalize() + part[idx+1:].capitalize())
        else:
            result.append(part.capitalize())

    return " ".join(result)


def extract_fullname(text: str) -> str:
    """
    Extracts the full name from the resume text.
    
    Strategy:
    1. Check the first few non-empty lines (name is almost always at the top).
    2. Look for a "Name:" labeled field.
    3. Filter out common noise (headers, emails, addresses).
    4. Normalize casing.
    """
    if not text:
        return ""

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""

    # ── Strategy 1: Labeled name field ────────────────────────────────────────
    for line in lines[:15]:
        match = re.match(r'^(?:Full\s*)?Name\s*:\s*(.+)', line, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if _is_plausible_name(candidate):
                return _normalize_name(candidate)

    # ── Strategy 2: First plausible name in the top lines ─────────────────────
    for line in lines[:8]:
        # Skip very long lines (likely paragraphs)
        if len(line) > 60:
            continue

        # Skip lines that are obviously section headers
        upper = line.upper().strip()
        if upper in {"RESUME", "CV", "CURRICULUM VITAE", "PERSONAL INFORMATION",
                      "CONTACT INFORMATION", "CONTACT DETAILS", "PROFILE"}:
            continue

        # If line has a colon, check the value after the colon
        if ':' in line:
            # Could be "Name: John Doe" format
            _, _, after = line.partition(':')
            candidate = after.strip()
            if _is_plausible_name(candidate):
                return _normalize_name(candidate)
            continue

        if _is_plausible_name(line):
            return _normalize_name(line)

    # ── Strategy 3: Fallback — return first non-empty line as-is ──────────────
    return _normalize_name(lines[0]) if lines else ""