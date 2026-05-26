# Extractors (`/backend/app/extractors`)

## Overview
The `extractors` directory is dedicated to **Data Parsing and Natural Language Processing (NLP)**. It is heavily utilized for taking unstructured data (like raw text from a PDF resume) and turning it into structured data (JSON).

## Responsibilities
- **NLP Pipelines**: Hosting spaCy logic, dependency parsing, and entity recognition.
- **Pattern Matching**: Using Regex or heuristic rules to find emails, phones, education degrees, or skills within dense text.
- **Data Normalization**: Standardizing raw strings (e.g., mapping "B.S. Comp Sci" -> "Bachelor of Science in Computer Science").

## What NOT to do here
- **NO Database Access**: Extractors should be pure functions. They take strings/text in, and return dictionaries/schemas out. They should not talk to the database.
- **NO Statefulness**: Try to keep extraction logic stateless so it can be easily parallelized via Celery or background tasks.

## Developer Guidelines & Example
Extractors are meant to be robust. Always account for missing data or unpredictable formatting.

```python
import re

def extract_contact_info(text: str) -> dict:
    """
    Extracts email and phone number from raw resume text using Regex.
    """
    # Simple regex for demonstration
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
    
    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)
    
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None
    }
```
