"""
OCR Service - FastAPI microservice for prescription image processing.
Uses TrOCR (Microsoft Transformer OCR) for handwritten text recognition.
Falls back to EasyOCR for printed text.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional

import cv2
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

# Initialize models (singletons)
_trocr_processor = None
_trocr_model = None
_easyocr_reader = None


def get_trocr_model():
    """Get or create TrOCR model for handwritten text."""
    global _trocr_processor, _trocr_model
    if _trocr_model is None:
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            print("Loading TrOCR handwritten model... (first time may download ~1GB)")
            _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
            _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
            print("TrOCR model loaded successfully!")
        except Exception as e:
            print(f"Failed to load TrOCR: {e}")
            return None, None
    return _trocr_processor, _trocr_model


def get_easyocr_reader():
    """Get or create EasyOCR reader as fallback."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(
                settings.OCR_LANGUAGES,
                gpu=settings.OCR_USE_GPU
            )
        except Exception as e:
            print(f"Failed to load EasyOCR: {e}")
            return None
    return _easyocr_reader


def preprocess_image(image: np.ndarray) -> Image.Image:
    """Preprocess image for better OCR results."""
    # Convert to PIL Image
    if isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    else:
        pil_image = image
    
    # Convert to RGB if needed
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    
    # Resize if too small
    width, height = pil_image.size
    min_dim = 384  # TrOCR works well with this size
    if width < min_dim or height < min_dim:
        scale = max(min_dim / width, min_dim / height)
        new_size = (int(width * scale), int(height * scale))
        pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
    
    return pil_image


def extract_text_regions(image: np.ndarray) -> List[Tuple[np.ndarray, List]]:
    """
    Extract text regions from image using contour detection.
    Returns list of (cropped_image, bbox) tuples.
    """
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Dilate to connect text components
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilated = cv2.dilate(binary, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    height, width = image.shape[:2]
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter out very small or very large regions
        if w < 20 or h < 10 or w > width * 0.95 or h > height * 0.5:
            continue
        
        # Add padding
        pad = 10
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(width, x + w + pad)
        y2 = min(height, y + h + pad)
        
        cropped = image[y1:y2, x1:x2]
        bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        regions.append((cropped, bbox))
    
    # Sort by vertical position (top to bottom)
    regions.sort(key=lambda r: r[1][0][1])
    
    # If no regions found, return the whole image
    if not regions:
        bbox = [[0, 0], [width, 0], [width, height], [0, height]]
        regions = [(image, bbox)]
    
    return regions


def ocr_with_trocr(image: np.ndarray) -> List[Tuple[str, float, List]]:
    """
    Run TrOCR on image regions for handwritten text.
    Returns list of (text, confidence, bbox).
    """
    processor, model = get_trocr_model()
    if processor is None or model is None:
        return []
    
    import torch
    
    results = []
    regions = extract_text_regions(image)
    
    for region_img, bbox in regions:
        try:
            # Preprocess
            pil_img = preprocess_image(region_img)
            
            # Run TrOCR
            pixel_values = processor(pil_img, return_tensors="pt").pixel_values
            
            with torch.no_grad():
                generated_ids = model.generate(
                    pixel_values,
                    max_length=64,
                    num_beams=4,
                    early_stopping=True
                )
            
            text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            text = text.strip()
            
            if text and len(text) > 1:
                # TrOCR doesn't provide confidence, estimate based on text quality
                confidence = 0.85 if len(text) > 3 else 0.6
                results.append((text, confidence, bbox))
                
        except Exception as e:
            print(f"TrOCR error on region: {e}")
            continue
    
    return results


def ocr_with_easyocr(image: np.ndarray) -> List[Tuple[str, float, List]]:
    """Run EasyOCR on image (fallback for printed text)."""
    reader = get_easyocr_reader()
    if reader is None:
        return []
    
    try:
        results = reader.readtext(
            image,
            detail=1,
            paragraph=False,
            min_size=10,
            text_threshold=0.5,
            low_text=0.3
        )
        
        processed = []
        for bbox, text, conf in results:
            cleaned = text.strip()
            if cleaned and len(cleaned) > 0:
                processed.append((cleaned, float(conf), bbox))
        
        return processed
    except Exception as e:
        print(f"EasyOCR error: {e}")
        return []


def process_image(image: np.ndarray) -> List[Tuple[str, float, List]]:
    """
    Process image with TrOCR (handwritten) and EasyOCR (printed).
    Returns combined results with best matches.
    """
    # Try TrOCR first (better for handwriting)
    trocr_results = ocr_with_trocr(image)
    
    # Also try EasyOCR
    easyocr_results = ocr_with_easyocr(image)
    
    # If TrOCR got results, prefer them for handwriting
    if trocr_results:
        # Combine: TrOCR results + any EasyOCR results not overlapping
        combined = trocr_results.copy()
        
        # Add EasyOCR results that don't overlap with TrOCR
        for er_text, er_conf, er_bbox in easyocr_results:
            overlaps = False
            for tr_text, _, tr_bbox in trocr_results:
                # Simple overlap check
                if er_text.lower() in tr_text.lower() or tr_text.lower() in er_text.lower():
                    overlaps = True
                    break
            if not overlaps:
                combined.append((er_text, er_conf, er_bbox))
        
        return combined
    
    # Fall back to EasyOCR only
    return easyocr_results


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
    Uses TrOCR for handwritten text and EasyOCR as fallback.
    
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
