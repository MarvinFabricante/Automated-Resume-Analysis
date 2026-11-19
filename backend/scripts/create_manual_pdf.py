import os
import sys
import base64
import subprocess
import time
import fitz

def load_base64_image(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

logo_b64 = load_base64_image("frontend/public/assets/logo.png")
erd_b64 = load_base64_image("erd_output.png")

print(f"Loaded logo: {bool(logo_b64)}, ERD: {bool(erd_b64)}")
