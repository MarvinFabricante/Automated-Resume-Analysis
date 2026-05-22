"""
spaCy NLP Engine Package
────────────────────────
Provides a shared, singleton spaCy pipeline and pre-built
PhraseMatcher / Matcher instances for resume extraction.

Usage:
    from app.extractors.nlp import get_nlp, get_doc, get_skills_matcher
"""

from .nlp_engine import (
    get_nlp,
    get_doc,
    get_skills_matcher,
    get_cert_matcher,
    get_job_title_matcher,
    get_degree_matcher,
    get_ner_entities,
    get_ner_entities_multi,
    get_ner_entities_in_range,
    extract_noun_chunks,
    get_verb_object_pairs,
    get_sentence_spans,
    get_sentences_with_offsets,
    find_phrase_matches,
    find_phrase_matches_with_spans,
)
