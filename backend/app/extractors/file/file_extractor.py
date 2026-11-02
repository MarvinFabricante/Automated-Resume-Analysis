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

    # Remove zero-width characters and soft hyphens that break word/email boundaries
    for zw in ['\u200b', '\u200c', '\u200d', '\ufeff', '\xad', '\u2060', '\u200e', '\u200f']:
        text = text.replace(zw, '')
    text = text.replace('\u202f', ' ')

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
    Utility function to extract text from a file based on its extension or contents.
    Always returns cleaned and normalized text.
    Handles:
    - PDF documents (text-based and scanned/OCR)
    - Microsoft Word documents (.docx and legacy .doc)
    - Plain text files (.txt) with multi-encoding support
    - Magic-byte sniffing fallback if extension is missing, unknown, or mismatched
    """
    ext = file_extension.lower().strip('.')
    if '.' in ext:
        ext = ext.split('.')[-1]

    # Validate content (magic bytes) against disguised executables
    try:
        from app.utils.file_validator import validate_file_content, is_executable_binary
        with open(file_path, 'rb') as f:
            header = f.read(1024)

        # Immediate rejection if file content is an executable binary
        is_exe, _ = is_executable_binary(header)
        if is_exe:
            return ""

        is_valid, _ = validate_file_content(header, f"file.{ext}")
        if not is_valid:
            return ""

        # Auto-detect true format via magic bytes if the file is a valid document binary
        if b'%PDF' in header:
            ext = 'pdf'
        elif header.startswith(b'PK\x03\x04'):
            ext = 'docx'
        elif header.startswith(b'\xd0\xcf\x11\xe0'):
            ext = 'doc'
        elif not ext or ext not in ('pdf', 'doc', 'docx', 'txt'):
            ext = 'txt'
    except Exception:
        if not ext:
            ext = 'txt'

    raw_text = ""
    if ext == 'pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext in ['doc', 'docx']:
        raw_text = extract_text_from_docx(file_path)
    elif ext == 'txt':
        raw_text = extract_text_from_txt(file_path)

    # Cross-format fallback only for legitimate document formats (NOT executables or binary noise)
    if not raw_text or len(raw_text.strip()) < 10:
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)
            is_exe, _ = is_executable_binary(header)
            if is_exe:
                return ""
            if b'%PDF' in header and ext != 'pdf':
                raw_text = extract_text_from_pdf(file_path)
            elif (header.startswith(b'PK\x03\x04') or header.startswith(b'\xd0\xcf\x11\xe0')) and ext not in ('doc', 'docx'):
                raw_text = extract_text_from_docx(file_path)
            elif ext != 'txt' and not any(header.startswith(b) for b in (b'\x00', b'\x7fELF', b'MZ')):
                txt_fallback = extract_text_from_txt(file_path)
                if len(txt_fallback.strip()) > len(raw_text.strip()):
                    raw_text = txt_fallback
        except Exception:
            pass

    return clean_raw_text(raw_text)
