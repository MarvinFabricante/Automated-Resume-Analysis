import re


_PLACEHOLDER_EMAILS = {
    "your.email@example.com", "your.name@example.com", "name@email.com",
    "name@example.com", "username@domain.com", "email@example.com",
    "your_email@domain.com", "example@domain.com", "user@example.com"
}


def extract_email(text: str) -> str:
    """
    Extracts the candidate's email address from resume text.
    
    Strategy:
    1. Scan for labeled email patterns (e.g., 'Email: user@example.com').
    2. Extract valid email regex patterns from header area, then full text.
    3. Clean and normalize email (strip trailing punctuation, convert to lowercase).
    4. Filter out common template placeholder emails.
    """
    if not text:
        return ""

    # ── Strategy 1: Labeled email ─────────────────────────────────────────────
    labeled_pattern = r'(?:Email|E-mail|Mail|Contact\s+Email)\s*[:.\-]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    labeled_match = re.search(labeled_pattern, text, re.IGNORECASE)
    if labeled_match:
        candidate = _clean_email(labeled_match.group(1))
        if candidate and candidate not in _PLACEHOLDER_EMAILS:
            return candidate

    # ── Strategy 2: Scan header area first (phone/email almost always at top) ──
    header_text = text[:3000]
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    header_matches = re.findall(email_pattern, header_text)
    for m in header_matches:
        cleaned = _clean_email(m)
        if cleaned and cleaned not in _PLACEHOLDER_EMAILS:
            return cleaned

    # ── Strategy 3: Full text scan fallback ───────────────────────────────────
    all_matches = re.findall(email_pattern, text)
    for m in all_matches:
        cleaned = _clean_email(m)
        if cleaned and cleaned not in _PLACEHOLDER_EMAILS:
            return cleaned

    return ""


def _clean_email(email: str) -> str:
    """Clean up extracted email address and remove trailing punctuation."""
    if not email:
        return ""
    # Strip whitespace and common surrounding punct
    cleaned = email.strip().strip('<>()[]{},;:\'"')
    cleaned = cleaned.rstrip('.')
    return cleaned.lower()