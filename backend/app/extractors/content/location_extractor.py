"""
Philippine Location & Address Extractor
---------------------------------------
High-precision, deterministic NLP and geospatial extraction module tailored for
Philippine resumes, utilizing the Philippine Standard Geographic Code (PSGC),
flashtext KeywordProcessor, spaCy EntityRuler/PhraseMatcher, and address regex rules.

Extracts:
  - Residential / Permanent Addresses (House/Unit/Blk/Lot, Street, Subdivision, Purok/Sitio, Barangay, City, Province, Region, ZIP)
  - Work Experience & Education Inline Locations (Branches, Malls, Business Hubs like BGC/Ortigas, Cities, Provinces)
  - Performs Contextual Disambiguation (preventing false positives from school/person names like Rizal, Quezon)
  - Performs Automatic Province & Region Hierarchy Inference for unique municipalities.
"""

import sys
import os
import re
import json
import unicodedata
from typing import Dict, Any, Optional, List, Tuple

# Bootstrap sys.path for standalone execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except ImportError:
    spacy = None
    PhraseMatcher = None

try:
    from flashtext import KeywordProcessor
except ImportError:
    KeywordProcessor = None

from app.extractors.content.psgc_gazetteer import (
    PHILIPPINE_REGIONS,
    PHILIPPINE_PROVINCES,
    CORE_LGUS,
    COMMERCIAL_HUBS,
    remove_accents,
    lookup_location,
    infer_province_and_region,
    is_philippine_province,
    get_gazetteer
)


# ─── 1. Sub-Municipality Regex Patterns ───────────────────────────────────────

# Subdivision / Housing markers
_SUBD_MARKERS = r'\b(?:Subd\.?|Subdivision|Village|Compound|Cpd\.?|Homes|Residences|Condominium|Condo|Tower|Bldg\.?|Building)\b'
# Rural / Community markers
_RURAL_MARKERS = r'\b(?:Purok|Prk\.?|P\.|Sitio|Ste\.?|Zone|Poblacion|Pob\.?)\b'
# Housing unit / Lot markers
_HOUSING_MARKERS = r'\b(?:Blk\.?|Block|Lot|Phase|Ph\.?|Unit|Room|Rm\.?|Flr\.?|Floor|Apt\.?|Apartment)\b'
# Street markers
_STREET_MARKERS = r'\b(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Highway|H-way|Hwy\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Extension|Ext\.?)\b'
# Barangay markers
_BRGY_MARKERS = r'\b(?:Brgy\.?|Barangay|Bgy\.?)\b'
# Philippine 4-digit ZIP code
_ZIP_PATTERN = r'\b([1-9]\d{3})\b'


def _normalize_whitespace(text: str) -> str:
    """Standardizes spaces and hyphens."""
    if not text:
        return ""
    text = text.replace('–', '-').replace('—', '-').replace('•', ' ')
    return ' '.join(text.split())


# ─── 2. Hybrid NLP Matcher Setup (flashtext + spaCy) ──────────────────────────

_FLASHTEXT_PROCESSOR: Optional[Any] = None


def _get_flashtext_processor() -> Optional[Any]:
    """Initializes and caches the flashtext KeywordProcessor for O(N) LGU and Hub matching."""
    global _FLASHTEXT_PROCESSOR
    if _FLASHTEXT_PROCESSOR is not None:
        return _FLASHTEXT_PROCESSOR

    if KeywordProcessor is None:
        return None

    kp = KeywordProcessor(case_sensitive=False)

    # 1. Add Commercial Hubs
    for hub_name, hub_info in COMMERCIAL_HUBS.items():
        kp.add_keyword(hub_name, {"type": "HUB", "data": hub_info})

    # 2. Add LGUs
    for lgu in CORE_LGUS:
        for alias in lgu["aliases"]:
            kp.add_keyword(alias, {"type": "LGU", "data": lgu})
            alias_no_acc = remove_accents(alias)
            if alias_no_acc != alias:
                kp.add_keyword(alias_no_acc, {"type": "LGU", "data": lgu})

    # 3. Add Provinces
    for prov_name, reg_name in PHILIPPINE_PROVINCES.items():
        kp.add_keyword(prov_name, {"type": "PROVINCE", "data": {"province": prov_name, "region": reg_name}})

    _FLASHTEXT_PROCESSOR = kp
    return _FLASHTEXT_PROCESSOR


# ─── 3. Contextual Disambiguation & Address Parser ────────────────────────────

def parse_philippine_address(raw_text: str) -> Dict[str, Any]:
    """
    Parses a Philippine address or location string into the standardized JSON schema:
    {
      "raw_location_text": str,
      "normalized_location": str,
      "house_street_subdivision": str | None,
      "barangay": str | None,
      "city_or_municipality": str,
      "location_type": str,
      "business_district_or_branch": str | None,
      "province": str,
      "region": str,
      "zip_code": str | None,
      "confidence_score": float
    }
    """
    if not raw_text:
        return _empty_location_dict(raw_text)

    text = _normalize_whitespace(raw_text)

    # 1. Strip label prefixes like Address:, Permanent Address:, etc.
    text_clean = re.sub(
        r'^(?:Permanent\s+Address|Present\s+Address|Current\s+Address|Residential\s+Address|Home\s+Address|Address|Location|Residence)\s*[:.\-]\s*',
        '',
        text,
        flags=re.I
    ).strip()

    # 2. Extract ZIP Code (4 digits)
    zip_code = None
    zip_match = re.search(_ZIP_PATTERN, text_clean)
    if zip_match:
        zip_code = zip_match.group(1)
        text_without_zip = re.sub(rf'\b{zip_code}\b', '', text_clean).strip(' ,')
    else:
        text_without_zip = text_clean

    # 3. Detect Business District, Commercial Hub, Mall Branch, or Campus
    business_hub = None

    # Check Mall branches (e.g., "SM City Taytay", "Robinsons Galleria", "Ayala Malls Feliz")
    mall_match = re.search(r'\b((?:SM\s+City|SM|Robinsons|Ayala\s+Malls)\s+[A-Za-z]+)\b', text_without_zip, re.I)
    if mall_match:
        business_hub = mall_match.group(1).strip()

    # Check Employer or Campus Branches (e.g., "Crossing Branch", "Cainta Main Campus")
    branch_match = re.search(r'\b([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2}\s+(?:Branch|Main\s+Campus|Campus))\b', text_without_zip, re.I)
    if branch_match and not business_hub:
        business_hub = branch_match.group(1).strip()

    # Check known Commercial Hubs (e.g. BGC, Ortigas Center, Makati CBD, Clark, Subic)
    if not business_hub:
        for hub_k, hub_v in sorted(COMMERCIAL_HUBS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf'\b{re.escape(hub_k)}\b', text_without_zip, re.I):
                business_hub = hub_v["hub"]
                break

    # 4. Detect Province (with false-positive guard against schools and universities)
    matched_province = None
    for prov in sorted(PHILIPPINE_PROVINCES.keys(), key=len, reverse=True):
        if prov == "Metro Manila":
            pat = r'\b(?:Metro\s+Manila|M\.M\.|NCR)\b'
        else:
            pat = rf'\b{re.escape(prov)}\b'

        for m_prov in re.finditer(pat, text_without_zip, re.I):
            span = m_prov.span()
            preceding_str = text_without_zip[:span[0]]
            following_str = text_without_zip[span[1]:]

            # False-positive guard: "Jose Rizal University", "Rizal National Science High School"
            if re.search(r'(?:University\s+of|College\s+of|State\s+University)\s*$', preceding_str, re.I):
                continue
            if re.search(r'^\s*(?:National\s+High\s+School|High\s+School|Science\s+High\s+School|University|College|Hospital)', following_str, re.I):
                continue

            matched_province = prov
            break

        if matched_province:
            break

    # 5. Detect City / Municipality
    matched_lgu = None
    candidate_lgus = []

    for lgu in CORE_LGUS:
        for alias in lgu["aliases"]:
            # False-positive guard for "Manila" vs "Metro Manila"
            if alias.lower() in ("manila", "city of manila"):
                m_man = re.search(r'(?<!Metro\s)\b(?:City\s+of\s+)?Manila\b', text_without_zip, re.I)
                if not m_man:
                    continue
                span = m_man.span()
            else:
                pat = rf'\b{re.escape(alias)}\b'
                m_lgu = re.search(pat, text_without_zip, re.I)
                if not m_lgu:
                    continue
                span = m_lgu.span()

            following_str = text_without_zip[span[1]:]
            # False-positive guard: institution suffix
            if re.search(r'^\s*(?:National\s+High\s+School|High\s+School|Science\s+High\s+School|University|College|Hospital)', following_str, re.I):
                continue

            # Score this candidate:
            score = len(alias)
            if matched_province and lgu["province"].lower() == matched_province.lower():
                score += 100
            elif matched_province and lgu["province"].lower() != matched_province.lower():
                score -= 50

            candidate_lgus.append((score, span[0], lgu))

    if candidate_lgus:
        # Highest score first, then earliest position in text
        candidate_lgus.sort(key=lambda x: (-x[0], x[1]))
        matched_lgu = candidate_lgus[0][2]

    # If no LGU matched directly, check if a Commercial Hub implies one
    if not matched_lgu and business_hub:
        for hub_k, hub_v in COMMERCIAL_HUBS.items():
            if hub_k.lower() in business_hub.lower():
                matched_lgu = {
                    "name": hub_v["city"],
                    "canonical": hub_v["city"],
                    "type": hub_v["type"],
                    "province": hub_v["province"],
                    "region": hub_v["region"]
                }
                break

    # 6. Extract Barangay
    barangay = None
    brgy_match = re.search(r'\b(?:Brgy\.?|Barangay|Bgy\.?)\s*([A-Za-z0-9\s.-]+?)(?=,|\s+\d{4}|\s+(?:City|Municipality)|$)', text_without_zip, re.I)
    if brgy_match:
        barangay = brgy_match.group(1).strip(' ,.-')

    # 7. Extract House / Street / Subdivision
    house_street_subd = None
    split_pt = None
    if brgy_match:
        split_pt = brgy_match.start()
    elif matched_lgu:
        lgu_key = matched_lgu.get("name", matched_lgu["canonical"])
        m_lgu_pos = re.search(rf'\b{re.escape(lgu_key)}\b', text_without_zip, re.I)
        if m_lgu_pos:
            split_pt = m_lgu_pos.start()

    if split_pt and split_pt > 0:
        prefix = text_without_zip[:split_pt].strip(' ,-–—|')
        # Check if prefix contains address markers or house numbers
        if prefix and (re.search(rf'{_HOUSING_MARKERS}|{_RURAL_MARKERS}|{_SUBD_MARKERS}|{_STREET_MARKERS}', prefix, re.I) or re.search(r'\d+[-A-Za-z0-9]*', prefix)):
            house_street_subd = prefix

    # 8. Resolve Final Normalized Hierarchy
    city_muni = matched_lgu["canonical"] if matched_lgu else "Unknown"
    prov = matched_province if matched_province else (matched_lgu["province"] if matched_lgu else "Unknown")
    reg = PHILIPPINE_PROVINCES.get(prov, (matched_lgu["region"] if matched_lgu else "Unknown"))
    loc_type = matched_lgu["type"] if matched_lgu else "Unknown"

    if prov == "Metro Manila":
        norm_loc = f"{city_muni}, Metro Manila"
    elif prov != "Unknown" and city_muni != "Unknown":
        norm_loc = f"{city_muni}, {prov}"
    else:
        norm_loc = city_muni if city_muni != "Unknown" else (prov if prov != "Unknown" else "Philippines")

    # 9. Confidence Score Calculation
    conf = 0.50
    if matched_lgu:
        conf += 0.25
    if matched_province:
        conf += 0.15
    if barangay:
        conf += 0.05
    if zip_code:
        conf += 0.05
    conf = min(round(conf, 2), 1.0)

    return {
        "raw_location_text": raw_text.strip(),
        "normalized_location": norm_loc,
        "house_street_subdivision": house_street_subd,
        "barangay": barangay,
        "city_or_municipality": city_muni,
        "location_type": loc_type,
        "business_district_or_branch": business_hub,
        "province": prov,
        "region": reg,
        "zip_code": zip_code,
        "confidence_score": conf
    }


def _empty_location_dict(raw_text: str) -> Dict[str, Any]:
    return {
        "raw_location_text": (raw_text or "").strip(),
        "normalized_location": "Philippines",
        "house_street_subdivision": None,
        "barangay": None,
        "city_or_municipality": "Unknown",
        "location_type": "Unknown",
        "business_district_or_branch": None,
        "province": "Unknown",
        "region": "Unknown",
        "zip_code": None,
        "confidence_score": 0.0
    }


# ─── 4. Public API Extraction Methods ─────────────────────────────────────────

def extract_applicant_address(resume_text: str) -> Dict[str, Any]:
    """
    Extracts the applicant's residential or permanent address from resume header or labeled fields.
    Returns structured dictionary matching the expected JSON schema.
    """
    if not resume_text:
        return _empty_location_dict("")

    lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
    header_lines = lines[:20]

    # Strategy 1: Explicitly labeled address field (e.g. "Address: ...", "Permanent Address: ...")
    labeled_pattern = r'(?:Permanent\s+Address|Present\s+Address|Current\s+Address|Residential\s+Address|Home\s+Address|Address|Location|Residence)\s*[:.\-]\s*(.+)'
    for line in header_lines:
        m = re.match(labeled_pattern, line, re.I)
        if m:
            val = m.group(1).strip()
            # If line is pipe-separated, take the address chunk
            chunks = re.split(r'\s*[|•\t]\s*', val)
            for ch in chunks:
                parsed = parse_philippine_address(ch)
                if parsed["city_or_municipality"] != "Unknown" or parsed["province"] != "Unknown":
                    return parsed
            parsed = parse_philippine_address(val)
            if parsed["city_or_municipality"] != "Unknown":
                return parsed

    # Strategy 2: Scan header contact chunks (pipes, bullets, tabs)
    for line in header_lines:
        if len(line) > 250:
            continue
        chunks = re.split(r'\s*[|•\t]\s*', line)
        for chunk in chunks:
            ch_clean = chunk.strip()
            # Skip emails, URLs, and phone numbers
            if '@' in ch_clean or 'http' in ch_clean or re.search(r'^(?:\+?63|0)9\d{9}$', ch_clean):
                continue
            parsed = parse_philippine_address(ch_clean)
            if parsed["city_or_municipality"] != "Unknown" and parsed["confidence_score"] >= 0.70:
                return parsed

    # Strategy 3: Full resume header fallback
    header_block = " ".join(header_lines[:10])
    parsed_header = parse_philippine_address(header_block)
    if parsed_header["city_or_municipality"] != "Unknown":
        return parsed_header

    return _empty_location_dict("")


def extract_inline_location(text_snippet: str) -> Dict[str, Any]:
    """
    Extracts inline location, city, province, and employer branch or hub from
    a work experience or education line snippet.
    """
    if not text_snippet:
        return _empty_location_dict("")
    return parse_philippine_address(text_snippet)


def extract_location(text: str) -> str:
    """
    Backward-compatible function returning a clean normalized location string
    e.g. "Teresa, Rizal" or "Pasig City, Metro Manila".
    """
    parsed = extract_applicant_address(text)
    if parsed["normalized_location"] and parsed["normalized_location"] != "Philippines":
        return parsed["normalized_location"]

    # Fallback to general scan
    lines = [line.strip() for line in text.split('\n') if line.strip()][:15]
    for line in lines:
        for chunk in re.split(r'\s*[|•\t]\s*', line):
            if '@' in chunk or 'http' in chunk:
                continue
            parsed_ch = parse_philippine_address(chunk)
            if parsed_ch["city_or_municipality"] != "Unknown":
                return parsed_ch["normalized_location"]

    return "Philippines"


# ─── 5. Runnable Demonstration & Test Block ───────────────────────────────────

if __name__ == "__main__":
    patterns = [
        (
            "Pattern 1 (Suburban Subdivision + Barangay + Municipality + Province)",
            "Address: Blk 8 Lot 15 Phase 2, Carissa Homes East, Brgy. Bagumbayan, Teresa, Rizal 1880"
        ),
        (
            "Pattern 2 (Provincial Purok / Sitio Format)",
            "Permanent Address: Purok 4, Sitio Maligaya, Brgy. San Roque, Sto. Tomas, Batangas"
        ),
        (
            "Pattern 3 (Metro Manila Urban / Condo / Street Format)",
            "24-B Mabini St., Brgy. Kapitolyo, Pasig City, Metro Manila"
        ),
        (
            "Pattern 4 (Work Experience Commercial Hub / Mall Branch Format)",
            "Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna\nAccenture Philippines | BGC, Taguig City\nChowking - SM City Taytay, Rizal"
        ),
        (
            "Pattern 5 (Municipality-Only Inference & Disambiguation)",
            "ICCT Colleges - Cainta Main Campus\nRizal National Science High School, Binangonan, Rizal"
        ),
    ]

    print("=" * 70)
    print("PHILIPPINE LOCATION & ADDRESS EXTRACTION DEMONSTRATION")
    print("=" * 70)

    # Test 1: Pattern 1
    print("\n--- Pattern 1 ---")
    p1_res = extract_applicant_address(patterns[0][1])
    print(json.dumps(p1_res, indent=2))

    # Test 2: Pattern 2
    print("\n--- Pattern 2 ---")
    p2_res = extract_applicant_address(patterns[1][1])
    print(json.dumps(p2_res, indent=2))

    # Test 3: Pattern 3
    print("\n--- Pattern 3 ---")
    p3_res = extract_applicant_address(patterns[2][1])
    print(json.dumps(p3_res, indent=2))

    # Test 4: Pattern 4
    print("\n--- Pattern 4 ---")
    p4_snippets = [
        "Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna",
        "Accenture Philippines | BGC, Taguig City",
        "Chowking - SM City Taytay, Rizal"
    ]
    for snip in p4_snippets:
        print(f"\nSnippet: {snip}")
        print(json.dumps(extract_inline_location(snip), indent=2))

    # Test 5: Pattern 5
    print("\n--- Pattern 5 ---")
    p5_snippets = [
        "ICCT Colleges - Cainta Main Campus",
        "Rizal National Science High School, Binangonan, Rizal"
    ]
    for snip in p5_snippets:
        print(f"\nSnippet: {snip}")
        print(json.dumps(extract_inline_location(snip), indent=2))