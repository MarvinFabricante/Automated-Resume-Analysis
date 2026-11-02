import logging

logger = logging.getLogger(__name__)


def extract_text_from_txt(file_path: str) -> str:
    """
    Extracts text from a .txt file with automatic multi-encoding support:
    - UTF-8 with or without BOM (utf-8-sig)
    - Standard UTF-8
    - UTF-16 (little & big endian)
    - Windows-1252 / CP1252
    - ISO-8859-1 / Latin-1
    Falls back to lossy UTF-8 decoding to guarantee no text file is rejected due to encoding.
    """
    try:
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()

        if not raw_bytes:
            return ""

        # Try common text encodings in order of likelihood
        for enc in ('utf-8-sig', 'utf-8', 'utf-16', 'windows-1252', 'latin-1'):
            try:
                return raw_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue

        # Ultimate fallback: decode with replacement
        return raw_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"Error reading TXT file {file_path}: {e}")
        return ""
