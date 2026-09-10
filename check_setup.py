"""
Setup Verification Script
Run this first to confirm all dependencies are installed correctly.
Usage: python check_setup.py
"""

import sys

print("=" * 60)
print("   OmniDoc Studio - Dependency Checker  v2.0")
print("=" * 60)

results = []


def check(name, fn):
    try:
        fn()
        print(f"  [OK]   {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  [FAIL] {name}  --  {e}")
        results.append((name, False, str(e)))


# ── Python packages ────────────────────────────────────────────────────────
print("\n[Python Packages]")
check("pdf2image",       lambda: __import__("pdf2image"))
check("paddleocr",       lambda: __import__("paddleocr"))
check("paddlepaddle",    lambda: __import__("paddle"))
check("opencv (cv2)",    lambda: __import__("cv2"))
check("python-docx",     lambda: __import__("docx"))
check("openai",          lambda: __import__("openai"))
check("python-dotenv",   lambda: __import__("dotenv"))
check("tqdm",            lambda: __import__("tqdm"))
check("numpy",           lambda: __import__("numpy"))
check("Pillow",          lambda: __import__("PIL"))
check("rich",            lambda: __import__("rich"))
check("httpx",           lambda: __import__("httpx"))
check("customtkinter",   lambda: __import__("customtkinter"))
check("pikepdf",         lambda: __import__("pikepdf"))

# ── System tools ───────────────────────────────────────────────────────────
import os
print("\n[System Tools]")
poppler_paths = [
    r"C:\poppler\Library\bin",
    r"C:\poppler\bin",
]
poppler_ok = False
poppler_found_at = ""
for p in poppler_paths:
    if os.path.exists(os.path.join(p, "pdftoppm.exe")):
        poppler_ok = True
        poppler_found_at = p
        break

if poppler_ok:
    print(f"  [OK]   Poppler ({poppler_found_at})")
else:
    print(f"  [WARN] Poppler NOT FOUND at C:\\poppler\\bin or C:\\poppler\\Library\\bin")
    print(f"         Download: https://github.com/oschwartz10612/poppler-windows/releases")
    print(f"         Extract to C:\\poppler\\  (so C:\\poppler\\bin\\pdftoppm.exe exists)")

# ── Environment / API keys ────────────────────────────────────────────────
print("\n[Configuration]")
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY", "")
if api_key and api_key != "your_openrouter_api_key_here":
    print(f"  [OK]   OPENROUTER_API_KEY set in .env")
else:
    print(f"  [WARN] OPENROUTER_API_KEY not set \u2014 edit .env with your key")
    print(f"         Get a FREE key at: https://openrouter.ai/keys")

output_dir = os.getenv("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files")
print(f"  [INFO] OUTPUT_DIR = {output_dir}")

# ── Summary ───────────────────────────────────────────────────────────────
print()
passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)
failed = [(n, e) for n, ok, e in results if not ok]

print("=" * 60)
print(f"Packages: {passed}/{total} OK  |  Poppler: {'OK' if poppler_ok else 'MISSING'}  |  API Key: {'SET' if api_key and api_key != 'your_openrouter_api_key_here' else 'NOT SET'}")

if failed:
    print(f"\nFailed packages ({len(failed)}). Install with:")
    print(f"  pip install -r requirements.txt")

if passed == total and poppler_ok:
    print("\n[OK] All good! You can now run:")
    print('  python main.py --input "your_scan.pdf"     (CLI mode)')
    print('  python gui_app.py                           (Desktop GUI)')
else:
    print("\nFix the issues above before running the extractor.")

print("=" * 60)
