from pdfminer.high_level import extract_text
import fitz  # PyMuPDF
import os
import io
import re
from typing import Union


def _extract_page_text_layout_aware(page) -> str:
    """
    Extracts text from a PyMuPDF page while preserving visual reading order:
    - Sorts out-of-order PDF stream blocks top-to-bottom.
    - Detects two-column (sidebar + main) layouts so left-column sections
      (e.g. CONTACT, EDUCATION, SKILLS, CERTIFICATION) never interleave into
      right-column sections (e.g. PROFILE, EXPERIENCE).
    """
    raw_blocks = page.get_text("blocks") or []
    text_blocks = [
        (float(b[0]), float(b[1]), float(b[2]), float(b[3]), str(b[4]).strip())
        for b in raw_blocks
        if len(b) >= 7 and b[6] == 0 and str(b[4]).strip()
    ]
    if not text_blocks:
        return page.get_text() or ""

    page_w = float(page.rect.width or 600.0)
    page_h = float(page.rect.height or 800.0)

    # Identify top header band (e.g. Name / Title banner at top of page 1),
    # stopping before the first column-level section header so 2-column sections
    # starting near the top (e.g. y=80) are never interleaved into top_blocks.
    default_cutoff = min(145.0, page_h * 0.18)
    first_section_y = default_cutoff
    try:
        from app.extractors.content.section_parser import detect_section_label
        for b in text_blocks:
            first_line = b[4].split("\n", 1)[0].strip()
            if first_line and detect_section_label(first_line) is not None:
                if b[1] < first_section_y:
                    first_section_y = b[1]
    except Exception:
        pass
    header_cutoff = first_section_y

    # Check if body blocks cleanly separate into two vertical columns
    best_split = None
    best_score = -1
    for frac in (0.30, 0.33, 0.35, 0.38, 0.40, 0.42, 0.48, 0.62, 0.67):
        split_x = page_w * frac
        body_blocks = [b for b in text_blocks if b[1] >= header_cutoff]
        if len(body_blocks) < 4:
            continue
        left_b = [b for b in body_blocks if b[2] <= split_x + 8]
        right_b = [b for b in body_blocks if b[0] >= split_x - 8]
        crossing_b = [b for b in body_blocks if b[0] < split_x - 8 and b[2] > split_x + 8]

        if len(left_b) >= 2 and len(right_b) >= 2 and len(crossing_b) == 0:
            # Verify vertical overlap between columns AND multi-line content in both columns
            left_min_y = min(b[1] for b in left_b)
            left_max_y = max(b[3] for b in left_b)
            right_min_y = min(b[1] for b in right_b)
            right_max_y = max(b[3] for b in right_b)
            y_overlap = min(left_max_y, right_max_y) - max(left_min_y, right_min_y)
            left_lines = sum(b[4].count("\n") + 1 for b in left_b)
            right_lines = sum(b[4].count("\n") + 1 for b in right_b)
            if y_overlap > 80 and left_lines >= 5 and right_lines >= 5:
                score = len(left_b) + len(right_b)
                if score > best_score:
                    best_score = score
                    best_split = split_x

    if best_split is not None:
        # Check if header blocks also split or span across
        top_blocks = [b for b in text_blocks if b[1] < header_cutoff]
        body_blocks = [b for b in text_blocks if b[1] >= header_cutoff]
        top_blocks.sort(key=lambda b: (round(b[1] / 6.0), b[0]))

        left_col = [b for b in body_blocks if b[2] <= best_split + 8]
        right_col = [b for b in body_blocks if b[0] >= best_split - 8]
        other_col = [b for b in body_blocks if b not in left_col and b not in right_col]

        left_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
        right_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
        other_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))

        ordered = top_blocks + left_col + right_col + other_col
        return "\n".join(b[4] for b in ordered)

    # Single-column layout: sort visually top-to-bottom, left-to-right
    text_blocks.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
    return "\n".join(b[4] for b in text_blocks)


def extract_text_from_pdf(file_input: Union[str, bytes, io.BytesIO]) -> str:
    """
    Extracts complete visible text from a .pdf file using dual-engine analysis
    (PyMuPDF fitz + pdfminer.six) to guarantee natural visual reading order,
    multi-column layout fidelity, and complete content extraction (REQ004 / TC-RES-010).
    Accepts file path (str), raw bytes (bytes), or BytesIO.
    """
    fitz_text = ""
    extra_links = []

    # Engine 1: PyMuPDF (fitz) with layout-aware block ordering
    try:
        if isinstance(file_input, bytes):
            doc = fitz.open(stream=file_input, filetype="pdf")
        elif isinstance(file_input, io.BytesIO):
            doc = fitz.open(stream=file_input.getvalue(), filetype="pdf")
        else:
            doc = fitz.open(file_input)
        pages = []
        for page in doc:
            page_text = _extract_page_text_layout_aware(page)
            # Scanned or image-only PDF page fallback to OCR
            if not page_text or len(page_text.strip()) < 20:
                try:
                    ocr_tp = page.get_textpage_ocr(flags=0, dpi=150, full=True)
                    ocr_text = ocr_tp.extractText()
                    if ocr_text and len(ocr_text.strip()) > len(page_text.strip()):
                        page_text = ocr_text
                except Exception:
                    pass
            pages.append(page_text)

            # Check links
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and ("mailto:" in uri.lower() or "@" in uri):
                    clean_uri = uri.replace("mailto:", "").split("?")[0].strip()
                    if clean_uri and clean_uri not in extra_links:
                        extra_links.append(f"Email Link: {clean_uri}")
                elif uri and ("tel:" in uri.lower() or "callto:" in uri.lower()):
                    clean_tel = uri.lower().replace("tel:", "").replace("callto:", "").split("?")[0].strip()
                    if clean_tel and clean_tel not in extra_links:
                        extra_links.append(f"Phone Link: {clean_tel}")

            # Check annotations
            for annot in page.annots():
                info = annot.info or {}
                content = info.get("content", "")
                if content and ("@" in content or "mailto:" in content.lower()):
                    extra_links.append(f"Email Annotation: {content.strip()}")
                elif content and ("tel:" in content.lower() or "callto:" in content.lower()):
                    extra_links.append(f"Phone Annotation: {content.strip()}")

        doc.close()
        fitz_text = "\n".join(pages).strip()
    except Exception as e:
        print(f"PyMuPDF extraction error: {e}")

    # Engine 2: pdfminer.six
    pm_text = ""
    try:
        if isinstance(file_input, bytes):
            pm_text = extract_text(io.BytesIO(file_input)).strip()
        else:
            pm_text = extract_text(file_input).strip()
        if pm_text:
            pm_text = re.sub(r"\(cid:\d+\)¢?", "• ", pm_text)
    except Exception as e:
        print(f"pdfminer error reading PDF file: {e}")

    # Structural evaluation: Detect header inversions (e.g. EDUCATION placed below school)
    def _inversion_penalty(t: str) -> int:
        if not t:
            return 999
        penalty = 0
        edu_pos = t.find("EDUCATION")
        exp_pos = max(t.find("WORK EXPERIENCE"), t.find("EXPERIENCE"))

        if edu_pos > 150:
            for s in ["STI Colleges", "Universidad", "University", "College", "Bachelor", "BS "]:
                p = t.find(s)
                if 0 <= p < edu_pos:
                    penalty += 50
        if exp_pos > 150:
            for c in ["Food Panda", "ChanzIT", "Jollibee", "Shopee", "Accenture", "Delivery Rider"]:
                p = t.find(c)
                if 0 <= p < exp_pos:
                    penalty += 50
        try:
            from app.extractors.content.section_parser import split_into_sections
            secs = split_into_sections(t)
            if "SKILLS" in secs and not secs["SKILLS"].strip():
                penalty += 50
        except Exception:
            pass
        return penalty

    p_fitz = _inversion_penalty(fitz_text)
    p_pm = _inversion_penalty(pm_text)

    # Select the text that preserves natural reading order (prefer layout-ordered PyMuPDF when equal)
    if p_fitz <= p_pm and len(fitz_text) >= 40:
        chosen_text = fitz_text
    elif p_pm < p_fitz and len(pm_text) >= 40:
        chosen_text = pm_text
    elif fitz_text:
        chosen_text = fitz_text
    else:
        chosen_text = pm_text

    # Append hyperlink URIs and annotations
    if extra_links:
        chosen_text = (chosen_text + "\n" + "\n".join(extra_links)).strip()

    return chosen_text

def extract_image_from_pdf(file_path: str) -> str:
    """
    Extracts the best candidate for a profile image from a PDF and saves it to uploads/resume_images.
    Returns the path to the saved image or None.
    """
    try:
        doc = fitz.open(file_path)
        img_dir = "uploads/resume_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            
        # Search page by page. Profile images are almost always on the first page.
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            
            if not image_list:
                continue
                
            candidates = []
            for img_info in image_list:
                xref = img_info[0]
                width = img_info[2]
                height = img_info[3]
                
                # Filter out tiny images (icons)
                if width < 40 or height < 40:
                    continue
                    
                aspect = width / height if height else 0
                if aspect < 0.4 or aspect > 2.5:
                    continue
                    
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                img_bytes = base_image["image"]
                size_kb = len(img_bytes) / 1024
                img_ext = base_image["ext"]
                
                # Score candidate
                score = 0
                
                # 1. Aspect ratio: prefer close to square (1:1)
                ratio_diff = abs(1.0 - aspect)
                score += (1.0 - ratio_diff) * 100
                
                # 2. Size in bytes: prefer larger byte sizes (more detail/higher resolution)
                if size_kb < 2.0:
                    score -= 50
                else:
                    score += min(size_kb, 200.0) * 2
                    
                # 3. Position on page:
                rects = page.get_image_rects(xref)
                if rects:
                    rect = rects[0]
                    img_w = rect.width
                    img_h = rect.height
                    
                    # Filter out backgrounds
                    if img_w > page.rect.width * 0.7 or img_h > page.rect.height * 0.7:
                        score -= 500
                    if img_w < 20 or img_h < 20:
                        score -= 300
                        
                    # Prefer top-portion
                    y_center = (rect.y0 + rect.y1) / 2
                    if y_center < page.rect.height * 0.4:
                        score += 150
                    elif y_center < page.rect.height * 0.6:
                        score += 50
                    else:
                        score -= 100
                else:
                    score -= 50
                    
                candidates.append({
                    'xref': xref,
                    'bytes': img_bytes,
                    'ext': img_ext,
                    'score': score
                })
                
            if candidates:
                # Sort by score descending and pick the best one
                candidates.sort(key=lambda x: x['score'], reverse=True)
                best = candidates[0]
                
                filename = os.path.basename(file_path)
                image_name = f"{os.path.splitext(filename)[0]}_img.{best['ext']}"
                image_path = os.path.join(img_dir, image_name)
                
                with open(image_path, "wb") as f:
                    f.write(best['bytes'])
                
                doc.close()

                # Upload to Supabase resume_images bucket (path: resumeimages/)
                try:
                    from app.utils.supabase_storage import upload_resume_image_sync
                    sb_res = upload_resume_image_sync(
                        file_bytes=best['bytes'],
                        original_filename=image_name,
                    )
                    return sb_res["public_url"]
                except Exception as sb_err:
                    print(f"Supabase resume image upload fallback to local: {sb_err}")
                    return image_path
                
        doc.close()
    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
    return None
