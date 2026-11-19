import base64
with open('frontend/public/assets/logo.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')
print("Logo base64 verified, size:", len(b64))
