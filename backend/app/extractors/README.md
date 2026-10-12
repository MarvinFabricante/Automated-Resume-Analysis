# Extractors (`app/extractors`)

The `extractors` package houses the **Document Ingestion & Natural Language Processing (NLP)** pipeline. It converts unstructured document streams (PDF, DOCX, TXT) into normalized, structured JSON data.

## Architecture & Submodules

```
app/extractors/
├── resume_processor.py         # Main orchestrator linking file readers, parsers, and NLP
├── file/                       # File ingestion layer
│   ├── pdf_extractor.py        # PDF text & layout extraction (PyMuPDF)
│   ├── docx_extractor.py       # DOCX parsing (python-docx)
│   └── txt_extractor.py        # Plain-text normalization
├── content/                    # Field-specific heuristic & regex parsers
│   ├── section_parser.py       # Resume boundary & section header segmenter
│   ├── name_extractor.py       # Candidate name heuristics & entity parsing
│   ├── email_extractor.py      # RFC-compliant email detection
│   ├── phone_extractor.py      # International & local phone number matching
│   ├── skills_extractor.py     # Weighted keyword & phrase matchers
│   ├── experience_extractor.py # Work experience timeline & tenure calculation
│   ├── education_extractor.py  # Degree, institution, and major normalization
│   └── certifications_extractor.py # Industry certification extraction
└── nlp/                        # spaCy linguistic models & custom entity pipeline
    ├── nlp_engine.py           # Shared pipeline singleton & PhraseMatcher instances
    └── spacy_extractor.py      # Linguistic extraction helpers
```

## Responsibilities

- **Document Parsing**: Extract raw text and layout structure from various resume file formats.
- **Section Segmentation**: Partition resumes into discrete conceptual zones (Experience, Education, Skills, Summary).
- **Entity Extraction**: Extract key candidate attributes using heuristic rules, regular expressions, and spaCy PhraseMatchers.
- **Data Normalization**: Standardize degree classifications, date ranges, and technical competencies.

## Best Practices & Prohibitions

- **Pure Functions**: Extractors should remain stateless and pure—accepting raw text or byte streams and returning structured dictionaries.
- **No Database Access**: Extractors must never perform database operations. Database persistence belongs in services and repositories.
- **No Network / External API Dependencies**: Extraction runs entirely locally in sub-second time without relying on external cloud APIs.

## Developer Guidelines & Example

```python
import re
from typing import Dict, Optional

def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extracts contact information from raw resume text using regex patterns.
    """
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
    
    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)
    
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
    }
```
