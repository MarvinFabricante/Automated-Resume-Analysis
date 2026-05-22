import re

# Philippine cities, provinces, and common location indicators
_PH_LOCATIONS = {
    # NCR
    "MANILA", "QUEZON CITY", "MAKATI", "TAGUIG", "PASIG", "MANDALUYONG",
    "PASAY", "PARAÑAQUE", "PARANAQUE", "MUNTINLUPA", "LAS PIÑAS", "LAS PINAS",
    "MARIKINA", "CALOOCAN", "MALABON", "NAVOTAS", "VALENZUELA", "SAN JUAN",
    "PATEROS", "BGC", "BONIFACIO GLOBAL CITY", "METRO MANILA",
    # Major cities
    "CEBU", "CEBU CITY", "DAVAO", "DAVAO CITY", "ILOILO", "ILOILO CITY",
    "BACOLOD", "ZAMBOANGA", "CAGAYAN DE ORO", "CDO", "GENERAL SANTOS",
    "BAGUIO", "ANGELES CITY", "CLARK", "OLONGAPO", "SUBIC",
    "ANTIPOLO", "CAINTA", "TAYTAY", "RIZAL", "CAVITE", "LAGUNA",
    "BATANGAS", "BULACAN", "PAMPANGA", "NUEVA ECIJA", "PANGASINAN",
    "TAGAYTAY", "LEGAZPI", "NAGA", "TACLOBAN", "DUMAGUETE",
    "SAN FERNANDO", "LIPA", "CALAMBA", "BIÑAN", "BINAN", "SANTA ROSA",
    # Provinces / regions
    "CALABARZON", "CENTRAL LUZON", "WESTERN VISAYAS", "CENTRAL VISAYAS",
    "NCR", "NATIONAL CAPITAL REGION",
    # Country
    "PHILIPPINES",
}

# International location indicators
_INTL_INDICATORS = {
    "CITY", "STATE", "PROVINCE", "COUNTY", "DISTRICT", "REGION",
    "STREET", "AVENUE", "BOULEVARD", "ROAD", "DRIVE",
    "UNITED STATES", "USA", "CANADA", "UK", "UNITED KINGDOM",
    "AUSTRALIA", "SINGAPORE", "JAPAN", "INDIA", "GERMANY",
    "FRANCE", "SPAIN", "ITALY", "BRAZIL", "MEXICO",
    "DUBAI", "ABU DHABI", "SAUDI ARABIA", "QATAR", "BAHRAIN", "KUWAIT",
    "HONG KONG", "TAIWAN", "SOUTH KOREA", "CHINA",
    "NEW YORK", "LOS ANGELES", "CHICAGO", "HOUSTON", "SAN FRANCISCO",
    "SEATTLE", "LONDON", "TORONTO", "SYDNEY", "MELBOURNE",
}


def extract_location(text: str) -> str:
    """
    Extracts the candidate's location from resume text.
    
    Strategy:
    1. Look for labeled location/address fields.
    2. Scan header lines for Philippine city/province mentions.
    3. Detect ZIP-code or city-state patterns.
    """
    if not text:
        return ""

    # ── Strategy 1: Labeled fields ────────────────────────────────────────────
    labeled_patterns = [
        r'(?:Address|Location|City|Residence|Place)\s*[:.\-]\s*(.+)',
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).split('\n')[0].strip()
            # Don't return extremely long addresses (probably a paragraph)
            if value and len(value) < 120:
                return _clean_location(value)

    # ── Strategy 2: Scan header area for known locations ──────────────────────
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    header_lines = lines[:10]  # Location is almost always in the first 10 lines

    for line in header_lines:
        if len(line) > 120:
            continue

        upper = line.upper()

        # Check for Philippine locations
        for loc in _PH_LOCATIONS:
            if loc in upper:
                return _clean_location(line)

        # Check for international indicators
        for ind in _INTL_INDICATORS:
            if ind in upper:
                # Exclude section headers
                if not _is_section_header(line):
                    return _clean_location(line)

    # ── Strategy 3: ZIP code patterns ─────────────────────────────────────────
    # Philippine ZIP: 4-digit number near an address
    # US ZIP: 5-digit or 5+4
    for line in header_lines:
        if re.search(r'\b\d{4,5}(?:-\d{4})?\b', line):
            if not re.search(r'@|\d{7,}', line):  # exclude emails and phone numbers
                if len(line) < 100:
                    return _clean_location(line)

    # ── Strategy 4: City, State/Country pattern ───────────────────────────────
    for line in header_lines:
        # "City, State" or "City, Country" pattern
        match = re.match(r'^([A-Z][a-zA-Z\s]+),\s*([A-Z][a-zA-Z\s]+)$', line.strip())
        if match and len(line) < 60:
            return _clean_location(line)

    return ""


def _clean_location(location: str) -> str:
    """Clean and normalize a location string."""
    if not location:
        return ""
    # Remove leading bullets, dashes, pipes
    location = re.sub(r'^[\s\-–—•|:]+', '', location)
    # Remove trailing special chars
    location = re.sub(r'[\s\-–—•|:]+$', '', location)
    # Collapse whitespace
    location = re.sub(r'\s+', ' ', location).strip()
    return location


def _is_section_header(line: str) -> bool:
    """Check if a line looks like a section header rather than an address."""
    headers = [
        "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS",
        "PROJECTS", "OBJECTIVE", "SUMMARY", "PROFILE", "REFERENCES",
    ]
    upper = line.strip().upper()
    return upper in headers or any(upper == h for h in headers)