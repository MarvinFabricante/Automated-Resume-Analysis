import docx
import zipfile
import os
import re
import fitz
import subprocess
import tempfile
import shutil
import logging
from typing import List, Tuple, Set, Optional

logger = logging.getLogger(__name__)


def _convert_doc_to_docx(file_path: str) -> Optional[str]:
    """
    Attempts to convert a legacy binary .doc file to modern .docx
    using LibreOffice/soffice in headless mode.
    Returns the path to the converted .docx file (located in a temporary directory),
    or None if conversion failed or LibreOffice is not installed.
    """
    try:
        # Check if already a valid zip (a .docx file simply misnamed as .doc)
        if zipfile.is_zipfile(file_path):
            return file_path

        soffice_bin = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice_bin:
            logger.warning("Neither soffice nor libreoffice is available for .doc conversion.")
            return None

        tmp_dir = tempfile.mkdtemp(prefix="doc_conv_")
        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to", "docx",
            "--outdir", tmp_dir,
            file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if res.returncode == 0:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            converted_path = os.path.join(tmp_dir, f"{base_name}.docx")
            if os.path.exists(converted_path) and zipfile.is_zipfile(converted_path):
                return converted_path
        logger.warning(f"LibreOffice conversion failed for {file_path}: {res.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"Error converting .doc to .docx: {e}")
    return None


def _extract_text_from_legacy_or_rtf(file_path: str) -> str:
    """
    Direct stream text extraction for legacy binary Word (.doc OLE CFBF)
    or Rich Text Format (.rtf) files when LibreOffice is not available.
    Extracts UTF-16LE and ASCII text blocks without corrupting encoding.
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # Check for Rich Text Format
        if data.startswith(b"{\\rtf"):
            text_str = data.decode("latin-1", errors="ignore")
            text_str = re.sub(r'\\([a-z]{1,32})(-?\d+)? ?', ' ', text_str)
            text_str = re.sub(r'[{}]', '', text_str)
            text_str = re.sub(r'\\\n', '\n', text_str)
            return text_str.strip()

        # Check for OLE2 CFBF (.doc) or generic binary document stream
        if data.startswith(b"\xd0\xcf\x11\xe0") or b"WordDocument" in data[:2048]:
            utf16_strings = []
            for match in re.finditer(b'(?:[\x20-\x7E]\x00){4,}', data):
                try:
                    s = match.group(0).decode('utf-16le', errors='ignore').strip()
                    if len(s) > 3 and not s.startswith(('Root Entry', 'WordDocument', 'Table', 'Data')):
                        utf16_strings.append(s)
                except Exception:
                    pass

            ascii_strings = []
            for match in re.finditer(b'[\x20-\x7E\r\n\t]{4,}', data):
                try:
                    s = match.group(0).decode('ascii', errors='ignore').strip()
                    if len(s) > 3 and not s.startswith(('Root Entry', 'WordDocument', 'Table', 'Data', 'SummaryInformation')):
                        ascii_strings.append(s)
                except Exception:
                    pass

            combined = []
            for s in utf16_strings:
                if s not in combined:
                    combined.append(s)
            for s in ascii_strings:
                if s not in combined:
                    combined.append(s)

            return "\n".join(combined).strip()
    except Exception as e:
        logger.warning(f"Error in legacy doc/rtf fallback extraction: {e}")
    return ""


def _format_para_text(p_elem, doc_obj: docx.Document) -> str:
    """
    Extracts text from a Word paragraph XML element while preserving:
    - Bullet and numbered list markers (•) from <w:numPr> or list styles
    - Soft line breaks (<w:br/>) and tabs (<w:tab/>)
    """
    try:
        p = docx.text.paragraph.Paragraph(p_elem, doc_obj)
        txt = p.text.strip()
        if not txt:
            return ""

        # Check if paragraph has bullet or numbering properties
        has_num = bool(p_elem.xpath('.//*[local-name()="numPr"]'))
        style_name = ""
        try:
            if p.style and p.style.name:
                style_name = p.style.name.lower()
        except Exception:
            pass

        is_list = has_num or "bullet" in style_name or "list" in style_name
        if is_list:
            # Prepend bullet if it does not already start with a bullet glyph or number
            if not txt.startswith(("•", "-", "*", "▪", "►", "✓", "◆", "■", "□", "▸", "▹", "–", "—")) and not re.match(r'^\d+[\.\)]\s*', txt):
                txt = f"• {txt}"

        return txt
    except Exception:
        # Fallback to direct text nodes
        parts = [n.text for n in p_elem.xpath('.//*[local-name()="t"]') if n.text]
        return "".join(parts).strip()


def _extract_textboxes_from_elem(elem) -> List[str]:
    """
    Extracts text strings from all textboxes (DrawingML and legacy VML)
    anchored inside an element, using local-name() to be namespace-agnostic.
    """
    tb_texts = []
    try:
        # DrawingML textboxes: <w:txbxContent>
        # VML textboxes: <v:textbox>
        txbxs = elem.xpath('.//*[local-name()="txbxContent" or local-name()="textbox"]')
        for txbx in txbxs:
            for p in txbx.xpath('.//*[local-name()="p"]'):
                p_text = "".join(node.text for node in p.xpath('.//*[local-name()="t"]') if node.text).strip()
                if p_text:
                    # Check for bullets inside textbox
                    has_num = bool(p.xpath('.//*[local-name()="numPr"]'))
                    if has_num and not p_text.startswith(("•", "-", "*", "▪", "►", "✓")) and not re.match(r'^\d+[\.\)]\s*', p_text):
                        p_text = f"• {p_text}"
                    tb_texts.append(p_text)
    except Exception as e:
        logger.debug(f"Error extracting textboxes from element: {e}")
    return tb_texts


def _extract_cell_text(cell_elem, doc_obj: docx.Document) -> str:
    """
    Extracts text from all child paragraphs and nested tables inside a table cell,
    preserving paragraph boundaries and anchored textboxes.
    """
    lines = []
    try:
        for child in cell_elem:
            tag = child.tag.split('}')[-1]
            if tag == 'p':
                # Anchored textboxes inside this cell paragraph
                for tb in _extract_textboxes_from_elem(child):
                    if tb and tb not in lines:
                        lines.append(tb)
                t = _format_para_text(child, doc_obj)
                if t:
                    lines.append(t)
            elif tag == 'tbl':
                nested_tbl_lines = _extract_table_text(child, doc_obj)
                lines.extend(nested_tbl_lines)
    except Exception as e:
        logger.debug(f"Error extracting cell text: {e}")
    return '\n'.join(lines)


def _extract_table_text(tbl_elem, doc_obj: docx.Document) -> List[str]:
    """
    Extracts text from a table element:
    1. Deduplicates merged cells (gridSpan) to prevent repeating section headers.
    2. Detects multi-column layout tables (resume columns) vs tabular data tables:
       - Multi-column layout rows: each column cell is extracted vertically,
         preserving headings and bullet lists intact on their own lines.
       - Tabular data rows: cells are single short phrases and joined with ' | '.
    """
    tbl_lines = []
    try:
        tbl = docx.table.Table(tbl_elem, doc_obj)
        for row in tbl.rows:
            # Deduplicate horizontally merged cells
            unique_cells = []
            for c in row.cells:
                if not unique_cells or c._tc != unique_cells[-1]._tc:
                    unique_cells.append(c)

            if not unique_cells:
                continue

            # Check if this row is a layout row (multi-column resume layout)
            # A row is a layout row if ANY cell has multiple lines/paragraphs or is long (> 100 chars)
            is_layout = False
            cell_texts = []
            for c in unique_cells:
                ctxt = _extract_cell_text(c._tc, doc_obj).strip()
                cell_texts.append(ctxt)
                if '\n' in ctxt or len(ctxt) > 100:
                    is_layout = True

            if is_layout:
                # Vertical extraction for multi-column resume layout
                for ctxt in cell_texts:
                    if ctxt:
                        tbl_lines.append(ctxt)
            else:
                # Tabular data row (e.g. Role | Company | Dates)
                row_items = [t for t in cell_texts if t]
                if row_items:
                    tbl_lines.append(" | ".join(row_items))
    except Exception as e:
        logger.debug(f"Error extracting table text: {e}")
    return tbl_lines


def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from a .docx (or converted .doc) file with high fidelity matching PDF extraction:
    - Traverses document body elements in true reading order (paragraphs, tables, content controls).
    - Checks first page headers and normal headers (where candidate contact info commonly resides).
    - Formats bullets and lists (•) to match downstream NLP parser expectations.
    - Accurately splits multi-column resume layout tables and single-line tabular rows.
    - Handles Structured Document Tags (<w:sdt>) used in official Word resume templates.
    - Extracts textboxes (DrawingML & legacy VML) without dropping content.
    - Captures hyperlink target URIs (mailto:, tel:, LinkedIn, GitHub, portfolios).
    """
    tmp_converted_file = None
    try:
        target_path = file_path
        if not zipfile.is_zipfile(file_path):
            converted = _convert_doc_to_docx(file_path)
            if converted:
                target_path = converted
                tmp_converted_file = converted
            else:
                fallback_txt = _extract_text_from_legacy_or_rtf(file_path)
                if fallback_txt and len(fallback_txt.strip()) > 10:
                    return fallback_txt
                logger.warning(f"File {file_path} is not a valid zip and cannot be converted.")
                return ""

        doc = docx.Document(target_path)
        full_text: List[str] = []
        seen_headers: Set[str] = set()

        # ── 1. Section Headers (first_page_header & header) ───────────────────
        for section in doc.sections:
            headers_to_check = []
            try:
                if getattr(section, 'different_first_page_header_footer', False):
                    headers_to_check.append(section.first_page_header)
                headers_to_check.append(section.header)
                if getattr(section, 'even_page_header', None):
                    headers_to_check.append(section.even_page_header)
            except Exception:
                pass

            for h in headers_to_check:
                try:
                    for hp in h.paragraphs:
                        # Check anchored textboxes in header
                        for tb in _extract_textboxes_from_elem(hp._element):
                            if tb and tb not in seen_headers:
                                seen_headers.add(tb)
                                full_text.append(tb)
                        t = _format_para_text(hp._element, doc)
                        if t and t not in seen_headers:
                            seen_headers.add(t)
                            full_text.append(t)
                    for ht in h.tables:
                        tbl_lines = _extract_table_text(ht._element, doc)
                        for tl in tbl_lines:
                            if tl and tl not in seen_headers:
                                seen_headers.add(tl)
                                full_text.append(tl)
                except Exception:
                    pass

        # ── 2. Sequential Body Traversal (p, tbl, sdt in document order) ───────
        def process_body_element(elem):
            tag = elem.tag.split('}')[-1]
            if tag == 'p':
                # Check anchored textboxes inside this paragraph
                for tb in _extract_textboxes_from_elem(elem):
                    if tb and tb not in full_text:
                        full_text.append(tb)
                txt = _format_para_text(elem, doc)
                if txt:
                    full_text.append(txt)
            elif tag == 'tbl':
                tbl_lines = _extract_table_text(elem, doc)
                full_text.extend(tbl_lines)
            elif tag == 'sdt':
                # Structured Document Tag (Content Control)
                for sdt_content in elem.xpath('.//*[local-name()="sdtContent"]'):
                    for child in sdt_content:
                        process_body_element(child)

        try:
            for elem in doc._element.body:
                process_body_element(elem)
        except Exception as e:
            logger.warning(f"Error traversing body elements in DOCX: {e}")
            # Fallback to standard doc.paragraphs and doc.tables if body iteration failed
            for p in doc.paragraphs:
                t = _format_para_text(p._element, doc)
                if t:
                    full_text.append(t)
            for t in doc.tables:
                full_text.extend(_extract_table_text(t._element, doc))

        # ── 3. Standalone / Floating Textboxes (Catch any unvisited shapes) ─────
        try:
            standalone_tb = []
            for txbx in doc.element.xpath('.//*[local-name()="txbxContent" or local-name()="textbox"]'):
                for p in txbx.xpath('.//*[local-name()="p"]'):
                    p_text = "".join(node.text for node in p.xpath('.//*[local-name()="t"]') if node.text).strip()
                    if p_text and p_text not in full_text and p_text not in seen_headers:
                        standalone_tb.append(p_text)
            if standalone_tb:
                # If standalone textboxes contain contact keywords (@, phone, contact),
                # place them near the top after headers to ensure candidate identification
                has_contact_info = any("@" in t or re.search(r'\b(?:09|\+63|\d{7,})\b', t) for t in standalone_tb)
                if has_contact_info:
                    header_len = len(seen_headers)
                    full_text[header_len:header_len] = standalone_tb
                else:
                    full_text.extend(standalone_tb)
        except Exception:
            pass

        # ── 4. Section Footers ────────────────────────────────────────────────
        for section in doc.sections:
            footers_to_check = []
            try:
                if getattr(section, 'different_first_page_header_footer', False):
                    footers_to_check.append(section.first_page_footer)
                footers_to_check.append(section.footer)
            except Exception:
                pass

            for f in footers_to_check:
                try:
                    for fp in f.paragraphs:
                        t = _format_para_text(fp._element, doc)
                        if t and t not in full_text:
                            full_text.append(t)
                    for ft in f.tables:
                        tbl_lines = _extract_table_text(ft._element, doc)
                        for tl in tbl_lines:
                            if tl and tl not in full_text:
                                full_text.append(tl)
                except Exception:
                    pass

        # ── 5. Document relationships / Hyperlinks (email, phone, portfolios) ─
        try:
            extra_links: List[str] = []
            for rel in doc.part.rels.values():
                if "hyperlink" in getattr(rel, "reltype", "").lower():
                    target = getattr(rel, "target_ref", "")
                    if not target:
                        continue
                    t_lower = target.lower()
                    if "mailto:" in t_lower or "@" in target:
                        clean_target = target.replace("mailto:", "").split("?")[0].strip()
                        if clean_target and clean_target not in full_text:
                            extra_links.append(f"Email Link: {clean_target}")
                    elif "tel:" in t_lower or "callto:" in t_lower:
                        clean_tel = t_lower.replace("tel:", "").replace("callto:", "").split("?")[0].strip()
                        if clean_tel and clean_tel not in full_text:
                            extra_links.append(f"Phone Link: {clean_tel}")
                    elif any(domain in t_lower for domain in ["linkedin.com", "github.com", "gitlab.com", "behance.net", "portfolio"]):
                        clean_url = target.split("?")[0].strip()
                        if clean_url and clean_url not in full_text:
                            extra_links.append(f"Profile Link: {clean_url}")

            if extra_links:
                full_text.extend(extra_links)
        except Exception:
            pass

        return '\n'.join(full_text)
    except Exception as e:
        logger.error(f"Error reading DOCX file: {e}")
        return ""
    finally:
        # Clean up temporary converted file if LibreOffice was used
        if tmp_converted_file and os.path.exists(tmp_converted_file):
            try:
                parent_dir = os.path.dirname(tmp_converted_file)
                shutil.rmtree(parent_dir, ignore_errors=True)
            except Exception:
                pass


def extract_image_from_docx(file_path: str) -> Optional[str]:
    """
    Extracts the best candidate for a candidate profile image from a DOCX file.
    - Inspects image appearance order in headers and document body.
    - Filters out icons, non-photo formats (.emf, .wmf, .svg), and background banners.
    - Scores candidate images by aspect ratio (preferring 1:1, 2x2, or 3:4 portrait),
      file size, resolution, and document position.
    - Saves the selected image to uploads/resume_images and uploads to Supabase.
    """
    tmp_converted_file = None
    try:
        target_path = file_path
        if not zipfile.is_zipfile(file_path):
            converted = _convert_doc_to_docx(file_path)
            if converted:
                target_path = converted
                tmp_converted_file = converted
            else:
                return None

        img_dir = "uploads/resume_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

        # Parse image reference order from header and document relationship files
        ordered_media: List[str] = []
        with zipfile.ZipFile(target_path, 'r') as z:
            header_rels = [n for n in z.namelist() if n.startswith('word/_rels/header') and n.endswith('.rels')]
            doc_rels = [n for n in z.namelist() if n == 'word/_rels/document.xml.rels']
            for rf in header_rels + doc_rels:
                try:
                    content = z.read(rf).decode('utf-8', errors='ignore')
                    for match in re.finditer(r'Target="([^"]+)"', content):
                        target = match.group(1).replace('../media/', 'word/media/').replace('media/', 'word/media/')
                        if target.startswith('word/media/') and target not in ordered_media:
                            ordered_media.append(target)
                except Exception:
                    pass

            candidates = []
            for member in z.infolist():
                if member.filename.startswith('word/media/'):
                    fn_lower = member.filename.lower()
                    # Skip vector clip art and non-raster formats
                    if fn_lower.endswith(('.emf', '.wmf', '.svg', '.xml', '.bin', '.rels')):
                        continue

                    img_bytes = z.read(member.filename)
                    size_kb = len(img_bytes) / 1024

                    # Try to parse dimensions using PyMuPDF (fitz)
                    try:
                        pix = fitz.Pixmap(img_bytes)
                        width = pix.width
                        height = pix.height
                        pix = None  # Free resources
                    except Exception as e:
                        logger.debug(f"fitz could not parse image {member.filename}: {e}")
                        continue

                    # Filter out tiny images (social icons, bullets, divider dots)
                    if width < 40 or height < 40:
                        continue

                    aspect = width / height if height else 0
                    # Filter out extreme aspect ratios (divider lines, wide banners, tall borders)
                    if aspect < 0.4 or aspect > 2.5:
                        continue

                    # Score candidate
                    score = 0.0

                    # 1. Aspect ratio: strong preference for portrait/square resume photos (0.75 - 1.35)
                    ratio_diff = abs(1.0 - aspect)
                    if 0.70 <= aspect <= 1.35:
                        score += 150.0 - (ratio_diff * 40.0)
                    elif 0.50 <= aspect < 0.70 or 1.35 < aspect <= 1.80:
                        score += 60.0 - (ratio_diff * 30.0)
                    else:
                        score -= 50.0

                    # 2. Appearance order: images in headers or referenced first in document get bonus
                    if member.filename in ordered_media:
                        order_idx = ordered_media.index(member.filename)
                        if any(h in member.filename for h in header_rels) or order_idx == 0:
                            score += 120.0
                        elif order_idx < 3:
                            score += 80.0
                        else:
                            score += max(0.0, 40.0 - order_idx * 5.0)
                    else:
                        num_match = re.search(r'image(\d+)', os.path.basename(member.filename))
                        if num_match:
                            index = int(num_match.group(1))
                            score += max(0.0, 50.0 - index * 5.0)

                    # 3. Size in bytes: prefer larger byte sizes (more detail/higher resolution)
                    score += min(size_kb, 300.0) * 1.5

                    # 4. Ideal photo dimensions (100px to 1200px)
                    if 100 <= width <= 1200 and 100 <= height <= 1200:
                        score += 50.0

                    candidates.append({
                        'filename': member.filename,
                        'bytes': img_bytes,
                        'score': score,
                        'size_kb': size_kb,
                        'width': width,
                        'height': height
                    })

        if candidates:
            # Sort by score descending
            candidates.sort(key=lambda x: x['score'], reverse=True)
            best = candidates[0]

            _, img_ext = os.path.splitext(best['filename'])
            img_ext = img_ext.strip('.').lower()
            if not img_ext or img_ext in ('jpeg', 'jpg'):
                img_ext = 'jpg'

            orig_name = os.path.basename(file_path)
            clean_base = os.path.splitext(orig_name)[0]
            image_name = f"{clean_base}_img.{img_ext}"
            image_path = os.path.join(img_dir, image_name)

            with open(image_path, "wb") as f:
                f.write(best['bytes'])

            logger.info(f"Extracted DOCX profile image: {image_name} (score: {best['score']:.2f}, size: {best['size_kb']:.1f}KB, {best['width']}x{best['height']})")

            # Upload to Supabase resume_images bucket if available
            try:
                from app.utils.supabase_storage import upload_resume_image_sync
                sb_res = upload_resume_image_sync(
                    file_bytes=best['bytes'],
                    original_filename=image_name,
                )
                if sb_res and "public_url" in sb_res:
                    return sb_res["public_url"]
            except Exception as sb_err:
                logger.debug(f"Supabase DOCX profile image upload fallback to local: {sb_err}")

            return image_path

    except Exception as e:
        logger.warning(f"Error extracting image from DOCX: {e}")
    finally:
        if tmp_converted_file and os.path.exists(tmp_converted_file):
            try:
                parent_dir = os.path.dirname(tmp_converted_file)
                shutil.rmtree(parent_dir, ignore_errors=True)
            except Exception:
                pass

    return None
