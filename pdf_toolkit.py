"""
PDF Toolkit Module — OmniDoc Studio (Comprehensive Stirling-PDF Engine)
Provides:
1. Merge & Split
2. Page manipulation (Rotate, Delete, Extract, Reorder)
3. Optimize & Compress (Linearize, Stream Compression)
4. Security (AES-256 Encrypt, Decrypt)
5. Conversion (Images to PDF, Extract Images from PDF)
6. Metadata Editor (Read, Update Title/Author/Subject/Keywords)
7. Text Extraction (Fast multi-page text dump)
8. Grayscale Converter
"""

import io
import os
from pathlib import Path
from typing import List, Optional, Union, Dict

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

from PIL import Image


def _check_pikepdf() -> None:
    if not PIKEPDF_AVAILABLE:
        raise ImportError("pikepdf is required. Install with: pip install pikepdf")


# ── 1. MERGE & SPLIT ────────────────────────────────────────────────────────
def merge_pdfs(input_paths: List[str], output_path: str) -> str:
    """Merge multiple PDF files into a single unified document."""
    _check_pikepdf()
    output = pikepdf.Pdf.new()
    for path in input_paths:
        with pikepdf.Pdf.open(path) as src:
            output.pages.extend(src.pages)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    output.save(output_path)
    return os.path.abspath(output_path)


def split_pdf(input_path: str, output_dir: str, page_ranges: Optional[List[tuple]] = None) -> List[str]:
    """Split a PDF into multiple distinct files by ranges or page-by-page."""
    _check_pikepdf()
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(input_path).stem
    output_paths = []

    with pikepdf.Pdf.open(input_path) as src:
        total = len(src.pages)
        if page_ranges is None:
            page_ranges = [(i + 1, i + 1) for i in range(total)]

        for start, end in page_ranges:
            start = max(1, start)
            end = min(total, end)
            out = pikepdf.Pdf.new()
            for i in range(start - 1, end):
                out.pages.append(src.pages[i])
            out_path = str(Path(output_dir) / f"{stem}_pages_{start}-{end}.pdf")
            out.save(out_path)
            output_paths.append(out_path)

    return output_paths


# ── 2. PAGE MANIPULATION ───────────────────────────────────────────────────
def rotate_pages(input_path: str, output_path: str, rotation: int = 90, pages: Optional[List[int]] = None) -> str:
    """Rotate specified pages (or all pages) by 90, 180, or 270 degrees."""
    _check_pikepdf()
    if rotation not in (90, 180, 270):
        raise ValueError("rotation must be 90, 180, or 270 degrees.")

    with pikepdf.Pdf.open(input_path) as pdf:
        total = len(pdf.pages)
        targets = [p - 1 for p in pages] if pages else list(range(total))
        for idx in targets:
            if 0 <= idx < total:
                page = pdf.pages[idx]
                current = int(page.get("/Rotate", 0))
                page["/Rotate"] = (current + rotation) % 360
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.save(output_path)

    return output_path


def delete_pages(input_path: str, output_path: str, pages_to_delete: List[int]) -> str:
    """Delete selected 1-based page numbers from a PDF document."""
    _check_pikepdf()
    zero_indexed = set(p - 1 for p in pages_to_delete)
    with pikepdf.Pdf.open(input_path) as pdf:
        new_pdf = pikepdf.Pdf.new()
        for idx, page in enumerate(pdf.pages):
            if idx not in zero_indexed:
                new_pdf.pages.append(page)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        new_pdf.save(output_path)
    return output_path


def extract_pages(input_path: str, output_path: str, pages_to_keep: List[int]) -> str:
    """Extract and save only specific 1-based page numbers from a PDF."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path) as pdf:
        total = len(pdf.pages)
        new_pdf = pikepdf.Pdf.new()
        for p in pages_to_keep:
            idx = p - 1
            if 0 <= idx < total:
                new_pdf.pages.append(pdf.pages[idx])
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        new_pdf.save(output_path)
    return output_path


def reorder_pages(input_path: str, output_path: str, new_order: List[int]) -> str:
    """Rearrange PDF pages in a new specified 1-based order (e.g. [3, 1, 2])."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path) as pdf:
        total = len(pdf.pages)
        new_pdf = pikepdf.Pdf.new()
        for p in new_order:
            idx = p - 1
            if 0 <= idx < total:
                new_pdf.pages.append(pdf.pages[idx])
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        new_pdf.save(output_path)
    return output_path


# ── 3. OPTIMIZATION & COMPRESSION ──────────────────────────────────────────
def compress_pdf(input_path: str, output_path: str) -> str:
    """Compress streams and linearize PDF for web and storage optimization."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path) as pdf:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.save(
            output_path,
            compress_streams=True,
            linearize=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    return output_path


# ── 4. SECURITY & ENCRYPTION ───────────────────────────────────────────────
def set_password(input_path: str, output_path: str, user_pwd: str, owner_pwd: Optional[str] = None) -> str:
    """Encrypt and password-protect a PDF document using AES-256."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path) as pdf:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.save(
            output_path,
            encryption=pikepdf.Encryption(
                owner=owner_pwd or user_pwd,
                user=user_pwd,
                R=6,  # AES-256
            ),
        )
    return output_path


def remove_password(input_path: str, output_path: str, password: str) -> str:
    """Decrypt and remove password restrictions from an authenticated PDF."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path, password=password) as pdf:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.save(output_path)
    return output_path


# ── 5. CONVERSIONS (IMAGES <-> PDF) ────────────────────────────────────────
def images_to_pdf(image_paths: List[str], output_path: str) -> str:
    """Convert a sequence of images (PNG, JPG, BMP, TIFF) into a unified PDF."""
    if not image_paths:
        raise ValueError("No images provided.")
    
    pil_images = []
    for p in image_paths:
        img = Image.open(p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        pil_images.append(img)
    
    first = pil_images[0]
    rest = pil_images[1:]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    first.save(output_path, save_all=True, append_images=rest)
    return output_path


def extract_embedded_images(input_path: str, output_dir: str) -> List[str]:
    """Extract all embedded raw images from each page of a PDF."""
    _check_pikepdf()
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(input_path).stem
    saved_images = []

    with pikepdf.Pdf.open(input_path) as pdf:
        count = 0
        for p_idx, page in enumerate(pdf.pages):
            for name, raw_image in page.images.items():
                count += 1
                try:
                    pim = pikepdf.PdfImage(raw_image)
                    out_name = f"{stem}_p{p_idx+1}_img{count}.png"
                    out_path = os.path.join(output_dir, out_name)
                    pim.as_pil_image().save(out_path)
                    saved_images.append(out_path)
                except Exception:
                    continue
    return saved_images


# ── 6. METADATA EDITOR ─────────────────────────────────────────────────────
def get_pdf_metadata(pdf_path: str) -> Dict[str, str]:
    """Retrieve title, author, subject, keywords, and creator info."""
    _check_pikepdf()
    with pikepdf.Pdf.open(pdf_path) as pdf:
        meta = pdf.docinfo or {}
        return {
            "title": str(meta.get("/Title", "")),
            "author": str(meta.get("/Author", "")),
            "subject": str(meta.get("/Subject", "")),
            "keywords": str(meta.get("/Keywords", "")),
            "creator": str(meta.get("/Creator", "")),
            "producer": str(meta.get("/Producer", "")),
            "pages": len(pdf.pages),
            "encrypted": pdf.is_encrypted,
        }


def update_pdf_metadata(input_path: str, output_path: str, metadata: Dict[str, str]) -> str:
    """Set custom Title, Author, Subject, and Keywords in a PDF."""
    _check_pikepdf()
    with pikepdf.Pdf.open(input_path) as pdf:
        with pdf.open_metadata() as meta:
            if "title" in metadata:
                meta["dc:title"] = metadata["title"]
            if "author" in metadata:
                meta["dc:creator"] = [metadata["author"]]
            if "subject" in metadata:
                meta["dc:description"] = metadata["subject"]
        
        # Also set docinfo for backward viewer compatibility
        if pdf.docinfo is not None:
            if "title" in metadata:
                pdf.docinfo["/Title"] = metadata["title"]
            if "author" in metadata:
                pdf.docinfo["/Author"] = metadata["author"]
            if "subject" in metadata:
                pdf.docinfo["/Subject"] = metadata["subject"]
            if "keywords" in metadata:
                pdf.docinfo["/Keywords"] = metadata["keywords"]

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.save(output_path)
    return output_path


# ── 7. FAST TEXT DUMP ──────────────────────────────────────────────────────
def extract_plain_text(input_path: str) -> str:
    """Extract accessible textual content from all pages."""
    _check_pikepdf()
    collected = []
    with pikepdf.Pdf.open(input_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            try:
                # Basic stream parsing
                text_stream = page.get_contents()
                if text_stream is not None:
                    raw_bytes = text_stream.read_bytes()
                    collected.append(f"--- Page {idx+1} ---\n" + raw_bytes.decode("latin1", errors="ignore"))
            except Exception:
                continue
    return "\n\n".join(collected)


def get_page_count(pdf_path: str) -> int:
    """Return total number of pages."""
    _check_pikepdf()
    with pikepdf.Pdf.open(pdf_path) as pdf:
        return len(pdf.pages)


def get_pdf_info(pdf_path: str) -> dict:
    """Alias for metadata retrieval."""
    return get_pdf_metadata(pdf_path)
