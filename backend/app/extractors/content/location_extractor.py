import re

# Philippine cities, provinces, regions, and common location indicators
_PH_LOCATIONS = [
    # NCR
    "QUEZON CITY", "MAKATI CITY", "MAKATI", "TAGUIG CITY", "TAGUIG",
    "PASIG CITY", "PASIG", "MANDALUYONG CITY", "MANDALUYONG",
    "MANILA", "CITY OF MANILA", "PASAY CITY", "PASAY",
    "PARAÑAQUE CITY", "PARANAQUE CITY", "PARAÑAQUE", "PARANAQUE",
    "MUNTINLUPA CITY", "MUNTINLUPA", "LAS PIÑAS CITY", "LAS PINAS CITY", "LAS PIÑAS", "LAS PINAS",
    "MARIKINA CITY", "MARIKINA", "CALOOCAN CITY", "CALOOCAN",
    "MALABON CITY", "MALABON", "NAVOTAS CITY", "NAVOTAS",
    "VALENZUELA CITY", "VALENZUELA", "SAN JUAN CITY", "SAN JUAN",
    "PATEROS", "BGC", "BONIFACIO GLOBAL CITY", "METRO MANILA", "NCR",
    "NATIONAL CAPITAL REGION",

    # Major Philippine cities
    "CEBU CITY", "CEBU", "DAVAO CITY", "DAVAO", "ILOILO CITY", "ILOILO",
    "BACOLOD CITY", "BACOLOD", "ZAMBOANGA CITY", "ZAMBOANGA",
    "CAGAYAN DE ORO CITY", "CAGAYAN DE ORO",
    "GENERAL SANTOS CITY", "GENERAL SANTOS", "BAGUIO CITY", "BAGUIO",
    "ANGELES CITY", "CLARK", "SUBIC", "OLONGAPO CITY", "OLONGAPO",
    "ANTIPOLO CITY", "ANTIPOLO", "CAINTA", "TAYTAY", "BINANGONAN",
    "CALAMBA CITY", "CALAMBA", "BIÑAN CITY", "BINAN CITY", "BIÑAN", "BINAN",
    "SANTA ROSA CITY", "STA. ROSA CITY", "SANTA ROSA", "STA. ROSA",
    "SAN PEDRO CITY", "SAN PEDRO", "CABUYAO CITY", "CABUYAO",
    "LIPA CITY", "LIPA", "BATANGAS CITY", "TAGAYTAY CITY", "TAGAYTAY",
    "DASMARIÑAS CITY", "DASMARINAS CITY", "DASMARIÑAS", "DASMARINAS",
    "IMUS CITY", "IMUS", "BACOOR CITY", "BACOOR", "GENERAL TRIAS",
    "LEGAZPI CITY", "LEGAZPI", "NAGA CITY", "NAGA", "TACLOBAN CITY", "TACLOBAN",
    "DUMAGUETE CITY", "DUMAGUETE", "SAN FERNANDO", "TARLAC CITY",
    "DAGUPAN CITY", "DAGUPAN", "URDANETA CITY", "URDANETA", "LAOAG CITY",
    "VIGAN CITY", "PUERTO PRINCESA", "ROXAS CITY", "ORMOC CITY", "ORMOC",
    "BUTUAN CITY", "ILIGAN CITY", "COTABATO CITY",

    # Philippine provinces / regions
    "CAVITE", "LAGUNA", "BATANGAS", "RIZAL", "QUEZON PROVINCE", "BULACAN",
    "PAMPANGA", "NUEVA ECIJA", "TARLAC", "PANGASINAN", "ZAMBALES", "BATAAN",
    "LA UNION", "BENGUET", "ILOCOS SUR", "ILOCOS NORTE", "ALBAY", "CAMARINES SUR",
    "PALAWAN", "BOHOL", "LEYTE", "NEGROS OCCIDENTAL", "NEGROS ORIENTAL",
    "MISAMIS ORIENTAL", "DAVAO DEL SUR", "CALABARZON", "CENTRAL LUZON",

    # Country
    "PHILIPPINES",
]

# International location indicators
_INTL_LOCATIONS = [
    "UNITED STATES", "USA", "CANADA", "UNITED KINGDOM", "UK", "AUSTRALIA",
    "SINGAPORE", "JAPAN", "INDIA", "GERMANY", "FRANCE", "SPAIN", "ITALY",
    "NETHERLANDS", "SWITZERLAND", "SWEDEN", "NEW ZEALAND", "IRELAND",
    "DUBAI", "UAE", "UNITED ARAB EMIRATES", "ABU DHABI", "SAUDI ARABIA",
    "QATAR", "HONG KONG", "TAIWAN", "SOUTH KOREA", "MALAYSIA", "VIETNAM",
    "THAILAND", "INDONESIA",
    # Cities
    "NEW YORK", "LOS ANGELES", "CHICAGO", "HOUSTON", "SAN FRANCISCO",
    "SAN JOSE", "SEATTLE", "AUSTIN", "BOSTON", "DENVER", "ATLANTA",
    "LONDON", "MANCHESTER", "TORONTO", "VANCOUVER", "SYDNEY", "MELBOURNE",
    "TOKYO", "BERLIN", "PARIS", "AMSTERDAM",
]

_NOT_LOCATION_WORDS = {
    "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "PROJECTS",
    "SUMMARY", "PROFILE", "ABOUT", "REFERENCES", "OBJECTIVE", "LANGUAGES",
    "GITHUB", "LINKEDIN", "EMAIL", "PHONE", "TEL", "MOBILE", "CURRICULUM", "VITAE", "RESUME",
    "JR", "JR.", "SR", "SR.", "II", "III", "IV", "V", "CPA", "RN", "MD", "PHD"
}


def _clean_location(location: str) -> str:
    """Clean and normalize a location string."""
    if not location:
        return ""
    cleaned = re.sub(r'^[\s\-–—•|:*#]+', '', location)
    cleaned = re.sub(r'[\s\-–—•|:*#]+$', '', cleaned)
    cleaned = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', cleaned)
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.strip(' ,-–—•|')


def _is_known_location(chunk: str) -> bool:
    """Check if chunk contains a known Philippine or international city/province/country."""
    c_upper = chunk.strip().upper()
    if not c_upper or len(c_upper) < 3 or len(c_upper) > 90:
        return False
    if '@' in chunk or 'http' in chunk or 'www.' in chunk or 'linkedin' in chunk:
        return False
    if len(re.findall(r'\d', chunk)) >= 7:
        return False

    # Check against noise/name suffixes
    words = [w.strip(' ,.') for w in c_upper.split()]
    if any(w in _NOT_LOCATION_WORDS for w in words):
        # Allow if it's clearly e.g. "Makati City, Philippines" despite other tokens
        if not any(loc in c_upper for loc in ["MANILA", "MAKATI", "QUEZON CITY", "PASIG", "TAGUIG", "PHILIPPINES"]):
            return False

    # Check known Philippine locations (longest matches first)
    for loc in _PH_LOCATIONS:
        pattern = r'\b' + re.escape(loc) + r'\b'
        if re.search(pattern, c_upper):
            return True

    # Check international locations
    for loc in _INTL_LOCATIONS:
        pattern = r'\b' + re.escape(loc) + r'\b'
        if re.search(pattern, c_upper):
            return True

    return False


def _is_valid_location_chunk(chunk: str) -> bool:
    """Check if a string segment is a legitimate location."""
    c = chunk.strip()
    if len(c) < 3 or len(c) > 90:
        return False
    if '@' in c or 'http' in c or 'www.' in c or 'linkedin' in c or 'github' in c:
        return False
    if len(re.findall(r'\d', c)) >= 7:
        return False

    # Don't match person names with suffixes like "JUAN M. DELA CRUZ, JR."
    if re.search(r'[,.\s]+(?:Jr\.?|Sr\.?|II|III|IV|V|CPA|RN|MD)$', c, re.IGNORECASE):
        return False

    if _is_known_location(c):
        return True

    # "City, Province/State/Country" pattern (ensure second part is not a personal suffix)
    match = re.match(r'^([A-Za-z\s.\-]+),\s*([A-Za-z\s.\-]+)$', c)
    if match:
        part2 = match.group(2).strip().upper()
        if part2 not in _NOT_LOCATION_WORDS and len(part2) >= 2:
            return True

    return False


def extract_location(text: str) -> str:
    """
    Extracts the candidate's location/residence from resume text.
    """
    if not text:
        return ""

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    header_lines = lines[:15]

    # ── Strategy 1: Labeled location field ────────────────────────────────────
    labeled_patterns = [
        r'(?:Current\s+Location|Location|Address|Residence|City)\s*[:.\-]\s*(.+)',
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            line_val = match.group(1).split('\n')[0].strip()
            chunks = re.split(r'\s*[|•\t]\s*', line_val)
            for ch in chunks:
                if _is_known_location(ch):
                    return _clean_location(ch)
            for ch in chunks:
                if _is_valid_location_chunk(ch):
                    return _clean_location(ch)
            if _is_valid_location_chunk(line_val):
                return _clean_location(line_val)

    # ── Strategy 2: Prioritized Scan for Known Locations in Header Chunks ─────
    # Split header lines into segments and find the chunk with a KNOWN location
    for line in header_lines:
        if len(line) > 250:
            continue
        segments = re.split(r'\s*[|•\t]\s*', line)
        for seg in segments:
            seg_clean = seg.strip()
            if _is_known_location(seg_clean):
                return _clean_location(seg_clean)

    # ── Strategy 3: spaCy NER (GPE / LOC) in Header Area ───────────────────────
    try:
        from app.extractors.nlp.nlp_engine import get_doc
        doc = get_doc(text[:1500])
        gpe_entities = [ent.text.strip() for ent in doc.ents if ent.label_ in ("GPE", "LOC")]
        for gpe in gpe_entities:
            for line in header_lines:
                if gpe in line and not re.search(r'@|\d{7,}|http', line):
                    segments = re.split(r'\s*[|•\t]\s*', line)
                    for seg in segments:
                        if gpe in seg and _is_known_location(seg):
                            return _clean_location(seg)
                    if _is_valid_location_chunk(gpe):
                        return _clean_location(gpe)
    except Exception:
        pass

    # ── Strategy 4: Generic Valid Location Chunk Fallback ─────────────────────
    header_loc = ""
    for line in header_lines:
        if len(line) > 200:
            continue
        segments = re.split(r'\s*[|•\t]\s*', line)
        for seg in segments:
            seg_clean = seg.strip()
            if _is_valid_location_chunk(seg_clean):
                header_loc = _clean_location(seg_clean)
                break
        if header_loc:
            break

    if header_loc and header_loc.upper() not in {"PHILIPPINES", "USA", "REMOTE"}:
        return header_loc

    # ── Strategy 5: Infer City from Context if only Country was Found ─────────
    for city in [
        "QUEZON CITY", "MAKATI", "TAGUIG", "PASIG", "MANILA", "MANDALUYONG",
        "PASAY", "PARAÑAQUE", "MUNTINLUPA", "LAS PIÑAS", "MARIKINA", "CALOOCAN",
        "CEBU CITY", "CEBU", "DAVAO CITY", "DAVAO", "ILOILO CITY", "ILOILO",
        "BACOLOD", "BAGUIO", "ANGELES", "ANTIPOLO", "CALAMBA", "SANTA ROSA",
        "LIPA", "BATANGAS", "CAVITE", "LAGUNA", "RIZAL", "BULACAN", "PAMPANGA",
    ]:
        if re.search(r'\b' + re.escape(city) + r'\b', text, re.IGNORECASE):
            return f"{city.title()}, Philippines"

    return header_loc if header_loc else ""