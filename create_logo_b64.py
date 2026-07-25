import base64
import os

logo_path = os.path.join('assets', 'images', 'logo.png')
with open(logo_path, 'rb') as f:
    b64_str = base64.b64encode(f.read()).decode('utf-8')

with open('logo_b64.py', 'w') as f:
    f.write(f"LOGO_B64 = '{b64_str}'\n")

print("Generated logo_b64.py")
