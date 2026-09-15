"""
OmniDoc Studio — Native Webview App Launcher & Bridge API
Runs the ultra-responsive modern HTML5/Tailwind/Material workstation UI
powered by the underlying Stirling + PaddleOCR + OpenRouter Python engines.
"""

import os
import sys
import json
import time
import base64
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
        self._ocr_running = False

    def set_window(self, window):
        self.window = window

    def _js(self, code):
        """Safely evaluate JavaScript in the webview from any thread."""
        try:
            if self.window:
                self.window.evaluate_js(code)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # File Selection
    # ─────────────────────────────────────────────────────────────────────────

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
            pdf_paths = sorted(Path(self.batch_dir).glob("*.pdf"))
            files_meta = []
            for p in pdf_paths[:50]:
                try:
                    info = pdf_toolkit.get_pdf_metadata(str(p))
                    size_mb = os.path.getsize(str(p)) / (1024 * 1024)
                    files_meta.append({
                        "filename": p.name,
                        "path": str(p),
                        "pages": info.get("pages", 1),
                        "size_mb": f"{size_mb:.1f} MB"
                    })
                except Exception:
                    files_meta.append({
                        "filename": p.name,
                        "path": str(p),
                        "pages": "?",
                        "size_mb": "? MB"
                    })
            return {
                "success": True,
                "directory": self.batch_dir,
                "count": len(pdf_paths),
                "files": files_meta
            }
        return {"success": False}

    # ─────────────────────────────────────────────────────────────────────────
    # PDF Thumbnails (real page previews via PyMuPDF)
    # ─────────────────────────────────────────────────────────────────────────

    def get_pdf_thumbnails(self, pdf_path=None, max_pages=20):
        """Return base64 PNG thumbnails for each page of the selected PDF."""
        target = pdf_path or self.selected_pdf
        if not target or not os.path.exists(target):
            return {"success": False, "error": "No PDF selected"}
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(target)
            total = len(doc)
            limit = min(total, max_pages)
            thumbs = []
            for i in range(limit):
                page = doc[i]
                # Scale so longest edge = 240px (good for thumbnails)
                zoom = 240.0 / max(page.rect.width, page.rect.height)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                png_bytes = pix.tobytes("png")
                b64 = base64.b64encode(png_bytes).decode("ascii")
                thumbs.append({
                    "page": i + 1,
                    "data": f"data:image/png;base64,{b64}"
                })
            doc.close()
            return {"success": True, "thumbnails": thumbs, "total": total}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Async OCR Pipeline (non-blocking, streams progress to UI)
    # ─────────────────────────────────────────────────────────────────────────

    def run_ocr_to_docx(self, input_path=None, use_ai=True, dpi=300):
        """
        Kick off the OCR pipeline in a background daemon thread.
        Returns immediately with {"success": True, "async": True} so the
        webview thread is never blocked.  Progress + completion are pushed
        to the browser via evaluate_js calls.
        """
        target_pdf = input_path or self.selected_pdf
        if not target_pdf or not os.path.exists(target_pdf):
            return {"success": False, "error": "No valid PDF file selected."}

        if self._ocr_running:
            return {"success": False, "error": "OCR already in progress."}

        def _pipeline():
            self._ocr_running = True
            out_name = Path(target_pdf).stem + ".docx"
            out_path = str(self.output_dir / out_name)

            def log(msg, pct=None):
                safe_msg = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                if pct is not None:
                    self._js(f"window.updateOCRProgress({pct}, '{safe_msg}')")
                else:
                    self._js(f"window.appendOCRLog('{safe_msg}')")

            try:
                log("Loading PDF converter…", 5)
                from pdf_converter import pdf_to_images

                log("Rendering PDF pages to images…", 10)
                images = pdf_to_images(target_pdf, dpi=int(dpi))
                total = len(images)
                log(f"Rendered {total} page(s). Initialising OCR engine…", 15)

                from ocr_engine import OCREngine
                engine = OCREngine(language="en", use_gpu=False)

                pages_elements = []
                for idx, img in enumerate(images):
                    pct = 15 + int(60 * (idx / total))
                    log(f"[Page {idx+1}/{total}] Neural OCR scan…", pct)
                    elems = engine.extract_page(img)
                    pages_elements.append(elems)

                log("All pages extracted. Building Word document…", 80)
                from word_generator import WordGenerator
                generator = WordGenerator()
                generator.generate_toc(pages_elements)
                for page_idx, elems in enumerate(pages_elements):
                    generator.add_page(page_idx, elems)
                generator.save(out_path)

                self.last_exported_docx = out_path
                size_mb = os.path.getsize(out_path) / (1024 * 1024)
                log(f"DOCX saved: {out_name} ({size_mb:.2f} MB)", 100)

                result_json = json.dumps({
                    "success": True,
                    "output_path": out_path,
                    "filename": out_name,
                    "size_mb": f"{size_mb:.2f} MB",
                    "pages": total
                })
                self._js(f"window.ocrComplete({result_json})")

            except Exception as exc:
                err = str(exc).replace("\\", "\\\\").replace("'", "\\'")
                log(f"ERROR: {err}", 0)
                self._js(f"window.ocrComplete({{\"success\":false,\"error\":\"{err}\"}})")
            finally:
                self._ocr_running = False

        threading.Thread(target=_pipeline, daemon=True).start()
        return {"success": True, "async": True}

    # ─────────────────────────────────────────────────────────────────────────
    # Split / Merge / Security
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # Utility / Open Files
    # ─────────────────────────────────────────────────────────────────────────

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
        title="OmniDoc Studio — v2.5 Enterprise Workstation",
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
