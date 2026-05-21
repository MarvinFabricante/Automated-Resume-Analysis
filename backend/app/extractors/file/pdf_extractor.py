from pdfminer.high_level import extract_text
import fitz  # PyMuPDF
import os

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a .pdf file using pdfminer.six.
    """
    try:
        text = extract_text(file_path)
        return text
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return ""

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
                return image_path
                
        doc.close()
    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
    return None
