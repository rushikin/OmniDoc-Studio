"""
OmniDoc Studio — Native Webview App Launcher & Bridge API
Runs the ultra-responsive modern HTML5/Tailwind/Material workstation UI
powered by the underlying Stirling + PaddleOCR + OpenRouter Python engines.
"""

import os
import sys
import json
import time
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# Ensure current directory and _internal are in sys.path
base_dir = Path(__file__).resolve().parent
internal_dir = base_dir / "_internal"
for p in (str(base_dir), str(internal_dir)):
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

try:
    import webview
except ImportError:
    print("pywebview is required to run the native window.")
    print("Run: pip install pywebview")
    sys.exit(1)

import pdf_toolkit

class BridgeAPI:
    def __init__(self):
        self.window = None
        self.selected_pdf = None
        self.merge_files = []
        self.batch_dir = None
        self.output_dir = Path(os.environ.get("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_exported_docx = None
        self.last_exported_pdf = None

    def set_window(self, window):
        self.window = window

    def select_pdf(self):
        """Open native Windows file dialog to select a PDF."""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select PDF File - OmniDoc Studio",
            filetypes=[("PDF Documents (*.pdf)", "*.pdf"), ("All Files (*.*)", "*.*")]
        )
        root.destroy()
        if path:
            self.selected_pdf = os.path.normpath(path)
            file_name = os.path.basename(self.selected_pdf)
            size_mb = os.path.getsize(self.selected_pdf) / (1024 * 1024)
            info = pdf_toolkit.get_pdf_metadata(self.selected_pdf)
            pages = info.get("pages", 1)
            return {
                "success": True,
                "path": self.selected_pdf,
                "filename": file_name,
                "size_mb": f"{size_mb:.1f} MB",
                "pages": pages
            }
        return {"success": False}

    def select_multiple_pdfs(self):
        """Open native Windows file dialog to select multiple PDFs for merging."""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        paths = filedialog.askopenfilenames(
            title="Select Multiple PDFs - OmniDoc Studio",
            filetypes=[("PDF Documents (*.pdf)", "*.pdf")]
        )
        root.destroy()
        if paths:
            self.merge_files = [os.path.normpath(p) for p in paths]
            res = []
            for p in self.merge_files:
                size_mb = os.path.getsize(p) / (1024 * 1024)
                info = pdf_toolkit.get_pdf_metadata(p)
                res.append({
                    "path": p,
                    "filename": os.path.basename(p),
                    "size_mb": f"{size_mb:.1f} MB",
                    "pages": info.get("pages", 1)
                })
            return {"success": True, "files": res}
        return {"success": False}

    def select_batch_directory(self):
        """Open native Windows folder dialog to choose batch scan directory."""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select Folder With Scanned PDFs")
        root.destroy()
        if folder:
            self.batch_dir = os.path.normpath(folder)
            files = [str(p) for p in Path(self.batch_dir).glob("*.pdf")]
            return {
                "success": True,
                "directory": self.batch_dir,
                "count": len(files),
                "files": [os.path.basename(f) for f in files[:20]]
            }
        return {"success": False}

    def run_ocr_to_docx(self, input_path=None, use_ai=True, dpi=300):
        """Run complete extraction pipeline and write native Word DOCX."""
        target_pdf = input_path or self.selected_pdf
        if not target_pdf or not os.path.exists(target_pdf):
            return {"success": False, "error": "No valid PDF file selected."}

        out_name = Path(target_pdf).stem + ".docx"
        out_path = str(self.output_dir / out_name)
        
        try:
            from pdf_converter import pdf_to_images
            from ocr_engine import OCREngine
            from word_generator import WordGenerator

            images = pdf_to_images(target_pdf, dpi=dpi)
            
            engine = OCREngine(language="en", use_gpu=False)
            pages_elements = []
            for img in images:
                elems = engine.extract_page(img)
                pages_elements.append(elems)

            generator = WordGenerator()
            generator.generate_toc(pages_elements)
            for idx, elems in enumerate(pages_elements):
                generator.add_page(idx, elems)
            generator.save(out_path)

            self.last_exported_docx = out_path
            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            return {
                "success": True,
                "output_path": out_path,
                "filename": out_name,
                "size_mb": f"{size_mb:.2f} MB",
                "pages": len(images)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def split_selected_pdf(self, page_indices=None):
        """Split selected PDF by selected page numbers."""
        target_pdf = self.selected_pdf
        if not target_pdf or not os.path.exists(target_pdf):
            return {"success": False, "error": "No PDF selected to split."}
        
        split_dir = self.output_dir / (Path(target_pdf).stem + "_Split_Pages")
        split_dir.mkdir(parents=True, exist_ok=True)

        try:
            created = pdf_toolkit.split_pdf(target_pdf, str(split_dir))
            return {
                "success": True,
                "directory": str(split_dir),
                "created_count": len(created)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def merge_staged_pdfs(self, output_filename="Merged_OmniDoc_Export.pdf"):
        """Merge all currently staged PDFs into a single file."""
        if not self.merge_files or len(self.merge_files) < 2:
            return {"success": False, "error": "At least 2 PDF files required to merge."}
        
        out_path = str(self.output_dir / output_filename)
        try:
            pdf_toolkit.merge_pdfs(self.merge_files, out_path)
            self.last_exported_pdf = out_path
            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            return {
                "success": True,
                "output_path": out_path,
                "filename": output_filename,
                "size_mb": f"{size_mb:.2f} MB"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_security_and_compress(self, password=""):
        """Encrypt and optimize current document."""
        target_pdf = self.selected_pdf
        if not target_pdf or not os.path.exists(target_pdf):
            return {"success": False, "error": "No PDF selected."}
        
        out_path = str(self.output_dir / (Path(target_pdf).stem + "_Secured.pdf"))
        try:
            if password:
                pdf_toolkit.set_password(target_pdf, out_path, user_pwd=password)
            else:
                pdf_toolkit.compress_pdf(target_pdf, out_path)
            return {"success": True, "output_path": out_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_output_folder(self):
        """Open Windows Explorer at output destination."""
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)
            return {"success": True}
        return {"success": False}

    def open_file(self, file_path=None):
        """Open generated Word docx or PDF in native Windows application."""
        target = file_path or self.last_exported_docx or self.last_exported_pdf
        if target and os.path.exists(target):
            os.startfile(target)
            return {"success": True}
        return {"success": False, "error": "File does not exist."}


def main():
    ui_dir = Path(__file__).parent / "ui"
    index_file = ui_dir / "index.html"

    if not index_file.exists():
        print(f"ERROR: UI index file not found at: {index_file}")
        sys.exit(1)

    api = BridgeAPI()
    window = webview.create_window(
        title="OmniDoc Studio — v2.4 Enterprise Workstation",
        url=str(index_file.resolve()),
        width=1380,
        height=860,
        min_size=(960, 640),
        resizable=True,
        js_api=api,
    )
    api.set_window(window)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
