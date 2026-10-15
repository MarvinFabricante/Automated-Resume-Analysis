import re
from typing import List, Tuple, Set, Optional

# Regex for labeled fields (e.g. "Mobile: 0917-123-4567" or "Contact No.: +63 918 234 5678")
_LABELED_PREFIX_REGEX = re.compile(
    r'(?:mobile(?:\s*phone|\s*number|\s*no\.?)?|'
    r'cell(?:\s*phone|\s*number|\s*no\.?)?|'
    r'cellphone(?:\s*number|\s*no\.?)?|'
    r'phone(?:\s*number|\s*no\.?)?|'
    r'telephone(?:\s*number|\s*no\.?)?|'
    r'tel(?:\s*no\.?)?|'
    r'contact(?:\s*number|\s*no\.?)?|'
    r'personal\s*contact|direct\s*line|hotline|call)'
    r'[\s:.\-–—|•/>]*'
    r'([+]?[\d\s\-().]{7,25}\d)',
    re.IGNORECASE
)

# Regex for unicode / emoji markers (📞, 📱, 📲, ☎️, etc.)
_ICON_PREFIX_REGEX = re.compile(
    r'[📞📱📲☎️☎✆℡]\s*[:.\-]?\s*'
    r'([+]?[\d\s\-().]{7,25}\d)',
    re.IGNORECASE
)

# Regex for tel: or callto: URI links
_TEL_LINK_REGEX = re.compile(
    r'(?:tel|callto):\s*([+]?[\d\s\-().]{7,25}\d)',
    re.IGNORECASE
)

# Philippine Mobile regex patterns
_PH_MOBILE_PATTERNS = [
    # +63 9XX XXX XXXX or +63-9XX-XXX-XXXX or +63.9XX.XXX.XXXX
    re.compile(r'(?:\+63|0063)\s*(?:\(0\)\s*|\(09\)\s*)?9\d{2}[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    # +63 (9XX) XXX-XXXX or +63 (9XX) XXX XXXX
    re.compile(r'(?:\+63|0063)\s*\(\s*9\d{2}\s*\)[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    # (+63) 9XX XXX XXXX or (63) 9XX XXX XXXX or (+63) 09XX XXX XXXX
    re.compile(r'\(\s*\+?63\s*\)[\s\-.]*(?:0\s*)?9\d{2}[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    # +639XXXXXXXXX
    re.compile(r'(?:\+63|0063)9\d{9}\b'),
    # 639XXXXXXXXX or 63 9XX XXX XXXX
    re.compile(r'\b639\d{2}[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    re.compile(r'\b639\d{9}\b'),
    # 09XX-XXX-XXXX or 09XX XXX XXXX or 09XX.XXX.XXXX
    re.compile(r'\b09\d{2}[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    # (09XX) XXX-XXXX or (09XX) XXX XXXX
    re.compile(r'\(\s*09\d{2}\s*\)[\s\-./]?\d{3}[\s\-./]?\d{4}\b'),
    # 09XX-XXXX-XXX or 09XX XXXX XXX
    re.compile(r'\b09\d{2}[\s\-./]?\d{4}[\s\-./]?\d{3}\b'),
    # 09XXXXXXXXX (compact 11 digits)
    re.compile(r'\b09\d{9}\b'),
    # Spaced digits in PDF extraction (e.g. 0 9 1 7 1 2 3 4 5 6 7)
    re.compile(r'\b0\s*9\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\b'),
]

# Philippine Landline regex patterns
_PH_LANDLINE_PATTERNS = [
    # Metro Manila 8-digit: (02) 8XXX-XXXX or +63 2 8XXX-XXXX or 02-8XXX-XXXX
    re.compile(r'(?:\+63[\s\-.]?2|02|\(02\))\s*[378]\d{3}[\s\-.]?\d{4}\b'),
    re.compile(r'\(\s*02\s*\)[\s\-.]?[378]\d{3}[\s\-.]?\d{4}\b'),
    re.compile(r'\+63\s*\(?2\)?[\s\-.]?[378]\d{3}[\s\-.]?\d{4}\b'),
    # Provincial Landlines: (049) 5XX-XXXX or +63 49 5XX-XXXX or 049-5XX-XXXX
    re.compile(r'\(\s*0[3-8]\d{1,2}\s*\)[\s\-.]?\d{3,4}[\s\-.]?\d{4}\b'),
    re.compile(r'\b0[3-8]\d{1,2}[\s\-.]?\d{3,4}[\s\-.]?\d{4}\b'),
    re.compile(r'\+63[\s\-.]?[3-8]\d{1,2}[\s\-.]?\d{3,4}[\s\-.]?\d{4}\b'),
    # Metro Manila Legacy 7-digit: (02) XXX-XXXX or 02-XXX-XXXX
    re.compile(r'\(\s*02\s*\)[\s\-.]?\d{3}[\s\-.]?\d{4}\b'),
    re.compile(r'\b02[\s\-.]?\d{3}[\s\-.]?\d{4}\b'),
]

# General International patterns (fallback if no PH number found)
_GENERAL_PATTERNS = [
    re.compile(r'\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}\b'),
    re.compile(r'\(\s*\d{3}\s*\)[\s\-.]\d{3}[\s\-.]\d{4}\b'),
    re.compile(r'\b\d{3}[-.]\d{3}[-.]\d{4}\b'),
]


def _is_date_or_non_phone(val: str) -> bool:
    """Check if candidate is a date range, year, tax id, postal code, or other noise."""
    if not val:
        return True

    clean = re.sub(r'[\s\-–—]+', '-', val.strip())

    # Date ranges: 2018-2022, 2020 - Present, 2019 - 2024
    if re.fullmatch(r'(?:19|20)\d{2}-(?:19|20)\d{2}', clean):
        return True
    if re.fullmatch(r'(?:19|20)\d{2}', clean):
        return True
    if re.search(r'\b(?:19|20)\d{2}\s*[-–—]\s*(?:present|current|now|ongoing)\b', val, re.IGNORECASE):
        return True

    # Date formats: 2022-05-15 or 05/12/2023 or 2020.01.15
    if re.fullmatch(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', clean):
        return True
    if re.fullmatch(r'\d{1,2}[-./]\d{1,2}[-./]\d{4}', clean):
        return True

    # TIN format: 123-456-789-000 (4 groups of 3)
    if re.fullmatch(r'\d{3}-\d{3}-\d{3}-\d{3}', clean):
        return True
    # SSS format: 12-3456789-0
    if re.fullmatch(r'\d{2}-\d{7}-\d{1}', clean):
        return True

    digits = re.sub(r'\D', '', val)
    if len(digits) < 7 or len(digits) > 15:
        return True

    # Repeated identical dummy digits (e.g. 0000000000, 1111111111, 9999999999)
    if len(set(digits)) == 1:
        return True

    # Sequential test sequences: 0123456789, 1234567890
    if digits in "01234567890123456789" or digits in "98765432109876543210":
        return True

    return False


def _clean_phone(raw_phone: str) -> str:
    """
    Clean and standardize a candidate phone number string.
    Normalizes Philippine mobile numbers to consistent readable formats.
    """
    if not raw_phone:
        return ""

    cleaned = raw_phone.strip()
    # Strip prefixes like tel: or callto:
    cleaned = re.sub(r'^(?:tel|callto):\s*', '', cleaned, flags=re.IGNORECASE)

    # Strip surrounding noise
    cleaned = cleaned.strip('.,;:|•*#\'"`')
    cleaned = cleaned.strip('<>{}[]')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if _is_date_or_non_phone(cleaned):
        return ""

    digits = re.sub(r'\D', '', cleaned)
    if len(digits) < 7:
        return ""

    # Normalize international prefix: 0063 -> 63
    if digits.startswith("0063"):
        digits = digits[2:]
    # Drop trunk zero from international format: 6309 -> 639
    if digits.startswith("6309"):
        digits = "63" + digits[3:]

    # 1. Philippine Mobile (12 digits starting with 639): +63 9XX XXX XXXX
    if digits.startswith("639") and len(digits) == 12:
        return f"+63 {digits[2:5]} {digits[5:8]} {digits[8:12]}"

    # 2. Philippine Mobile (11 digits starting with 09): 09XX-XXX-XXXX
    if digits.startswith("09") and len(digits) == 11:
        return f"{digits[0:4]}-{digits[4:7]}-{digits[7:11]}"

    # 3. Philippine Mobile missing trunk 0 (10 digits starting with 9): 09XX-XXX-XXXX
    if len(digits) == 10 and digits.startswith("9"):
        return f"0{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"

    # 4. Metro Manila Landline (8-digit): (02) 8XXX-XXXX or +63 2 8XXX-XXXX
    if digits.startswith("632") and len(digits) == 11:
        return f"+63 2 {digits[3:7]} {digits[7:11]}"
    if digits.startswith("02") and len(digits) == 10:
        return f"(02) {digits[2:6]}-{digits[6:10]}"

    # 5. Provincial Landline (10 digits starting with 0): (0XX) XXX-XXXX
    if digits.startswith("0") and len(digits) == 10 and not digits.startswith("09"):
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"

    return cleaned


def is_valid_phone(phone: str) -> bool:
    """Public helper to verify if a phone string is a valid phone number."""
    return bool(_clean_phone(phone))


def _score_phone(
    phone_clean: str,
    pos: int,
    total_len: int,
    is_labeled: bool,
    is_icon: bool,
    is_mobile_label: bool,
    text_lower: str
) -> float:
    """
    Score candidate phone numbers to rank and select the applicant's primary contact number.
    """
    score = 50.0

    if is_labeled:
        score += 100.0
    if is_mobile_label:
        score += 30.0
    if is_icon:
        score += 90.0

    # Header proximity (< 1500 chars)
    if pos < 1500:
        score += 80.0
    elif pos < 3000:
        score += 45.0
    elif pos < 5000:
        score += 15.0

    # Heavy penalty for References section (these belong to 3rd party references)
    ref_idx = text_lower.find("references")
    if ref_idx != -1 and pos > ref_idx:
        score -= 130.0

    digits = re.sub(r'\D', '', phone_clean)

    # Philippine Mobile numbers get top priority (essential for applicant SMS/calls)
    if (digits.startswith("09") and len(digits) == 11) or (digits.startswith("639") and len(digits) == 12):
        score += 70.0
    # Philippine Landline
    elif (digits.startswith("02") and len(digits) in (9, 10)) or (digits.startswith("632") and len(digits) in (10, 11)):
        score += 40.0
    elif digits.startswith("0") and len(digits) == 10:
        score += 35.0

    return score


def extract_all_phones(text: str) -> List[str]:
    """
    Extracts all unique phone numbers found in resume text, ranked by
    likelihood of being the candidate's personal contact number.
    Philippine mobile and landline numbers are prioritized.
    """
    if not text:
        return []

    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    text_lower = text_norm.lower()
    total_len = len(text_norm)

    candidates_dict = {}

    def add_candidate(raw: str, pos: int, is_labeled: bool = False, is_icon: bool = False, is_mobile_label: bool = False):
        cleaned = _clean_phone(raw)
        if not cleaned:
            return
        score = _score_phone(cleaned, pos, total_len, is_labeled, is_icon, is_mobile_label, text_lower)
        if cleaned not in candidates_dict or score > candidates_dict[cleaned]:
            candidates_dict[cleaned] = score

    # 1. Labeled phone fields (e.g. "Mobile: 0917-123-4567")
    for m in _LABELED_PREFIX_REGEX.finditer(text_norm):
        raw_prefix = text_norm[m.start():m.start(1)].lower()
        is_mob = any(k in raw_prefix for k in ["mobile", "cell"])
        add_candidate(m.group(1), m.start(), is_labeled=True, is_mobile_label=is_mob)

    # 2. Icon / Emoji prefixed numbers (📞, 📱, 📲, etc.)
    for m in _ICON_PREFIX_REGEX.finditer(text_norm):
        add_candidate(m.group(1), m.start(), is_icon=True)

    # 3. Tel / callto hyperlink URIs
    for m in _TEL_LINK_REGEX.finditer(text_norm):
        add_candidate(m.group(1), m.start(), is_labeled=True)

    # 4. Philippine Mobile patterns across entire text
    for pat in _PH_MOBILE_PATTERNS:
        for m in pat.finditer(text_norm):
            add_candidate(m.group(0), m.start())

    # 5. Philippine Landline patterns across entire text
    for pat in _PH_LANDLINE_PATTERNS:
        for m in pat.finditer(text_norm):
            add_candidate(m.group(0), m.start())

    # 6. General international patterns fallback
    for pat in _GENERAL_PATTERNS:
        for m in pat.finditer(text_norm):
            add_candidate(m.group(0), m.start())

    sorted_phones = sorted(candidates_dict.items(), key=lambda x: x[1], reverse=True)
    return [phone for phone, score in sorted_phones]


def extract_phone(text: str) -> str:
    """
    Extracts the candidate's primary contact phone number from resume text.
    Handles all Philippine mobile formats, Metro Manila and provincial landlines,
    and general international phone formats with candidate ranking.
    """
    phones = extract_all_phones(text)
    return phones[0] if phones else ""