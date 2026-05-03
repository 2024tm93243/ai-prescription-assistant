"""
OCR Service - FastAPI microservice for prescription image processing.
Uses EasyOCR running locally for text extraction.
Includes preprocessing optimizations for handwritten prescriptions.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from typing import List, Tuple

import cv2
import easyocr
import numpy as np
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES
from shared.models import OCRLine, OCRResult, HealthStatus, ErrorResponse

settings = get_settings()

app = FastAPI(
    title="OCR Service",
    description="EasyOCR-based prescription image processing service",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize EasyOCR reader (singleton)
_ocr_reader = None


def get_ocr_reader() -> easyocr.Reader:
    """Get or create EasyOCR reader instance."""
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(
            settings.OCR_LANGUAGES,
            gpu=settings.OCR_USE_GPU,
            model_storage_directory=None,
            download_enabled=True
        )
    return _ocr_reader


def preprocess_for_handwriting(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better handwriting recognition.
    Applies denoising, contrast enhancement, and adaptive thresholding.
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # Resize if image is too small (helps OCR)
    height, width = gray.shape[:2]
    min_dimension = 1000
    if height < min_dimension or width < min_dimension:
        scale = max(min_dimension / height, min_dimension / width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Apply adaptive thresholding for better text separation
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Convert back to RGB for EasyOCR
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
    
    return result


def load_image_from_bytes(data: bytes) -> np.ndarray:
    """Load image from bytes into numpy array."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(image)


def load_pdf_pages(data: bytes) -> List[np.ndarray]:
    """Load PDF pages as images."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pdf2image is required for PDF processing"
        )
    
    pages = convert_from_bytes(data, dpi=300)  # Higher DPI for better quality
    return [np.array(page.convert("RGB")) for page in pages]


def process_image(image: np.ndarray, use_preprocessing: bool = True) -> List[Tuple[str, float, List]]:
    """
    Run OCR on a single image, return list of (text, confidence, bbox).
    Uses preprocessing optimized for handwritten text.
    """
    reader = get_ocr_reader()
    
    # Try with preprocessing first (better for handwriting)
    if use_preprocessing:
        preprocessed = preprocess_for_handwriting(image)
        results_preprocessed = reader.readtext(
            preprocessed,
            detail=1,
            paragraph=False,
            min_size=10,
            text_threshold=0.6,
            low_text=0.3,
            link_threshold=0.3,
            canvas_size=2560,
            mag_ratio=1.5
        )
    else:
        results_preprocessed = []
    
    # Also try original image (better for printed text)
    results_original = reader.readtext(
        image,
        detail=1,
        paragraph=False,
        min_size=10,
        text_threshold=0.7,
        low_text=0.4,
        link_threshold=0.4,
        canvas_size=2560,
        mag_ratio=1.5
    )
    
    # Use the results with better overall confidence
    def avg_conf(results):
        if not results:
            return 0
        return sum(r[2] for r in results) / len(results)
    
    # Choose the better result set
    if avg_conf(results_preprocessed) > avg_conf(results_original):
        results = results_preprocessed
    else:
        results = results_original
    
    processed = []
    for bbox, text, conf in results:
        cleaned = text.strip()
        if cleaned and len(cleaned) > 0:
            processed.append((cleaned, float(conf), bbox))
    
    return processed


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        service=SERVICE_NAMES["ocr"],
        status="healthy",
        version="1.0.0"
    )


@app.post("/ocr", response_model=OCRResult)
async def perform_ocr(file: UploadFile = File(...)):
    """
    Process uploaded prescription image with OCR.
    
    Accepts: JPG, PNG, BMP, TIFF, PDF
    Returns: Extracted text with per-line confidence scores
    """
    # Validate file extension
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Load images
    try:
        if ext == ".pdf":
            images = load_pdf_pages(content)
        else:
            images = [load_image_from_bytes(content)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load image: {str(e)}")
    
    # Process all pages
    all_lines: List[OCRLine] = []
    all_confidences: List[float] = []
    
    try:
        for image in images:
            results = process_image(image)
            for text, conf, bbox in results:
                all_lines.append(OCRLine(
                    text=text,
                    confidence=conf,
                    bbox=bbox if isinstance(bbox, list) else None
                ))
                all_confidences.append(conf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
    
    # Calculate average confidence
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    
    # Build raw text
    raw_text = "\n".join(line.text for line in all_lines)
    
    return OCRResult(
        filename=filename,
        page_count=len(images),
        lines=all_lines,
        average_confidence=avg_confidence,
        raw_text=raw_text,
        processed_at=datetime.utcnow()
    )


@app.post("/ocr/text-only")
async def perform_ocr_text_only(file: UploadFile = File(...)):
    """
    Simplified OCR endpoint returning only text and average confidence.
    Useful for quick extraction without full metadata.
    """
    result = await perform_ocr(file)
    return {
        "filename": result.filename,
        "text": result.raw_text,
        "confidence": result.average_confidence
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.OCR_SERVICE_PORT,
        reload=True
    )
