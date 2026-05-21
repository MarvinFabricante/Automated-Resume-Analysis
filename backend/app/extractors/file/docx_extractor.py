import docx
import zipfile
import os
import re
import fitz

def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from a .docx file using python-docx.
    """
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
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
            return image_path
            
    except Exception as e:
        print(f"Error extracting image from DOCX: {e}")
        
    return None

