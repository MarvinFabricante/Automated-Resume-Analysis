"""Central NLP engine for resume preprocessing and extraction.

This module is the single entry point for spaCy-based preprocessing,
NER, and rule-based extraction used by the resume pipeline. All resume
text should be passed through `extract_all()` to obtain normalized
text, named entities, and extracted structured fields.

No LLMs are used here; all processing is spaCy + rule-based.
"""
import logging
import re
from functools import lru_cache
from typing import Dict, Any, List, Optional

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher, Matcher
from spacy.tokens import Doc


def _normalize_text(text: str) -> str:
    # Basic normalization: collapse whitespace, remove excessive punctuation noise
    t = text or ""
    t = t.replace('\r', '\n')
    t = re.sub(r"\u2013|\u2014", '-', t)  # normalize dashes
    t = re.sub(r"\t+", ' ', t)
    t = re.sub(r"[^\S\n]+", ' ', t)
    # Collapse multiple newlines into single newline
    t = re.sub(r"\n+", '\n', t)
    t = t.strip()
    return t


def extract_advanced_skills(doc: Doc) -> list[str]:
    from app.extractors.content.skills_extractor import _format_skill
    skills_matcher = get_skills_matcher()
    skills = find_phrase_matches(doc, skills_matcher)
    
    formatted_skills = []
    seen = set()
    for s in skills:
        f = _format_skill(s)
        if f and f.upper() not in seen:
            seen.add(f.upper())
            formatted_skills.append(f)
    return formatted_skills


def extract_advanced_experience(doc: Doc) -> list[str]:
    entries = []
    job_matcher = get_job_title_matcher()
    
    matches = job_matcher(doc)
    match_spans = spacy.util.filter_spans([doc[start:end] for match_id, start, end in matches])
    
    # Filter out common section headers from ORGs
    bad_orgs = {"EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "SKILLS", "SUMMARY", "PROJECTS", "CONTACT", "AWARDS", "LANGUAGES", "PROFILE", "ABOUT", "ABOUT ME", "REFERENCES", "EMPLOYMENT", "WORK EXPERIENCE"}
    orgs = [(ent.text.strip(), ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == 'ORG' and ent.text.strip().upper() not in bad_orgs]
    dates = [(ent.text.strip(), ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == 'DATE']
    
    for m in re.finditer(r'\b(?:\d{4}|present|current|\w{3,9}\s+\d{4}|\d{1,2}/\d{4})\b', doc.text, re.I):
        dates.append((m.group(0), m.start(), m.end()))
        
    for span in match_spans:
        title = span.text.strip().replace('\n', ' ')
        
        closest_org = None
        min_dist_org = 120
        for org_text, start, end in orgs:
            dist = min(abs(start - span.end_char), abs(span.start_char - end))
            if dist < min_dist_org:
                min_dist_org = dist
                closest_org = org_text.replace('\n', ' ')
                
        closest_date = None
        min_dist_date = 120
        for date_text, start, end in dates:
            dist = min(abs(start - span.end_char), abs(span.start_char - end))
            if dist < min_dist_date:
                min_dist_date = dist
                closest_date = date_text.replace('\n', ' ')
                
        entry_parts = [title]
        if closest_org:
            entry_parts.append(f"at {closest_org}")
        if closest_date:
            entry_parts.append(f"({closest_date})")
            
        entry = " ".join(entry_parts).strip()
        if entry and entry not in entries:
            entries.append(entry)
            
    return entries[:10]


def extract_advanced_education(doc: Doc) -> list[str]:
    entries = []
    degree_matcher = get_degree_matcher()
    
    matches = degree_matcher(doc)
    match_spans = spacy.util.filter_spans([doc[start:end] for match_id, start, end in matches])
    
    bad_orgs = {"EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "SKILLS", "SUMMARY", "PROJECTS", "CONTACT", "AWARDS", "LANGUAGES", "PROFILE", "ABOUT", "ABOUT ME", "REFERENCES", "EMPLOYMENT", "WORK EXPERIENCE"}
    orgs = [(ent.text.strip(), ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == 'ORG' and ent.text.strip().upper() not in bad_orgs]
    
    for m in re.finditer(r'\b((?:[A-Z][a-z]+\s+)+(?:University|College|Institute)(?:\s+of\s+[A-Z][a-z]+)?)\b', doc.text):
        org = m.group(1).strip()
        if org.upper() not in bad_orgs:
            orgs.append((org, m.start(), m.end()))
        
    dates = [(ent.text.strip(), ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == 'DATE']
    for m in re.finditer(r'\b(?:\d{4})\b', doc.text):
        dates.append((m.group(0), m.start(), m.end()))
    
    for span in match_spans:
        degree = span.text.strip().replace('\n', ' ')
        
        closest_org = None
        min_dist_org = 150
        for org_text, start, end in orgs:
            dist = min(abs(start - span.end_char), abs(span.start_char - end))
            if dist < min_dist_org:
                min_dist_org = dist
                closest_org = org_text.replace('\n', ' ')
                
        closest_date = None
        min_dist_date = 100
        for date_text, start, end in dates:
            dist = min(abs(start - span.end_char), abs(span.start_char - end))
            if dist < min_dist_date:
                min_dist_date = dist
                closest_date = date_text.replace('\n', ' ')
                
        entry_parts = [degree]
        if closest_org:
            entry_parts.append(f"from {closest_org}")
        if closest_date:
            entry_parts.append(f"({closest_date})")
            
        entry = " ".join(entry_parts).strip()
        if entry and entry not in entries:
            entries.append(entry)
            
    return entries[:5]


def extract_advanced_certifications(doc: Doc) -> list[str]:
    cert_matcher = get_cert_matcher()
    certs = find_phrase_matches(doc, cert_matcher)
    
    for sent in doc.sents:
        s = sent.text.strip()
        if re.search(r'\b(certified|certificate|certification)\b', s, re.I):
            m = re.search(r'(?i)(?:certified in|certificate in|certification for)\s+([A-Z][a-z0-9\s]+(?:[A-Z][a-z0-9\s]+)?)', s)
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in [c.lower() for c in certs] and len(cand) > 3:
                    certs.append(cand)
    return list(set(certs))


def extract_all(text: str) -> Dict[str, Any]:
    """Preprocess text with spaCy, run extractors, and return structured output."""
    clean = _normalize_text(text)
    doc = get_doc(clean)

    skills = extract_advanced_skills(doc)
    experience = extract_advanced_experience(doc)
    education = extract_advanced_education(doc)
    certifications = extract_advanced_certifications(doc)

    entities = [(ent.text, ent.label_) for ent in doc.ents]

    return {
        "clean_text": clean,
        "doc": doc,
        "skills": skills,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "entities": entities,
    }
"""
spaCy NLP Engine — Singleton Loader & Shared Utilities
──────────────────────────────────────────────────────
Loads the spaCy model ONCE and exposes:
  • get_nlp()           → the Language pipeline
  • get_doc(text)       → a processed Doc (cached per text hash)
  • get_skills_matcher()→ PhraseMatcher pre-loaded with the skills KB
  • get_cert_matcher()  → PhraseMatcher pre-loaded with known certs
  • get_job_title_matcher() → Matcher for job title token patterns
  • get_degree_matcher()→ PhraseMatcher for degree terms
  • get_ner_entities()  → convenience wrapper for NER extraction
  • extract_noun_chunks → extract meaningful noun chunks from text
  • find_phrase_matches()→ run a PhraseMatcher and return matched strings

All matchers use the LOWER attribute so matching is case-insensitive.
"""

logger = logging.getLogger(__name__)

# ─── Singleton NLP Pipeline ──────────────────────────────────────────────────

_nlp: Optional[Language] = None


def get_nlp() -> Language:
    """Return the shared spaCy Language pipeline (lazy singleton)."""
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy model 'en_core_web_sm'...")
        _nlp = spacy.load("en_core_web_sm", disable=[])
        # Increase max_length for very large resumes
        _nlp.max_length = 500_000
        logger.info("spaCy model loaded successfully.")
    return _nlp


def get_doc(text: str) -> Doc:
    """
    Process text through the spaCy pipeline and return a Doc.
    Uses lru_cache keyed on the hash of the text to avoid
    re-processing the same resume text multiple times.
    """
    return _get_doc_cached(hash(text), text)


@lru_cache(maxsize=8)
def _get_doc_cached(text_hash: int, text: str) -> Doc:
    """Cache processed Docs by their hash to avoid re-processing."""
    nlp = get_nlp()
    # Clean text before processing
    cleaned = _preprocess_text(text)
    return nlp(cleaned)


def _preprocess_text(text: str) -> str:
    """
    Light preprocessing before spaCy ingestion.
    Normalizes whitespace and removes control characters
    while preserving newlines for section detection.
    """
    # Replace tabs with spaces
    text = text.replace('\t', '  ')
    # Collapse multiple spaces (not newlines) into single space
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Remove null bytes and other control chars except \n
    text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


# ─── Skills PhraseMatcher ────────────────────────────────────────────────────

_skills_matcher: Optional[PhraseMatcher] = None


def get_skills_matcher() -> PhraseMatcher:
    """
    Return a PhraseMatcher pre-loaded with the skills knowledge base.
    Uses LOWER attribute for case-insensitive matching.
    Built once, then cached.
    """
    global _skills_matcher
    if _skills_matcher is None:
        _skills_matcher = _build_skills_matcher()
    return _skills_matcher


def _build_skills_matcher() -> PhraseMatcher:
    """Build the skills PhraseMatcher from the knowledge base."""
    from app.extractors.content.skills_extractor import COMMON_SKILLS

    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    # Process skills in batches for efficiency
    patterns = []
    skill_list = list(COMMON_SKILLS)

    for skill in skill_list:
        # Create a doc pattern for each skill
        pattern_doc = nlp.make_doc(skill.lower())
        patterns.append(pattern_doc)

    if patterns:
        matcher.add("SKILLS_KB", patterns)

    logger.info(f"Skills PhraseMatcher built with {len(patterns)} patterns.")
    return matcher


# ─── Certifications PhraseMatcher ────────────────────────────────────────────

_cert_matcher: Optional[PhraseMatcher] = None

# Well-known certification names for phrase matching
_CERT_PHRASES = [
    # Cloud
    "AWS Certified Solutions Architect", "AWS Certified Developer",
    "AWS Certified SysOps Administrator", "AWS Certified DevOps Engineer",
    "AWS Cloud Practitioner", "AWS Certified Cloud Practitioner",
    "Azure Administrator", "Azure Developer Associate",
    "Azure Solutions Architect", "Azure Fundamentals",
    "Azure Data Engineer", "Azure AI Engineer",
    "Google Cloud Professional Cloud Architect",
    "Google Cloud Professional Data Engineer",
    "Google Cloud Associate Cloud Engineer",
    "Certified Kubernetes Administrator", "CKA", "CKAD", "CKS",
    # Programming / Dev
    "Oracle Certified Professional", "Oracle Certified Associate",
    "Microsoft Certified Professional", "Microsoft Certified Developer",
    "Certified Scrum Master", "CSM", "Certified Scrum Developer",
    "Certified Scrum Product Owner", "CSPO",
    "Project Management Professional", "PMP",
    "PRINCE2 Foundation", "PRINCE2 Practitioner",
    "ITIL Foundation", "ITIL Practitioner",
    # Data / AI
    "TensorFlow Developer Certificate",
    "Databricks Certified", "Snowflake SnowPro",
    "Google Data Analytics Certificate",
    "IBM Data Science Professional Certificate",
    "SAS Certified", "Tableau Desktop Specialist",
    # Security
    "CISSP", "CISM", "CEH", "Certified Ethical Hacker",
    "CompTIA Security+", "CompTIA A+", "CompTIA Network+",
    "CompTIA Cloud+", "CompTIA Linux+", "CompTIA CySA+",
    "OSCP", "GIAC",
    # Networking
    "CCNA", "CCNP", "CCIE",
    "Cisco Certified Network Associate",
    "Cisco Certified Network Professional",
    # Agile
    "SAFe Agilist", "SAFe Practitioner", "SAFe Scrum Master",
    "Lean Six Sigma Green Belt", "Lean Six Sigma Black Belt",
    "Six Sigma Yellow Belt", "Six Sigma White Belt",
    "PMI-ACP",
    # Philippine-specific
    "Civil Service Eligibility", "Civil Service Professional",
    "Board Passer", "PRC License",
    "Certified Public Accountant", "CPA",
    "Registered Nurse", "Licensed Professional Engineer",
]


def get_cert_matcher() -> PhraseMatcher:
    """Return a PhraseMatcher pre-loaded with known certifications."""
    global _cert_matcher
    if _cert_matcher is None:
        _cert_matcher = _build_cert_matcher()
    return _cert_matcher


def _build_cert_matcher() -> PhraseMatcher:
    """Build the certifications PhraseMatcher."""
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    patterns = []
    for cert in _CERT_PHRASES:
        pattern_doc = nlp.make_doc(cert.lower())
        patterns.append(pattern_doc)

    if patterns:
        matcher.add("CERTS_KB", patterns)

    logger.info(f"Cert PhraseMatcher built with {len(patterns)} patterns.")
    return matcher


# ─── Job Title Matcher (Token Patterns) ──────────────────────────────────────

_job_title_matcher: Optional[Matcher] = None

_SENIORITY = ["senior", "junior", "lead", "principal", "staff", "chief",
              "head", "associate", "assistant", "vice", "deputy", "executive"]

_DOMAIN = ["software", "web", "frontend", "backend", "fullstack", "full-stack",
           "mobile", "cloud", "data", "devops", "qa", "systems", "network",
           "security", "database", "platform", "infrastructure", "product",
           "program", "project", "technical", "it", "information", "digital",
           "business", "marketing", "sales", "operations", "machine", "learning",
           "human", "financial", "customer", "application", "solutions"]

_TITLE = ["engineer", "developer", "designer", "manager", "analyst",
          "specialist", "consultant", "director", "administrator",
          "coordinator", "architect", "scientist", "officer",
          "supervisor", "technician", "programmer", "tester",
          "intern", "trainer", "instructor", "accountant", "auditor",
          "representative", "strategist", "planner"]


def get_job_title_matcher() -> Matcher:
    """Return a spaCy Matcher for common job title token patterns."""
    global _job_title_matcher
    if _job_title_matcher is None:
        _job_title_matcher = _build_job_title_matcher()
    return _job_title_matcher


def _build_job_title_matcher() -> Matcher:
    """Build the job title Matcher with token patterns."""
    nlp = get_nlp()
    matcher = Matcher(nlp.vocab)

    # Seniority + Domain + Title  (e.g. "Senior Software Engineer")
    matcher.add("TITLE_SDT", [[
        {"LOWER": {"IN": _SENIORITY}},
        {"LOWER": {"IN": _DOMAIN}, "OP": "+"},
        {"LOWER": {"IN": _TITLE}},
    ]])
    # Domain + Domain + Title  (e.g. "Machine Learning Engineer")
    matcher.add("TITLE_DDT", [[
        {"LOWER": {"IN": _DOMAIN}},
        {"LOWER": {"IN": _DOMAIN}},
        {"LOWER": {"IN": _TITLE}},
    ]])
    # Domain + Title  (e.g. "Software Engineer")
    matcher.add("TITLE_DT", [[
        {"LOWER": {"IN": _DOMAIN}},
        {"LOWER": {"IN": _TITLE}},
    ]])
    # Seniority + Title  (e.g. "Senior Engineer")
    matcher.add("TITLE_ST", [[
        {"LOWER": {"IN": _SENIORITY}},
        {"LOWER": {"IN": _TITLE}},
    ]])
    # Title + "of" + Noun  (e.g. "Director of Engineering")
    matcher.add("TITLE_OF", [[
        {"LOWER": {"IN": _TITLE}},
        {"LOWER": "of"},
        {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"},
    ]])

    logger.info("Job title Matcher built.")
    return matcher


# ─── Degree PhraseMatcher ────────────────────────────────────────────────────

_degree_matcher: Optional[PhraseMatcher] = None

_DEGREE_PHRASES = [
    "Doctor of Philosophy", "Ph.D.", "PhD", "Doctorate",
    "Juris Doctor", "Doctor of Medicine",
    "Master of Science", "Master of Arts",
    "Master of Business Administration", "Master of Engineering",
    "Master of Education", "Master of Public Administration",
    "Master of Information Technology",
    "Bachelor of Science", "Bachelor of Arts", "Bachelor of Engineering",
    "Bachelor of Business Administration", "Bachelor of Commerce",
    "Bachelor of Fine Arts", "Bachelor of Information Technology",
    "Associate of Science", "Associate of Arts",
    "Associate's Degree", "Associates Degree",
    "Bachelor's Degree", "Bachelors Degree",
    "Master's Degree", "Masters Degree",
    "Undergraduate Degree", "Graduate Studies",
    "Diploma", "National Certificate", "Senior High School",
]


def get_degree_matcher() -> PhraseMatcher:
    """Return a PhraseMatcher for academic degree terms."""
    global _degree_matcher
    if _degree_matcher is None:
        _degree_matcher = _build_degree_matcher()
    return _degree_matcher


def _build_degree_matcher() -> PhraseMatcher:
    """Build the degree PhraseMatcher."""
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(d.lower()) for d in _DEGREE_PHRASES]
    if patterns:
        matcher.add("DEGREES", patterns)
    logger.info(f"Degree PhraseMatcher built with {len(patterns)} patterns.")
    return matcher


# ─── Convenience: Run PhraseMatcher ──────────────────────────────────────────

def find_phrase_matches(doc: Doc, matcher: PhraseMatcher) -> list[str]:
    """
    Run a PhraseMatcher on a Doc and return unique matched strings.
    Deduplicates by lowercase key, preserves original casing.
    """
    matches = matcher(doc)
    results = []
    seen = set()
    for match_id, start, end in matches:
        span_text = doc[start:end].text.strip()
        key = span_text.lower()
        if key not in seen and len(span_text) > 1:
            seen.add(key)
            results.append(span_text)
    return results


def find_phrase_matches_with_spans(doc: Doc, matcher: PhraseMatcher):
    """
    Run a PhraseMatcher and return (text, start_char, end_char) tuples.
    Useful when positional information matters.
    """
    matches = matcher(doc)
    results = []
    seen = set()
    for match_id, start, end in matches:
        span = doc[start:end]
        key = span.text.strip().lower()
        if key not in seen and len(span.text.strip()) > 1:
            seen.add(key)
            results.append((span.text.strip(), span.start_char, span.end_char))
    return results


# ─── NER Convenience Utilities ───────────────────────────────────────────────

def get_ner_entities(doc: Doc, label: str) -> list[str]:
    """
    Extract all entities of a given label from a spaCy Doc.

    Common labels:
      PERSON  — people names
      ORG     — organizations, companies, institutions
      GPE     — geo-political entities (countries, cities)
      LOC     — non-GPE locations
      DATE    — dates and date ranges
      NORP    — nationalities, religious/political groups
    """
    entities = []
    seen = set()
    for ent in doc.ents:
        if ent.label_ == label:
            text = ent.text.strip()
            key = text.lower()
            if key not in seen and len(text) > 1:
                seen.add(key)
                entities.append(text)
    return entities


def get_ner_entities_multi(doc: Doc, labels: list[str]) -> dict[str, list[str]]:
    """Extract entities for multiple labels at once."""
    result = {label: [] for label in labels}
    seen = {label: set() for label in labels}

    for ent in doc.ents:
        if ent.label_ in labels:
            text = ent.text.strip()
            key = text.lower()
            if key not in seen[ent.label_] and len(text) > 1:
                seen[ent.label_].add(key)
                result[ent.label_].append(text)

    return result


def get_ner_entities_in_range(doc: Doc, label: str,
                              start_char: int, end_char: int) -> list[str]:
    """Extract NER entities of a given label within a character range."""
    entities = []
    seen = set()
    for ent in doc.ents:
        if ent.label_ == label and ent.start_char >= start_char and ent.end_char <= end_char:
            text = ent.text.strip()
            key = text.lower()
            if key not in seen and len(text) > 1:
                seen.add(key)
                entities.append(text)
    return entities


# ─── Noun Chunk Extraction ───────────────────────────────────────────────────

def extract_noun_chunks(doc: Doc, min_length: int = 2) -> list[str]:
    """
    Extract meaningful noun chunks from a spaCy Doc.
    Filters out very short or stopword-only chunks.
    """
    chunks = []
    seen = set()
    for chunk in doc.noun_chunks:
        text = chunk.text.strip()
        key = text.lower()
        # Filter: minimum length, not all stopwords, not seen before
        if (len(text) >= min_length
                and key not in seen
                and not all(t.is_stop for t in chunk)):
            seen.add(key)
            chunks.append(text)
    return chunks


# ─── Token-level Utilities ───────────────────────────────────────────────────

def get_verb_object_pairs(doc: Doc) -> list[tuple[str, str]]:
    """
    Extract (verb, object) pairs from text.
    Useful for identifying responsibilities in experience sections.
    E.g., "developed APIs" → ("developed", "APIs")
    """
    pairs = []
    for token in doc:
        if token.pos_ == "VERB" and not token.is_stop:
            for child in token.children:
                if child.dep_ in ("dobj", "pobj", "attr"):
                    obj_text = " ".join(
                        t.text for t in child.subtree
                        if not t.is_punct
                    ).strip()
                    if obj_text and len(obj_text) > 2:
                        pairs.append((token.lemma_, obj_text))
    return pairs


def get_sentence_spans(doc: Doc) -> list[str]:
    """Return list of sentence strings from the doc."""
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def get_sentences_with_offsets(doc: Doc) -> list[tuple[str, int, int]]:
    """Return list of (sentence_text, start_char, end_char) tuples."""
    return [
        (sent.text.strip(), sent.start_char, sent.end_char)
        for sent in doc.sents if sent.text.strip()
    ]
