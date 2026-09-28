import re


def _is_date_range_or_year(matched_str: str) -> bool:
    """Check if the matched string is actually a year or date range (e.g. 2018-2022)."""
    clean = re.sub(r'[\s\-–—]+', '-', matched_str.strip())
    # Match 4-digit years like 2018-2022 or single years
    if re.fullmatch(r'(?:19|20)\d{2}-(?:19|20)\d{2}', clean):
        return True
    if re.fullmatch(r'(?:19|20)\d{2}', clean):
        return True
    return False


def _normalize_phone(phone: str) -> str:
    """Clean up and standardize a phone number string."""
    if not phone:
        return ""
    # Strip trailing punctuation, extra spaces, surrounding characters (preserve parentheses)
    cleaned = phone.strip().strip('.,;:|•-–—*#')
    cleaned = cleaned.strip('\'"{}[]')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def extract_phone(text: str) -> str:
    """
    Extracts the primary contact phone number from resume text.
    
    Handles:
      - Philippine Mobile: +63 9XX XXX XXXX, 09XX-XXX-XXXX, 09XXXXXXXXX, +639XXXXXXXXX
      - Philippine Landline: (02) 8XXX-XXXX, +63 2 8XXX-XXXX, (0XX) XXX-XXXX
      - US/Canada: +1 (XXX) XXX-XXXX, (XXX) XXX-XXXX, XXX-XXX-XXXX
      - International: +XX XXX XXX XXXX
      - Labeled fields: Phone:, Mobile:, Tel:, Contact:, Contact No.:
    """
    if not text:
        return ""

    # ── Strategy 1: Labeled phone field ───────────────────────────────────────
    labeled_patterns = [
        r'(?:Phone|Mobile(?:\s*No\.?)?|Contact(?:\s*No\.?|\s*Number)?|Tel(?:ephone)?|Cell)\s*[:.\-]?\s*'
        r'(\+?\d[\d\s\-().]{7,22}\d)',
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if not _is_date_range_or_year(candidate) and len(re.sub(r'\D', '', candidate)) >= 7:
                return _normalize_phone(candidate)

    # ── Strategy 2: Philippine Mobile & Landline Patterns ─────────────────────
    ph_patterns = [
        r'(\+63[\s\-]?9\d{2}[\s\-]?\d{3}[\s\-]?\d{4})',       # +63 9XX XXX XXXX
        r'(\+63[\s\-]?\d{10})',                                # +639XXXXXXXXX
        r'(\(0\d{1,2}\)[\s\-]?\d{3,4}[\s\-]?\d{4})',          # (02) 8XXX-XXXX or (049) 5XX-XXXX
        r'(09\d{2}[\s\-]?\d{3}[\s\-]?\d{4})',                 # 09XX-XXX-XXXX
        r'(09\d{9})',                                         # 09XXXXXXXXX
        r'(\+63[\s\-]?2[\s\-]?\d{4}[\s\-]?\d{4})',            # +63 2 8XXX XXXX
    ]
    header_text = text[:3000]

    for pattern in ph_patterns:
        match = re.search(pattern, header_text)
        if match:
            candidate = match.group(1).strip()
            if not _is_date_range_or_year(candidate):
                return _normalize_phone(candidate)

    # ── Strategy 3: General US & International patterns ───────────────────────
    general_patterns = [
        r'(\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4})',   # +1 (234) 567-8901
        r'(\(?\d{3}\)?[\s\-.]\d{3}[\s\-.]\d{4})',                              # (123) 456-7890 or 123-456-7890
        r'(\b\d{3}[-.]\d{3}[-.]\d{4}\b)',                                     # 123-456-7890
    ]

    for pattern in general_patterns:
        match = re.search(pattern, header_text)
        if match:
            candidate = match.group(1).strip()
            if not _is_date_range_or_year(candidate):
                return _normalize_phone(candidate)

    # ── Fallback: Scan full document for Philippine or general numbers ────────
    for pattern in ph_patterns + general_patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            if not _is_date_range_or_year(candidate):
                return _normalize_phone(candidate)

    return ""