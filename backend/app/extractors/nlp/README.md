spaCy extractor
===============

This module provides spaCy-based extraction helpers used by the resume
content pipeline. It relies on `en_core_web_sm` being available. The
project `requirements.txt` includes a pinned wheel for the model, but
if you need to install manually run:

```bash
python -m pip install -r backend/requirements.txt
# or, if model missing:
python -m spacy download en_core_web_sm
```

Notes:
- The extractor uses spaCy only (no LLMs) for tokenization, sentence
  segmentation and NER, combined with rule-based matching.
- Skills are detected via PhraseMatcher against the project's knowledge
  base and noun chunk scanning.
- Experience, education and certifications use NER + simple patterns
  to maximize precision while avoiding AI models.
