"""
Brand Entity Strength Checker V2 - Two-Step Approach
Step 1: Natural information gathering without classification bias
Step 2: Independent classification using GPT-4o-mini
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel
import json
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings
import sys

router = APIRouter()

# Classification labels
EntityStrength = Literal["KNOWN_STRONG", "KNOWN_WEAK", "UNKNOWN", "CONFUSED"]

class BrandEntityRequestV2(BaseModel):
    brand_name: str
    domain: Optional[str] = None  # e.g., "www.avea-life.com"
    information_vendor: str = "google"  # For main query: google or openai
    classifier_vendor: str = "openai"  # For classification: uses gpt-4o-mini

class ClassificationResult(BaseModel):
    specific_facts: int
    generic_claims: int
    entities_mentioned: int
    multiple_entities: bool
    classification: EntityStrength
    confidence: float
    reasoning: str

class EntityClassificationV2(BaseModel):
    label: EntityStrength
    confidence: float
    reasoning: str
    natural_response: str  # The unbiased response from Step 1
    classifier_analysis: ClassificationResult  # Analysis from Step 2
    specific_facts_count: int
    generic_claims_count: int
    entities_mentioned: List[str]
    disambiguation_needed: bool
    confusion_detected: bool
    methodology: str = "two-step"

class BrandEntityResponseV2(BaseModel):
    brand: str
    information_vendor: str
    classifier_vendor: str
    classification: EntityClassificationV2
    timestamp: datetime
    raw_responses: Dict[str, str]  # Both step 1 and step 2 raw responses

async def fetch_brand_info(domain: str) -> Dict[str, Any]:
    """
    Fetch and analyze a brand's website to understand what they actually do
    """
    if not domain:
        return {}
    
    # Clean up domain
    if not domain.startswith('http'):
        domain = f'https://{domain}'
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(domain)
            
            if response.status_code != 200:
                return {"error": f"Could not access website (status {response.status_code})"}
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key information
            title = soup.find('title')
            title_text = title.text.strip().lower() if title else ""
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = (meta_desc.get('content', '').lower() if meta_desc else "")
            
            # Industry detection
            combined_text = f"{title_text} {description}"
            
            industries = {
                "health/wellness": ["supplement", "health", "wellness", "nutrition", "vitamin", "longevity"],
                "telecommunications": ["telecom", "mobile", "carrier", "network", "5g", "4g"],
                "software/tech": ["software", "app", "platform", "api", "cloud", "saas"],
            }
            
            detected_industry = "unknown"
            for industry, keywords in industries.items():
                if any(kw in combined_text for kw in keywords):
                    detected_industry = industry
                    break
            
            return {
                "domain": domain,
                "title": title_text,
                "description": description,
                "industry": detected_industry
            }
            
    except Exception as e:
        return {"error": str(e)}

def create_natural_prompt(brand_name: str) -> tuple[str, str]:
    """
    Create a natural, unbiased prompt for information gathering
    No classification request, no testing indication
    """
    # No system prompt - keep it naked
    system_prompt = ""
    
    # User's exact prompt
    user_prompt = f"""Tell me about the brand {brand_name}. Tell me the top 20 things you associate with the brand. Also, what do they do, where are they based, and what are they known for?"""
    
    return system_prompt, user_prompt

def create_classification_prompt(brand_name: str, ai_response: str) -> tuple[str, str]:
    """
    Create a prompt for GPT-4o-mini to classify the response
    """
    system_prompt = """You are a classification assistant that analyzes AI responses to determine 
the depth and quality of knowledge about brands/companies. Be objective and consistent."""
    
    user_prompt = f"""Analyze this AI response about the brand '{brand_name}':

"{ai_response}"

Perform the following analysis:

1. Count SPECIFIC FACTS: Dates, locations, names of people, exact products, numbers, etc.
2. Count GENERIC CLAIMS: Vague statements that could apply to any company
3. Count DISTINCT ENTITIES: How many different companies/organizations are mentioned
4. Identify if multiple entities share the name (disambiguation needed)
5. Detect confusion: Is the AI mixing up different entities?

Classification rules:
- KNOWN_STRONG: 4+ specific facts about at least one entity
- KNOWN_WEAK: 1-3 specific facts
- UNKNOWN: 0 specific facts (only generic or no information)
- CONFUSED: Mixing different entities incorrectly

Return ONLY valid JSON in this exact format:
{{
    "specific_facts": <number>,
    "generic_claims": <number>,
    "entities_mentioned": <number>,
    "entity_names": ["list", "of", "entity", "names", "found"],
    "multiple_entities": <true/false>,
    "classification": "KNOWN_STRONG|KNOWN_WEAK|UNKNOWN|CONFUSED",
    "confidence": <0-100>,
    "reasoning": "Brief explanation of classification"
}}"""
    
    return system_prompt, user_prompt

async def classify_response(brand_name: str, ai_response: str, adapter: LangChainAdapter) -> ClassificationResult:
    """
    Use GPT-4o-mini to classify the AI response
    """
    system_prompt, user_prompt = create_classification_prompt(brand_name, ai_response)
    
    try:
        # Use GPT-4o-mini for classification (cheap and fast)
        response = await adapter.generate(
            vendor="openai",  # This will use gpt-4o-mini
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0,  # Deterministic classification
            max_tokens=300
        )
        
        response_text = response.get("text", "")
        
        # Extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                data = json.loads(json_str)
                return ClassificationResult(
                    specific_facts=data.get("specific_facts", 0),
                    generic_claims=data.get("generic_claims", 0),
                    entities_mentioned=data.get("entities_mentioned", 0),
                    multiple_entities=data.get("multiple_entities", False),
                    classification=data.get("classification", "UNKNOWN"),
                    confidence=data.get("confidence", 0),
                    reasoning=data.get("reasoning", "Classification failed")
                )
            except json.JSONDecodeError:
                pass
        
        # Fallback if JSON parsing fails
        return ClassificationResult(
            specific_facts=0,
            generic_claims=0,
            entities_mentioned=0,
            multiple_entities=False,
            classification="UNKNOWN",
            confidence=0,
            reasoning="Failed to parse classification response"
        )
        
    except Exception as e:
        return ClassificationResult(
            specific_facts=0,
            generic_claims=0,
            entities_mentioned=0,
            multiple_entities=False,
            classification="UNKNOWN",
            confidence=0,
            reasoning=f"Classification error: {str(e)}"
        )

@router.post("/brand-entity-strength-v2")
async def check_brand_entity_strength_v2(request: BrandEntityRequestV2):
    """
    Two-step entity strength checker:
    1. Get natural response from primary model (Gemini/GPT)
    2. Classify using GPT-4o-mini
    """
    
    adapter = LangChainAdapter()
    
    # Override the model for classification to use GPT-4o-mini
    from langchain_openai import ChatOpenAI
    adapter.models["classifier"] = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key
    )
    
    # Fetch actual brand info from website if provided
    brand_info = {}
    if request.domain:
        brand_info = await fetch_brand_info(request.domain)
    
    # Step 1: Get natural, unbiased response
    system_prompt, user_prompt = create_natural_prompt(request.brand_name)
    
    try:
        # Get information from primary model
        import asyncio
        # Only pass system_prompt if it's not empty
        generate_params = {
            "vendor": request.information_vendor,
            "prompt": user_prompt,
            "temperature": 0.3,
            "max_tokens": 1500
        }
        if system_prompt:  # Only add system_prompt if not empty
            generate_params["system_prompt"] = system_prompt
            
        information_response = await asyncio.wait_for(
            adapter.generate(**generate_params),
            timeout=60
        )
        
        natural_response = information_response.get("text", "")
        
        if not natural_response:
            raise HTTPException(status_code=500, detail="No response from information model")
        
        # Step 2: Classify the response using GPT-4o-mini
        classification = await classify_response(request.brand_name, natural_response, adapter)
        
        # Extract entity names from the natural response
        entity_names = []
        if hasattr(classification, 'entity_names'):
            entity_names = classification.entity_names
        
        # Determine disambiguation and confusion
        disambiguation_needed = classification.multiple_entities
        confusion_detected = classification.classification == "CONFUSED"
        
        # If we have brand info, check if AI is talking about the right entity
        if brand_info and brand_info.get("industry"):
            actual_industry = brand_info["industry"]
            # Simple check if the response mentions the right industry
            industry_keywords = {
                "health/wellness": ["supplement", "health", "wellness", "vitamin"],
                "telecommunications": ["telecom", "mobile", "carrier", "network"],
                "software/tech": ["software", "app", "platform", "technology"]
            }
            
            if actual_industry in industry_keywords:
                expected_words = industry_keywords[actual_industry]
                if not any(word in natural_response.lower() for word in expected_words):
                    confusion_detected = True
                    classification.reasoning += f" (Website indicates {actual_industry} but response doesn't match)"
        
        # Create the final classification
        entity_classification = EntityClassificationV2(
            label=classification.classification,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            natural_response=natural_response,
            classifier_analysis=classification,
            specific_facts_count=classification.specific_facts,
            generic_claims_count=classification.generic_claims,
            entities_mentioned=entity_names,
            disambiguation_needed=disambiguation_needed,
            confusion_detected=confusion_detected
        )
        
        # Create response
        response_data = BrandEntityResponseV2(
            brand=request.brand_name,
            information_vendor=request.information_vendor,
            classifier_vendor="gpt-4o-mini",
            classification=entity_classification,
            timestamp=datetime.now(),
            raw_responses={
                "information_response": natural_response,
                "classification_response": classification.reasoning
            }
        )
        
        return response_data.dict()
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Add batch endpoint for multiple brands
class BatchEntityRequestV2(BaseModel):
    brands: List[str]
    information_vendor: str = "google"

@router.post("/brand-entity-strength-v2/batch")
async def check_multiple_brands_v2(request: BatchEntityRequestV2):
    """
    Check multiple brands using the two-step approach
    """
    results = []
    
    for brand in request.brands[:10]:  # Limit to 10
        try:
            entity_request = BrandEntityRequestV2(
                brand_name=brand, 
                information_vendor=request.information_vendor
            )
            result = await check_brand_entity_strength_v2(entity_request)
            results.append({
                "brand": brand,
                "strength": result["classification"]["label"],
                "confidence": result["classification"]["confidence"],
                "methodology": "two-step"
            })
        except Exception as e:
            results.append({
                "brand": brand,
                "strength": "ERROR",
                "confidence": 0,
                "error": str(e)
            })
    
    return {"results": results}