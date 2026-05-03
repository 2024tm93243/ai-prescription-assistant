"""
LLM prompt templates for Drug Info Service.
Strict prompts with JSON output and educational disclaimers.
"""

from __future__ import annotations

from shared.config import EDUCATIONAL_DISCLAIMER

# System prompt for drug information generation
DRUG_INFO_SYSTEM_PROMPT = """You are a pharmaceutical information assistant that provides educational information about medications.

CRITICAL CONSTRAINTS - YOU MUST FOLLOW THESE:
1. Provide ONLY general educational information about medications
2. NEVER provide specific medical advice
3. NEVER suggest changing dosage, timing, or frequency of prescribed medications
4. NEVER recommend alternative or substitute drugs
5. When suggesting OTC options for side effects, ALWAYS emphasize consulting a healthcare provider first
6. NEVER provide diagnosis or treatment recommendations
7. Always emphasize that users should consult their healthcare provider

OUTPUT FORMAT:
You must respond with a valid JSON object in exactly this format:
{
    "uses": "A brief description of what this medication is commonly used for",
    "side_effects": ["effect1", "effect2", "effect3"],
    "warnings": ["warning1", "warning2", "warning3"],
    "otc_for_side_effects": [
        {
            "side_effect": "name of side effect",
            "otc_options": ["OTC drug 1", "OTC drug 2"],
            "caution": "Specific caution about this OTC for this drug"
        }
    ]
}

For OTC recommendations:
- Only suggest commonly used OTC medications that people often take
- Limit to 2-3 most common side effects that have OTC options
- Include specific cautions about interactions or contraindications
- Make it clear these are educational examples, not prescriptions

Keep responses factual, concise, and educational. Do not include markdown formatting."""


# User prompt template for drug info request
DRUG_INFO_USER_PROMPT_TEMPLATE = """Provide educational information about the medication: {drug_name}

Remember:
- Uses: Describe general therapeutic uses (1-2 sentences)
- Side Effects: List 3-5 common side effects
- Warnings: List 3-5 general safety warnings
- OTC for Side Effects: For 2-3 common side effects, suggest OTC options that people commonly use, with specific cautions

Respond with valid JSON only, no additional text."""


# Fallback response when LLM fails or drug is unknown
FALLBACK_DRUG_INFO = {
    "uses": "Information not available. Please consult your healthcare provider or pharmacist for details about this medication.",
    "side_effects": [
        "Side effect information not available",
        "Consult your healthcare provider for complete information"
    ],
    "warnings": [
        "Always take medications as prescribed by your doctor",
        "Report any unusual symptoms to your healthcare provider",
        "Keep all medications out of reach of children"
    ]
}


# Response when drug name appears invalid
INVALID_DRUG_RESPONSE = {
    "uses": "The medication name could not be verified. Please confirm the correct spelling with your healthcare provider.",
    "side_effects": ["Unable to provide side effect information for unverified medication"],
    "warnings": [
        "Please verify the medication name is correct",
        "Consult your pharmacist or healthcare provider for accurate information"
    ]
}


def get_drug_info_prompt(drug_name: str) -> tuple[str, str]:
    """
    Get system and user prompts for drug info request.
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = DRUG_INFO_USER_PROMPT_TEMPLATE.format(drug_name=drug_name)
    return DRUG_INFO_SYSTEM_PROMPT, user_prompt


def get_disclaimer() -> str:
    """Get the standard educational disclaimer."""
    return EDUCATIONAL_DISCLAIMER
