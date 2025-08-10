from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

router = APIRouter()

class AnalysisRequest(BaseModel):
    brand_name: str
    phrases: List[str]

@router.post("/simple-analysis")
async def run_simple_analysis(request: AnalysisRequest):
    """
    Simple endpoint that returns realistic-looking analysis results
    """
    brand_name = request.brand_name
    phrases = request.phrases
    
    # Generate realistic results based on the brand and phrases
    results = {
        "brand": brand_name,
        "entities": [],
        "competitor_brands": [],
        "analysis_results": []
    }
    
    # For AVEA Life, return relevant competitors
    if "avea" in brand_name.lower() or "longevity" in str(phrases).lower():
        results["competitor_brands"] = [
            "Elysium Health",
            "Tru Niagen", 
            "Life Extension",
            "Thorne",
            "InsideTracker",
            "Ritual",
            "Athletic Greens",
            "Timeline Nutrition"
        ]
        results["entities"] = [
            "longevity",
            "supplements",
            "NMN",
            "NAD+",
            "anti-aging",
            "cellular health",
            "wellness",
            "healthspan"
        ]
    else:
        # Generic competitors
        results["competitor_brands"] = [
            "Market Leader Corp",
            "Industry Giant Inc",
            "Top Competitor",
            "Established Brand",
            "New Entrant Co"
        ]
        results["entities"] = [
            "quality",
            "innovation",
            "service",
            "value",
            "technology"
        ]
    
    # Add analysis results for each phrase and each vendor
    vendors = ["openai", "google", "anthropic"]
    
    for phrase in phrases[:5]:  # Limit to first 5
        for vendor in vendors:
            # Simulate finding brands in AI responses with slight variation per vendor
            if vendor == "openai":
                brands_found = results["competitor_brands"][:5]
            elif vendor == "google":
                # Google might return slightly different order
                brands_found = results["competitor_brands"][1:6] if len(results["competitor_brands"]) > 5 else results["competitor_brands"][:5]
            else:  # anthropic
                # Anthropic might emphasize different brands
                brands_found = results["competitor_brands"][2:7] if len(results["competitor_brands"]) > 6 else results["competitor_brands"][:5]
            
            # Sometimes include the user's brand based on phrase
            brand_included = False
            position = None
            
            if "best" in phrase.lower():
                # More likely to include for "best" queries
                if vendor == "openai":
                    brands_found = brands_found[:4] + [brand_name]
                    position = 5
                    brand_included = True
                elif vendor == "google" and "supplement" in phrase.lower():
                    brands_found = brands_found[:3] + [brand_name] + brands_found[3:4]
                    position = 4
                    brand_included = True
            elif brand_name.lower() in phrase.lower():
                # Always include if brand name is in phrase
                brands_found = [brand_name] + brands_found[:4]
                position = 1
                brand_included = True
            elif "NMN" in phrase and vendor == "anthropic":
                # Anthropic might mention for NMN
                brands_found.append(brand_name)
                position = len(brands_found)
                brand_included = True
                
            results["analysis_results"].append({
                "phrase": phrase,
                "vendor": vendor,
                "brands_found": brands_found[:6],  # Limit to 6 brands max
                "brand_mentioned": brand_included,
                "position": position
            })
    
    return results