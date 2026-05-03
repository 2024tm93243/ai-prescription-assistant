"""
Drug Extractor Service - FastAPI microservice for parsing OCR output.
Extracts drug candidates with confidence levels from prescription text.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES
from shared.models import (
    DrugCandidate,
    ExtractionResult,
    ConfidenceLevel,
    compute_confidence_level,
    HealthStatus,
    OCRLine,
)

settings = get_settings()

app = FastAPI(
    title="Drug Extractor Service",
    description="Extracts drug names and details from OCR text",
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

# ============ Extraction Patterns ============

FREQ_HINTS = [
    "od", "bd", "bid", "tid", "qid", "qhs",
    "q6h", "q8h", "q12h", "q4h",
    "once daily", "twice daily", "three times daily",
    "four times daily", "every", "hourly",
]

ROUTE_HINTS = [
    "po", "oral", "iv", "im", "sc", "subcut",
    "topical", "inh", "sl", "sublingual",
    "pr", "rectal", "intranasal", "ophthalmic",
]

DOSAGE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg|g|mcg|ug|ml|mL|units|IU|%)\b",
    re.IGNORECASE
)

DURATION_RE = re.compile(
    r"\bfor\s+(\d+\s*(day|days|week|weeks|month|months))\b",
    re.IGNORECASE
)

QUANTITY_RE = re.compile(
    r"\b(\d+)\s*(tab|tabs|tablet|tablets|caps|capsule|capsules|ml|mL|dose|doses)\b",
    re.IGNORECASE
)

# Common drug name prefixes/suffixes to help identify drug names
DRUG_PREFIXES = ["tab", "cap", "inj", "syp", "cream", "oint", "drop", "susp"]

# ============ Common Drug Names Database ============
# Common drugs for fuzzy matching when OCR confidence is low
COMMON_DRUGS = [
    # Pain relievers / Analgesics
    "paracetamol", "acetaminophen", "ibuprofen", "aspirin", "naproxen",
    "diclofenac", "tramadol", "codeine", "morphine", "fentanyl",
    
    # Antibiotics
    "amoxicillin", "azithromycin", "ciprofloxacin", "doxycycline",
    "metronidazole", "cephalexin", "levofloxacin", "clindamycin",
    "erythromycin", "penicillin", "ampicillin", "augmentin",
    
    # Antihypertensives
    "amlodipine", "lisinopril", "losartan", "metoprolol", "atenolol",
    "ramipril", "enalapril", "valsartan", "hydrochlorothiazide",
    
    # Diabetes medications
    "metformin", "glipizide", "glimepiride", "sitagliptin", "insulin",
    
    # Gastrointestinal
    "omeprazole", "pantoprazole", "ranitidine", "famotidine",
    "lansoprazole", "esomeprazole", "antacid", "domperidone",
    
    # Respiratory
    "salbutamol", "montelukast", "cetirizine", "loratadine",
    "fluticasone", "budesonide", "theophylline", "prednisolone",
    
    # Cardiovascular
    "atorvastatin", "simvastatin", "rosuvastatin", "clopidogrel",
    "warfarin", "digoxin", "furosemide", "spironolactone",
    
    # Mental health
    "sertraline", "fluoxetine", "escitalopram", "alprazolam",
    "diazepam", "lorazepam", "amitriptyline", "risperidone",
    
    # Vitamins and supplements
    "vitamin", "calcium", "iron", "folic", "zinc", "multivitamin",
    
    # Other common
    "prednisone", "levothyroxine", "albuterol", "gabapentin",
    "pregabalin", "meloxicam", "cyclobenzaprine", "trazodone",
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def fuzzy_match_drug(text: str, threshold: float = 0.6) -> Tuple[str, float]:
    """
    Try to fuzzy match text against known drug names.
    Returns (matched_drug_name, similarity_score) or ("", 0) if no match.
    """
    if not text or len(text) < 3:
        return "", 0
    
    text_lower = text.lower().strip()
    best_match = ""
    best_score = 0
    
    for drug in COMMON_DRUGS:
        # Exact match
        if text_lower == drug:
            return drug.capitalize(), 1.0
        
        # Partial match (text is contained in drug or vice versa)
        if text_lower in drug or drug in text_lower:
            score = min(len(text_lower), len(drug)) / max(len(text_lower), len(drug))
            if score > best_score:
                best_score = score
                best_match = drug.capitalize()
                continue
        
        # Levenshtein distance based similarity
        distance = levenshtein_distance(text_lower, drug)
        max_len = max(len(text_lower), len(drug))
        similarity = 1 - (distance / max_len)
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = drug.capitalize()
    
    return best_match, best_score


# ============ Request Models ============

class ExtractionRequest(BaseModel):
    """Request for drug extraction."""
    lines: List[OCRLine]
    raw_text: str = ""


class SimpleExtractionRequest(BaseModel):
    """Simple extraction from raw text."""
    text: str
    default_confidence: float = 0.8


# ============ Helper Functions ============

def normalize_line(line: str) -> str:
    """Normalize whitespace in a line."""
    return re.sub(r"\s+", " ", line).strip()


def detect_frequency(line: str) -> str:
    """Detect medication frequency from line."""
    lower = line.lower()
    for hint in FREQ_HINTS:
        if hint in lower:
            return hint
    return ""


def detect_route(line: str) -> str:
    """Detect administration route from line."""
    lower = line.lower()
    for hint in ROUTE_HINTS:
        if re.search(rf"\b{re.escape(hint)}\b", lower):
            return hint
    return ""


def extract_dosage(line: str) -> str:
    """Extract dosage information from line."""
    match = DOSAGE_RE.search(line)
    if not match:
        return ""
    return f"{match.group(1)} {match.group(2)}"


def extract_duration(line: str) -> str:
    """Extract duration from line."""
    match = DURATION_RE.search(line)
    if match:
        return match.group(1)
    return ""


def extract_quantity(line: str) -> str:
    """Extract quantity from line."""
    match = QUANTITY_RE.search(line)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return ""


def guess_drug_name(line: str, ocr_confidence: float = 1.0) -> Tuple[str, float]:
    """
    Extract likely drug name from a prescription line.
    Uses heuristics and fuzzy matching to identify the drug name.
    Returns (drug_name, adjusted_confidence).
    """
    # Remove common prefixes
    cleaned = line
    for prefix in DRUG_PREFIXES:
        pattern = rf"^\s*{prefix}\.?\s+"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Split into tokens
    tokens = re.split(r"[^A-Za-z0-9\-]+", cleaned)
    tokens = [t for t in tokens if t and len(t) > 1]
    
    if not tokens:
        return "", 0
    
    # Filter out common non-drug words
    skip_words = {"mg", "ml", "tab", "cap", "daily", "for", "days", "take", "with", "food", "water", "before", "after", "meals"}
    
    # Try each token for drug name
    for token in tokens:
        if token.lower() in skip_words or token.isdigit():
            continue
        
        # Try fuzzy matching first
        matched_drug, match_score = fuzzy_match_drug(token)
        if matched_drug and match_score >= 0.6:
            # Adjust confidence based on fuzzy match score
            adjusted_conf = min(ocr_confidence, match_score)
            if match_score >= 0.85:
                adjusted_conf = max(ocr_confidence, match_score)  # High match boosts confidence
            return matched_drug, adjusted_conf
        
        # If OCR confidence is decent, use the token as-is
        if ocr_confidence >= 0.5:
            return token, ocr_confidence
    
    # Last resort: try fuzzy match on entire cleaned text
    matched_drug, match_score = fuzzy_match_drug(cleaned)
    if matched_drug and match_score >= 0.5:
        return matched_drug, match_score
    
    # Return first non-skip token if available
    for token in tokens:
        if token.lower() not in skip_words and not token.isdigit():
            return token, ocr_confidence
    
    return tokens[0] if tokens else "", ocr_confidence


def is_medication_line(line: str) -> bool:
    """Determine if a line likely contains medication information."""
    lower = line.lower()
    
    # Check for dosage pattern
    if DOSAGE_RE.search(line):
        return True
    
    # Check for frequency hints
    for hint in FREQ_HINTS:
        if hint in lower:
            return True
    
    # Check for drug prefixes
    for prefix in DRUG_PREFIXES:
        if lower.startswith(prefix) or f" {prefix}" in lower:
            return True
    
    return False


def extract_drug_from_line(
    text: str,
    confidence: float
) -> Tuple[DrugCandidate | None, bool]:
    """
    Extract drug information from a single line.
    Returns (DrugCandidate, is_medication_line).
    """
    clean = normalize_line(text)
    if not clean:
        return None, False
    
    if not is_medication_line(clean):
        return None, False
    
    drug_name, adjusted_confidence = guess_drug_name(clean, confidence)
    if not drug_name:
        return None, False
    
    # Use the better of OCR confidence or fuzzy match confidence
    final_confidence = max(confidence, adjusted_confidence)
    
    confidence_level = compute_confidence_level(final_confidence)
    requires_confirmation = confidence_level == ConfidenceLevel.LOW
    
    candidate = DrugCandidate(
        drug_id=str(uuid4())[:8],
        drug_name=drug_name,
        confidence=final_confidence,
        confidence_level=confidence_level,
        requires_confirmation=requires_confirmation,
        dosage=extract_dosage(clean),
        frequency=detect_frequency(clean),
        route=detect_route(clean),
        duration=extract_duration(clean),
        quantity=extract_quantity(clean),
        instructions=clean,
    )
    
    return candidate, True


# ============ API Endpoints ============

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        service=SERVICE_NAMES["extractor"],
        status="healthy",
        version="1.0.0"
    )


@app.post("/extract", response_model=ExtractionResult)
async def extract_drugs(request: ExtractionRequest):
    """
    Extract drug candidates from OCR lines.
    
    Each line includes text and confidence score.
    Returns structured medication list with confidence levels.
    """
    medications: List[DrugCandidate] = []
    unparsed_lines: List[str] = []
    seen_drugs: set = set()  # Avoid duplicates
    
    for line in request.lines:
        candidate, is_med = extract_drug_from_line(line.text, line.confidence)
        
        if candidate and candidate.drug_name.lower() not in seen_drugs:
            medications.append(candidate)
            seen_drugs.add(candidate.drug_name.lower())
        elif not is_med and line.text.strip():
            unparsed_lines.append(line.text.strip())
    
    # Also process raw_text if lines didn't yield results
    if not medications and request.raw_text:
        for line_text in request.raw_text.splitlines():
            candidate, is_med = extract_drug_from_line(line_text, 0.7)
            if candidate and candidate.drug_name.lower() not in seen_drugs:
                medications.append(candidate)
                seen_drugs.add(candidate.drug_name.lower())
    
    # Fallback: Direct fuzzy match on ALL text (for tablet photos, packaging)
    # This helps when OCR extracts just drug names without prescription indicators
    if not medications:
        all_text = request.raw_text if request.raw_text else " ".join(l.text for l in request.lines)
        # Try each word/token for fuzzy match against known drugs
        tokens = re.split(r"[^A-Za-z0-9\-]+", all_text)
        for token in tokens:
            if len(token) < 3 or token.lower() in {"the", "and", "for", "with", "take"}:
                continue
            matched_drug, score = fuzzy_match_drug(token)
            if matched_drug and score >= 0.7 and matched_drug.lower() not in seen_drugs:
                # Found a drug name match
                avg_confidence = sum(l.confidence for l in request.lines) / len(request.lines) if request.lines else 0.7
                final_confidence = max(avg_confidence, score)
                confidence_level = compute_confidence_level(final_confidence)
                
                candidate = DrugCandidate(
                    drug_id=str(uuid4())[:8],
                    drug_name=matched_drug,
                    confidence=final_confidence,
                    confidence_level=confidence_level,
                    requires_confirmation=confidence_level == ConfidenceLevel.LOW,
                    dosage=extract_dosage(all_text),
                    frequency="",
                    route="",
                    duration="",
                    quantity="",
                    instructions=f"From image: {token}",
                )
                medications.append(candidate)
                seen_drugs.add(matched_drug.lower())
    
    return ExtractionResult(
        prescription_id=str(uuid4()),
        medications=medications,
        unparsed_lines=unparsed_lines,
        extraction_timestamp=datetime.utcnow()
    )


@app.post("/extract/simple", response_model=ExtractionResult)
async def extract_drugs_simple(request: SimpleExtractionRequest):
    """
    Extract drugs from plain text (without per-line confidence).
    Uses default confidence for all extracted drugs.
    """
    lines = [
        OCRLine(text=line, confidence=request.default_confidence)
        for line in request.text.splitlines()
        if line.strip()
    ]
    
    return await extract_drugs(ExtractionRequest(
        lines=lines,
        raw_text=request.text
    ))


@app.post("/validate-drug-name")
async def validate_drug_name(drug_name: str):
    """
    Basic validation of a drug name.
    Returns whether it looks like a valid drug name.
    """
    if not drug_name or len(drug_name) < 2:
        return {"valid": False, "reason": "Name too short"}
    
    if drug_name.isdigit():
        return {"valid": False, "reason": "Name cannot be only digits"}
    
    if len(drug_name) > 50:
        return {"valid": False, "reason": "Name too long"}
    
    return {"valid": True, "drug_name": drug_name}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.DRUG_EXTRACTOR_PORT,
        reload=True
    )
