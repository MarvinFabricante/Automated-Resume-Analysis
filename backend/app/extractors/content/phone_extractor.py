import re


def extract_phone(text: str) -> str:
    """
    Extracts the primary phone number from resume text.
    
    Handles formats:
      - Philippine:  +639XXXXXXXXX, 09XXXXXXXXX, (02) XXXX-XXXX
      - US/Intl:     +1-234-567-8901, (123) 456-7890
      - Generic:     123-456-7890, 123.456.7890
    
    Prioritizes labeled phone fields, then scans the header area.
    """
    if not text:
        return ""

    # ── Strategy 1: Labeled phone field ───────────────────────────────────────
    labeled_patterns = [
        r'(?:Phone|Tel|Telephone|Mobile|Cell|Contact(?:\s*No\.?)?)\s*[:.\-]?\s*'
        r'(\+?\d[\d\s\-().]{7,20}\d)',
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_phone(match.group(1))

    # ── Strategy 2: Philippine phone patterns ─────────────────────────────────
    ph_patterns = [
        r'(\+63\s?\d{3}\s?\d{3}\s?\d{4})',     # +63 9XX XXX XXXX
        r'(\+63\s?\d{10})',                       # +639XXXXXXXXX
        r'(09\d{2}[\s\-]?\d{3}[\s\-]?\d{4})',   # 09XX-XXX-XXXX
        r'(\(0\d{1,2}\)\s?\d{3,4}[\s\-]?\d{4})', # (02) XXXX-XXXX
    ]
    for pattern in ph_patterns:
        match = re.search(pattern, text)
        if match:
            return _normalize_phone(match.group(1))

    # ── Strategy 3: General international patterns ────────────────────────────
    general_patterns = [
        r'(\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4})',  # +CC (XXX) XXX-XXXX
        r'(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})',                           # (XXX) XXX-XXXX
        r'(\d{10,11})',                                                         # raw 10-11 digit
    ]

    # Scan only the top portion of the resume (phone is usually near the header)
    header_text = text[:1500]
    for pattern in general_patterns:
        match = re.search(pattern, header_text)
        if match:
            return _normalize_phone(match.group(1))

    # ── Fallback: scan full text ──────────────────────────────────────────────
    for pattern in general_patterns:
        match = re.search(pattern, text)
        if match:
            return _normalize_phone(match.group(1))

    return ""


def _normalize_phone(phone: str) -> str:
    """Clean up a phone number string."""
    if not phone:
        return ""
    # Remove extra whitespace, keep formatting characters
    phone = re.sub(r'\s+', ' ', phone).strip()
    return phone