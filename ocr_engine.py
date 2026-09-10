"""
OCR Extraction Engine Module
Uses PaddleOCR 3.x to detect and extract text blocks and tables
from page images, preserving reading order.
"""

import os
from typing import List, Dict, Any

import numpy as np

# ---------------------------------------------------------------------------
# Monkeypatch importlib.metadata so paddlex can be imported even when its
# package metadata is unavailable (e.g. inside a PyInstaller bundle or any
# environment where the dist-info folder is missing).
# This must run BEFORE paddleocr/paddlex are imported.
# ---------------------------------------------------------------------------
def _patch_paddlex_metadata():
    import importlib.metadata
    try:
        importlib.metadata.metadata("paddlex")
        return  # metadata exists — nothing to do
    except importlib.metadata.PackageNotFoundError:
        pass

    from email.message import Message

    _original_metadata = importlib.metadata.metadata
    _original_requires = importlib.metadata.requires
    _original_version  = importlib.metadata.version

    def _mock_metadata(name):
        if name == "paddlex":
            m = Message()
            m["Name"]    = "paddlex"
            m["Version"] = "3.0.0"
            m["Provides-Extra"] = ""
            return m
        return _original_metadata(name)

    def _mock_requires(name):
        if name == "paddlex":
            return []
        return _original_requires(name)

    def _mock_version(name):
        if name == "paddlex":
            return "3.0.0"
        return _original_version(name)

    importlib.metadata.metadata = _mock_metadata
    importlib.metadata.requires = _mock_requires
    importlib.metadata.version  = _mock_version

_patch_paddlex_metadata()

# Also patch deps.is_dep_available after paddlex is importable
try:
    from paddlex.utils import deps as _paddlex_deps
    _paddlex_deps.is_dep_available = lambda *a, **kw: True
except Exception:
    pass


class OCREngine:
    """
    Wraps PaddleOCR for document layout analysis and extraction.
    Identifies text blocks and tables in their top-to-bottom reading order.
    """

    def __init__(self, language: str = "en", use_gpu: bool = False):
        """
        Initialize the PaddleOCR engines.

        Args:
            language: OCR language code (e.g., 'en', 'ch').
            use_gpu: Set True if a CUDA GPU is available.
        """
        print(f"[OCR Engine] Initializing PaddleOCR (lang={language}, gpu={use_gpu})...")

        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=language,
        )
        print("[OCR Engine] Ready.")

    def extract_page(self, cv_image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process a single page image and extract all structured elements.
        Detects titles vs body text using positional and length heuristics.

        Args:
            cv_image: A BGR numpy array representing one page.

        Returns:
            A list of element dicts, each with:
              - 'type': 'text' | 'title'
              - 'bbox': [x1, y1, x2, y2]
              - 'content': str
        """
        result = self.ocr.predict(cv_image)
        page_h = cv_image.shape[0]

        elements = []

        for page_result in result:
            rec_texts = page_result.get("rec_texts", [])
            dt_polys = page_result.get("dt_polys", [])
            rec_scores = page_result.get("rec_scores", [])

            if not rec_texts:
                continue

            line_items = []
            for i, text in enumerate(rec_texts):
                if not text.strip():
                    continue
                score = rec_scores[i] if i < len(rec_scores) else 1.0
                if score < 0.4:  # Lowered threshold for better recall
                    continue
                poly = dt_polys[i] if i < len(dt_polys) else [[0,0],[0,0],[0,0],[0,0]]
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                bbox = [min(xs), min(ys), max(xs), max(ys)]
                line_h = bbox[3] - bbox[1]
                line_items.append({"text": text, "bbox": bbox, "height": line_h, "score": score})

            # Sort by vertical then horizontal position (handles multi-column layouts)
            line_items.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

            if not line_items:
                continue

            # Average line height for title heuristics
            avg_height = sum(it["height"] for it in line_items) / len(line_items)

            paragraphs = self._merge_lines_into_paragraphs(line_items)

            for para in paragraphs:
                text_content = para["text"].strip()
                if not text_content:
                    continue

                # Title heuristic: short text near top of page with tall characters
                word_count = len(text_content.split())
                rel_y = para["bbox"][1] / max(page_h, 1)
                para_h = para["bbox"][3] - para["bbox"][1]
                is_title = (
                    word_count <= 10
                    and para_h > avg_height * 1.3
                    and rel_y < 0.3
                ) or (
                    word_count <= 6
                    and rel_y < 0.15
                )

                elements.append({
                    "type": "title" if is_title else "text",
                    "bbox": para["bbox"],
                    "content": text_content,
                })

        return elements

    def _merge_lines_into_paragraphs(
        self, line_items: List[Dict], gap_threshold: float = 25
    ) -> List[Dict]:
        """
        Merge consecutive text lines that are close together into paragraphs.
        Column-aware: lines in different horizontal columns are not merged.

        Args:
            line_items: Sorted list of {text, bbox, height} dicts.
            gap_threshold: Max vertical gap (pixels) to consider same paragraph.

        Returns:
            List of merged paragraph dicts.
        """
        if not line_items:
            return []

        paragraphs = []
        current_lines = [line_items[0]]

        for item in line_items[1:]:
            prev = current_lines[-1]
            prev_bottom = prev["bbox"][3]
            curr_top = item["bbox"][1]

            # Check vertical proximity
            vertical_ok = (curr_top - prev_bottom) <= gap_threshold

            # Check horizontal overlap (same column check)
            prev_left, prev_right = prev["bbox"][0], prev["bbox"][2]
            curr_left, curr_right = item["bbox"][0], item["bbox"][2]
            overlap = min(prev_right, curr_right) - max(prev_left, curr_left)
            prev_width = max(prev_right - prev_left, 1)
            horizontal_ok = overlap > prev_width * 0.3

            if vertical_ok and horizontal_ok:
                current_lines.append(item)
            else:
                paragraphs.append(self._merge_lines(current_lines))
                current_lines = [item]

        paragraphs.append(self._merge_lines(current_lines))
        return paragraphs

    def _merge_lines(self, lines: List[Dict]) -> Dict:
        """Combine a list of text lines into a single paragraph dict."""
        text = " ".join(line["text"] for line in lines)
        x1 = min(l["bbox"][0] for l in lines)
        y1 = min(l["bbox"][1] for l in lines)
        x2 = max(l["bbox"][2] for l in lines)
        y2 = max(l["bbox"][3] for l in lines)
        return {"text": text, "bbox": [x1, y1, x2, y2]}
