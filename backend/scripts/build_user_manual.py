import os
import sys
import base64
import subprocess
import fitz

# Read logo if exists
logo_b64 = ""
logo_path = "frontend/public/assets/logo.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode("utf-8")

erd_b64 = ""
erd_path = "erd_output.png"
if os.path.exists(erd_path):
    with open(erd_path, "rb") as f:
        erd_b64 = base64.b64encode(f.read()).decode("utf-8")

print(f"Loaded assets: logo ({len(logo_b64)} chars), ERD ({len(erd_b64)} chars)")
