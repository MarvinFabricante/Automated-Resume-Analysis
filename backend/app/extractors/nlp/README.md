# NLP Engine & Extractors (`app/extractors/nlp`)

The `nlp` module provides a high-performance, singleton **spaCy linguistic pipeline** and custom matcher suite engineered for deterministic resume entity extraction and semantic pattern matching.

## Architecture & Components

```
app/extractors/nlp/
├── __init__.py             # Public module exports and helper functions
├── nlp_engine.py           # Core spaCy singleton, pipeline configuration, and custom matchers
└── spacy_extractor.py      # High-level resume section extraction wrappers
```

## Features

- **spaCy NLP Pipeline**: Singleton language pipeline leveraging `en_core_web_sm` for tokenization, sentence boundaries, and Named Entity Recognition (NER).
- **PhraseMatcher Engine**: High-speed matching of technical skills, certifications, degrees, and job titles against curated taxonomy dictionaries.
- **Syntactic Parsing**: Noun chunk extraction, verb-object relationship mapping, and structural sentence analysis.
- **Deterministic & LLM-Free**: Delivers sub-second extraction precision without recurring API latency or token costs.

## Installation & Model Setup

The spaCy linguistic model is specified in `requirements.txt`. For manual installation or verification:

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Download the English language model (if missing)
python -m spacy download en_core_web_sm
```

## Usage Example

```python
from app.extractors.nlp import get_doc, get_skills_matcher, find_phrase_matches

# 1. Process raw text into a spaCy document
doc = get_doc(raw_resume_text)

# 2. Retrieve pre-compiled PhraseMatcher
matcher = get_skills_matcher()

# 3. Extract matching skill tokens
matched_skills = find_phrase_matches(doc, matcher)
```
