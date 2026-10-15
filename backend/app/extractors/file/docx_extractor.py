import docx
import zipfile
import os
import re
import fitz

def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from a .docx file using python-docx.
    Includes headers, footers, tables, text frames/boxes, and hyperlink targets.
    """
    try:
        doc = docx.Document(file_path)
        full_text = []

        # 1. Section Headers (where candidate contact info & email frequently reside)
        for section in doc.sections:
            try:
                for hp in section.header.paragraphs:
                    if hp.text.strip():
                        full_text.append(hp.text.strip())
                for ht in section.header.tables:
                    for row in ht.rows:
                        row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_cells:
                            full_text.append(" | ".join(row_cells))
            except Exception:
                pass

        # 2. Main body paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())

        # 3. Main body tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    full_text.append(" | ".join(row_cells))

        # 4. Text frames and shapes/textboxes (sidebar/contact cards)
        try:
            for txbx in doc.element.xpath('.//w:txbxContent'):
                for p in txbx.xpath('.//w:p'):
                    p_text = "".join(node.text for node in p.xpath('.//w:t') if node.text)
                    if p_text.strip():
                        full_text.append(p_text.strip())
        except Exception:
            pass

        # 5. Section Footers
        for section in doc.sections:
            try:
                for fp in section.footer.paragraphs:
                    if fp.text.strip():
                        full_text.append(fp.text.strip())
            except Exception:
                pass

        # 6. Document relationships / Hyperlinks (e.g. mailto: or tel: links)
        try:
            for rel in doc.part.rels.values():
                if "hyperlink" in getattr(rel, "reltype", "").lower():
                    target = getattr(rel, "target_ref", "")
                    if target and ("mailto:" in target.lower() or "@" in target):
                        clean_target = target.replace("mailto:", "").split("?")[0].strip()
                        if clean_target:
                            full_text.append(f"Email Link: {clean_target}")
                    elif target and ("tel:" in target.lower() or "callto:" in target.lower()):
                        clean_tel = target.lower().replace("tel:", "").replace("callto:", "").split("?")[0].strip()
                        if clean_tel:
                            full_text.append(f"Phone Link: {clean_tel}")
        except Exception:
            pass

        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error reading DOCX file: {e}")
        return ""

def extract_image_from_docx(file_path: str) -> str | None:
    """
    Extracts the best candidate for a profile image from a DOCX file.
    Saves it to uploads/resume_images.
    Returns the path to the saved image or None.
    """
    try:
        if not zipfile.is_zipfile(file_path):
            return None
            
        img_dir = "uploads/resume_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            
        candidates = []
        with zipfile.ZipFile(file_path, 'r') as z:
            # All images in DOCX are stored in word/media/
            for member in z.infolist():
                if member.filename.startswith('word/media/'):
                    # Read image bytes
                    img_bytes = z.read(member.filename)
                    size_kb = len(img_bytes) / 1024
                    
                    # Try to parse dimensions using PyMuPDF (fitz)
                    try:
                        pix = fitz.Pixmap(img_bytes)
                        width = pix.width
                        height = pix.height
                        pix = None # free resources
                    except Exception as e:
                        print(f"DEBUG: fitz could not load docx image {member.filename}: {e}")
                        continue
                        
                    # Filter out tiny images (icons)
                    if width < 40 or height < 40:
                        continue
                        
                    aspect = width / height if height else 0
                    if aspect < 0.4 or aspect > 2.5:
                        continue
                        
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
                        
                    # 3. Filename order: images are numbered in order of appearance in DOCX
                    # Prioritize earlier images (like image1.png vs image5.png)
                    num_match = re.search(r'image(\d+)', os.path.basename(member.filename))
                    if num_match:
                        index = int(num_match.group(1))
                        # Prioritize earlier images:
                        score += max(0, 50 - index * 5)
                        
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
            
            # Determine extension from member.filename
            _, img_ext = os.path.splitext(best['filename'])
            img_ext = img_ext.strip('.')
            if not img_ext:
                img_ext = 'png'
                
            filename = os.path.basename(file_path)
            image_name = f"{os.path.splitext(filename)[0]}_img.{img_ext}"
            image_path = os.path.join(img_dir, image_name)
            
            with open(image_path, "wb") as f:
                f.write(best['bytes'])
                
            print(f"DEBUG: Extracted DOCX profile image: {image_name} (score: {best['score']:.2f})")

            # Upload to Supabase resume_images bucket (path: resumeimages/)
            try:
                from app.utils.supabase_storage import upload_resume_image_sync
                sb_res = upload_resume_image_sync(
                    file_bytes=best['bytes'],
                    original_filename=image_name,
                )
                print(f"DEBUG: Uploaded DOCX profile image to Supabase: {sb_res['public_url']}")
                return sb_res["public_url"]
            except Exception as sb_err:
                print(f"Supabase DOCX profile image upload fallback to local: {sb_err}")
                return image_path
            
    except Exception as e:
        print(f"Error extracting image from DOCX: {e}")
        
    return None

