"""
Drug Info Service - FastAPI microservice for drug educational information.
Uses pluggable LLM providers (LM Studio local or Groq cloud).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import (
    get_settings,
    validate_llm_config,
    get_llm_config_summary,
    SERVICE_NAMES,
    EDUCATIONAL_DISCLAIMER
)
from shared.models import DrugInfo, DrugInfoRequest, HealthStatus, OTCRecommendation

# Import LLM client abstraction
from drug_info_service.llm_client import (
    LLMClient,
    create_llm_client,
    parse_llm_json_response
)

settings = get_settings()

# Import prompts
from drug_info_service.prompts import (
    get_drug_info_prompt,
    FALLBACK_DRUG_INFO,
    INVALID_DRUG_RESPONSE,
)

app = FastAPI(
    title="Drug Info Service",
    description="LLM-powered drug educational information service",
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


# ============ LLM Client Initialization ============

# Global LLM client instance
llm_client: Optional[LLMClient] = None

@app.on_event("startup")
async def startup_event():
    """Initialize LLM client on startup and validate configuration."""
    global llm_client
    
    # Validate configuration
    is_valid, error_msg = validate_llm_config(settings)
    if not is_valid:
        print(f"❌ LLM Configuration Error: {error_msg}")
        print("⚠️  Service will start but requests will fail until configuration is fixed.")
        print("📝 See README.md for configuration instructions.")
        return
    
    # Create LLM client
    try:
        llm_client = create_llm_client(settings)
        config_summary = get_llm_config_summary(settings, redact_secrets=True)
        print(f"✅ LLM Provider initialized: {config_summary['provider']}")
        print(f"   Model: {config_summary['model']}")
        print(f"   Base URL: {config_summary['base_url']}")
        
        # Check connectivity
        health = llm_client.health_check()
        if health['status'] == 'available':
            print(f"✅ LLM Provider connectivity: OK")
        else:
            print(f"⚠️  LLM Provider connectivity: {health.get('error', 'Unknown error')}")
            print("   Requests may fail until the provider is available.")
            
    except Exception as e:
        print(f"❌ Failed to initialize LLM client: {str(e)}")
        print("⚠️  Service will start but requests will fail.")


def get_llm_client() -> LLMClient:
    """Get the initialized LLM client or raise error."""
    if llm_client is None:
        raise HTTPException(
            status_code=503,
            detail="LLM client not initialized. Check service configuration."
        )
    return llm_client
    """
    Call LM Studio chat completion endpoint.
    
    Args:
        system_prompt: System message for the LLM
        user_prompt: User message/query
        
    Returns:
        LLM response text
        
    Raises:
        HTTPException: If LM Studio is unavailable or request fails
    """
    url = f"{settings.LMSTUDIO_BASE_URL}/chat/completions"
    
    payload = {
        "model": settings.LMSTUDIO_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": settings.LMSTUDIO_TEMPERATURE,
        "stream": False,
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=settings.LMSTUDIO_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="LM Studio server is not available. Please ensure it is running at "
                   f"{settings.LMSTUDIO_BASE_URL}"
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="LM Studio request timed out. The model may be loading or overloaded."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LM Studio request failed: {str(e)}"
        )


def parse_llm_json_response(response: str) -> dict:
    """
    Parse JSON from LLM response, handling code fences and malformed output.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Parsed dictionary
    """
    # Strip whitespace
    response = response.strip()
    
    # Remove code fences if present
    if response.startswith("```"):
        response = response.strip("`")
        if response.lower().startswith("json"):
            response = response[4:].strip()
    
    # Try to find JSON object in response
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None


def validate_drug_name(drug_name: str) -> bool:
    """Basic validation that drug name looks reasonable."""
    if not drug_name or len(drug_name) < 2:
        return False
    if drug_name.isdigit():
        return False
    if len(drug_name) > 100:
        return False
    return True


# ============ API Endpoints ============

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        service=SERVICE_NAMES["drug_info"],
        status="healthy",
        version="1.0.0"
    )


@app.get("/health/llm")
async def llm_health_check():
    """
    Check LLM provider status and connectivity.
    Returns provider name, status, and configuration (secrets redacted).
    """
    try:
        client = get_llm_client()
        health_status = client.health_check()
        config_summary = get_llm_config_summary(settings, redact_secrets=True)
        
        return {
            "service": "drug_info",
            "llm_provider": health_status.get("provider"),
            "llm_status": health_status.get("status"),
            "llm_config": config_summary,
            "details": health_status
        }
    except Exception as e:
        return {
            "service": "drug_info",
            "llm_status": "error",
            "error": str(e)
        }
        return {
            "status": "not_configured",
            "message": "GROQ_API_KEY not set. Get a free key from console.groq.com"
        }
    
    try:
        response = requests.get(
            f"{settings.GROQ_BASE_URL}/models",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=5
        )
        response.raise_for_status()
        return {
            "status": "healthy",
            "model": settings.GROQ_MODEL,
            "available_models": [m["id"] for m in response.json().get("data", [])][:5]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/health/llm")
async def llm_health_check():
    """Check which LLM is configured and its status."""
    if settings.USE_GROQ and settings.GROQ_API_KEY:
        groq_status = await groq_health_check()
        return {
            "active_llm": "groq",
            "model": settings.GROQ_MODEL,
            "status": groq_status
        }
    else:
        lmstudio_status = await lmstudio_health_check()
        return {
            "active_llm": "lmstudio",
            "model": settings.LMSTUDIO_CHAT_MODEL,
            "status": lmstudio_status
        }


@app.post("/drug-info", response_model=DrugInfo)
async def get_drug_info(request: DrugInfoRequest):
    """
    Get educational information about a drug.
    
    Uses LM Studio to generate:
    - General uses of the medication
    - Common side effects
    - Safety warnings
    
    Always includes educational disclaimer.
    """
    drug_name = request.drug_name.strip()
    
    # Validate drug name
    if not validate_drug_name(drug_name):
        return DrugInfo(
            drug_name=drug_name,
            uses=INVALID_DRUG_RESPONSE["uses"],
            side_effects=INVALID_DRUG_RESPONSE["side_effects"],
            warnings=INVALID_DRUG_RESPONSE["warnings"],
            disclaimer=EDUCATIONAL_DISCLAIMER,
            generated_at=datetime.utcnow()
        )
    
    # Get prompts
    system_prompt, user_prompt = get_drug_info_prompt(drug_name)
    
    try:
        # Get LLM client
        client = get_llm_client()
        
        # Call LLM
        llm_response = client.generate_drug_education(
            drug_name=drug_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Parse response
        parsed = parse_llm_json_response(llm_response)
        
        if parsed:
            # Parse OTC recommendations if present
            otc_recommendations = []
            if request.include_otc_recommendations and "otc_for_side_effects" in parsed:
                for otc_data in parsed.get("otc_for_side_effects", []):
                    if isinstance(otc_data, dict):
                        otc_rec = OTCRecommendation(
                            side_effect=otc_data.get("side_effect", ""),
                            otc_options=otc_data.get("otc_options", []),
                            caution=otc_data.get("caution", "Consult your healthcare provider before taking any OTC medication.")
                        )
                        otc_recommendations.append(otc_rec)
            
            return DrugInfo(
                drug_name=drug_name,
                uses=parsed.get("uses", FALLBACK_DRUG_INFO["uses"]),
                side_effects=parsed.get("side_effects", FALLBACK_DRUG_INFO["side_effects"]),
                warnings=parsed.get("warnings", FALLBACK_DRUG_INFO["warnings"]),
                otc_for_side_effects=otc_recommendations if request.include_otc_recommendations else [],
                disclaimer=EDUCATIONAL_DISCLAIMER if request.include_disclaimer else "",
                generated_at=datetime.utcnow()
            )
        else:
            # Parsing failed, use fallback
            return DrugInfo(
                drug_name=drug_name,
                uses=FALLBACK_DRUG_INFO["uses"],
                side_effects=FALLBACK_DRUG_INFO["side_effects"],
                warnings=FALLBACK_DRUG_INFO["warnings"],
                disclaimer=EDUCATIONAL_DISCLAIMER if request.include_disclaimer else "",
                generated_at=datetime.utcnow()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Return fallback on any error
        return DrugInfo(
            drug_name=drug_name,
            uses=f"Unable to retrieve information: {str(e)}",
            side_effects=FALLBACK_DRUG_INFO["side_effects"],
            warnings=FALLBACK_DRUG_INFO["warnings"],
            disclaimer=EDUCATIONAL_DISCLAIMER if request.include_disclaimer else "",
            generated_at=datetime.utcnow()
        )


@app.get("/drug-info/{drug_name}", response_model=DrugInfo)
async def get_drug_info_by_name(
    drug_name: str, 
    include_disclaimer: bool = True,
    include_otc: bool = True
):
    """
    Get educational information about a drug by name (GET endpoint).
    
    Path parameter version for simple requests.
    """
    return await get_drug_info(DrugInfoRequest(
        drug_name=drug_name,
        include_disclaimer=include_disclaimer,
        include_otc_recommendations=include_otc
    ))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.DRUG_INFO_SERVICE_PORT,
        reload=True
    )
