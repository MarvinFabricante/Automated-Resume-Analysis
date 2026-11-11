"""
Philippine Resume Certifications, Licenses & Eligibility Extraction Engine
========================================================================
High-recall, deterministic multi-item extraction engine for Philippine resumes.
Extracts:
1. PRC Board Licenses, post-nominals, and government eligibilities (CSC, LTO, PNP-SOSIA)
2. TESDA National Certificates (NC I to NC IV) and Certificates of Competency (COC)
3. Safety & Compliance certifications (DOLE BOSH/COSH SO1-SO4, Red Cross BLS, ISO, HACCP)
4. Vendor & Global IT credentials (AWS, Azure, GCP, CKA, Cisco, Oracle, CompTIA, Scrum)
5. Online bootcamps & training seminars (Coursera, Udemy, Sololearn, Ground Gurus, FreeCodeCamp)

Four-Layer Pipeline:
- Layer 0: Post-nominal PRC titles in resume header
- Layer 1: Gazetteer & ontology matching via FlashText + spaCy EntityRuler + RapidFuzz
- Layer 2: Structural regex catchers for dynamic Philippine credentials
- Layer 3: Bullet-level fallback parsing inside dedicated certification/training sections
- Layer 4: Metadata enrichment (issuing organization, issue date, status, credential ID/rating)
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

try:
    from flashtext import KeywordProcessor
except ImportError:
    KeywordProcessor = None

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

try:
    import dateparser
except ImportError:
    dateparser = None

try:
    import spacy
    from spacy.pipeline import EntityRuler
except ImportError:
    spacy = None
    EntityRuler = None

from app.extractors.content.certifications_taxonomy import (
    PHILIPPINE_CERTIFICATIONS_TAXONOMY,
    _KNOWN_ORGANIZATIONS,
    _POST_NOMINAL_MAP,
    _PROTECTED_PHRASES,
    _SECTION_HEADERS,
    _CREDENTIAL_MARKERS,
    load_external_certification_datasets,
)
from app.extractors.content.section_parser import (
    detect_section_label,
    split_dual_column_header,
)

logger = logging.getLogger(__name__)

_CERT_SECTIONS = {"Certifications", "Eligibility", "Seminars & Trainings"}
_CANONICAL_SEC_MAP = {
    "CERTIFICATIONS": "Certifications",
    "TRAINING": "Seminars & Trainings",
    "AWARDS": "Certifications",
    "EXPERIENCE": "Work Experience",
    "EDUCATION": "Education",
    "SKILLS": "Skills",
}
_BULLET_PREFIX_RE = re.compile(r'^(?:[•▪►✓*]|\-(?=\s)|\d{1,2}[\.\)])\s+')
_LEADING_YEAR_RE = re.compile(r'^((?:19|20)\d{2})\s*(?:[-–—|:]\s+)(.+)$')
_PURE_DATE_OR_YEAR_RE = re.compile(
    r'^(?:(?:19|20)\d{2}(?:\s*[-–—to]+\s*(?:(?:19|20)\d{2}|present))?|'
    r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{4})$',
    re.IGNORECASE,
)
_NON_ITEM_METADATA_RE = re.compile(
    r'^(?:issued\s*(?:by|on|date)?|issuer|provider|organization|valid\s*(?:until|thru|through)|'
    r'expir(?:es?|ation)|date(?:\s+issued)?|rating|score|reg(?:\.|istration)?\s*(?:no\.?|#)?|'
    r'license\s*(?:no\.?|#|id)|cert(?:ificate)?\s*(?:no\.?|#|id)|validation\s*(?:id|no\.?)?|'
    r'status|hours?|none|n/?a|not\s+applicable)\s*(?:[:\-–—]|$)',
    re.IGNORECASE,
)
_NON_SPLIT_COMMA_PART_RE = re.compile(
    r'^(?:inc\.?|corp\.?|ltd\.?|llc|co\.?|philippines|metro\s+manila|manila|city|province|'
    r'laguna|cavite|batangas|rizal|cebu|davao|quezon\s+city|makati|taguig|pasig|'
    r'active|passed|completed|expired|'
    r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{4}|'
    r'(?:19|20)\d{2}|\d+\s*hours?|rating\s*[:\-].*|'
    r'(?:cert|license|reg|validation)\s*(?:no\.?|id|#).*|issued\s+.*|valid\s+.*)$',
    re.IGNORECASE,
)


def _strip_list_prefix(line: str) -> str:
    """Strip leading bullet markers or numbering without eating leading digits in cert names (e.g. '5S')."""
    return re.sub(r'^(?:[•\-–—▪►✓*]|\(?\d{1,2}[\.\)])\s*', '', line.strip()).strip()


def _match_cert_header(candidate: str) -> Optional[str]:
    """Match a standalone header text against certification section headers and canonical labels."""
    clean = candidate.strip().strip("-=_*#•►:│┃ ")
    if not clean or len(clean.split()) > 8:
        return None
    for sec_name, pat in _SECTION_HEADERS.items():
        if pat.match(clean) or pat.match(candidate.strip()):
            return sec_name
    if ':' not in candidate and '|' not in candidate:
        sec_lbl = detect_section_label(clean)
        if sec_lbl:
            return _CANONICAL_SEC_MAP.get(sec_lbl, "Other")
    return None


# ─── Multi-Item Line Splitter & Header Helper ──────────────────────────────────

def is_header_line(line: str) -> Optional[str]:
    """
    Checks if a given line is a section header (e.g., 'LICENSES AND ELIGIBILITY').
    Returns section name if matched, else None.
    """
    stripped = line.strip()
    if not stripped or _BULLET_PREFIX_RE.match(stripped):
        return None
    if split_dual_column_header(stripped):
        return None
    return _match_cert_header(stripped)


def parse_header_line(
    line: str, current_section: str = "Header"
) -> Tuple[Optional[str], Optional[str], Optional[Tuple[str, str]]]:
    """
    Parse a header line into ``(section_name, inline_content, dual_columns)``.
    Supports standalone headers, inline ``Header: items`` / ``Header | items``,
    and dual-column table headers like ``CERTIFICATIONS | SKILLS``.
    """
    stripped = line.strip()
    if not stripped or _BULLET_PREFIX_RE.match(stripped):
        return None, None, None

    dual = split_dual_column_header(stripped)
    if dual:
        mapped_l = _CANONICAL_SEC_MAP.get(dual[0], "Other")
        mapped_r = _CANONICAL_SEC_MAP.get(dual[1], "Other")
        return None, None, (mapped_l, mapped_r)

    colon_idx = stripped.find(':')
    if colon_idx > 0:
        prefix = stripped[:colon_idx].strip()
        remainder = stripped[colon_idx + 1:].strip()
        sec = _match_cert_header(prefix)
        if sec:
            if (
                current_section == "Education"
                and prefix.lower() in {"honors", "awards", "honors/awards", "awards/honors", "honors & awards"}
            ):
                return None, None, None
            return sec, (remainder or None), None

    pipe_idx = stripped.find('|')
    if pipe_idx > 0:
        left = stripped[:pipe_idx].strip()
        right = stripped[pipe_idx + 1:].strip()
        if left and len(left.split()) <= 5:
            sec = _match_cert_header(left)
            if sec:
                return sec, (right or None), None

    sec = _match_cert_header(stripped)
    if sec:
        return sec, None, None

    return None, None, None


def split_compound_cert_line(line: str, in_cert_section: bool = False) -> List[str]:
    """
    Splits compound certification lines while preserving unified course names.
    Examples:
    - 'TESDA Food and Beverage Services NC II & Bread and Pastry Production NC II'
      -> ['TESDA Food and Beverage Services NC II', 'Bread and Pastry Production NC II']
    - 'Civil Engineering Board Exam Passer | RCE License No. 0154321'
      -> ['Civil Engineering Board Exam Passer', 'RCE License No. 0154321']
    - 'Certified Kubernetes Administrator (CKA) - Cloud Native Computing Foundation / Linux Foundation'
      -> Remains intact (does not split on ' / ' because 'Linux Foundation' is an org, not a separate cert)
    """
    temp = _strip_list_prefix(line)
    if not temp:
        return []

    # 1. Protect unified multi-word titles containing 'and', '&', etc.
    placeholders: Dict[str, str] = {}
    for idx, p in enumerate(_PROTECTED_PHRASES):
        pat = re.compile(re.escape(p), re.IGNORECASE)
        for m in pat.finditer(temp):
            ph = f"__PROT_PH_{idx}__"
            placeholders[ph] = m.group(0)
            temp = temp.replace(m.group(0), ph)

    # 2. Split on primary delimiters: pipe '|' or semicolon ';'
    raw_parts = re.split(r'[|;]', temp)

    has_marker = lambda s: any(re.search(m, s, re.IGNORECASE) for m in _CREDENTIAL_MARKERS)

    def _restore(s: str) -> str:
        for ph, orig in placeholders.items():
            s = s.replace(ph, orig)
        return s.strip()

    def _can_split_commas(segment: str, parts: List[str]) -> bool:
        if len(parts) <= 1:
            return False
        if all(has_marker(c) for c in parts):
            return True
        if not in_cert_section:
            return False
        if re.search(r'\s+[-–—]\s+', segment.split(',', 1)[0]):
            return False
        for c in parts:
            c_rest = _restore(c)
            if len(c_rest) < 4:
                return False
            if _NON_SPLIT_COMMA_PART_RE.match(c_rest) or c_rest.upper() in _KNOWN_ORGANIZATIONS:
                return False
        return True

    items: List[str] = []
    for rp in raw_parts:
        rp = rp.strip()
        if not rp:
            continue

        # 3. Check '&', ' / ', or ' and '
        # Only split if BOTH sides contain a credential marker (e.g. NC II, Certified, Passer)
        delim_pat = re.compile(r'\s+&\s+|\s+/\s+|\s+and\s+', re.IGNORECASE)
        splits = delim_pat.split(rp)
        if len(splits) > 1 and all(has_marker(s) for s in splits):
            for s in splits:
                s_clean = _restore(s)
                if len(s_clean) >= 3:
                    items.append(s_clean)
            continue

        # 4. Check comma outside parentheses
        c_parts = re.split(r',\s*(?![^()]*\))', rp)
        if _can_split_commas(rp, c_parts):
            for cp in c_parts:
                cp_clean = _restore(cp)
                if len(cp_clean) >= 3:
                    items.append(cp_clean)
            continue

        # 5. Keep as single item and restore placeholders
        rp_rest = _restore(rp)
        if len(rp_rest) >= 3:
            items.append(rp_rest)

    return items


# ─── Main Extraction Engine ───────────────────────────────────────────────────

class PhilippineCertificationsExtractor:
    """
    High-recall, deterministic Philippine Resume Certifications, Licenses & Eligibility Extractor.
    Adheres strictly to local NLP processing without external LLM dependencies.
    """

    def __init__(self):
        self.taxonomy = PHILIPPINE_CERTIFICATIONS_TAXONOMY
        self.alias_to_canonical: Dict[str, str] = {}
        self.keyword_processor = None
        self.spacy_nlp = None
        self.spacy_ruler = None
        self._build_index()

    def _build_index(self):
        """Builds FlashText KeywordProcessor, spaCy EntityRuler, and lookup tables."""
        if KeywordProcessor is not None:
            self.keyword_processor = KeywordProcessor(case_sensitive=False)

        if spacy is not None:
            try:
                self.spacy_nlp = spacy.blank("en")
                self.spacy_ruler = self.spacy_nlp.add_pipe("entity_ruler")
            except Exception as e:
                logger.warning(f"Could not initialize spaCy EntityRuler: {e}")
                self.spacy_nlp = None
                self.spacy_ruler = None

        self.alias_to_canonical = {}
        spacy_patterns = []

        for canonical, info in self.taxonomy.items():
            if self.keyword_processor is not None:
                self.keyword_processor.add_keyword(canonical, canonical)
            self.alias_to_canonical[canonical.lower()] = canonical

            if self.spacy_ruler is not None:
                spacy_patterns.append({
                    "label": "CERT",
                    "pattern": canonical,
                    "id": canonical
                })

            for alias in info.get("aliases", []):
                clean_alias = alias.strip()
                if clean_alias:
                    if self.keyword_processor is not None:
                        self.keyword_processor.add_keyword(clean_alias, canonical)
                    self.alias_to_canonical[clean_alias.lower()] = canonical
                    if self.spacy_ruler is not None and len(clean_alias.split()) <= 6:
                        spacy_patterns.append({
                            "label": "CERT",
                            "pattern": clean_alias,
                            "id": canonical
                        })

        if self.spacy_ruler is not None and spacy_patterns:
            try:
                self.spacy_ruler.add_patterns(spacy_patterns)
            except Exception as e:
                logger.warning(f"Failed to add patterns to spaCy EntityRuler: {e}")

    def _segment_document(self, text: str) -> List[Tuple[int, int, str]]:
        """Segments text into typed sections based on headers."""
        spans: List[Tuple[int, int, str]] = []
        lines = text.split('\n')
        current_section = "Header"
        section_start = 0
        char_offset = 0

        for idx, line in enumerate(lines):
            line_len = len(line) + 1
            clean = line.strip()

            if clean:
                matched_header, _, dual_hdr = parse_header_line(clean, current_section)
                if dual_hdr:
                    cert_col = next((c for c in dual_hdr if c in _CERT_SECTIONS), None)
                    matched_header = cert_col or dual_hdr[0]
                if matched_header:
                    if char_offset > section_start:
                        spans.append((section_start, char_offset, current_section))
                    current_section = matched_header
                    section_start = char_offset
                elif idx > 5 and current_section == "Header":
                    current_section = "General"

            char_offset += line_len

        if char_offset > section_start:
            spans.append((section_start, char_offset, current_section))

        return spans

    def _get_section(self, offset: int, spans: List[Tuple[int, int, str]]) -> str:
        """Finds the section name enclosing a character offset."""
        for start, end, name in spans:
            if start <= offset < end:
                return name
        return "General"

    def _extract_metadata_from_context(
        self, text_context: str, canonical_name: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Layer 4: Metadata Enrichment.
        Extracts issuing organization, dates (issue & expiration), status, and credential details.
        """
        # 1. Issuing Organization
        issuer: Optional[str] = None
        for org_key, org_canonical in _KNOWN_ORGANIZATIONS.items():
            if re.search(r'\b' + re.escape(org_key) + r'\b', text_context, re.IGNORECASE):
                issuer = org_canonical
                break

        if not issuer:
            m_iss = re.search(
                r'(?:issued\s+by|by|from|via|at)\s+([A-Za-z0-9\s&.,\-]+?)(?=[,\(\)\|\;\n]|$)',
                text_context, re.IGNORECASE
            )
            if m_iss:
                cand_iss = m_iss.group(1).strip().strip("-:,")
                if 2 < len(cand_iss) < 40 and not any(w in cand_iss.lower() for w in ["rating", "hours", "restriction", "valid", "code"]):
                    issuer = cand_iss

        if not issuer and canonical_name in self.taxonomy:
            issuer = self.taxonomy[canonical_name].get("default_issuer")

        # 2. Issue Date & Expiration Date
        # Mask title-embedded years (e.g. ISO 9001:2015, MOS Excel 2019, CCNA 200-301)
        masked_text = re.sub(r'ISO\s*\d+:\d{4}', lambda m: 'X' * len(m.group(0)), text_context, flags=re.IGNORECASE)
        masked_text = re.sub(r'\b(?:Excel|Word|Office|Windows|Server)\s+\d{4}\b', lambda m: 'X' * len(m.group(0)), masked_text, flags=re.IGNORECASE)
        masked_text = re.sub(r'\b(?:Valid\s+(?:until|thru)|Expires?)\s*[:\-]?\s*(?:[A-Za-z]{3,9}\s+)?\d{4}\b', lambda m: 'X' * len(m.group(0)), masked_text, flags=re.IGNORECASE)

        issue_date: Optional[str] = None
        # Explicit date indicators
        m_date = re.search(
            r'(?:Issued|Passed|Date|Completed)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{4}|\d{4})\b',
            masked_text, re.IGNORECASE
        )
        if m_date:
            raw_d = m_date.group(1).strip()
            if dateparser:
                dt = dateparser.parse(raw_d, settings={'PREFER_DAY_OF_MONTH': 'first'})
                has_month = bool(re.search(r'\b[A-Za-z]{3,9}\b', raw_d))
                issue_date = dt.strftime('%Y-%m' if has_month else '%Y') if dt else raw_d
            else:
                issue_date = raw_d
        else:
            # Standalone Month + Year
            m_my = re.search(
                r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b',
                masked_text, re.IGNORECASE
            )
            if m_my:
                raw_d = m_my.group(1).strip()
                if dateparser:
                    dt = dateparser.parse(raw_d, settings={'PREFER_DAY_OF_MONTH': 'first'})
                    issue_date = dt.strftime('%Y-%m') if dt else raw_d
                else:
                    issue_date = raw_d
            else:
                # Year in parentheses or after comma/dash (e.g. (2022) or , 2023)
                m_yr = re.search(r'(?:[\(,\-–—]\s*)\b(20\d{2}|19\d{2})\b(?:\s*[\)]|\s*$|\s*[,\|])', masked_text)
                if m_yr:
                    issue_date = m_yr.group(1).strip()

        # 3. Expiration or Status
        expiration_or_status: Optional[str] = None
        m_exp = re.search(
            r'(?:Valid\s+(?:until|thru)|Expires?|Validity|Expiration)\s*[:\-]?\s*\b([A-Za-z]{3,9}\s+\d{4}|\d{4})\b',
            text_context, re.IGNORECASE
        )
        if m_exp:
            raw_exp = m_exp.group(1).strip()
            if dateparser:
                dt = dateparser.parse(raw_exp, settings={'PREFER_DAY_OF_MONTH': 'first'})
                has_month = bool(re.search(r'\b[A-Za-z]{3,9}\b', raw_exp))
                fmt_exp = dt.strftime('%Y-%m' if has_month else '%Y') if dt else raw_exp
            else:
                fmt_exp = raw_exp
            expiration_or_status = f"Valid until {fmt_exp}"
        else:
            m_status = re.search(r'\b(Active|Passed|Passer|Lifetime\s+Validity|Expired)\b', text_context, re.IGNORECASE)
            if m_status:
                stat_val = m_status.group(1).title()
                if stat_val.lower() == "passer":
                    stat_val = "Passed"
                expiration_or_status = stat_val

        # 4. Credential ID or Details
        details_list: List[str] = []

        # License / Reg / Cert / Validation ID
        m_id = re.search(
            r'\b(?:(?:PRC\s+License|License|Reg(?:\.|istration)?|Cert(?:\.|ificate)?)\s*(?:No\.?|ID|#)|(?:Validation|License|Certificate|Cert)\s*(?:ID|#)?\s*[:\-])\s*[:\-]?\s*([A-Za-z0-9\-_/]+)',
            text_context, re.IGNORECASE
        )
        if m_id:
            details_list.append(m_id.group(0).strip())

        # Rating (e.g. Rating: 85.60%)
        m_rating = re.search(r'\bRating\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,4})?%?)', text_context, re.IGNORECASE)
        if m_rating:
            details_list.append(m_rating.group(0).strip())

        # LTO Restriction / DL Codes
        m_restr = re.search(
            r'\bRestriction(?:\s*Codes?)?\s*([0-9,\s]+(?:\s*/\s*DL\s*Codes?\s*[A-Za-z0-9,\s]+)?)',
            text_context, re.IGNORECASE
        )
        if m_restr:
            details_list.append(m_restr.group(0).strip())

        # Training Hours (e.g. 24 Hours, 40 Hours)
        m_hours = re.search(r'\b(\d+\s*Hours?)\b', text_context, re.IGNORECASE)
        if m_hours:
            details_list.append(m_hours.group(1).strip())

        details = " | ".join(details_list) if details_list else None
        return issuer, issue_date, expiration_or_status, details

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Executes the 4-layer extraction pipeline on the resume text.
        Returns full structured dictionary complying with the required JSON schema.
        """
        if not text or not text.strip():
            return {
                "total_certifications_count": 0,
                "summary_by_category": {
                    "prc_and_government_licenses": 0,
                    "tesda_national_certificates": 0,
                    "safety_and_compliance_certs": 0,
                    "it_and_professional_certs": 0,
                    "seminars_and_training_certificates": 0
                },
                "certifications": []
            }

        extracted_map: Dict[str, Dict[str, Any]] = {}
        lines = text.split('\n')

        # ── Layer 0: Post-Nominals in Resume Header ───────────────────────────
        for idx, line in enumerate(lines[:6]):
            m_post = re.search(r'\b(?:Engr\.|Arch\.|Dr\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),\s*([A-Z,\s/]+)\b', line)
            if m_post:
                titles = [t.strip().upper() for t in re.split(r'[,/]', m_post.group(2)) if t.strip()]
                for t in titles:
                    if t in _POST_NOMINAL_MAP:
                        canonical = _POST_NOMINAL_MAP[t]
                        meta = self.taxonomy.get(canonical, {})
                        extracted_map[canonical] = {
                            "canonical_name": canonical,
                            "raw_text": line.strip(),
                            "category": meta.get("category", "PRC / Government License"),
                            "issuing_organization": meta.get("default_issuer", "PRC"),
                            "issue_date": None,
                            "expiration_or_status": "Active",
                            "credential_id_or_details": f"Post-nominal {t}",
                            "source_section": "Header",
                            "extraction_method": "Regex_Pattern",
                            "confidence_score": 0.96
                        }

        # ── Document Line Traversal (Layers 1, 2, 3, 4) ───────────────────────
        current_section = "Header"
        dual_cols: Optional[Tuple[str, str]] = None
        cert_col_idx: Optional[int] = None

        for idx, line in enumerate(lines):
            clean_line = line.strip()
            if not clean_line:
                continue

            hdr_sec, inline_content, dual_hdr = parse_header_line(clean_line, current_section)
            if dual_hdr:
                dual_cols = dual_hdr
                cert_col_idx = (
                    0 if dual_hdr[0] in _CERT_SECTIONS else (1 if dual_hdr[1] in _CERT_SECTIONS else None)
                )
                current_section = dual_hdr[cert_col_idx] if cert_col_idx is not None else dual_hdr[0]
                continue

            if hdr_sec:
                dual_cols = None
                cert_col_idx = None
                current_section = hdr_sec
                if not inline_content:
                    continue
                target_line = inline_content
                sec = hdr_sec
            else:
                if dual_cols is not None and '|' in clean_line and '@' not in clean_line:
                    parts = [p.strip() for p in clean_line.split('|')]
                    if len(parts) == 2:
                        if cert_col_idx is not None:
                            target_line = parts[cert_col_idx]
                            sec = dual_cols[cert_col_idx]
                            if not target_line:
                                continue
                        else:
                            target_line = clean_line
                            sec = dual_cols[0]
                    else:
                        target_line = clean_line
                        sec = dual_cols[cert_col_idx] if cert_col_idx is not None else current_section
                else:
                    if idx > 5 and current_section == "Header" and dual_cols is None:
                        current_section = "General"
                    target_line = clean_line
                    sec = dual_cols[cert_col_idx] if (dual_cols and cert_col_idx is not None) else current_section

            in_cert_section = sec in _CERT_SECTIONS

            line_year: Optional[str] = None
            if in_cert_section:
                m_lead_yr = _LEADING_YEAR_RE.match(target_line)
                if m_lead_yr:
                    line_year = m_lead_yr.group(1)
                    target_line = m_lead_yr.group(2).strip()

            items = split_compound_cert_line(target_line, in_cert_section=in_cert_section)

            for item in items:
                if _NON_ITEM_METADATA_RE.match(item) or _PURE_DATE_OR_YEAR_RE.match(item):
                    continue

                matched_for_item = False

                # ── Layer 1: Gazetteer & Ontology Matching ────────────────
                # 1a. FlashText exact match
                if self.keyword_processor is not None:
                    kw_matches = self.keyword_processor.extract_keywords(item)
                    if kw_matches:
                        for canonical in kw_matches:
                            meta = self.taxonomy.get(canonical, {})
                            iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                            if not dt and target_line != item:
                                _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                                dt = line_dt
                            dt = dt or line_year
                            if not iss:
                                iss = meta.get("default_issuer")

                            self._merge_or_add_entry(
                                extracted_map=extracted_map,
                                canonical=canonical,
                                raw_text=item,
                                category=meta.get("category", "Seminar / Training Certificate"),
                                issuer=iss or "Professional Organization",
                                issue_date=dt,
                                expiration=exp,
                                details=det,
                                source_section=sec,
                                method="Gazetteer_Exact",
                                confidence=0.98
                            )
                            matched_for_item = True

                # 1b. spaCy EntityRuler match (if FlashText missed)
                if not matched_for_item and self.spacy_nlp is not None:
                    try:
                        doc = self.spacy_nlp(item)
                        for ent in doc.ents:
                            if ent.label_ == "CERT" and ent.ent_id_:
                                canonical = ent.ent_id_
                                meta = self.taxonomy.get(canonical, {})
                                iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                                if not dt and target_line != item:
                                    _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                                    dt = line_dt
                                dt = dt or line_year
                                self._merge_or_add_entry(
                                    extracted_map=extracted_map,
                                    canonical=canonical,
                                    raw_text=item,
                                    category=meta.get("category", "Seminar / Training Certificate"),
                                    issuer=iss or meta.get("default_issuer", "Professional Organization"),
                                    issue_date=dt,
                                    expiration=exp,
                                    details=det,
                                    source_section=sec,
                                    method="Gazetteer_Exact",
                                    confidence=0.97
                                )
                                matched_for_item = True
                    except Exception:
                        pass

                # 1c. RapidFuzz Near-Match (for typos inside cert sections)
                if not matched_for_item and fuzz and process and in_cert_section:
                    best = process.extractOne(
                        item,
                        list(self.taxonomy.keys()),
                        scorer=fuzz.token_sort_ratio
                    )
                    if best and best[1] >= 89.0:
                        canonical = best[0]
                        meta = self.taxonomy.get(canonical, {})
                        iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                        if not dt and target_line != item:
                            _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                            dt = line_dt
                        dt = dt or line_year
                        self._merge_or_add_entry(
                            extracted_map=extracted_map,
                            canonical=canonical,
                            raw_text=item,
                            category=meta.get("category", "Seminar / Training Certificate"),
                            issuer=iss or meta.get("default_issuer", "Professional Organization"),
                            issue_date=dt,
                            expiration=exp,
                            details=det,
                            source_section=sec,
                            method="Gazetteer_Exact",
                            confidence=0.94
                        )
                        matched_for_item = True

                if matched_for_item:
                    continue

                # ── Layer 2: Dynamic Regex Catchers ───────────────────────
                # 2a. Dynamic TESDA NC / COC
                m_coc_prefix = re.search(
                    r'(?:TESDA\s+)?Certificate\s+of\s+Competency\s+(?:in\s+)?([A-Za-z0-9\s/&,()\-]+?)(?:\s*\(|$)',
                    item, re.IGNORECASE
                )
                m_tesda = re.search(
                    r'(?:TESDA\s+)?([A-Za-z0-9\s/&,()\-]+?)\s*(NC\s*(?:I|II|III|IV)|National\s*Certificate\s*(?:I|II|III|IV)|COC(?:\s*\d+)?|Certificate\s*of\s*Competency)\b',
                    item, re.IGNORECASE
                )
                if m_coc_prefix or m_tesda:
                    if m_coc_prefix:
                        trade = m_coc_prefix.group(1).strip().strip("-:,")
                        canonical = f"TESDA COC in {trade.title()}"
                    else:
                        trade = m_tesda.group(1).strip().strip("-:,")
                        level = m_tesda.group(2).strip().upper()
                        level = re.sub(r'NATIONAL\s*CERTIFICATE', 'NC', level, flags=re.IGNORECASE)
                        canonical = f"{trade.title()} {level}"
                    iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                    if not dt and target_line != item:
                        _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                        dt = line_dt
                    dt = dt or line_year
                    self._merge_or_add_entry(
                        extracted_map=extracted_map,
                        canonical=canonical,
                        raw_text=item,
                        category="TESDA National Certificate",
                        issuer=iss or "TESDA",
                        issue_date=dt,
                        expiration=exp,
                        details=det,
                        source_section=sec,
                        method="Regex_Pattern",
                        confidence=0.95
                    )
                    matched_for_item = True
                    continue

                # 2b. Dynamic PRC / Board Exam
                m_prc = re.search(
                    r'(?:PRC\s+)?(?:Registered|Licensed)?\s*([A-Za-z\s]+?)(?:Board\s*Exam(?:ination)?\s*Passer|Licensure\s*Exam(?:ination)?\s*Passer)\b',
                    item, re.IGNORECASE
                )
                if m_prc:
                    field = m_prc.group(1).strip().title()
                    canonical = f"PRC Licensed {field}"
                    iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                    if not dt and target_line != item:
                        _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                        dt = line_dt
                    dt = dt or line_year
                    self._merge_or_add_entry(
                        extracted_map=extracted_map,
                        canonical=canonical,
                        raw_text=item,
                        category="PRC / Government License",
                        issuer=iss or "PRC",
                        issue_date=dt,
                        expiration=exp or "Passed",
                        details=det,
                        source_section=sec,
                        method="Regex_Pattern",
                        confidence=0.95
                    )
                    matched_for_item = True
                    continue

                # 2c. Dynamic Civil Service / Government Eligibility
                m_csc = re.search(
                    r'(?:Civil\s+Service|Career\s+Service)\s+(Professional|Sub-?Professional)(?:\s+(?:Eligib(?:le|ility)|Exam(?:ination)?(?:\s+Passer)?))?',
                    item, re.IGNORECASE
                )
                if m_csc:
                    sub = m_csc.group(1).title()
                    canonical = f"Civil Service {sub} Eligibility"
                    iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                    if not dt and target_line != item:
                        _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                        dt = line_dt
                    dt = dt or line_year
                    self._merge_or_add_entry(
                        extracted_map=extracted_map,
                        canonical=canonical,
                        raw_text=item,
                        category="PRC / Government License",
                        issuer=iss or "Civil Service Commission",
                        issue_date=dt,
                        expiration=exp or "Passed",
                        details=det,
                        source_section=sec,
                        method="Regex_Pattern",
                        confidence=0.95
                    )
                    matched_for_item = True
                    continue

                # 2d. Dynamic Online & Training Bootcamp Certificate
                m_boot = re.search(
                    r'\b(Certificate\s+of\s+(?:Completion|Participation|Attendance|Achievement|Excellence|Appreciation|Recognition|Training|Merit)|Certified\s+in|Certificate\s+in)\s+(?:in\s+)?'
                    r'([^.\n|;()]+)',
                    item, re.IGNORECASE
                )
                if m_boot:
                    prefix_raw = re.sub(r'\s+', ' ', m_boot.group(1).strip())
                    raw_rest = m_boot.group(2).strip()
                    cand_provider: Optional[str] = None
                    m_org = re.search(
                        r'\s+(?:[-–—|]|issued\s+by|by|from|via|at)\s+([A-Za-z0-9\s&.,\-]+)$',
                        raw_rest, re.IGNORECASE
                    )
                    if m_org:
                        c_title = raw_rest[:m_org.start()].strip("()-: ")
                        cand_provider = m_org.group(1).strip()
                    else:
                        c_title = raw_rest.strip("()-: ")

                    c_title = re.sub(r'^(?:in|for|on)\s+', '', c_title, flags=re.IGNORECASE).strip()
                    if len(c_title) >= 3:
                        if c_title.islower():
                            c_title = c_title.title()
                        if prefix_raw.lower().startswith("certificate in"):
                            canonical = f"Certificate in {c_title}"
                        elif prefix_raw.lower().startswith("certified in"):
                            canonical = f"Certified in {c_title}"
                        else:
                            canonical = f"{prefix_raw.title().replace(' Of ', ' of ')} in {c_title}"

                        iss, dt, exp, det = self._extract_metadata_from_context(item, canonical)
                        if not dt and target_line != item:
                            _, line_dt, _, _ = self._extract_metadata_from_context(target_line, canonical)
                            dt = line_dt
                        dt = dt or line_year
                        if cand_provider and len(cand_provider) > 2 and not any(w in cand_provider.lower() for w in ["hours", "rating", "valid"]):
                            iss = cand_provider

                        self._merge_or_add_entry(
                            extracted_map=extracted_map,
                            canonical=canonical,
                            raw_text=item,
                            category="Seminar / Training Certificate",
                            issuer=iss or "Training Provider",
                            issue_date=dt,
                            expiration=exp or "Active",
                            details=det,
                            source_section=sec,
                            method="Regex_Pattern",
                            confidence=0.92
                        )
                        matched_for_item = True
                        continue

                # ── Layer 3: Item-Level Fallback Extractor Inside Cert Sections ─
                if not matched_for_item and in_cert_section:
                    clean_item = _strip_list_prefix(item)
                    m_item_yr = _LEADING_YEAR_RE.match(clean_item)
                    item_year = line_year
                    if m_item_yr:
                        item_year = m_item_yr.group(1)
                        clean_item = m_item_yr.group(2).strip()

                    if _NON_ITEM_METADATA_RE.match(clean_item) or _PURE_DATE_OR_YEAR_RE.match(clean_item):
                        continue

                    clean_title = re.sub(r'\s*\([^)]*\)', '', clean_item).strip()
                    clean_title = re.split(r'\s+[-–—]\s+', clean_title, maxsplit=1)[0].strip()
                    if len(clean_title) < 3 or _NON_ITEM_METADATA_RE.match(clean_title) or _PURE_DATE_OR_YEAR_RE.match(clean_title):
                        continue

                    iss, dt, exp, det = self._extract_metadata_from_context(clean_item, clean_title)
                    if not dt and target_line != item:
                        _, line_dt, _, _ = self._extract_metadata_from_context(target_line, clean_title)
                        dt = line_dt
                    dt = dt or item_year

                    cat = "Seminar / Training Certificate"
                    low_item = clean_item.lower()
                    if any(w in low_item for w in ["safety", "bosh", "cosh", "iso", "hazard", "risk", "osha", "first aid", "bls", "haccp"]):
                        cat = "Safety & Compliance"
                    elif any(w in low_item for w in ["board", "prc", "csc", "license", "eligibility", "passed"]):
                        cat = "PRC / Government License"
                    elif any(w in low_item for w in ["tesda", "nc i", "nc ii", "nc iii", "nc iv", "national certificate", "coc"]):
                        cat = "TESDA National Certificate"
                    elif any(w in low_item for w in ["aws", "azure", "google", "cloud", "cisco", "python", "developer", "engineer"]):
                        cat = "IT & Professional Certification"

                    self._merge_or_add_entry(
                        extracted_map=extracted_map,
                        canonical=clean_title,
                        raw_text=clean_item,
                        category=cat,
                        issuer=iss or "Seminar / Training Provider",
                        issue_date=dt,
                        expiration=exp or "Active",
                        details=det,
                        source_section=sec,
                        method="Section_Bullet_Parse",
                        confidence=0.85
                    )

        # ── Output Formatting & Summary Aggregation ───────────────────────────
        final_certs = list(extracted_map.values())
        final_certs.sort(key=lambda x: (x["category"], x["canonical_name"]))

        summary = {
            "prc_and_government_licenses": len([c for c in final_certs if c["category"] == "PRC / Government License"]),
            "tesda_national_certificates": len([c for c in final_certs if c["category"] == "TESDA National Certificate"]),
            "safety_and_compliance_certs": len([c for c in final_certs if c["category"] == "Safety & Compliance"]),
            "it_and_professional_certs": len([c for c in final_certs if c["category"] == "IT & Professional Certification"]),
            "seminars_and_training_certificates": len([c for c in final_certs if c["category"] == "Seminar / Training Certificate"])
        }

        return {
            "total_certifications_count": len(final_certs),
            "summary_by_category": summary,
            "certifications": final_certs
        }

    def _merge_or_add_entry(
        self,
        extracted_map: Dict[str, Dict[str, Any]],
        canonical: str,
        raw_text: str,
        category: str,
        issuer: Optional[str],
        issue_date: Optional[str],
        expiration: Optional[str],
        details: Optional[str],
        source_section: str,
        method: str,
        confidence: float
    ):
        """Intelligently merges duplicate or related credential entries keeping the richest details."""
        if canonical not in extracted_map:
            extracted_map[canonical] = {
                "canonical_name": canonical,
                "raw_text": raw_text,
                "category": category,
                "issuing_organization": issuer or "Professional Organization",
                "issue_date": issue_date,
                "expiration_or_status": expiration,
                "credential_id_or_details": details,
                "source_section": source_section,
                "extraction_method": method,
                "confidence_score": confidence
            }
        else:
            existing = extracted_map[canonical]
            if details:
                current_det = existing.get("credential_id_or_details")
                if not current_det:
                    existing["credential_id_or_details"] = details
                else:
                    existing_chunks = [c.strip() for c in current_det.split("|")]
                    new_chunks = [c.strip() for c in details.split("|")]
                    for nc in new_chunks:
                        if nc and not any(nc.lower() == ec.lower() for ec in existing_chunks):
                            existing_chunks.append(nc)
                    existing["credential_id_or_details"] = " | ".join(existing_chunks)
            if issue_date and not existing.get("issue_date"):
                existing["issue_date"] = issue_date
            if expiration:
                if not existing.get("expiration_or_status") or existing.get("expiration_or_status") == "Active":
                    existing["expiration_or_status"] = expiration
            if issuer and (not existing.get("issuing_organization") or existing.get("issuing_organization") in {"Professional Organization", "PRC"}):
                existing["issuing_organization"] = issuer
            if confidence > existing.get("confidence_score", 0):
                existing["confidence_score"] = confidence
                existing["extraction_method"] = method
            if existing.get("source_section") == "Header" and source_section in {"Certifications", "Eligibility", "Seminars & Trainings"}:
                existing["source_section"] = source_section
                existing["raw_text"] = raw_text


# ─── Public API Functions ──────────────────────────────────────────────────────

_GLOBAL_EXTRACTOR: Optional[PhilippineCertificationsExtractor] = None


def get_certifications_extractor() -> PhilippineCertificationsExtractor:
    """Singleton getter for the Philippine certifications extraction engine."""
    global _GLOBAL_EXTRACTOR
    if _GLOBAL_EXTRACTOR is None:
        _GLOBAL_EXTRACTOR = PhilippineCertificationsExtractor()
    return _GLOBAL_EXTRACTOR


def extract_structured_certifications(text: str) -> Dict[str, Any]:
    """
    Extracts structured certifications conforming to the expected JSON schema.
    """
    extractor = get_certifications_extractor()
    return extractor.extract(text)


def extract_certifications(text: str) -> str:
    """
    Backward-compatible pipe-separated certifications string.
    """
    result = extract_structured_certifications(text)
    certs = result.get("certifications", [])
    if not certs:
        return ""
    names = [c["canonical_name"] for c in certs]
    return " | ".join(names[:25])


# ─── Demonstration & Test Block ────────────────────────────────────────────────

if __name__ == "__main__":
    extractor = get_certifications_extractor()

    resume_1_blue_collar = """
ALEXANDER BAUTISTA
Calamba City, Laguna | 09171234567 | alex.bautista@gmail.com

CERTIFICATIONS & LICENSES
- TESDA Food and Beverage Services NC II & Bread and Pastry Production NC II (Issued: June 2022)
- Housekeeping NC II - TESDA Rizal Provincial Training Center (Cert No. 22040102001, Issued: 2021)
- LTO Professional Driver's License (Restriction 1, 2, 3 / DL Code A, B) - Valid until 2028
- Standard First Aid and Basic Life Support (BLS) - Philippine Red Cross (24 Hours, 2023)
- PNP-SOSIA Security Guard License (License No. SG-8891234, Active)
"""

    resume_2_engineering = """
Engr. Juanito Dela Cruz, RCE, RMP
Makati City, Metro Manila | 09171234567 | jdelacruz.ce@gmail.com

LICENSES AND ELIGIBILITY
- PRC Registered Civil Engineer (Civil Engineering Board Exam Passer, Rating: 85.60%, PRC License No. 0154321)
- PRC Registered Master Plumber (Master Plumber Licensure Examination Passer, Reg. No. 008921)
- Basic Occupational Safety and Health for SO2 (BOSH SO2) - DOLE-BWC Accredited (40 Hours, 2023)
- Construction Occupational Safety and Health (COSH Certified, Safety Officer 2)
- ISO 9001:2015 Quality Management System Internal Auditor - TUV Rheinland
- Autodesk Certified Professional: AutoCAD for Civil Engineering
"""

    resume_3_bpo_admin = """
CLARISSE MENDOZA
Quezon City, Metro Manila | 09181234567 | clarisse.mendoza@gmail.com

ELIGIBILITY & PROFESSIONAL CERTIFICATIONS
- Career Service Professional Eligibility (Civil Service Commission, Rating: 86.42%, Passed March 2021)
- Honor Graduate Eligibility (PD 907) - Civil Service Commission
- Microsoft Office Specialist: Excel Associate (MOS Excel 2019 Certified) - Certiport
- Lean Six Sigma Yellow Belt Certification (SSYB) - Six Sigma PH (2022)
- Certified Customer Service Professional (CCSP)

SEMINARS & TRAININGS ATTENDED
- Effective Business Writing and Executive Correspondence Workshop (16 Hours, 2023)
- Conflict De-escalation & Complaint Handling Masterclass - BPO Academy
- Records Management and 201 File Maintenance Training - National Archives of the Philippines
"""

    resume_4_dev_it = """
ALEXANDER REYES
Taguig City, Metro Manila | alex.reyes@gmail.com

CERTIFICATIONS & CREDENTIALS
- AWS Certified Solutions Architect - Associate (Validation: AWS-SAA-908123, Valid until Nov 2026)
- Certified Kubernetes Administrator (CKA) - Cloud Native Computing Foundation / Linux Foundation
- Cisco Certified Network Associate (CCNA 200-301) - Cisco Systems (Active)
- HashiCorp Certified: Terraform Associate (003)

TRAININGS & BOOTCAMPS
- Certificate of Completion in Java Web Development Bootcamp - Ground Gurus (120 Hours, 2023)
- Certificate of Participation in Reactive Microservices with Spring Boot - PCI Innovations
- Sololearn Python Intermediate Certification (Certificate ID: SL-778899)
- FreeCodeCamp Responsive Web Design Certification
"""

    resumes = [
        ("Resume 1: Blue-Collar & Service Worker (TESDA, LTO, Red Cross, SOSIA)", resume_1_blue_collar),
        ("Resume 2: Civil Engineering & Construction Safety (PRC, DOLE OSH, ISO, AutoCAD)", resume_2_engineering),
        ("Resume 3: BPO, Admin & Government (CSC Eligibility, PD 907, MOS, Six Sigma)", resume_3_bpo_admin),
        ("Resume 4: Software Developer & Cloud Infrastructure (AWS, CKA, CCNA, Bootcamps)", resume_4_dev_it),
    ]

    for title, resume_text in resumes:
        print(f"\n{'='*80}\n{title}\n{'='*80}")
        result = extractor.extract(resume_text)
        print(f"Total Certifications Extracted: {result['total_certifications_count']}")
        print(f"Summary by Category:\n{json.dumps(result['summary_by_category'], indent=2)}")
        print("\nExtracted Certifications:")
        for c in result["certifications"]:
            print(f"  • [{c['category']}] {c['canonical_name']}")
            print(f"    - Raw: '{c['raw_text']}'")
            print(f"    - Issuer: {c['issuing_organization']} | Issue Date: {c['issue_date']} | Status: {c['expiration_or_status']}")
            print(f"    - Details: {c['credential_id_or_details']} | Method: {c['extraction_method']} (Conf: {c['confidence_score']})")
