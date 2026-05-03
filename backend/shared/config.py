"""
Shared configuration for all microservices.
Prescription Understanding & Patient Education Assistant
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service ports
    GATEWAY_PORT: int = 8000
    OCR_SERVICE_PORT: int = 8001
    DRUG_EXTRACTOR_PORT: int = 8002
    DRUG_INFO_SERVICE_PORT: int = 8003
    AUDIT_SERVICE_PORT: int = 8004
    
    # Service URLs (for inter-service communication)
    OCR_SERVICE_URL: str = "http://localhost:8001"
    DRUG_EXTRACTOR_URL: str = "http://localhost:8002"
    DRUG_INFO_SERVICE_URL: str = "http://localhost:8003"
    AUDIT_SERVICE_URL: str = "http://localhost:8004"
    
    # LLM Provider Selection (lmstudio | groq)
    LLM_PROVIDER: str = "groq"  # Options: "lmstudio", "groq"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_RETRIES: int = 2
    LLM_LOG_LEVEL: str = "info"  # Options: "debug", "info", "warn", "error"
    
    # LM Studio configuration (local provider)
    LMSTUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LMSTUDIO_MODEL: str = "google/gemma-4-e2b"
    LMSTUDIO_API_KEY: str = "lm-studio"  # Placeholder (not required by LM Studio)
    LMSTUDIO_TEMPERATURE: float = 0.2
    LMSTUDIO_HEALTHCHECK_PATH: str = "/models"
    
    # Groq API configuration (cloud provider - free tier)
    GROQ_API_KEY: str = ""  # REQUIRED if LLM_PROVIDER=groq. Get from console.groq.com
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.3
    GROQ_API_VERSION: str = "v1"
    
    # Application environment
    APP_ENV: str = "dev"  # Options: "dev", "prod"
    
    # OCR configuration
    OCR_LANGUAGES: list = ["en"]
    OCR_USE_GPU: bool = False
    
    # Confidence thresholds
    CONFIDENCE_HIGH_THRESHOLD: float = 0.85
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.60
    
    # File storage
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".pdf"}
    
    # Retention policy (hours)
    IMAGE_RETENTION_HOURS: int = 24
    LOG_RETENTION_HOURS: int = 168  # 7 days
    
    # CORS settings
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Application info
    APP_NAME: str = "Prescription Understanding & Patient Education Assistant"
    APP_VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def validate_llm_config(settings: Settings) -> tuple[bool, str]:
    """
    Validate LLM configuration.
    
    Returns:
        (is_valid, error_message)
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider not in ["lmstudio", "groq"]:
        return False, f"Invalid LLM_PROVIDER: '{provider}'. Must be 'lmstudio' or 'groq'"
    
    if provider == "groq":
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "":
            return False, (
                "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
                "Get a free key from https://console.groq.com"
            )
        if not settings.GROQ_MODEL:
            return False, "GROQ_MODEL is required when using Groq provider"
    
    elif provider == "lmstudio":
        if not settings.LMSTUDIO_MODEL:
            return False, "LMSTUDIO_MODEL is required when using LM Studio provider"
        if not settings.LMSTUDIO_BASE_URL:
            return False, "LMSTUDIO_BASE_URL is required when using LM Studio provider"
    
    return True, ""


def get_llm_config_summary(settings: Settings, redact_secrets: bool = True) -> dict:
    """
    Get LLM configuration summary for logging/diagnostics.
    
    Args:
        settings: Application settings
        redact_secrets: If True, redact API keys
        
    Returns:
        Configuration summary dict
    """
    provider = settings.LLM_PROVIDER.lower()
    
    summary = {
        "provider": provider,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
        "max_retries": settings.LLM_MAX_RETRIES,
        "log_level": settings.LLM_LOG_LEVEL,
        "app_env": settings.APP_ENV,
    }
    
    if provider == "groq":
        summary.update({
            "base_url": settings.GROQ_BASE_URL,
            "model": settings.GROQ_MODEL,
            "temperature": settings.GROQ_TEMPERATURE,
            "api_key": "***REDACTED***" if redact_secrets else settings.GROQ_API_KEY,
        })
    elif provider == "lmstudio":
        summary.update({
            "base_url": settings.LMSTUDIO_BASE_URL,
            "model": settings.LMSTUDIO_MODEL,
            "temperature": settings.LMSTUDIO_TEMPERATURE,
        })
    
    return summary


# Fixed disclaimer text (used across services)
EDUCATIONAL_DISCLAIMER = (
    "DISCLAIMER: This information is for educational purposes only and is not "
    "intended as medical advice. Do not change your medication regimen without "
    "consulting your healthcare provider. Always follow your doctor's instructions "
    "regarding dosage, timing, and duration of treatment."
)


# Service names for logging
SERVICE_NAMES = {
    "gateway": "API Gateway",
    "ocr": "OCR Service",
    "extractor": "Drug Extractor Service",
    "drug_info": "Drug Info Service",
    "audit": "Audit Service",
}
