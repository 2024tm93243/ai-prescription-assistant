"""
API Gateway / Backend-for-Frontend (BFF) Service.
Orchestrates requests between frontend and microservices.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

import httpx
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES, EDUCATIONAL_DISCLAIMER
from shared.models import (
    UploadPrescriptionResponse,
    DrugCandidate,
    ConfirmDrugRequest,
    ConfirmDrugResponse,
    DrugInfoResponse,
    HealthStatus,
    ConfidenceLevel,
)

settings = get_settings()

app = FastAPI(
    title="Prescription Understanding API Gateway",
    description="Backend-for-Frontend service orchestrating prescription processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for prescription sessions (for demo purposes)
# In production, use Redis or a database
prescription_sessions: Dict[str, dict] = {}


# ============ Service Clients ============

async def call_ocr_service(file_content: bytes, filename: str) -> dict:
    """Call OCR Service to process prescription image."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"file": (filename, file_content)}
            response = await client.post(
                f"{settings.OCR_SERVICE_URL}/ocr",
                files=files
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OCR Service error: {response.text}"
                )
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="OCR service timed out. The image may be too complex or the service is busy. Please try again."
        )


async def call_drug_extractor(ocr_result: dict) -> dict:
    """Call Drug Extractor Service to parse OCR output."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.DRUG_EXTRACTOR_URL}/extract",
                json={
                    "lines": ocr_result.get("lines", []),
                    "raw_text": ocr_result.get("raw_text", "")
                }
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Drug Extractor error: {response.text}"
                )
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Drug extraction timed out. Please try again."
        )


async def call_drug_info_service(drug_name: str) -> dict:
    """Call Drug Info Service to get educational information."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{settings.DRUG_INFO_SERVICE_URL}/drug-info/{drug_name}"
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Drug Info Service error: {response.text}"
                )
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Drug info service timed out. The AI model is taking too long. Please try again."
        )


# ============ API Endpoints ============

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Gateway health check."""
    return HealthStatus(
        service=SERVICE_NAMES["gateway"],
        status="healthy",
        version="1.0.0"
    )


@app.get("/health/services")
async def services_health_check():
    """Check health of all downstream services."""
    services = {
        "gateway": "healthy",
        "ocr_service": "unknown",
        "drug_extractor": "unknown",
        "drug_info_service": "unknown",
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check OCR Service
        try:
            resp = await client.get(f"{settings.OCR_SERVICE_URL}/health")
            services["ocr_service"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except:
            services["ocr_service"] = "unavailable"
        
        # Check Drug Extractor
        try:
            resp = await client.get(f"{settings.DRUG_EXTRACTOR_URL}/health")
            services["drug_extractor"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except:
            services["drug_extractor"] = "unavailable"
        
        # Check Drug Info Service
        try:
            resp = await client.get(f"{settings.DRUG_INFO_SERVICE_URL}/health")
            services["drug_info_service"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except:
            services["drug_info_service"] = "unavailable"
    
    return services


@app.post("/api/upload-prescription", response_model=UploadPrescriptionResponse)
async def upload_prescription(file: UploadFile = File(...)):
    """
    Upload and process a prescription image.
    
    Pipeline:
    1. OCR Service extracts text from image
    2. Drug Extractor parses medications
    3. Returns medications with confidence levels
    
    If any drug has LOW confidence, requires_user_confirmation is True.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {list(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    try:
        # Step 1: OCR
        ocr_result = await call_ocr_service(content, file.filename)
        
        # Step 2: Extract drugs
        extraction_result = await call_drug_extractor(ocr_result)
        
        # Process medications
        medications = []
        drugs_needing_confirmation = []
        
        for med in extraction_result.get("medications", []):
            drug = DrugCandidate(**med)
            medications.append(drug)
            
            if drug.confidence_level == ConfidenceLevel.LOW:
                drugs_needing_confirmation.append(drug.drug_name)
        
        prescription_id = extraction_result.get("prescription_id", str(uuid4()))
        
        # Store session for potential confirmation
        prescription_sessions[prescription_id] = {
            "medications": [m.dict() for m in medications],
            "ocr_confidence": ocr_result.get("average_confidence", 0),
            "created_at": datetime.utcnow().isoformat()
        }
        
        return UploadPrescriptionResponse(
            prescription_id=prescription_id,
            filename=file.filename,
            ocr_confidence=ocr_result.get("average_confidence", 0),
            medications=medications,
            requires_user_confirmation=len(drugs_needing_confirmation) > 0,
            drugs_needing_confirmation=drugs_needing_confirmation,
            processed_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/confirm-drug", response_model=ConfirmDrugResponse)
async def confirm_drug(request: ConfirmDrugRequest):
    """
    Confirm or correct a low-confidence drug name.
    
    Used when OCR confidence is LOW and user needs to verify.
    """
    session = prescription_sessions.get(request.prescription_id)
    if not session:
        raise HTTPException(status_code=404, detail="Prescription session not found")
    
    # Find and update the drug
    for med in session["medications"]:
        if med["drug_id"] == request.drug_id:
            original_name = med["drug_name"]
            med["drug_name"] = request.confirmed_name
            med["confidence_level"] = "HIGH"
            med["requires_confirmation"] = False
            
            return ConfirmDrugResponse(
                success=True,
                drug_id=request.drug_id,
                original_name=original_name,
                confirmed_name=request.confirmed_name,
                message="Drug name confirmed successfully"
            )
    
    raise HTTPException(status_code=404, detail="Drug not found in prescription")


@app.get("/api/drug-info/{drug_name}", response_model=DrugInfoResponse)
async def get_drug_info(drug_name: str):
    """
    Get educational information about a specific drug.
    
    Returns:
    - General uses
    - Common side effects
    - Safety warnings
    - OTC recommendations for side effects
    - Educational disclaimer
    """
    try:
        info = await call_drug_info_service(drug_name)
        
        return DrugInfoResponse(
            drug_name=info.get("drug_name", drug_name),
            uses=info.get("uses", "Information not available"),
            side_effects=info.get("side_effects", []),
            warnings=info.get("warnings", []),
            disclaimer=info.get("disclaimer", EDUCATIONAL_DISCLAIMER),
            otc_for_side_effects=info.get("otc_for_side_effects", []),
            otc_disclaimer=info.get("otc_disclaimer")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Return fallback info on error
        return DrugInfoResponse(
            drug_name=drug_name,
            uses="Unable to retrieve information. Please consult your healthcare provider.",
            side_effects=["Information not available"],
            warnings=["Always consult your healthcare provider for medication information"],
            disclaimer=EDUCATIONAL_DISCLAIMER
        )


@app.get("/api/prescription/{prescription_id}")
async def get_prescription(prescription_id: str):
    """Get stored prescription data."""
    session = prescription_sessions.get(prescription_id)
    if not session:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return session


@app.delete("/api/prescription/{prescription_id}")
async def delete_prescription(prescription_id: str):
    """Delete prescription data (privacy compliance)."""
    if prescription_id in prescription_sessions:
        del prescription_sessions[prescription_id]
        return {"message": "Prescription data deleted"}
    raise HTTPException(status_code=404, detail="Prescription not found")


# ============ Static Information ============

@app.get("/api/disclaimer")
async def get_disclaimer():
    """Get the standard educational disclaimer."""
    return {"disclaimer": EDUCATIONAL_DISCLAIMER}


@app.get("/api/info")
async def get_api_info():
    """Get API information and capabilities."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "supported_formats": list(settings.ALLOWED_EXTENSIONS),
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "confidence_thresholds": {
            "high": f">= {settings.CONFIDENCE_HIGH_THRESHOLD * 100}%",
            "medium": f"{settings.CONFIDENCE_MEDIUM_THRESHOLD * 100}% - {settings.CONFIDENCE_HIGH_THRESHOLD * 100}%",
            "low": f"< {settings.CONFIDENCE_MEDIUM_THRESHOLD * 100}%"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.GATEWAY_PORT,
        reload=True
    )
