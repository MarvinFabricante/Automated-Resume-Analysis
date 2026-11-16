import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import base64
import subprocess
import time
import fitz

from scripts.manual_builder.styles import get_css
from scripts.manual_builder.cover import get_cover_html
from scripts.manual_builder.ch1_overview import get_ch1_html
from scripts.manual_builder.ch2_access import get_ch2_html
from scripts.manual_builder.ch3_candidate import get_ch3_html
from scripts.manual_builder.ch4_hr import get_ch4_html
from scripts.manual_builder.ch5_admin import get_ch5_html
from scripts.manual_builder.ch6_ai_engine import get_ch6_html
from scripts.manual_builder.ch7_ops import get_ch7_html
from scripts.manual_builder.ch8_troubleshooting import get_ch8_html

def load_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

print("Loading image assets...")
logo_b64 = load_b64("frontend/public/assets/logo.png")
erd_b64 = load_b64("erd_output.png")

print("Assembling HTML document...")
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Automated Resume Analysis System — Enterprise User Manual</title>
    <style>
        {get_css()}
    </style>
</head>
<body>
    {get_cover_html(logo_b64)}
    {get_ch1_html(erd_b64)}
    {get_ch2_html()}
    {get_ch3_html()}
    {get_ch4_html()}
    {get_ch5_html()}
    {get_ch6_html()}
    {get_ch7_html()}
    {get_ch8_html()}
</body>
</html>
"""

html_path = "/tmp/aras_user_manual.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Wrote {len(html_content)} characters to {html_path}")

raw_pdf_path = "/tmp/aras_raw.pdf"
output_pdf_path = "/home/marvin/Documents/automated_resume_analysis/Automated_Resume_Analysis_User_Manual.pdf"

print("Compiling HTML to PDF via headless Google Chrome...")
chrome_cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--no-pdf-header-footer",
    f"--print-to-pdf={raw_pdf_path}",
    html_path
]

res = subprocess.run(chrome_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Chrome compilation failed:", res.stderr)
    sys.exit(1)

print(f"Raw PDF compiled successfully: {os.path.getsize(raw_pdf_path)} bytes")

print("Stamping running headers, footers, divider lines and page numbers via PyMuPDF...")
doc = fitz.open(raw_pdf_path)
total_pages = len(doc)
print(f"Total document pages: {total_pages}")

# Header & Footer styling parameters
hdr_color = (0.2, 0.25, 0.35)
rule_color = (0.82, 0.85, 0.90)
ftr_color = (0.35, 0.40, 0.50)

for idx in range(total_pages):
    if idx == 0:
        continue  # Skip cover page
        
    page = doc[idx]
    rect = page.rect
    page_num = idx + 1
    
    # Running Header
    hdr_left = "AUTOMATED RESUME ANALYSIS SYSTEM — OPERATIONS MANUAL"
    hdr_right = "MARIWASA SIAM CERAMICS INC."
    
    page.insert_text((42, 32), hdr_left, fontsize=7.5, color=hdr_color)
    # Estimate width for right alignment
    page.insert_text((rect.width - 195, 32), hdr_right, fontsize=7.5, color=(0.15, 0.30, 0.70))
    
    # Header Rule Line
    page.draw_line((42, 38), (rect.width - 42, 38), color=rule_color, width=0.65)
    
    # Footer Rule Line
    page.draw_line((42, rect.height - 38), (rect.width - 42, rect.height - 38), color=rule_color, width=0.65)
    
    # Running Footer
    ftr_left = "Standard Operating Procedure & End-User System Guide"
    ftr_center = "RESTRICTED / INTERNAL BUSINESS USE"
    ftr_right = f"Page {page_num} of {total_pages}"
    
    page.insert_text((42, rect.height - 25), ftr_left, fontsize=7.5, color=ftr_color)
    page.insert_text((rect.width / 2 - 75, rect.height - 25), ftr_center, fontsize=7, color=(0.55, 0.60, 0.70))
    page.insert_text((rect.width - 100, rect.height - 25), ftr_right, fontsize=7.5, color=hdr_color)

doc.save(output_pdf_path)
print(f"SUCCESS! Professional User Manual written to: {output_pdf_path}")
print(f"Final PDF Size: {os.path.getsize(output_pdf_path)} bytes with {total_pages} pages.")
