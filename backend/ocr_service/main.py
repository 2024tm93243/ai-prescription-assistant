"""
OCR Service - FastAPI microservice for prescription image processing.
Uses Groq vision LLM for OCR (no system dependencies or GPU required).
"""

from __future__ import annotations

import base64
import io
import os
import sys
from datetime import datetime
from typing import List, Tuple

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES
from shared.models import OCRLine, OCRResult, HealthStatus, ErrorResponse

settings = get_settings()

app = FastAPI(
    title="OCR Service",
    description="Prescription OCR via Groq vision LLM — no system dependencies",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vision model — Groq multimodal model for handwritten OCR
VISION_OCR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


async def ocr_with_vision_llm(
    image_bytes: bytes, content_type: str = "image/jpeg"
) -> List[Tuple[str, float, List]]:
    """
    Send image to Groq vision LLM and return extracted text lines.
    Returns list of (text, confidence, bbox) tuples.
    No system packages or GPU required.
    """
    import httpx

    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not set. Add it in Render environment variables.",
        )

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": VISION_OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{content_type};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all the text visible in this prescription image. "
                            "Return each line of text on a separate line. "
                            "Output only the extracted text, no explanations."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.GROQ_BASE_URL}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Vision OCR error ({resp.status_code}): {resp.text[:400]}",
        )

    extracted = resp.json()["choices"][0]["message"]["content"].strip()

    results: List[Tuple[str, float, List]] = []
    for line in extracted.splitlines():
        line = line.strip()
        if line:
            results.append((line, 0.90, []))
    return results


def pdf_pages_to_jpeg_bytes(data: bytes) -> List[bytes]:
    """Convert PDF pages to JPEG bytes for vision LLM."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pdf2image is required for PDF processing",
        )
    pages = convert_from_bytes(data, dpi=200)
    result = []
    for page in pages:
        buf = io.BytesIO()
        page.convert("RGB").save(buf, format="JPEG", quality=90)
        result.append(buf.getvalue())
    return result


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        service=SERVICE_NAMES["ocr"],
        status="healthy",
        version="2.0.0",
    )


@app.post("/ocr", response_model=OCRResult)
async def perform_ocr(file: UploadFile = File(...)):
    """
    Process uploaded prescription image with OCR using Groq vision LLM.
    Accepts: JPG, PNG, BMP, TIFF, PDF
    Returns: Extracted text with per-line confidence scores.
    """
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    all_lines: List[OCRLine] = []
    all_confidences: List[float] = []
    page_count = 1

    try:
        if ext == ".pdf":
            pages = pdf_pages_to_jpeg_bytes(content)
            page_count = len(pages)
            for page_bytes in pages:
                for text, conf, _ in await ocr_with_vision_llm(page_bytes, "image/jpeg"):
                    all_lines.append(OCRLine(text=text, confidence=conf))
                    all_confidences.append(conf)
        else:
            content_type = _CONTENT_TYPES.get(ext, "image/jpeg")
            for text, conf, _ in await ocr_with_vision_llm(content, content_type):
                all_lines.append(OCRLine(text=text, confidence=conf))
                all_confidences.append(conf)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    raw_text = "\n".join(line.text for line in all_lines)

    return OCRResult(
        filename=filename,
        page_count=page_count,
        lines=all_lines,
        average_confidence=avg_confidence,
        raw_text=raw_text,
        processed_at=datetime.utcnow(),
    )


@app.post("/ocr/text-only")
async def perform_ocr_text_only(file: UploadFile = File(...)):
    """Simplified endpoint returning only text and average confidence."""
    result = await perform_ocr(file)
    return {
        "text": result.raw_text,
        "confidence": result.average_confidence,
        "line_count": len(result.lines),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.OCR_SERVICE_PORT, reload=True)
