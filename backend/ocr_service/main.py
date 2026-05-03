"""
OCR Service - FastAPI microservice for prescription image processing.
Uses Tesseract OCR via pytesseract (no GPU required).
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES
from shared.models import OCRLine, OCRResult, HealthStatus, ErrorResponse

settings = get_settings()

app = FastAPI(
    title="OCR Service",
    description="TrOCR + EasyOCR prescription image processing service",
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

# No heavy model singletons needed — pytesseract calls the system binary directly.


def ocr_with_pytesseract(image: np.ndarray) -> List[Tuple[str, float, List]]:
    """
    Run Tesseract OCR on image.
    Returns list of (text, confidence, bbox).
    Tesseract needs no GPU and has zero heavy dependencies.
    """
    try:
        import pytesseract
        pil_image = Image.fromarray(image)
        # Enhance contrast for better handwriting recognition
        pil_image = pil_image.convert("L")  # Greyscale
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
        results: List[Tuple[str, float, List]] = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 0:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                results.append((text, conf / 100.0, bbox))
        return results
    except Exception as e:
        print(f"Pytesseract error: {e}")
        return []


def process_image(image: np.ndarray) -> List[Tuple[str, float, List]]:
    """Process image with Tesseract OCR."""
    return ocr_with_pytesseract(image)


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
    
    pages = convert_from_bytes(data, dpi=300)
    return [np.array(page.convert("RGB")) for page in pages]


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
    Uses Tesseract OCR (no GPU required).

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
    """
    result = await perform_ocr(file)
    return {
        "text": result.raw_text,
        "confidence": result.average_confidence,
        "line_count": len(result.lines)
    }


if __name__ == "__main__":
    uvicorn.run(
        "main_trocr:app",
        host="0.0.0.0",
        port=settings.OCR_SERVICE_PORT,
        reload=True
    )
