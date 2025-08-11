"""
Brand Entity Strength Checker
Determines if a brand is a known entity in AI models (strong, weak, unknown)
Based on entity-checker V52 methodology
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel
import json
from datetime import datetime
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

# Classification labels
EntityStrength = Literal["KNOWN_STRONG", "KNOWN_WEAK", "UNKNOWN", "EMPTY"]

class BrandEntityRequest(BaseModel):
    brand_name: str
    vendor: str = "openai"  # openai or google
    include_reasoning: bool = True

class EntityClassification(BaseModel):
    label: EntityStrength
    confidence: float  # 0-100
    reasoning: Optional[str] = None
    specific_claims: list[str] = []
    generic_claims: list[str] = []
    
class BrandEntityResponse(BaseModel):
    brand: str
    vendor: str
    classification: EntityClassification
    timestamp: datetime
    raw_response: Optional[str] = None

def create_probe_prompt(brand_name: str) -> tuple[str, str]:
    """
    Create the system and user prompts for entity checking
    """
    system_prompt = """You are evaluating whether a brand/company is genuinely known to you.

Classify responses into one of these categories:
- OK_STRONG: You have specific, verifiable facts about this real entity (founding date, location, products, leadership, etc.)
- OK_WEAK: You recognize the name or have some context but lack specific details
- CLARIFY: You have no information about this brand - it's completely unknown to you
- BLOCKED: You cannot or will not provide information

Important: Be honest about what you don't know. If you have zero information about a brand, classify it as CLARIFY. Only use OK_WEAK if you have at least some contextual knowledge.

Be honest about what you actually know vs. what you're inferring."""

    user_prompt = f"""Tell me about {brand_name}. What do they do, where are they based, and what are they known for?

Provide your response in this JSON format:
{{
    "classification": "OK_STRONG|OK_WEAK|CLARIFY|HALLUCINATION|BLOCKED",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your classification",
    "specific_claims": ["List of specific, verifiable facts you know"],
    "generic_claims": ["List of generic or inferred statements"],
    "response_text": "Your natural language response about the brand"
}}"""

    return system_prompt, user_prompt

def classify_response(response_data: Dict[str, Any]) -> EntityClassification:
    """
    Process the model's response and classify entity strength
    """
    # Map internal labels to public labels
    label_map = {
        "OK_STRONG": "KNOWN_STRONG",
        "OK_WEAK": "KNOWN_WEAK",
        "CLARIFY": "UNKNOWN",
        "BLOCKED": "EMPTY"
    }
    
    raw_label = response_data.get("classification", "CLARIFY")
    label = label_map.get(raw_label, "UNKNOWN")
    
    # Extract confidence score
    confidence = float(response_data.get("confidence", 30))  # Default to low confidence
    
    # Adjust confidence based on classification
    if label == "KNOWN_STRONG" and len(response_data.get("specific_claims", [])) < 2:
        # Downgrade if not enough specific claims
        label = "KNOWN_WEAK"
        confidence = min(confidence, 60)
    elif label == "KNOWN_WEAK" and len(response_data.get("specific_claims", [])) > 3:
        # Upgrade if many specific claims
        label = "KNOWN_STRONG"
        confidence = max(confidence, 70)
    elif label == "UNKNOWN":
        # For completely unknown brands, cap the confidence
        specific_claims = response_data.get("specific_claims", [])
        generic_claims = response_data.get("generic_claims", [])
        
        # If model has zero information, ensure low confidence
        if len(specific_claims) == 0 and len(generic_claims) == 0:
            confidence = min(confidence, 30)  # Very low confidence for unknowns
    
    return EntityClassification(
        label=label,
        confidence=confidence,
        reasoning=response_data.get("reasoning"),
        specific_claims=response_data.get("specific_claims", []),
        generic_claims=response_data.get("generic_claims", [])
    )

@router.post("/brand-entity-strength", response_model=BrandEntityResponse)
async def check_brand_entity_strength(request: BrandEntityRequest):
    """
    Check if a brand is a known entity in the AI model
    Returns classification of entity strength with confidence score
    """
    
    adapter = LangChainAdapter()
    
    # Create probe prompts
    system_prompt, user_prompt = create_probe_prompt(request.brand_name)
    
    try:
        # Query the model
        # Note: GPT-5 only supports default temperature (1.0)
        temperature = 1.0 if request.vendor == "openai" else 0.3
        response = await adapter.generate(
            vendor=request.vendor,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=500
        )
        
        response_text = response.get("text", "")
        
        # Try to parse JSON response
        response_data = {}
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                response_data = json.loads(response_text[json_start:json_end])
        except json.JSONDecodeError:
            # Fallback: analyze response text manually
            response_lower = response_text.lower()
            
            if "i don't have" in response_lower or "i'm not aware" in response_lower or response_text.strip() == "":
                response_data = {
                    "classification": "CLARIFY",
                    "confidence": 20,  # Very low confidence for complete unknowns
                    "reasoning": "Model has no knowledge of this brand",
                    "specific_claims": [],
                    "generic_claims": []
                }
            elif "cannot provide" in response_lower or "unable to" in response_lower:
                response_data = {
                    "classification": "BLOCKED",
                    "confidence": 90,
                    "reasoning": "Model refused to provide information",
                    "specific_claims": [],
                    "generic_claims": []
                }
            else:
                # Try to determine from content
                specific_indicators = ["founded in", "headquartered in", "ceo", "$", "employees", "acquired"]
                specific_count = sum(1 for ind in specific_indicators if ind in response_lower)
                
                if specific_count >= 3:
                    response_data = {
                        "classification": "OK_STRONG",
                        "confidence": 70,
                        "reasoning": "Response contains specific details",
                        "specific_claims": [],
                        "generic_claims": []
                    }
                else:
                    response_data = {
                        "classification": "OK_WEAK",
                        "confidence": 50,
                        "reasoning": "Response is generic",
                        "specific_claims": [],
                        "generic_claims": []
                    }
        
        # Classify the response
        classification = classify_response(response_data)
        
        return BrandEntityResponse(
            brand=request.brand_name,
            vendor=request.vendor,
            classification=classification,
            timestamp=datetime.now(),
            raw_response=response_text if request.include_reasoning else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking brand entity: {str(e)}")

class BatchEntityRequest(BaseModel):
    brands: list[str]
    vendor: str = "openai"

@router.post("/brand-entity-strength/batch")
async def check_multiple_brands(request: BatchEntityRequest):
    """
    Check multiple brands at once
    """
    results = []
    
    for brand in request.brands[:10]:  # Limit to 10 for safety
        try:
            entity_request = BrandEntityRequest(brand_name=brand, vendor=request.vendor, include_reasoning=False)
            result = await check_brand_entity_strength(entity_request)
            results.append({
                "brand": brand,
                "strength": result.classification.label,
                "confidence": result.classification.confidence
            })
        except Exception as e:
            results.append({
                "brand": brand,
                "strength": "ERROR",
                "confidence": 0,
                "error": str(e)
            })
    
    return {"results": results}