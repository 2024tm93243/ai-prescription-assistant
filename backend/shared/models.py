"""
Shared Pydantic models for all microservices.
Prescription Understanding & Patient Education Assistant
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """OCR confidence level thresholds."""
    HIGH = "HIGH"      # >= 85%
    MEDIUM = "MEDIUM"  # 60% - 85%
    LOW = "LOW"        # < 60%


def compute_confidence_level(confidence: float) -> ConfidenceLevel:
    """Convert numeric confidence to categorical level."""
    if confidence >= 0.85:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.60:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


# ============ OCR Service Models ============

class OCRLine(BaseModel):
    """Single line from OCR with confidence."""
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: Optional[List[List[float]]] = None


class OCRResult(BaseModel):
    """Result from OCR Service."""
    filename: str
    page_count: int
    lines: List[OCRLine]
    average_confidence: float = Field(ge=0.0, le=1.0)
    raw_text: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# ============ Drug Extractor Models ============

class DrugCandidate(BaseModel):
    """Extracted drug candidate with confidence."""
    drug_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    drug_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    requires_confirmation: bool = False
    dosage: str = ""
    frequency: str = ""
    route: str = ""
    duration: str = ""
    quantity: str = ""
    instructions: str = ""


class ExtractionResult(BaseModel):
    """Result from Drug Extractor Service."""
    prescription_id: str = Field(default_factory=lambda: str(uuid4()))
    medications: List[DrugCandidate]
    unparsed_lines: List[str] = []
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ Drug Info Service Models ============

class OTCRecommendation(BaseModel):
    """OTC drug recommendation for managing side effects."""
    side_effect: str
    otc_options: List[str]
    caution: str = "Consult your healthcare provider before taking any OTC medication."


class DrugInfoRequest(BaseModel):
    """Request for drug educational information."""
    drug_name: str
    include_disclaimer: bool = True
    include_otc_recommendations: bool = True


class DrugInfo(BaseModel):
    """Educational information about a drug."""
    drug_name: str
    uses: str
    side_effects: List[str]
    warnings: List[str]
    otc_for_side_effects: Optional[List[OTCRecommendation]] = []
    disclaimer: str = (
        "DISCLAIMER: This information is for educational purposes only and is not "
        "intended as medical advice. Do not change your medication regimen without "
        "consulting your healthcare provider. Always follow your doctor's instructions "
        "regarding dosage, timing, and duration of treatment."
    )
    otc_disclaimer: str = (
        "⚠️ IMPORTANT: OTC recommendations are for educational purposes only. "
        "ALWAYS consult your doctor or pharmacist before taking any OTC medication, "
        "as they may interact with your prescribed drugs or worsen certain conditions."
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============ API Gateway Models ============

class UploadPrescriptionResponse(BaseModel):
    """Response after uploading and processing a prescription."""
    prescription_id: str
    filename: str
    ocr_confidence: float
    medications: List[DrugCandidate]
    requires_user_confirmation: bool = False
    drugs_needing_confirmation: List[str] = []
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class ConfirmDrugRequest(BaseModel):
    """Request to confirm a low-confidence drug name."""
    prescription_id: str
    drug_id: str
    confirmed_name: str


class ConfirmDrugResponse(BaseModel):
    """Response after confirming a drug name."""
    success: bool
    drug_id: str
    original_name: str
    confirmed_name: str
    message: str


class DrugInfoResponse(BaseModel):
    """Full drug info response including disclaimer."""
    drug_name: str
    uses: str
    side_effects: List[str]
    warnings: List[str]
    disclaimer: str
    otc_for_side_effects: Optional[List[OTCRecommendation]] = None
    otc_disclaimer: Optional[str] = None


# ============ Audit/Logging Models ============

class AuditLogEntry(BaseModel):
    """Privacy-preserving audit log entry."""
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str  # e.g., "PRESCRIPTION_UPLOADED", "DRUG_INFO_REQUESTED"
    prescription_id: Optional[str] = None
    drug_count: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    # Note: No PHI (drug names, patient info) stored in audit logs


# ============ Health Check Models ============

class HealthStatus(BaseModel):
    """Service health status."""
    service: str
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ Error Models ============

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
