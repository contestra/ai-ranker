from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import json
import re
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

class RealAnalysisRequest(BaseModel):
    brand_name: str
    phrases: List[str]

class RealAnalysisResponse(BaseModel):
    brand: str
    entities: List[str]
    competitor_brands: List[str]
    analysis_results: List[Dict[str, Any]]

@router.post("/real-analysis", response_model=RealAnalysisResponse)
async def run_real_analysis(request: RealAnalysisRequest):
    """
    Actually query AI models for brand rankings
    """
    # Check if we have API keys configured
    if not settings.openai_api_key and not settings.google_api_key and not settings.anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="No AI API keys configured. Please set OPENAI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY in your .env file"
        )
    
    adapter = LangChainAdapter()
    brand_name = request.brand_name
    phrases = request.phrases[:5]  # Limit to 5 phrases to avoid rate limits
    
    results = {
        "brand": brand_name,
        "entities": [],
        "competitor_brands": set(),
        "analysis_results": []
    }
    
    # Determine available vendors based on API keys
    available_vendors = []
    if settings.openai_api_key:
        available_vendors.append("openai")
    if settings.google_api_key:
        available_vendors.append("google")
    if settings.anthropic_api_key:
        available_vendors.append("anthropic")
    
    if not available_vendors:
        raise HTTPException(
            status_code=500,
            detail="No valid API keys found. Please configure at least one AI provider."
        )
    
    # Query each phrase with each available vendor
    for phrase in phrases:
        for vendor in available_vendors:
            try:
                # Create a prompt that will return brand recommendations
                prompt = f"""You are a helpful assistant providing product recommendations. 
                
A user asks: "{phrase}"

Please recommend the top 5-7 brands or products that best match this query. 
Focus on real, established brands in the market.
Return your response as a simple numbered list with just the brand names, like:
1. Brand Name
2. Another Brand
3. Third Brand

Keep your response concise and just list the brands."""

                # Query the AI model
                # Google doesn't support max_tokens parameter
                if vendor == "google":
                    response = await adapter.generate(
                        vendor=vendor,
                        prompt=prompt,
                        temperature=0.3  # Lower temperature for more consistent results
                    )
                else:
                    response = await adapter.generate(
                        vendor=vendor,
                        prompt=prompt,
                        temperature=0.3,  # Lower temperature for more consistent results
                        max_tokens=200
                    )
                
                # Parse the response to extract brand names
                text = response["text"]
                brands_found = []
                
                # Extract numbered list items (e.g., "1. Brand Name")
                lines = text.split('\n')
                for line in lines:
                    # Match patterns like "1. Brand" or "- Brand" or "* Brand" or "• Brand"
                    # Also handle two-space indentation that Google sometimes uses
                    match = re.match(r'^(?:\s*)?(?:\d+\.|\-|\*|•)\s+(.+?)(?:\s*[-–].*)?$', line.strip())
                    if match:
                        brand = match.group(1).strip()
                        # Clean up the brand name - remove trailing punctuation
                        brand = brand.rstrip('.,;:')
                        # Remove any parenthetical notes but keep the brand name
                        brand = re.sub(r'\s*\([^)]*\)$', '', brand)
                        
                        # Check if this looks like a brand name (not a sentence)
                        if (brand and 
                            len(brand) > 2 and 
                            len(brand) < 50 and 
                            not brand.lower().startswith(('the ', 'it ', 'this ', 'that ', 'there '))):
                            brands_found.append(brand)
                
                # Check if user's brand was mentioned
                brand_mentioned = False
                position = None
                
                for i, found_brand in enumerate(brands_found):
                    if brand_name.lower() in found_brand.lower():
                        brand_mentioned = True
                        position = i + 1
                        break
                
                # Add all found brands to competitor list
                results["competitor_brands"].update(brands_found)
                
                # Store the result
                results["analysis_results"].append({
                    "phrase": phrase,
                    "vendor": vendor,
                    "brands_found": brands_found[:6],  # Limit to 6 brands
                    "brand_mentioned": brand_mentioned,
                    "position": position
                })
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error querying {vendor} for '{phrase}': {str(e)}")
                # Add a failed result
                results["analysis_results"].append({
                    "phrase": phrase,
                    "vendor": vendor,
                    "brands_found": [],
                    "brand_mentioned": False,
                    "position": None,
                    "error": str(e)
                })
    
    # Extract entities from the phrases and responses
    entities = set()
    
    # Common entities in the space
    entity_keywords = {
        "supplements", "vitamins", "health", "wellness", "longevity", 
        "anti-aging", "NMN", "NAD+", "resveratrol", "collagen",
        "nutrition", "biohacking", "cellular", "mitochondria",
        "antioxidants", "probiotics", "omega-3", "protein"
    }
    
    # Extract entities from phrases
    for phrase in phrases:
        phrase_lower = phrase.lower()
        for keyword in entity_keywords:
            if keyword.lower() in phrase_lower:
                entities.add(keyword)
    
    # Add some entities based on brand category
    if "longevity" in brand_name.lower() or "life" in brand_name.lower():
        entities.update(["longevity", "anti-aging", "healthspan"])
    if "supplement" in " ".join(phrases).lower():
        entities.update(["supplements", "nutrition", "wellness"])
    
    results["entities"] = list(entities)[:10]
    results["competitor_brands"] = list(results["competitor_brands"])[:10]
    
    return results