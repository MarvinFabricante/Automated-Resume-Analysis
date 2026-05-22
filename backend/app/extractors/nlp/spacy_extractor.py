import re
from typing import List

import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc

from ..content.skills_extractor import COMMON_SKILLS, _format_skill


_NLP = None


def get_nlp():
    global _NLP
    if _NLP is None:
        # Lazy-load model; project requirements pin en_core_web_sm
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            # Fallback to spacy.load by name
            _NLP = spacy.load("en_core_web_sm")
    return _NLP


def process_text(text: str) -> Doc:
    nlp = get_nlp()
    # Normalize whitespace and clean common noise
    clean = re.sub(r"\s+", " ", text.strip())
    return nlp(clean)


def extract_skills_spacy(text: str, max_results: int = 50) -> List[str]:
    """Use spaCy PhraseMatcher + simple context scanning to extract skills."""
    nlp = get_nlp()
    doc = nlp(text)

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    # Build patterns from COMMON_SKILLS
    patterns = [nlp.make_doc(s.lower()) for s in COMMON_SKILLS]
    matcher.add("SKILL", patterns)

    found = []
    spans = []
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        spans.append((span.start_char, span.end_char, span.text))

    # Also capture noun_chunks that often represent multi-word skills
    for nc in doc.noun_chunks:
        text_nc = nc.text.strip()
        if len(text_nc) > 1 and len(text_nc) < 60:
            spans.append((nc.start_char, nc.end_char, text_nc))

    # Deduplicate by normalized uppercase form and prefer longer spans
    spans_sorted = sorted(spans, key=lambda x: (x[0], -(x[1] - x[0])))
    seen = set()
    skills = []
    for _, _, s in spans_sorted:
        key = s.strip().upper()
        # normalize synonyms via _format_skill
        formatted = _format_skill(s)
        if not formatted:
            continue
        canon = formatted.upper()
        if canon in seen:
            continue
        # simple noise filter
        if len(formatted) < 2:
            continue
        seen.add(canon)
        skills.append(formatted)
        if len(skills) >= max_results:
            break

    return skills


_DATE_RANGE_RE = re.compile(r"(\b\d{4}\b|\bpresent\b|\bcurrent\b|\b\d{2}/\d{4}\b|\b\w{3,9}\s+\d{4}\b)", re.I)


def extract_experience_spacy(text: str, max_entries: int = 10) -> List[str]:
    """Extract experience lines using sentence segmentation + NER heuristics.

    Returns a list of human-readable role entries (title at company; dates).
    """
    doc = process_text(text)
    entries = []

    for sent in doc.sents:
        stext = sent.text.strip()
        if len(stext) < 20:
            continue
        # Heuristic: sentences mentioning a year/date or keywords likely describe experience
        if _DATE_RANGE_RE.search(stext) or re.search(r'\b(experience|responsible|led|joined|worked|managed|senior|engineer|developer|consultant|analyst|director|manager)\b', stext, re.I):
            # Try to find ROLE and ORG
            role = None
            org = None
            # pattern: "<Role> at <Org>" or "<Role>, <Org>"
            m = re.search(r'(?P<role>[A-Za-z\-/& ]{2,80})\s+(?:at|@|with)\s+(?P<org>[A-Za-z0-9 &\.\-]{2,80})', stext)
            if m:
                role = m.group('role').strip(' ,–—')
                org = m.group('org').strip(' ,–—')
            else:
                # use NER to find ORG
                for ent in sent.ents:
                    if ent.label_ == 'ORG':
                        org = ent.text
                        break
                # role as title-cased noun chunk before org
                if org:
                    before = stext.split(org)[0]
                    # take last noun chunk-like phrase
                    parts = re.split(r'[,:\-–—\n]', before)
                    candidate = parts[-1].strip()
                    if 2 <= len(candidate) <= 60:
                        role = candidate

            # extract a date range snippet
            dates = []
            for ent in sent.ents:
                if ent.label_ in ('DATE',):
                    dates.append(ent.text)
            # fallback regex
            if not dates:
                dr = re.findall(r'\b(?:\d{4}|present|current|\w{3,9}\s+\d{4}|\d{1,2}/\d{4})\b', stext, re.I)
                dates = dr

            entry_parts = []
            if role:
                entry_parts.append(role)
            if org:
                entry_parts.append(f"at {org}")
            if dates:
                entry_parts.append("(" + ", ".join(dates[:2]) + ")")

            entry = " ".join(entry_parts).strip()
            if entry and entry not in entries:
                entries.append(entry)
                if len(entries) >= max_entries:
                    break

    return entries


def extract_education_spacy(text: str, max_entries: int = 5) -> List[str]:
    doc = process_text(text)
    degree_keywords = ['bachelor', 'master', 'mba', 'bs', 'ba', 'phd', 'doctor', 'associate', "degree"]
    entries = []
    for sent in doc.sents:
        s = sent.text.strip()
        if any(k in s.lower() for k in degree_keywords) or 'university' in s.lower() or 'college' in s.lower():
            # capture organization and degree
            school = None
            degree = None
            for ent in sent.ents:
                if ent.label_ == 'ORG' and not school:
                    school = ent.text
                if ent.label_ == 'DATE' and not degree:
                    # date might indicate graduation year
                    degree = degree or ''
            # attempt to find degree phrase
            m = re.search(r'((Bachelor|Master|B\.A\.|B\.S\.|M\.S\.|MBA|Ph\.D|Doctor)[^,\n]*)', s, re.I)
            if m:
                degree = m.group(1).strip()
            entry = s
            if entry not in entries:
                entries.append(entry)
                if len(entries) >= max_entries:
                    break
    return entries


def extract_certifications_spacy(text: str, max_entries: int = 10) -> List[str]:
    doc = process_text(text)
    entries = []
    for sent in doc.sents:
        s = sent.text.strip()
        if re.search(r'\b(certified|certificate|certification|issued by|credential)\b', s, re.I):
            # Simplify: take noun chunks or phrase after certificate keywords
            m = re.search(r'certificate[s]?\s*[:\-]?\s*(.+)', s, re.I)
            if m:
                cand = m.group(1).strip()
                entries.append(cand)
                continue
            # else take chunk
            for nc in sent.noun_chunks:
                txt = nc.text.strip()
                if len(txt) > 3 and 'certificate' not in txt.lower():
                    entries.append(txt)
                    break
    # dedupe
    seen = []
    for e in entries:
        if e not in seen:
            seen.append(e)
    return seen[:max_entries]
