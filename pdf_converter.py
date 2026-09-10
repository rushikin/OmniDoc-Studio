"""
PDF to Image Converter Module
Converts each page of a scanned PDF into a high-resolution image.
"""

import os
from pathlib import Path
from typing import List

import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image


def get_poppler_path() -> str | None:
    """
    Returns the Poppler binaries path for Windows.
    Checks multiple known install locations.
    """
    candidates = [
        r"C:\poppler\Library\bin",   # conda-style layout (current install)
        r"C:\poppler\bin",           # flat layout
    ]
    for path in candidates:
        if os.path.exists(os.path.join(path, "pdftoppm.exe")):
            return path
    return None  # Let pdf2image find it from PATH


def pdf_to_images(pdf_path: str, dpi: int = 300, output_folder: str = None) -> List[np.ndarray]:
    """
    Convert a PDF file to a list of OpenCV images (one per page).

    Args:
        pdf_path: Path to the input PDF file.
        dpi: Resolution for rendering pages. Higher = better OCR, slower.
        output_folder: If set, saves debug images here.

    Returns:
        A list of numpy arrays (OpenCV images) for each page.
    """
    print(f"[PDF Converter] Loading: {pdf_path}")
    print(f"[PDF Converter] DPI: {dpi}")

    poppler_path = get_poppler_path()
    pil_images = convert_from_path(
        pdf_path,
        dpi=dpi,
        poppler_path=poppler_path
    )

    print(f"[PDF Converter] Found {len(pil_images)} page(s).")

    cv_images = []
    for i, pil_img in enumerate(pil_images):
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        cv_img = preprocess_image(cv_img)
        cv_images.append(cv_img)

        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
            save_path = os.path.join(output_folder, f"page_{i + 1:03d}.png")
            cv2.imwrite(save_path, cv_img)
            print(f"[PDF Converter] Saved page image: {save_path}")

    return cv_images


def preprocess_image(img: np.ndarray, auto_rotate: bool = True) -> np.ndarray:
    """
    Apply comprehensive image preprocessing to improve OCR accuracy.
    Steps:
        1. Grayscale conversion
        2. Light denoising
        3. CLAHE contrast enhancement for faded/uneven scans
        4. Auto-rotation correction (deskew) for skewed pages
        5. OTSU binarization
        6. Convert back to BGR for PaddleOCR

    Args:
        img: Input BGR image as numpy array.
        auto_rotate: If True, detect and correct page skew.

    Returns:
        Preprocessed BGR image as numpy array.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Step 1: Mild denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Step 2: CLAHE — great for faded or unevenly lit scans
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Step 3: Deskew correction
    if auto_rotate:
        gray = _deskew(gray)

    # Step 4: OTSU binarization
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Convert back to BGR so PaddleOCR can process it
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return result


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Detect and correct page skew using Hough line detection.
    Only corrects angles <= 10 degrees to avoid over-rotating valid layouts.

    Args:
        gray: Grayscale input image.

    Returns:
        Deskewed grayscale image (or original if skew is undetectable).
    """
    try:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        edges = cv2.Canny(thresh, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
        if lines is None or len(lines) == 0:
            return gray

        angles = []
        for line in lines[:50]:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            if abs(angle) <= 10:
                angles.append(angle)

        if not angles:
            return gray

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.3:
            return gray

        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        return cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return gray  # Deskew failed — return original
