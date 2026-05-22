import logging
from .file.file_extractor import extract_file_content
from .content.content_extractor import extract_content

logger = logging.getLogger(__name__)


def process_resume(file_path: str, file_extension: str) -> dict:
    """
    Main entry point for resume processing.

    Pipeline:
    1. Extract raw text from file (PDF/DOCX/TXT).
    2. Run rule-based extractors (regex, NLP, keyword matching,
       structured parsing) for immediate structured data.
    3. Extract profile image if available.

    NOTE: Gemini AI is NOT used during extraction.
          It is reserved exclusively for the analysis / candidate-job
          matching stage (see gemini_analyze_match in gemini_service.py).
    """
    print(f"DEBUG: Processing file at {file_path}")
    text = extract_file_content(file_path, file_extension)
    if not text:
        print("DEBUG: extract_file_content returned empty text")
        return {}

    print(f"DEBUG: Successfully extracted {len(text)} characters of text")

    # ── Step 2: Rule-based extraction (no LLM) ───────────────────────────────
    extracted_data = extract_content(text)
    print(f"DEBUG: Rule-based extraction complete for: {extracted_data.get('fullname', 'unknown')}")
    print(f"DEBUG: Skills found: {len(extracted_data.get('skills', '').split('|'))} items")
    print(f"DEBUG: Experience entries: {len(extracted_data.get('experience', '').split('|'))} items")
    print(f"DEBUG: Education: {extracted_data.get('education', 'none')[:80]}")
    print(f"DEBUG: Certifications found: {extracted_data.get('certifications', 'none')[:80]}")
    print(f"DEBUG: Years of experience: {extracted_data.get('years_experience', 0)}")

    # ── Step 3: Extract profile image if PDF or DOCX ──────────────────────────
    ext = file_extension.lower().strip('.')
    image_path = None
    if ext == 'pdf':
        from .file.pdf_extractor import extract_image_from_pdf
        image_path = extract_image_from_pdf(file_path)
    elif ext in ('docx', 'doc'):
        from .file.docx_extractor import extract_image_from_docx
        image_path = extract_image_from_docx(file_path)

    if image_path:
        extracted_data['profile_image_url'] = f"http://localhost:8000/{image_path}"

    return extracted_data
