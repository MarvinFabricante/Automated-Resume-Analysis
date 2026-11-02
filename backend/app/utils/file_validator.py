import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Known executable and dangerous binary signatures
EXECUTABLE_SIGNATURES = [
    (b"MZ", "Windows Executable (.exe, .dll, .sys, .scr)"),
    (b"ZM", "DOS Executable"),
    (b"\x7fELF", "Linux ELF Executable / Binary"),
    (b"\xfe\xed\xfa\xce", "Mach-O Binary (32-bit)"),
    (b"\xfe\xed\xfa\xcf", "Mach-O Binary (64-bit)"),
    (b"\xce\xfa\xed\xfe", "Mach-O Binary (32-bit reverse)"),
    (b"\xcf\xfa\xed\xfe", "Mach-O Binary (64-bit reverse)"),
    (b"\xca\xfe\xba\xbe", "Java Classfile / Mach-O Fat Binary"),
    (b"\x00asm", "WebAssembly Binary"),
    (b"#!", "Executable Script"),
]


def is_executable_binary(header: bytes) -> Tuple[bool, Optional[str]]:
    """
    Inspects the binary header (magic bytes) to determine if a file is an
    executable or binary executable payload.
    """
    if not header:
        return False, None
    for sig, desc in EXECUTABLE_SIGNATURES:
        if header.startswith(sig):
            return True, desc
    return False, None


def validate_file_content(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validates file content (magic bytes) against its claimed extension.
    Strictly rejects disguised executables (.exe renamed to .pdf, etc.)
    and mismatched / corrupted document formats.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not file_bytes or len(file_bytes) == 0:
        return False, "File is empty (0 bytes)."

    header = file_bytes[:1024]
    ext = os.path.splitext(filename or "")[1].lower().strip('.')

    # 1. Immediate rejection of executable binaries regardless of claimed extension
    is_exe, exe_desc = is_executable_binary(header)
    if is_exe:
        logger.warning(
            f"Security rejection: Uploaded file '{filename}' contains executable signature ({exe_desc})."
        )
        return False, f"File rejected by content check: Executable file ({exe_desc}) disguised as '{ext or 'document'}' is not accepted."

    # 2. PDF Content Validation: Must contain %PDF magic bytes within first 1024 bytes
    if ext == 'pdf':
        if b'%PDF' not in header:
            logger.warning(f"Content check failure: File '{filename}' claimed .pdf but lacks %PDF header.")
            return False, "File rejected by content check: The file has a .pdf extension but does not contain valid PDF content."

    # 3. DOCX and DOC Content Validation: Accepts ZIP (PK), OLE CFBF, or RTF Word headers
    elif ext in ('docx', 'doc'):
        is_zip = header.startswith(b'PK')
        is_cfbf = header.startswith(b'\xd0\xcf\x11\xe0')
        is_rtf = header.startswith(b'{\\rtf')
        is_xml = header.strip().startswith(b'<?xml') or b'<w:document' in header[:200]
        if not (is_zip or is_cfbf or is_rtf or is_xml):
            logger.warning(f"Content check failure: File '{filename}' claimed .{ext} but lacks valid Word document header.")
            return False, f"File rejected by content check: The file has a .{ext} extension but does not contain valid Microsoft Word document content."

    # 5. TXT Content Validation: Plain text should not have high null-byte density
    elif ext == 'txt':
        null_count = header.count(b'\x00')
        if null_count > len(header) * 0.05:
            logger.warning(f"Content check failure: File '{filename}' claimed .txt but contains binary data.")
            return False, "File rejected by content check: The file has a .txt extension but contains binary or non-text data."

    # 6. Physical Resume Scan Images
    elif ext in ('png', 'jpg', 'jpeg', 'webp'):
        if ext == 'png' and not header.startswith(b'\x89PNG\r\n\x1a\n'):
            return False, "File rejected by content check: Invalid PNG image header."
        elif ext in ('jpg', 'jpeg') and not header.startswith(b'\xff\xd8\xff'):
            return False, "File rejected by content check: Invalid JPEG image header."
        elif ext == 'webp' and not (header.startswith(b'RIFF') and b'WEBP' in header[:16]):
            return False, "File rejected by content check: Invalid WEBP image header."

    return True, ""
