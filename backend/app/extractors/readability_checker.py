"""
Non-blocking ATS readability checker for uploaded applicant resumes.

Evaluates a resume file + extracted text + extracted fields purely for friendly,
applicant-facing guidance. Warnings are NEVER stored as a negative mark against
the applicant and are NEVER exposed to HR as a penalty.
"""
import logging
import os
import re
import zipfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}\b|"
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s*(?:19|20)?\d{2}\b",
    re.IGNORECASE,
)

_EMAIL_FALLBACK_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_FALLBACK_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")

_BASIC_HEADING_RE = re.compile(
    r"^\s*(?:education|academic\s+background|skills|technical\s+skills|core\s+competencies|"
    r"work\s+experience|employment\s+history|professional\s+experience|experience|"
    r"certifications?|licenses?\s*(?:&|and)\s*certifications?|trainings?|seminars?|"
    r"summary|profile|objective)\s*[:\-]?\s*$",
    re.IGNORECASE,
)


def inspect_file_readability_signals(file_path: str, file_extension: str) -> Dict[str, Any]:
    """
    Inspect raw PDF / DOCX file structure for:
      - password protection / encryption
      - native extractable text length (before OCR)
      - multi-column layout indicators (two-column PDF pages or multi-column Word layout tables/sections)
    """
    ext = (file_extension or "").lower().strip(".")
    signals: Dict[str, Any] = {
        "password_protected": False,
        "native_text_chars": None,
        "is_multi_column": False,
        "has_images_only": False,
        "page_count": None,
        "fast_sample_text": "",
    }

    if not file_path or not os.path.isfile(file_path):
        return signals

    # 1. PDF checks via PyMuPDF
    if ext == "pdf":
        try:
            import fitz
            doc = fitz.open(file_path)
            try:
                if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
                    # Try empty password (some PDFs have owner permissions only, not user password)
                    if doc.needs_pass and not doc.authenticate(""):
                        signals["password_protected"] = True
                        return signals

                page_count = len(doc)
                signals["page_count"] = page_count
                native_chars = 0
                total_images = 0
                two_col_pages = 0
                fast_sample_parts: List[str] = []

                from app.extractors.file.pdf_extractor import _extract_page_layout_parts

                # For oversized documents (>10 pages, e.g. 80-page thesis manuscripts or manuals),
                # avoid running heavy layout geometry on every page — inspect first 5 + last 2 pages only.
                layout_page_limit = page_count if page_count <= 10 else 5
                sample_indices = set(range(min(5, page_count)))
                if page_count > 5:
                    sample_indices.update(range(max(5, page_count - 2), page_count))

                prev_split = None
                for idx in range(page_count):
                    if page_count > 10 and idx not in sample_indices:
                        continue
                    page = doc[idx]
                    raw_page_txt = (page.get_text("text") or "").strip()
                    native_chars += len(re.sub(r"\s+", "", raw_page_txt))
                    if idx in sample_indices and raw_page_txt:
                        fast_sample_parts.append(raw_page_txt)
                    try:
                        total_images += len(page.get_images(full=False) or [])
                    except Exception:
                        pass
                    if idx < layout_page_limit:
                        try:
                            parts = _extract_page_layout_parts(page, prev_split_x=prev_split)
                            if parts.get("is_two_col"):
                                two_col_pages += 1
                                prev_split = parts.get("split_x")
                            else:
                                prev_split = None
                        except Exception:
                            pass

                signals["native_text_chars"] = native_chars
                signals["fast_sample_text"] = "\n\n".join(fast_sample_parts).strip()
                if two_col_pages > 0:
                    signals["is_multi_column"] = True
                if native_chars < 120 and total_images > 0:
                    signals["has_images_only"] = True
            finally:
                doc.close()
        except Exception as exc:
            logger.debug(f"PDF readability inspection notice: {exc}")

    # 2. DOCX / DOC checks
    elif ext in ("docx", "doc"):
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read(8192)
            # Encrypted Office Open XML (.docx) is wrapped in an OLE CFBF container with EncryptedPackage
            if raw_bytes.startswith(b"\xd0\xcf\x11\xe0") and (
                b"E\x00n\x00c\x00r\x00y\x00p\x00t\x00e\x00d\x00P\x00a\x00c\x00k\x00a\x00g\x00e" in raw_bytes
                or b"EncryptedPackage" in raw_bytes
                or b"E\x00n\x00c\x00r\x00y\x00p\x00t\x00i\x00o\x00n\x00I\x00n\x00f\x00o" in raw_bytes
            ):
                signals["password_protected"] = True
                return signals

            if zipfile.is_zipfile(file_path):
                # Extract page/word metadata & explicit page breaks from OOXML package
                xml_pages: Optional[int] = None
                xml_words: Optional[int] = None
                explicit_pages: Optional[int] = None
                try:
                    import xml.etree.ElementTree as ET
                    with zipfile.ZipFile(file_path, "r") as zf:
                        names = set(zf.namelist())
                        if "docProps/app.xml" in names:
                            app_xml = zf.read("docProps/app.xml")
                            root = ET.fromstring(app_xml)
                            for elem in root.iter():
                                tag = elem.tag.split("}")[-1]
                                if tag == "Pages" and elem.text and elem.text.strip().isdigit():
                                    val = int(elem.text.strip())
                                    if val > 0:
                                        xml_pages = val
                                elif tag == "Words" and elem.text and elem.text.strip().isdigit():
                                    val = int(elem.text.strip())
                                    if val >= 0:
                                        xml_words = val
                        if "word/document.xml" in names:
                            doc_xml_bytes = zf.read("word/document.xml")
                            # Count explicit hard page breaks and Word-rendered page breaks
                            hard_breaks = len(re.findall(rb"<w:br\b[^>]*w:type=[\"']page[\"']", doc_xml_bytes))
                            rendered_breaks = len(re.findall(rb"<w:lastRenderedPageBreak\b", doc_xml_bytes))
                            break_cnt = max(hard_breaks, rendered_breaks)
                            if break_cnt >= 1:
                                explicit_pages = break_cnt + 1
                except Exception as xml_exc:
                    logger.debug(f"DOCX XML page metadata check notice: {xml_exc}")

                import docx
                doc = docx.Document(file_path)

                # Trust docProps/app.xml <Pages> only when corroborated by word/paragraph count
                # (avoids stale metadata when an applicant edits a multi-page template down to 1 page)
                trusted_xml_pages: Optional[int] = None
                if xml_pages is not None and xml_pages >= 2:
                    para_count = len(doc.paragraphs)
                    if (
                        (xml_words is not None and xml_words >= xml_pages * 50)
                        or (explicit_pages is not None and explicit_pages >= 2)
                        or para_count >= xml_pages * 4
                    ):
                        trusted_xml_pages = xml_pages

                candidate_pages = [p for p in (explicit_pages, trusted_xml_pages) if p is not None]
                if candidate_pages:
                    signals["page_count"] = max(candidate_pages)
                signals["docx_xml_pages"] = xml_pages
                signals["docx_xml_words"] = xml_words
                signals["docx_explicit_pages"] = explicit_pages

                # Check section multi-column settings (<w:cols w:num="2">)
                for sect in doc.sections:
                    try:
                        cols_elems = sect._sectPr.xpath('.//*[local-name()="cols"]')
                        for ce in cols_elems:
                            num_attr = ce.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}num") or ce.get("num")
                            if num_attr and int(num_attr) >= 2:
                                signals["is_multi_column"] = True
                                break
                    except Exception:
                        pass

                # Check for multi-column layout tables (cap scan on huge non-resume DOCX files)
                if not signals["is_multi_column"]:
                    for tbl in doc.tables[:25]:
                        for row in tbl.rows[:40]:
                            unique_cells = []
                            for c in row.cells:
                                if not unique_cells or c._tc != unique_cells[-1]._tc:
                                    unique_cells.append(c)
                            if len(unique_cells) >= 2:
                                non_empty_long = sum(
                                    1
                                    for c in unique_cells
                                    if len((c.text or "").strip()) > 90 or "\n" in (c.text or "").strip()
                                )
                                if non_empty_long >= 2:
                                    signals["is_multi_column"] = True
                                    break
                        if signals["is_multi_column"]:
                            break
        except Exception as exc:
            logger.debug(f"DOCX readability inspection notice: {exc}")

    return signals


def evaluate_resume_readability(
    file_path: str,
    file_extension: str,
    raw_text: str,
    extracted_data: Optional[Dict[str, Any]] = None,
    file_signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a friendly, plain-language, non-blocking readability check report for the applicant.
    """
    signals = file_signals if file_signals is not None else inspect_file_readability_signals(file_path, file_extension)
    data = extracted_data or {}
    text = (raw_text or "").strip()
    warnings: List[Dict[str, str]] = []

    # 1. Password-protected file
    if signals.get("password_protected"):
        warnings.append({
            "code": "password_protected",
            "title": "Password-protected file",
            "message": "This file is password-protected, so we could not read its text.",
            "suggestion": "Remove the password and upload an unprotected PDF or DOCX file, or fill in your details on the next step.",
        })
        return {
            "status": "warning",
            "summary": "We could not read this file because it is password-protected.",
            "warnings": warnings,
        }

    # 2. Very little extractable text (likely a scanned image or photo)
    non_ws_len = len(re.sub(r"\s+", "", text))
    word_count = len(re.findall(r"[A-Za-z0-9]+", text))
    native_chars = signals.get("native_text_chars")
    is_low_text = (
        non_ws_len < 150
        or word_count < 25
        or signals.get("has_images_only")
        or (native_chars is not None and native_chars < 100)
    )
    if is_low_text:
        warnings.append({
            "code": "low_text",
            "title": "Very little readable text found",
            "message": "Your file has very little extractable text, which usually happens with a photo or scanned image.",
            "suggestion": "Upload a text-based PDF or DOCX saved directly from Word or Google Docs so your full experience can be read.",
        })

    # 3. Multi-column text that can interleave
    if signals.get("is_multi_column"):
        warnings.append({
            "code": "multi_column",
            "title": "Multi-column layout detected",
            "message": "Your resume appears to use two or more columns, which can cause lines from different sections to mix together.",
            "suggestion": "Use a simple one-column layout without sidebars or layout tables, and double-check your details on the next step.",
        })

    # Only run deeper text-based checks if there is at least some text
    if non_ws_len >= 40:
        # 4. Recognizable section headings
        recognized_sections = set()
        detect_fn = None
        try:
            from app.extractors.content.section_parser import detect_section_label
            detect_fn = detect_section_label
        except Exception:
            pass

        for line in text.splitlines():
            clean_ln = line.strip()
            if not clean_ln or len(clean_ln) > 65:
                continue
            if detect_fn is not None:
                lbl = detect_fn(clean_ln)
                if lbl:
                    recognized_sections.add(str(lbl).lower())
            if _BASIC_HEADING_RE.match(clean_ln):
                recognized_sections.add(clean_ln.lower().rstrip(":- "))

        if len(recognized_sections) == 0:
            warnings.append({
                "code": "missing_headings",
                "title": "Section headings not recognized",
                "message": "We could not find clear section headings in your resume.",
                "suggestion": "Use plain headings on their own lines: Education, Skills, Work Experience, and Certifications.",
            })

        # 5. Email or phone not found
        found_email = bool((data.get("email") or "").strip()) or bool(_EMAIL_FALLBACK_RE.search(text))
        found_phone = bool((data.get("phone") or "").strip()) or bool(_PHONE_FALLBACK_RE.search(text))
        if not found_email or not found_phone:
            if not found_email and not found_phone:
                missing_label = "email address or phone number"
            elif not found_email:
                missing_label = "email address"
            else:
                missing_label = "phone number"
            warnings.append({
                "code": "missing_contact",
                "title": f"Contact info missing ({missing_label})",
                "message": f"We could not find your {missing_label} in the uploaded file.",
                "suggestion": "Place your email and phone number in plain text at the top of page 1 (not inside an image, header, or footer), or enter them on the next step.",
            })

        # 6. Dates missing
        has_dates_in_text = bool(_DATE_RE.search(text))
        work_exps = data.get("work_experiences") or []
        edu_entries = data.get("education_entries") or []
        has_structured_dates = any(
            (isinstance(w, dict) and (w.get("start_date") or w.get("end_date") or w.get("duration")))
            for w in work_exps
        ) or any(
            (isinstance(e, dict) and (e.get("year") or e.get("graduation_year") or e.get("dates")))
            for e in edu_entries
        )
        if not has_dates_in_text and not has_structured_dates:
            warnings.append({
                "code": "missing_dates",
                "title": "Work or education dates not found",
                "message": "We could not detect clear dates for your jobs or education.",
                "suggestion": 'Write dates clearly next to each role or school, for example "Customer Service Representative, June 2023 - Present".',
            })

    if not warnings:
        return {
            "status": "ok",
            "summary": "Looks readable",
            "warnings": [],
        }

    return {
        "status": "warning",
        "summary": "We noticed a few things that may affect how your resume is read. You can still continue and edit any details on the next step.",
        "warnings": warnings,
    }
