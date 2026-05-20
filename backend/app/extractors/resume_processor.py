import logging
from .file.file_extractor import extract_file_content
from .content.content_extractor import extract_content

logger = logging.getLogger(__name__)


def process_resume(file_path: str, file_extension: str) -> dict:
    """
    Main entry point for resume processing.
    1. Extracts raw text from file.
    2. Uses fast rule-based extractors for immediate credential display.
    3. Leaves LLM/Gemini work to post-processing analysis endpoints after parsing.
    """
    print(f"DEBUG: Processing file at {file_path}")
    text = extract_file_content(file_path, file_extension)
    if not text:
        print("DEBUG: extract_file_content returned empty text")
        return {}

    print(f"DEBUG: Successfully extracted {len(text)} characters of text")

    # Fast extraction only. Do not call Gemini here; upload should return
    # credentials immediately. Gemini remains available for match/analysis after
    # the parsed resume data has already been returned to the frontend.
    extracted_data = extract_content(text)
    print(f"DEBUG: Fast extraction complete for: {extracted_data.get('fullname', 'unknown')}")

    # ── 3. Extract profile image if PDF ──────────────────────────────────────
    if file_extension.lower().strip('.') == 'pdf':
        from .file.pdf_extractor import extract_image_from_pdf
        image_path = extract_image_from_pdf(file_path)
        if image_path:
            extracted_data['profile_image_url'] = f"http://localhost:8000/{image_path}"

    return extracted_data
