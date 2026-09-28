import re
from .pdf_extractor import extract_text_from_pdf
from .docx_extractor import extract_text_from_docx
from .txt_extractor import extract_text_from_txt


def clean_raw_text(text: str) -> str:
    """
    Standardize raw extracted text:
    - Normalizes newlines and whitespace
    - Replaces tabs with clean single spaces
    - Removes non-printable / null characters
    - Normalizes Unicode hyphens, bullets, and quotes
    """
    if not text:
        return ""
    # Remove null and non-printable control chars (preserve \n)
    text = text.replace('\x00', '').replace('\xa0', ' ').replace('\x0c', '\n')
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Normalize unicode hyphens/dashes to standard hyphen or dash
    text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015]', '-', text)
    # Normalize unicode quotes
    text = re.sub(r'[\u2018\u2019]', "'", text)
    text = re.sub(r'[\u201c\u201d]', '"', text)
    # Normalize unicode bullets
    text = re.sub(r'[\u2022\u2023\u25e6\u2043\u2219\u25cb\u25cf\u25a0\u25aa]', '•', text)

    # Normalize tabs and spaces per line
    lines = []
    for line in text.split('\n'):
        line_clean = re.sub(r'[\t ]+', ' ', line).strip()
        lines.append(line_clean)

    cleaned = '\n'.join(lines)
    # Collapse 3+ consecutive newlines to 2
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def extract_file_content(file_path: str, file_extension: str) -> str:
    """
    Utility function to extract text from a file based on its extension.
    Always returns cleaned and normalized text.
    """
    ext = file_extension.lower().strip('.')
    raw_text = ""

    if ext == 'pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext in ['doc', 'docx']:
        raw_text = extract_text_from_docx(file_path)
    elif ext == 'txt':
        raw_text = extract_text_from_txt(file_path)

    return clean_raw_text(raw_text)
