import re
import urllib.parse
from typing import List, Tuple, Set, Optional

# Common template and placeholder emails to completely ignore
_PLACEHOLDER_EMAILS = {
    "your.email@example.com", "your.name@example.com", "name@email.com",
    "name@example.com", "username@domain.com", "email@example.com",
    "your_email@domain.com", "example@domain.com", "user@example.com",
    "first.last@example.com", "john.doe@example.com", "someone@example.com",
    "test@test.com", "test@example.com", "sample@email.com", "sample@domain.com",
    "myname@email.com", "applicant@email.com", "candidate@email.com",
    "your-email@here.com", "your.email@gmail.com", "yourname@domain.com",
    "yourusername@gmail.com", "yourname@gmail.com", "fullname@email.com",
    "xyz@domain.com", "abc@xyz.com", "example@example.com", "placeholder@domain.com",
    "email@address.com", "mail@example.com", "candidate@domain.com",
    "resume@domain.com", "cv@domain.com", "user@domain.com"
}

_PLACEHOLDER_DOMAINS = {
    "example.com", "example.org", "example.net", "sample.com", "domain.com",
    "test.com", "test.org", "yourcompany.com", "mycompany.com", "site.com",
    "yoursite.com", "website.com", "company.com", "somedomain.com"
}

# File extensions that should never be matched as email TLDs
_EXCLUDED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "tiff", "ico",
    "pdf", "doc", "docx", "txt", "rtf", "odt", "xls", "xlsx", "csv",
    "zip", "tar", "gz", "rar", "7z", "mp3", "mp4", "wav", "mov", "avi",
    "exe", "dll", "bin", "iso", "css", "js", "html", "htm", "xml", "json"
}

# Major personal and consumer webmail providers
_COMMON_PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.com.ph", "yahoo.co.uk", "yahoo.com.au",
    "yahoo.ca", "yahoo.in", "outlook.com", "hotmail.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "protonmail.ch",
    "zoho.com", "zohomail.com", "mail.com", "gmx.com", "gmx.net",
    "aol.com", "yandex.com", "yandex.ru", "fastmail.com", "tutanota.com",
    "tuta.com", "hey.com", "pm.me"
}

# Generic corporate or administrative role prefixes (penalized to favor candidate's personal email)
_GENERIC_ROLES = {
    "info", "support", "help", "careers", "jobs", "hr", "recruitment", "recruiting",
    "admin", "administrator", "contact", "sales", "office", "team", "inquiries",
    "billing", "marketing", "privacy", "press", "media", "service", "services",
    "customerservice", "feedback", "noreply", "no-reply", "donotreply", "webmaster",
    "postmaster", "hostmaster", "root", "security", "legal", "compliance", "join",
    "talent", "people", "hiring", "applicant", "applications"
}

# Regex for explicit email labels (e.g. "Email: user@example.com")
_LABELED_PREFIX_REGEX = re.compile(
    r'(?:email|e-mail|e\s*-\s*mail|e_mail|mail|contact\s+email|email\s+address|'
    r'e-mail\s+address|electronic\s+mail|primary\s+email|email\s+id|e-mail\s+id|'
    r'personal\s+email|work\s+email|contact\s+mail|reach\s+(?:me\s+)?at|inquiries\s*to)'
    r'[\s:.\-–—|•/>]*'
    r'[<(\[{]?'
    r'([a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+(?:\s*\.\s*[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+)*'
    r'\s*@\s*'
    r'[a-zA-Z0-9-]+(?:\s*\.\s*[a-zA-Z0-9-]+)*\s*\.\s*[a-zA-Z]{2,24})',
    re.IGNORECASE
)

# Regex for unicode / emoji markers (✉️, 📧, 📨, etc.)
_ICON_PREFIX_REGEX = re.compile(
    r'[✉📧📨✉️📩👤@]\s*[:.\-]?\s*[<(\[{]?'
    r'([a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+(?:\s*\.\s*[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+)*'
    r'\s*@\s*'
    r'[a-zA-Z0-9-]+(?:\s*\.\s*[a-zA-Z0-9-]+)*\s*\.\s*[a-zA-Z]{2,24})',
    re.IGNORECASE
)

# Regex for mailto URI links
_MAILTO_REGEX = re.compile(
    r'mailto:\s*([^\s"\'<>?#]+)',
    re.IGNORECASE
)

# Standard RFC-5322 permissive email regex
_STANDARD_EMAIL_REGEX = re.compile(
    r'\b[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\b',
    re.IGNORECASE
)

# Spaced or line-wrapped emails (common in PDF multi-column or wrap extractions)
_SPACED_EMAIL_REGEX = re.compile(
    r'\b([a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+(?:\s*\.\s*[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+)*)'
    r'\s*@\s*'
    r'([a-zA-Z0-9-]+(?:\s*\.\s*[a-zA-Z0-9-]+)*\s*\.\s*[a-zA-Z]{2,24})\b',
    re.IGNORECASE
)

# Obfuscated emails (e.g. name [at] domain [dot] com)
_OBFUSCATED_EMAIL_REGEX = re.compile(
    r'\b([a-zA-Z0-9._%+-]+)'
    r'\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\bat\b|\[\s*@\s*\])\s*'
    r'([a-zA-Z0-9.-]+)'
    r'\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\bdot\b|\[\s*\.\s*\]|\.)\s*'
    r'([a-zA-Z]{2,24}(?:\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\bdot\b|\.)\s*[a-zA-Z]{2,10})*)',
    re.IGNORECASE
)


def _clean_email(email: str) -> str:
    """
    Clean and validate an extracted candidate email string.
    - Decodes URL encoding (e.g. %40 -> @)
    - Strips prefixes, trailing punctuation, brackets, quotes
    - Removes internal spaces around @ and dots
    - Returns standardized lowercase email or empty string if invalid
    """
    if not email:
        return ""

    # Unquote URL-encoded characters
    email = urllib.parse.unquote(email)

    # Strip mailto prefix if present
    if email.lower().startswith("mailto:"):
        email = email[7:]
    email = email.split('?')[0].split('#')[0]

    # Strip surrounding noise
    email = email.strip().strip('<>()[]{},;:\'"`')
    email = email.rstrip('.-_/')

    # Remove internal whitespace if any was introduced by PDF wrapping
    if ' ' in email or '\t' in email or '\n' in email:
        parts = email.split('@')
        if len(parts) == 2:
            local_p = re.sub(r'\s+', '', parts[0])
            domain_p = re.sub(r'\s+', '', parts[1])
            email = f"{local_p}@{domain_p}"
        else:
            email = re.sub(r'\s+', '', email)

    cleaned = email.strip().lower()

    if not cleaned or cleaned.count('@') != 1:
        return ""

    local_part, domain_part = cleaned.split('@')
    if not local_part or not domain_part:
        return ""

    if '.' not in domain_part:
        return ""

    tld = domain_part.split('.')[-1]
    if len(tld) < 2 or not tld.isalpha() or tld in _EXCLUDED_EXTENSIONS:
        return ""

    # Basic RFC check on characters
    if not re.match(r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+$', local_part):
        return ""
    if not re.match(r'^[a-zA-Z0-9.-]+$', domain_part):
        return ""

    if cleaned in _PLACEHOLDER_EMAILS:
        return ""

    if domain_part in _PLACEHOLDER_DOMAINS:
        return ""

    return cleaned


def is_valid_email(email: str) -> bool:
    """Public helper to verify if an email string is valid and not a placeholder."""
    return bool(_clean_email(email))


def _score_email(
    email: str,
    pos: int,
    total_len: int,
    is_labeled: bool,
    is_icon: bool,
    is_mailto: bool,
    candidate_name: str,
    text_lower: str
) -> float:
    """
    Score candidate emails to rank and select the applicant's primary email.
    """
    score = 50.0

    # Explicit signals
    if is_labeled:
        score += 100.0
    if is_icon:
        score += 90.0
    if is_mailto:
        score += 70.0

    # Header / Top-of-resume positioning (candidates almost always put contact info at top)
    if pos < 1500:
        score += 80.0
    elif pos < 3000:
        score += 45.0
    elif pos < 5000:
        score += 20.0

    # Heavy penalty for emails inside the References section (these belong to 3rd party references)
    ref_idx = text_lower.find("references")
    if ref_idx != -1 and pos > ref_idx:
        score -= 120.0

    local_part, domain_part = email.split('@')

    # Domain bonuses
    if domain_part in _COMMON_PERSONAL_DOMAINS:
        score += 40.0
    elif domain_part.endswith(".edu") or domain_part.endswith(".edu.ph") or domain_part.endswith(".ac.uk"):
        score += 30.0

    # Generic role inbox penalties
    if local_part in _GENERIC_ROLES:
        score -= 90.0
    for gr in _GENERIC_ROLES:
        if local_part.startswith(gr + ".") or local_part.startswith(gr + "_") or local_part.startswith(gr + "-"):
            score -= 70.0
            break

    # Correlation with candidate's actual name
    if candidate_name:
        cleaned_name = re.sub(r'[^a-zA-Z\s]', '', candidate_name).lower()
        tokens = [t for t in cleaned_name.split() if len(t) > 1]
        local_clean = re.sub(r'[^a-zA-Z0-9]', '', local_part)

        if len(tokens) >= 2:
            full_concat = "".join(tokens)
            if full_concat in local_clean:
                score += 120.0
            else:
                first = tokens[0]
                last = tokens[-1]
                if first in local_clean and last in local_clean:
                    score += 110.0
                elif last in local_clean:
                    score += 65.0
                elif first in local_clean:
                    score += 40.0
                elif local_clean.startswith(first[0]) and last in local_clean:
                    score += 85.0
        elif len(tokens) == 1:
            if tokens[0] in local_clean:
                score += 50.0

    return score


def extract_all_emails(text: str, candidate_name: str = "") -> List[str]:
    """
    Extracts ALL valid emails from resume text, ranked by relevance and likelihood
    of being the candidate's personal contact email.
    """
    if not text:
        return []

    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    text_lower = text_norm.lower()
    total_len = len(text_norm)

    candidates_dict = {}

    def add_candidate(raw: str, pos: int, is_labeled: bool = False, is_icon: bool = False, is_mailto: bool = False):
        cleaned = _clean_email(raw)
        if not cleaned:
            return
        score = _score_email(cleaned, pos, total_len, is_labeled, is_icon, is_mailto, candidate_name, text_lower)
        if cleaned not in candidates_dict or score > candidates_dict[cleaned]:
            candidates_dict[cleaned] = score

    # 1. Check labeled email patterns
    for m in _LABELED_PREFIX_REGEX.finditer(text_norm):
        add_candidate(m.group(1), m.start(), is_labeled=True)

    # 2. Check icon / emoji prefixed emails
    for m in _ICON_PREFIX_REGEX.finditer(text_norm):
        add_candidate(m.group(1), m.start(), is_icon=True)

    # 3. Check mailto: link targets
    for m in _MAILTO_REGEX.finditer(text_norm):
        add_candidate(m.group(1), m.start(), is_mailto=True)

    # 4. Check obfuscated emails (e.g. name [at] domain [dot] com)
    for m in _OBFUSCATED_EMAIL_REGEX.finditer(text_norm):
        user, domain, tlds = m.group(1), m.group(2), m.group(3)
        tlds_clean = re.sub(r'\[\s*dot\s*\]|\(\s*dot\s*\)|\bdot\b|\[\s*\.\s*\]|\s+', '.', tlds)
        tlds_clean = re.sub(r'\.+', '.', tlds_clean)
        constructed = f"{user.strip()}@{domain.strip()}.{tlds_clean.strip('.')}"
        add_candidate(constructed, m.start(), is_labeled=False)

    # 5. Check spaced or line-wrapped emails
    for m in _SPACED_EMAIL_REGEX.finditer(text_norm):
        user, domain = m.group(1), m.group(2)
        constructed = f"{user}@{domain}"
        add_candidate(constructed, m.start())

    # 6. Check standard emails across entire text
    for m in _STANDARD_EMAIL_REGEX.finditer(text_norm):
        add_candidate(m.group(0), m.start())

    sorted_emails = sorted(candidates_dict.items(), key=lambda x: x[1], reverse=True)
    return [email for email, score in sorted_emails]


def extract_email(text: str, candidate_name: str = "") -> str:
    """
    Extracts the candidate's primary email address from resume text.
    Uses multi-stage pattern recognition, de-obfuscation, and scoring.
    """
    emails = extract_all_emails(text, candidate_name)
    return emails[0] if emails else ""