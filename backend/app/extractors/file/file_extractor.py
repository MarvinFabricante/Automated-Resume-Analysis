import re
import unicodedata
from .pdf_extractor import extract_text_from_pdf
from .docx_extractor import extract_text_from_docx
from .txt_extractor import extract_text_from_txt


# Comprehensive emoji regex covering all Unicode emoji blocks & pictographs
_EMOJI_PATTERN = re.compile(
    r'['
    r'\U0001F600-\U0001F64F'  # Emoticons
    r'\U0001F300-\U0001F5FF'  # Misc Symbols and Pictographs
    r'\U0001F680-\U0001F6FF'  # Transport and Map Symbols
    r'\U0001F700-\U0001F77F'  # Alchemical Symbols
    r'\U0001F780-\U0001F7FF'  # Geometric Shapes Extended
    r'\U0001F800-\U0001F8FF'  # Supplemental Arrows-C
    r'\U0001F900-\U0001F9FF'  # Supplemental Symbols and Pictographs
    r'\U0001FA00-\U0001FA6F'  # Chess Symbols
    r'\U0001FA70-\U0001FAFF'  # Symbols and Pictographs Extended-A
    r'\U0001FB00-\U0001FBFF'  # Symbols for Legacy Computing
    r'\U0001F000-\U0001F02F'  # Mahjong Tiles
    r'\U0001F0A0-\U0001F0FF'  # Playing Cards
    r'\U0001F100-\U0001F2FF'  # Enclosed Alphanumeric / Ideographic Supplement
    r'\u2600-\u26FF'          # Misc Symbols (telephone, envelope, warning, umbrella, etc.)
    r'\u2700-\u27BF'          # Dingbats (scissors, checkmark, envelope, stars, etc.)
    r'\u2300-\u23FF'          # Misc Technical (watch, hourglass, keyboard, etc.)
    r'\u2B00-\u2BFF'          # Misc Symbols and Arrows
    r'\u2460-\u24FF'          # Enclosed Alphanumerics
    r'\uFE00-\uFE0F'          # Variation Selectors
    r'\u20E3'                # Combining Enclosing Keycap
    r']+',
    flags=re.UNICODE
)


def remove_emojis(text: str) -> str:
    """Removes all emojis, variation selectors, and decorative pictographs."""
    if not text:
        return ""
    t = _EMOJI_PATTERN.sub('', text)
    cleaned = []
    for char in t:
        cat = unicodedata.category(char)
        if cat in ('So', 'Co', 'Cs'):
            continue
        cleaned.append(char)
    return ''.join(cleaned)


def clean_raw_text(text: str) -> str:
    """
    Standardize raw extracted text (REQ005 / TC-RES-011):
    - Normalizes newlines and whitespace
    - Replaces tabs and extra spaces with clean single spaces
    - Removes non-printable / null characters and zero-width spaces
    - Removes all emojis, decorative pictographs, and stray symbols
    - Preserves accented letters (e.g. ñ, Ñ, á, é, í, ó, ú, ü, etc.)
    - Normalizes Unicode hyphens, bullets, and quotes
    """
    if not text:
        return ""
    # Remove null and non-printable control chars (preserve \n)
    text = text.replace('\x00', '').replace('\xa0', ' ').replace('\x0c', '\n')
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove zero-width characters and soft hyphens that break word/email boundaries
    for zw in ['\u200b', '\u200c', '\u200d', '\ufeff', '\xad', '\u2060', '\u200e', '\u200f', '\ufffd']:
        text = text.replace(zw, '')
    text = text.replace('\u202f', ' ')

    # Normalize unicode hyphens/dashes to standard hyphen or dash
    text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015]', '-', text)
    # Normalize unicode quotes
    text = re.sub(r'[\u2018\u2019]', "'", text)
    text = re.sub(r'[\u201c\u201d]', '"', text)
    # Normalize unicode bullets
    text = re.sub(r'[\u2022\u2023\u25e6\u2043\u2219\u25cb\u25cf\u25a0\u25aa]', '•', text)

    # Remove all emojis and pictographs
    text = _EMOJI_PATTERN.sub('', text)

    # Remove characters in Unicode Category 'So' (Symbol, other), 'Co' (Private use), 'Cs' (Surrogate),
    # or other non-printable control characters (Cc) except newline and tab.
    # Accented letters (Category Lu/Ll) and standard punctuation (P*), math/currency (Sm/Sc) are preserved.
    cleaned_chars = []
    for char in text:
        cat = unicodedata.category(char)
        if cat in ('So', 'Co', 'Cs'):
            continue
        if cat == 'Cc' and char not in ('\n', '\t'):
            continue
        cleaned_chars.append(char)
    text = ''.join(cleaned_chars)

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
