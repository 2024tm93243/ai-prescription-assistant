"""
LLM Client Abstraction - Clean provider interface.
Supports LM Studio (local) and Groq (cloud) providers.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Optional

import requests
from fastapi import HTTPException


class LLMClient(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_drug_education(
        self,
        drug_name: str,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """
        Generate educational drug information.
        
        Args:
            drug_name: Name of the drug
            system_prompt: System instructions for LLM
            user_prompt: User query/prompt
            
        Returns:
            LLM response text (should be JSON)
        """
        pass
    
    @abstractmethod
    def health_check(self) -> dict:
        """
        Check if provider is available.
        
        Returns:
            Dict with status, provider name, and connectivity info
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        pass


class LMStudioLLMClient(LLMClient):
    """LM Studio local server provider."""
    
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 120,
        temperature: float = 0.2,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.api_key = api_key or "lm-studio"  # Placeholder
        
    def generate_drug_education(
        self,
        drug_name: str,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call LM Studio chat completion endpoint."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "stream": False,
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except requests.exceptions.ConnectionError:
            raise HTTPException(
                status_code=503,
                detail=f"LM Studio server is not available at {self.base_url}. "
                       "Please ensure LM Studio is running with a loaded model."
            )
        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=504,
                detail="LM Studio request timed out. The model may be loading or overloaded."
            )
        except requests.exceptions.HTTPError as e:
            raise HTTPException(
                status_code=500,
                detail=f"LM Studio HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"LM Studio request failed: {str(e)}"
            )
    
    def health_check(self) -> dict:
        """Check if LM Studio server is reachable."""
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return {
                "provider": "lmstudio",
                "status": "available",
                "base_url": self.base_url,
                "model": self.model,
                "models_available": len(data.get("data", [])),
            }
        except Exception as e:
            return {
                "provider": "lmstudio",
                "status": "unavailable",
                "base_url": self.base_url,
                "error": str(e),
            }
    
    def get_provider_name(self) -> str:
        return "lmstudio"


class GroqLLMClient(LLMClient):
    """Groq cloud API provider."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
        temperature: float = 0.3
    ):
        if not api_key or api_key == "":
            raise ValueError(
                "GROQ_API_KEY is required. Get a free key from console.groq.com"
            )
        
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        
    def generate_drug_education(
        self,
        drug_name: str,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call Groq API for chat completion."""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": 2048,
            "stream": False,
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except requests.exceptions.ConnectionError:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to Groq API. Check your internet connection."
            )
        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=504,
                detail="Groq API request timed out."
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid GROQ_API_KEY. Get a valid key from console.groq.com"
                )
            elif e.response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Groq API error: Forbidden. Check your API key permissions."
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Groq API rate limit exceeded. Please try again later."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Groq API error: {e.response.status_code} - {e.response.text[:200]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Groq API request failed: {str(e)}"
            )
    
    def health_check(self) -> dict:
        """Check if Groq API is reachable."""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return {
                "provider": "groq",
                "status": "available",
                "base_url": self.base_url,
                "model": self.model,
                "models_available": len(data.get("data", [])),
            }
        except Exception as e:
            return {
                "provider": "groq",
                "status": "unavailable",
                "base_url": self.base_url,
                "error": str(e),
            }
    
    def get_provider_name(self) -> str:
        return "groq"


def parse_llm_json_response(response: str) -> Optional[dict]:
    """
    Parse JSON from LLM response, handling code fences and malformed output.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
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


def create_llm_client(settings) -> LLMClient:
    """
    Factory function to create the appropriate LLM client based on configuration.
    
    Args:
        settings: Application settings object
        
    Returns:
        LLMClient instance (LMStudioLLMClient or GroqLLMClient)
        
    Raises:
        ValueError: If provider is invalid or configuration is incomplete
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "lmstudio":
        return LMStudioLLMClient(
            base_url=settings.LMSTUDIO_BASE_URL,
            model=settings.LMSTUDIO_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            temperature=settings.LMSTUDIO_TEMPERATURE,
            api_key=settings.LMSTUDIO_API_KEY,
        )
    
    elif provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
                "Get a free key from https://console.groq.com"
            )
        
        return GroqLLMClient(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            model=settings.GROQ_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            temperature=settings.GROQ_TEMPERATURE,
        )
    
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: '{provider}'. Must be 'lmstudio' or 'groq'"
        )
