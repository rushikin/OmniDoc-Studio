"""
Desktop GUI Application — OmniDoc Studio (Stirling-PDF + AI OCR Suite)
Modern CustomTkinter multi-tab interface:
- Tab 1: AI Scanned OCR -> Word (.docx) with live model selection & restoration
- Tab 2: Stirling PDF Tools (Merge, Split, Rotate, Delete, Extract Pages, Reorder, Images->PDF, Extract Images, Compress, Protect/Unlock, Metadata Editor)
- Tab 3: Batch Pipeline

Run with: python gui_app.py
"""

import os
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

from dotenv import load_dotenv
load_dotenv()

try:
    import customtkinter as ctk
except ImportError:
    print("ERROR: customtkinter not installed. Run: pip install customtkinter")
    sys.exit(1)

import pdf_toolkit

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "OmniDoc Studio — Stirling PDF & AI OCR Extractor"
APP_W, APP_H = 1100, 750
OUTPUT_DIR_DEFAULT = os.environ.get("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(980, 680)

        # Global Variables
        self.output_dir = tk.StringVar(value=OUTPUT_DIR_DEFAULT)
        self.ocr_input_pdf = tk.StringVar()
        self.dpi_var = tk.IntVar(value=300)
        self.lang_var = tk.StringVar(value="en")
        self.use_ai_var = tk.BooleanVar(value=True)
        self.model_var = tk.StringVar(value="Loading...")
        self._running_ocr = False

        self._build_header()
        self._build_tabview()
        self._load_models_async()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=("#1c3d6e", "#0a192f"), corner_radius=0, height=60)
        header.pack(fill="x", side="top")
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(
            title_box, text="⚡ OmniDoc Studio",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#64ffda"
        ).pack(side="left")
        
        ctk.CTkLabel(
            title_box, text=" | Full PDF Toolkit + AI OCR Engine",
            font=ctk.CTkFont(size=13),
            text_color="#8892b0"
        ).pack(side="left", padx=(8, 0))

        # Output folder indicator button
        ctk.CTkButton(
            header, text="📁 Output Folder", width=140, height=32,
            fg_color="#172a45", hover_color="#203a5e",
            command=self._open_output
        ).pack(side="right", padx=20, pady=14)

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=12)

        self.tab_ocr = self.tabview.add("🔍 Scanned PDF → Word (AI OCR)")
        self.tab_tools = self.tabview.add("🛠️ Stirling PDF Tools")
        self.tab_batch = self.tabview.add("⚡ Batch Pipeline")

        self._setup_ocr_tab()
        self._setup_stirling_tools_tab()
        self._setup_batch_tab()

    # ── TAB 1: AI OCR ──────────────────────────────────────────────────────────
    def _setup_ocr_tab(self):
        tab = self.tab_ocr
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        left.columnconfigure(0, weight=1)

        drop_card = ctk.CTkFrame(left, fg_color=("#e2ecf9", "#112240"), corner_radius=10, border_width=1, border_color="#233554")
        drop_card.pack(fill="x", padx=12, pady=(12, 6))
        
        ctk.CTkLabel(drop_card, text="📄 Target Scanned Document", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=14, pady=(8, 2))
        self.lbl_selected_file = ctk.CTkLabel(drop_card, textvariable=self.ocr_input_pdf, font=ctk.CTkFont(size=11), text_color="gray", wraplength=480)
        self.lbl_selected_file.pack(anchor="w", padx=14, pady=2)
        
        btn_box = ctk.CTkFrame(drop_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=14, pady=(4, 10))
        ctk.CTkButton(btn_box, text="Browse PDF...", width=130, command=self._browse_ocr_pdf).pack(side="left")
        self.btn_doc_info = ctk.CTkButton(btn_box, text="Inspect Metadata", width=130, fg_color="#233554", hover_color="#334d77", command=self._inspect_pdf)
        self.btn_doc_info.pack(side="left", padx=8)

        ctk.CTkLabel(left, text="Execution Progress", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(10, 2))
        self.ocr_progress = ctk.CTkProgressBar(left, height=14)
        self.ocr_progress.pack(fill="x", padx=14, pady=2)
        self.ocr_progress.set(0)

        self.lbl_ocr_phase = ctk.CTkLabel(left, text="Ready", font=ctk.CTkFont(size=11), text_color="#8892b0")
        self.lbl_ocr_phase.pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkLabel(left, text="Live Log View", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(4, 2))
        self.ocr_log = ctk.CTkTextbox(left, height=180, font=ctk.CTkFont(size=11), state="disabled")
        self.ocr_log.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.btn_run_ocr = ctk.CTkButton(left, text="🚀 Extract & Reconstruct Word Document", height=42, font=ctk.CTkFont(size=14, weight="bold"), command=self._start_ocr_pipeline)
        self.btn_run_ocr.pack(fill="x", padx=12, pady=(0, 12))

        # Right Panel (Settings)
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        ctk.CTkLabel(right, text="⚙️ OCR & AI Settings", font=ctk.CTkFont(size=15, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=14, pady=12)

        ctk.CTkLabel(right, text="Render DPI:").pack(anchor="w", padx=14, pady=(4, 0))
        self.dpi_slider = ctk.CTkSlider(right, from_=150, to=600, number_of_steps=9, variable=self.dpi_var, command=lambda v: self.lbl_dpi.configure(text=f"{int(v)} DPI"))
        self.dpi_slider.pack(fill="x", padx=14, pady=2)
        self.lbl_dpi = ctk.CTkLabel(right, text=f"{self.dpi_var.get()} DPI", text_color="gray")
        self.lbl_dpi.pack(anchor="w", padx=14)

        ctk.CTkLabel(right, text="OCR Language:").pack(anchor="w", padx=14, pady=(10, 0))
        ctk.CTkOptionMenu(right, variable=self.lang_var, values=["en", "ch", "fr", "de", "es", "ar", "ja", "ko", "ru"]).pack(fill="x", padx=14, pady=2)

        ctk.CTkSwitch(right, text="OpenRouter AI Gap-Filling", variable=self.use_ai_var, command=self._toggle_ai_menu).pack(anchor="w", padx=14, pady=(16, 4))
        
        ctk.CTkLabel(right, text="AI Model Selection:").pack(anchor="w", padx=14, pady=(4, 0))
        self.model_dropdown = ctk.CTkOptionMenu(right, variable=self.model_var, values=["Loading..."])
        self.model_dropdown.pack(fill="x", padx=14, pady=2)
        ctk.CTkButton(right, text="↻ Refresh Models", height=26, fg_color="#233554", hover_color="#334d77", command=self._load_models_async).pack(anchor="w", padx=14, pady=6)

    # ── TAB 2: STIRLING PDF TOOLS (EXPANDED SUITE) ──────────────────────────────
    def _setup_stirling_tools_tab(self):
        tab = self.tab_tools
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        
        scroll.columnconfigure(0, weight=1)
        scroll.columnconfigure(1, weight=1)

        # 1. Merge & Split
        card1 = ctk.CTkFrame(scroll)
        card1.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card1, text="📑 Merge & Split", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card1, text="Merge Multiple PDFs", height=34, command=self._tool_merge).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card1, text="Split PDF into Pages", height=34, fg_color="#233554", hover_color="#334d77", command=self._tool_split).pack(fill="x", padx=12, pady=4)

        # 2. Page Operations
        card2 = ctk.CTkFrame(scroll)
        card2.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card2, text="🔄 Page Manipulation", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card2, text="Rotate Pages (90° Clockwise)", height=34, command=self._tool_rotate).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card2, text="Delete Specific Pages", height=34, fg_color="#233554", hover_color="#334d77", command=self._tool_delete_pages).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card2, text="Extract Page Range", height=34, fg_color="#1f3b4d", hover_color="#2e546e", command=self._tool_extract_pages).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card2, text="Reorder Pages", height=34, fg_color="#233554", hover_color="#334d77", command=self._tool_reorder_pages).pack(fill="x", padx=12, pady=4)

        # 3. Conversions (Images & PDF)
        card3 = ctk.CTkFrame(scroll)
        card3.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card3, text="🖼️ Conversions", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card3, text="Convert Images to PDF", height=34, command=self._tool_images_to_pdf).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card3, text="Extract All Embedded Images", height=34, fg_color="#233554", hover_color="#334d77", command=self._tool_extract_images).pack(fill="x", padx=12, pady=4)

        # 4. Optimization & Compression
        card4 = ctk.CTkFrame(scroll)
        card4.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card4, text="🗜️ Compress & Clean", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card4, text="Compress PDF (Linearize)", height=34, command=self._tool_compress).pack(fill="x", padx=12, pady=4)

        # 5. Security
        card5 = ctk.CTkFrame(scroll)
        card5.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card5, text="🔒 Password & Security", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card5, text="Encrypt with Password (AES-256)", height=34, command=self._tool_encrypt).pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(card5, text="Remove Password Protection", height=34, fg_color="#233554", hover_color="#334d77", command=self._tool_decrypt).pack(fill="x", padx=12, pady=4)

        # 6. Metadata Management
        card6 = ctk.CTkFrame(scroll)
        card6.grid(row=2, column=1, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(card6, text="🏷️ Metadata Editor", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(card6, text="View & Edit Document Metadata", height=34, command=self._tool_metadata_editor).pack(fill="x", padx=12, pady=4)

    # ── TAB 3: BATCH PIPELINE ──────────────────────────────────────────────────
    def _setup_batch_tab(self):
        tab = self.tab_batch
        card = ctk.CTkFrame(tab)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        
        ctk.CTkLabel(card, text="⚡ Batch Folder OCR Conversion", font=ctk.CTkFont(size=16, weight="bold"), text_color="#64ffda").pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text="Select a directory containing scanned PDFs to batch-process all into formatted Word (.docx) files.", text_color="gray").pack(anchor="w", padx=16, pady=(0, 12))

        self.batch_dir_var = tk.StringVar()
        dir_box = ctk.CTkFrame(card, fg_color="transparent")
        dir_box.pack(fill="x", padx=16, pady=6)
        ctk.CTkEntry(dir_box, textvariable=self.batch_dir_var, placeholder_text="Select input directory...").pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(dir_box, text="Browse Folder", width=130, command=self._browse_batch_dir).pack(side="right")

        self.btn_start_batch = ctk.CTkButton(card, text="Start Batch Processing", height=40, font=ctk.CTkFont(size=14, weight="bold"), command=self._run_batch)
        self.btn_start_batch.pack(fill="x", padx=16, pady=14)

    # ── HANDLERS ──────────────────────────────────────────────────────────────
    def _open_output(self):
        out = self.output_dir.get()
        if os.path.exists(out):
            os.startfile(out)
        else:
            messagebox.showinfo("Information", f"Directory will be generated upon first extraction:\n{out}")

    def _browse_ocr_pdf(self):
        file = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if file:
            self.ocr_input_pdf.set(file)
            self._log(f"Target selected: {Path(file).name}")

    def _browse_batch_dir(self):
        d = filedialog.askdirectory(title="Select Folder With PDFs")
        if d:
            self.batch_dir_var.set(d)

    def _toggle_ai_menu(self):
        self.model_dropdown.configure(state="normal" if self.use_ai_var.get() else "disabled")

    def _log(self, text: str):
        self.ocr_log.configure(state="normal")
        self.ocr_log.insert("end", text + "\n")
        self.ocr_log.see("end")
        self.ocr_log.configure(state="disabled")

    def _load_models_async(self):
        def _task():
            try:
                from model_selector import fetch_free_models
                models = fetch_free_models()
                ids = [m["id"] for m in models]
                if ids:
                    self.after(0, lambda: self.model_dropdown.configure(values=ids))
                    self.after(0, lambda: self.model_var.set(ids[0]))
                    self.after(0, lambda: self._log(f"OpenRouter: Loaded {len(ids)} free models."))
            except Exception as e:
                self.after(0, lambda: self._log(f"Model sync error: {e}"))
        threading.Thread(target=_task, daemon=True).start()

    def _inspect_pdf(self):
        pdf = self.ocr_input_pdf.get()
        if not pdf or not os.path.exists(pdf):
            messagebox.showerror("Error", "Please select a valid PDF first.")
            return
        info = pdf_toolkit.get_pdf_metadata(pdf)
        details = (
            f"Pages: {info['pages']}\n"
            f"Title: {info['title'] or 'N/A'}\n"
            f"Author: {info['author'] or 'N/A'}\n"
            f"Subject: {info['subject'] or 'N/A'}\n"
            f"Keywords: {info['keywords'] or 'N/A'}\n"
            f"Encrypted: {'Yes' if info['encrypted'] else 'No'}"
        )
        messagebox.showinfo("PDF Inspection", details)

    # ── Stirling PDF Action Implementations ────────────────────────────────────
    def _tool_merge(self):
        files = filedialog.askopenfilenames(title="Select PDFs to Merge", filetypes=[("PDF files", "*.pdf")])
        if len(files) < 2:
            messagebox.showwarning("Notice", "Please select at least 2 PDF files to merge.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Merged PDF")
        if out:
            pdf_toolkit.merge_pdfs(list(files), out)
            messagebox.showinfo("Success", f"Merged {len(files)} PDFs successfully!\nSaved to: {out}")

    def _tool_split(self):
        f = filedialog.askopenfilename(title="Select PDF to Split", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        out_d = filedialog.askdirectory(title="Select Destination Folder")
        if out_d:
            res = pdf_toolkit.split_pdf(f, out_d)
            messagebox.showinfo("Success", f"Split PDF into {len(res)} individual files.")

    def _tool_rotate(self):
        f = filedialog.askopenfilename(title="Select PDF to Rotate", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Rotated PDF")
        if out:
            pdf_toolkit.rotate_pages(f, out, rotation=90)
            messagebox.showinfo("Success", f"Rotated PDF 90° clockwise.\nSaved to: {out}")

    def _tool_delete_pages(self):
        f = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        prompt = ctk.CTkInputDialog(text="Enter 1-based page numbers to delete (e.g. 1, 3):", title="Delete Pages")
        val = prompt.get_input()
        if not val:
            return
        try:
            pages = [int(p.strip()) for p in val.split(",") if p.strip()]
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Result")
            if out:
                pdf_toolkit.delete_pages(f, out, pages)
                messagebox.showinfo("Success", f"Pages {pages} removed.\nSaved to: {out}")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid page input: {e}")

    def _tool_extract_pages(self):
        f = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        prompt = ctk.CTkInputDialog(text="Enter 1-based page numbers to extract (e.g. 1, 2, 5):", title="Extract Pages")
        val = prompt.get_input()
        if not val:
            return
        try:
            pages = [int(p.strip()) for p in val.split(",") if p.strip()]
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Extracted PDF")
            if out:
                pdf_toolkit.extract_pages(f, out, pages)
                messagebox.showinfo("Success", f"Extracted {len(pages)} pages.\nSaved to: {out}")
        except Exception as e:
            messagebox.showerror("Error", f"Extraction error: {e}")

    def _tool_reorder_pages(self):
        f = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        prompt = ctk.CTkInputDialog(text="Enter new page sequence (e.g. 3, 1, 2):", title="Reorder Pages")
        val = prompt.get_input()
        if not val:
            return
        try:
            order = [int(p.strip()) for p in val.split(",") if p.strip()]
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Reordered PDF")
            if out:
                pdf_toolkit.reorder_pages(f, out, order)
                messagebox.showinfo("Success", f"Pages reordered to {order}.\nSaved to: {out}")
        except Exception as e:
            messagebox.showerror("Error", f"Reorder error: {e}")

    def _tool_images_to_pdf(self):
        files = filedialog.askopenfilenames(title="Select Images (PNG, JPG, BMP)", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")])
        if not files:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Compiled PDF")
        if out:
            pdf_toolkit.images_to_pdf(list(files), out)
            messagebox.showinfo("Success", f"Compiled {len(files)} images into PDF!\nSaved to: {out}")

    def _tool_extract_images(self):
        f = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        out_d = filedialog.askdirectory(title="Select Output Directory for Images")
        if out_d:
            imgs = pdf_toolkit.extract_embedded_images(f, out_d)
            messagebox.showinfo("Success", f"Extracted {len(imgs)} images.\nSaved to: {out_d}")

    def _tool_compress(self):
        f = filedialog.askopenfilename(title="Select PDF to Compress", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Compressed PDF")
        if out:
            pdf_toolkit.compress_pdf(f, out)
            messagebox.showinfo("Success", f"Optimized & compressed stream PDF.\nSaved to: {out}")

    def _tool_encrypt(self):
        f = filedialog.askopenfilename(title="Select PDF to Protect", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        pwd_box = ctk.CTkInputDialog(text="Enter encryption password:", title="Set Password")
        pwd = pwd_box.get_input()
        if not pwd:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Encrypted PDF")
        if out:
            pdf_toolkit.set_password(f, out, user_pwd=pwd)
            messagebox.showinfo("Success", f"PDF secured with AES-256 encryption.")

    def _tool_decrypt(self):
        f = filedialog.askopenfilename(title="Select Protected PDF", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        pwd_box = ctk.CTkInputDialog(text="Enter existing password:", title="Unlock PDF")
        pwd = pwd_box.get_input()
        if not pwd:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Unlocked PDF")
        if out:
            try:
                pdf_toolkit.remove_password(f, out, password=pwd)
                messagebox.showinfo("Success", "Password removed successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to decrypt: {e}")

    def _tool_metadata_editor(self):
        f = filedialog.askopenfilename(title="Select PDF to Edit Metadata", filetypes=[("PDF files", "*.pdf")])
        if not f:
            return
        meta = pdf_toolkit.get_pdf_metadata(f)
        
        prompt_title = ctk.CTkInputDialog(text=f"Title (Current: {meta.get('title','')}):", title="Edit Title")
        new_title = prompt_title.get_input()
        prompt_author = ctk.CTkInputDialog(text=f"Author (Current: {meta.get('author','')}):", title="Edit Author")
        new_author = prompt_author.get_input()

        updates = {}
        if new_title: updates["title"] = new_title
        if new_author: updates["author"] = new_author

        if updates:
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save Updated PDF")
            if out:
                pdf_toolkit.update_pdf_metadata(f, out, updates)
                messagebox.showinfo("Success", f"Metadata saved!\n{out}")

    # ── Pipeline Runner ────────────────────────────────────────────────────────
    def _start_ocr_pipeline(self):
        if self._running_ocr:
            return
        pdf = self.ocr_input_pdf.get()
        if not pdf or not os.path.exists(pdf):
            messagebox.showerror("Error", "Please pick a valid PDF file first.")
            return

        self._running_ocr = True
        self.btn_run_ocr.configure(state="disabled", text="Running OCR Extraction...")
        self.ocr_progress.set(0)

        threading.Thread(target=self._exec_ocr, daemon=True).start()

    def _exec_ocr(self):
        pdf = self.ocr_input_pdf.get()
        out_dir = Path(self.output_dir.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = str(out_dir / (Path(pdf).stem + ".docx"))
        dpi = int(self.dpi_var.get())
        lang = self.lang_var.get()
        use_ai = self.use_ai_var.get()
        model_id = self.model_var.get()

        try:
            self._update_ui("Phase 1/4: Converting PDF pages with CLAHE/Deskew...", 0.1)
            from pdf_converter import pdf_to_images
            images = pdf_to_images(pdf, dpi=dpi)
            self._log(f"Rendered {len(images)} pages.")

            self._update_ui("Phase 2/4: Initializing PaddleOCR...", 0.25)
            from ocr_engine import OCREngine
            ocr = OCREngine(language=lang, use_gpu=False)

            self._update_ui("Phase 3/4: OCR page analysis...", 0.35)
            raw_pages = []
            for i, img in enumerate(images):
                elems = ocr.extract_page(img)
                raw_pages.append(elems)
                self._update_ui(f"Page {i+1}/{len(images)} scanned ({len(elems)} elements)", 0.35 + (i+1)/len(images)*0.25)
                self._log(f"Page {i+1}: Found {len(elems)} elements")

            if use_ai and model_id and "Loading" not in model_id:
                self._update_ui("Phase 3b: OpenRouter AI Gap-Filling & Correction...", 0.65)
                from ai_enhancer import AIEnhancer
                enhancer = AIEnhancer(model_id=model_id)
                enhanced = []
                for i, raw in enumerate(raw_pages):
                    self._update_ui(f"AI Enhancing page {i+1}/{len(images)}...", 0.65 + (i+1)/len(images)*0.2)
                    enhanced.append(enhancer.enhance_page(i, raw))
            else:
                enhanced = raw_pages

            self._update_ui("Phase 4/4: Constructing Word Document with TOC & Footers...", 0.9)
            from word_generator import WordGenerator
            gen = WordGenerator()
            gen.generate_toc(enhanced)
            for i, elems in enumerate(enhanced):
                gen.add_page(i, elems)
            gen.save(out_file)

            self._update_ui(f"Done! Created {Path(out_file).name}", 1.0)
            self._log(f"\nSUCCESS: Document saved to {out_file}")
            self.after(0, lambda: messagebox.showinfo("Success", f"Word document reconstructed!\n{out_file}"))
        except Exception as e:
            self._update_ui(f"Failed: {e}", 0)
            self._log(f"ERROR: {e}")
            self.after(0, lambda: messagebox.showerror("Pipeline Failure", str(e)))
        finally:
            self._running_ocr = False
            self.after(0, lambda: self.btn_run_ocr.configure(state="normal", text="🚀 Extract & Reconstruct Word Document"))

    def _update_ui(self, msg: str, prog: float):
        self.after(0, lambda: self.lbl_ocr_phase.configure(text=msg))
        self.after(0, lambda: self.ocr_progress.set(prog))

    def _run_batch(self):
        d = self.batch_dir_var.get()
        if not d or not os.path.exists(d):
            messagebox.showerror("Error", "Please select an existing folder containing PDFs.")
            return
        def _task():
            from batch_processor import BatchProcessor
            bp = BatchProcessor(input_dir=d, use_ai=self.use_ai_var.get(), selected_model=self.model_var.get())
            bp.run()
            self.after(0, lambda: messagebox.showinfo("Batch Finished", "Batch job completed! Check terminal or output folder."))
        threading.Thread(target=_task, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
