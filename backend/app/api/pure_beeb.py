"""
Pure BEEB Implementation
Using embedding APIs directly for pure vector similarity analysis
No chat/completion APIs - only measuring semantic space distances
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import numpy as np
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

class PureBEEBRequest(BaseModel):
    brand_name: str
    tracked_phrases: List[str]
    use_canonical_entities: bool = True
    vendor: str = None  # Optional: specify vendor, otherwise uses all available

class PureBEEBResponse(BaseModel):
    brand: str
    top_entities: List[Dict[str, Any]]  # B→E: Entities associated with brand
    top_brands: List[Dict[str, Any]]    # E→B: Brands associated with phrases

# Predefined entities to test against (for any brand)
STANDARD_ENTITIES = [
    # Industry/Market
    "technology", "software", "hardware", "telecommunications", "mobile", "network",
    "healthcare", "medicine", "pharmaceuticals", "biotech", "medical devices",
    "supplements", "nutrition", "wellness", "fitness", "health",
    "finance", "banking", "insurance", "investment", "fintech",
    "retail", "ecommerce", "marketplace", "shopping", "consumer goods",
    "automotive", "transportation", "logistics", "delivery", "mobility",
    
    # Product attributes
    "quality", "premium", "luxury", "affordable", "value", "budget",
    "innovative", "cutting-edge", "advanced", "traditional", "classic",
    "sustainable", "eco-friendly", "organic", "natural", "synthetic",
    "clinical", "scientific", "research-backed", "evidence-based", "proven",
    
    # Specific to supplements/longevity
    "longevity", "anti-aging", "healthspan", "lifespan", "vitality",
    "NMN", "NAD+", "resveratrol", "collagen", "omega-3", "probiotics",
    "vitamins", "minerals", "antioxidants", "amino acids", "peptides",
    "cellular health", "mitochondria", "telomeres", "autophagy", "senescence",
    "biohacking", "optimization", "performance", "recovery", "energy",
    
    # Geographic
    "Swiss", "European", "American", "Asian", "Japanese", "German",
    "Turkey", "Turkish", "Istanbul", "Ankara",
    
    # Telecom specific (to test AVEA confusion)
    "AVEA", "Turkcell", "Vodafone", "mobile operator", "GSM", "4G", "5G",
    "roaming", "data plan", "prepaid", "postpaid", "coverage"
]

# Predefined brands to test against
STANDARD_BRANDS = [
    # Supplement/Longevity brands
    "Elysium Health", "Tru Niagen", "Life Extension", "Thorne Research",
    "Pure Encapsulations", "NOW Foods", "Jarrow Formulas", "Garden of Life",
    "Vital Proteins", "Athletic Greens", "Ritual", "HUM Nutrition",
    "Timeline Nutrition", "ProHealth Longevity", "Renue By Science",
    "Double Wood Supplements", "Alive By Science", "Solgar", "Nature Made",
    "Nutricost", "BulkSupplements", "Nootropics Depot", "Swanson",
    
    # Potential confusions
    "AVEA", "AVEA Telecom", "AVEA Turkey", "AVEA Mobile",
    
    # Other health brands
    "GNC", "Vitamin Shoppe", "iHerb", "Vitacost", "CVS Health",
    "Walgreens", "Amazon Basics", "Kirkland Signature",
    
    # Wellness/Lifestyle
    "Goop", "Moon Juice", "Bulletproof", "Four Sigmatic", "HVMN",
    "Onnit", "MindBodyGreen", "Sakara Life", "Daily Harvest"
]

def dot_product_similarity(vec_a: np.ndarray, vec_b: np.ndarray, normalize: bool = True) -> float:
    """
    Calculate dot product similarity
    If normalize=True, this is equivalent to cosine similarity
    """
    if normalize:
        # Normalize vectors
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a > 0:
            vec_a = vec_a / norm_a
        if norm_b > 0:
            vec_b = vec_b / norm_b
    
    return float(np.dot(vec_a, vec_b))

@router.post("/pure-beeb", response_model=PureBEEBResponse)
async def run_pure_beeb(request: PureBEEBRequest):
    """
    Pure BEEB analysis using only embedding APIs
    No chat/completion - just measuring vector distances
    """
    
    if not settings.openai_api_key and not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="No embedding API keys configured"
        )
    
    adapter = LangChainAdapter()
    brand_name = request.brand_name
    tracked_phrases = request.tracked_phrases[:10]  # Limit for performance
    
    # Determine which vendor(s) to use
    vendors_to_use = []
    
    if request.vendor:
        # Use specific vendor if requested
        if request.vendor == "openai" and settings.openai_api_key:
            vendors_to_use = ["openai"]
        elif request.vendor == "google" and settings.google_api_key:
            vendors_to_use = ["google"]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Vendor {request.vendor} not available or no API key configured"
            )
    else:
        # Use all available vendors
        if settings.openai_api_key:
            vendors_to_use.append("openai")
        if settings.google_api_key:
            vendors_to_use.append("google")
    
    if not vendors_to_use:
        raise HTTPException(
            status_code=500,
            detail="No embedding API keys configured"
        )
    
    # Run analysis for each vendor
    all_results = {}
    
    for vendor in vendors_to_use:
        print(f"\nRunning BEEB analysis with {vendor} embeddings...")
        vendor_results = await run_vendor_beeb(
            adapter, vendor, brand_name, tracked_phrases
        )
        all_results[vendor] = vendor_results
    
    # If single vendor requested, return just those results
    if request.vendor and request.vendor in all_results:
        return all_results[request.vendor]
    
    # Otherwise return first available vendor results (for backward compatibility)
    first_vendor = vendors_to_use[0]
    return all_results[first_vendor]

async def run_vendor_beeb(
    adapter: LangChainAdapter,
    vendor: str,
    brand_name: str,
    tracked_phrases: List[str]
) -> PureBEEBResponse:
    """Run BEEB analysis for a specific vendor's embeddings"""
    normalize = True  # Always normalize for consistency
    
    # Get brand embedding
    brand_embedding = await adapter.get_embedding(vendor, brand_name)
    brand_vec = np.array(brand_embedding)
    
    # B→E Analysis: Calculate similarity between brand and all entities
    entity_similarities = []
    
    for entity in STANDARD_ENTITIES:
        try:
            entity_embedding = await adapter.get_embedding(vendor, entity)
            entity_vec = np.array(entity_embedding)
            
            # Calculate dot product similarity
            similarity = dot_product_similarity(brand_vec, entity_vec, normalize=normalize)
            
            entity_similarities.append({
                "entity": entity,
                "similarity": similarity
            })
        except Exception as e:
            print(f"Error getting embedding for entity '{entity}': {str(e)}")
    
    # Sort by similarity and format for display
    entity_similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    top_entities = []
    for i, item in enumerate(entity_similarities[:20]):
        # Convert similarity to display metrics
        # Higher similarity = higher frequency, lower position, higher weight
        frequency = int(50 * abs(item["similarity"]))  # Scale to 0-50
        avg_position = 1 + (1 - abs(item["similarity"])) * 9  # 1-10 range
        weighted_score = abs(item["similarity"])  # Direct similarity as weight
        
        top_entities.append({
            "entity": item["entity"],
            "frequency": max(1, frequency),
            "avg_position": round(avg_position, 2),
            "weighted_score": round(weighted_score, 3),
            "raw_similarity": round(item["similarity"], 4)  # Include raw score for debugging
        })
    
    # E→B Analysis: Calculate similarity between phrases and brands
    brand_phrase_scores = {}
    
    # Get embeddings for all tracked phrases
    phrase_embeddings = []
    for phrase in tracked_phrases:
        try:
            embedding = await adapter.get_embedding(vendor, phrase)
            phrase_embeddings.append(np.array(embedding))
        except Exception as e:
            print(f"Error getting embedding for phrase '{phrase}': {str(e)}")
    
    # Calculate average phrase embedding
    if phrase_embeddings:
        avg_phrase_vec = np.mean(phrase_embeddings, axis=0)
        
        # Test all brands including user's brand
        test_brands = STANDARD_BRANDS + [brand_name]
        
        for test_brand in test_brands:
            try:
                brand_test_embedding = await adapter.get_embedding(vendor, test_brand)
                brand_test_vec = np.array(brand_test_embedding)
                
                # Calculate similarity to average phrase vector
                similarity = dot_product_similarity(avg_phrase_vec, brand_test_vec, normalize=normalize)
                
                brand_phrase_scores[test_brand] = similarity
                
            except Exception as e:
                print(f"Error getting embedding for brand '{test_brand}': {str(e)}")
    
    # Sort brands by similarity and format
    brand_similarities = [
        {"brand": brand, "similarity": score}
        for brand, score in brand_phrase_scores.items()
        if brand.lower() != brand_name.lower()  # Exclude the user's brand from its own results
    ]
    brand_similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    top_brands = []
    for i, item in enumerate(brand_similarities[:20]):
        frequency = int(40 * abs(item["similarity"]))
        avg_position = 1 + (1 - abs(item["similarity"])) * 9
        weighted_score = abs(item["similarity"])
        
        # Mark if it's the user's brand (shouldn't happen now but keep for safety)
        is_user_brand = item["brand"].lower() == brand_name.lower()
        
        top_brands.append({
            "brand": item["brand"],
            "frequency": max(1, frequency),
            "avg_position": round(avg_position, 2),
            "weighted_score": round(weighted_score, 3),
            "raw_similarity": round(item["similarity"], 4),
            "is_user_brand": is_user_brand
        })
    
    # Log some insights
    print(f"\nTop 5 entities for {brand_name}:")
    for e in top_entities[:5]:
        print(f"  - {e['entity']}: {e['raw_similarity']}")
    
    print(f"\nTop 5 brands for phrases {tracked_phrases[:2]}...:")
    for b in top_brands[:5]:
        mark = " (YOU)" if b.get("is_user_brand") else ""
        print(f"  - {b['brand']}{mark}: {b['raw_similarity']}")
    
    # Find AVEA telecom confusion if testing AVEA Life
    if "AVEA Life" in brand_name:
        avea_entities = [e for e in top_entities if "AVEA" in e["entity"] or "telecom" in e["entity"].lower()]
        if avea_entities:
            print(f"\nWARNING: CONFUSION DETECTED: {brand_name} associates with:")
            for e in avea_entities:
                print(f"  - {e['entity']}: {e['raw_similarity']}")
    
    return PureBEEBResponse(
        brand=brand_name,
        top_entities=top_entities,
        top_brands=top_brands
    )

@router.post("/vendor-beeb", response_model=Dict[str, PureBEEBResponse])
async def run_all_vendor_beeb(request: PureBEEBRequest):
    """
    Run BEEB analysis for all available vendors separately
    Returns results for each vendor's embedding space
    """
    
    if not settings.openai_api_key and not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="No embedding API keys configured"
        )
    
    adapter = LangChainAdapter()
    brand_name = request.brand_name
    tracked_phrases = request.tracked_phrases[:10]
    
    results = {}
    
    # Run for OpenAI if available
    if settings.openai_api_key:
        print("\nRunning BEEB for OpenAI embeddings...")
        results["openai"] = await run_vendor_beeb(
            adapter, "openai", brand_name, tracked_phrases
        )
    
    # Run for Google if available
    if settings.google_api_key:
        print("\nRunning BEEB for Google embeddings...")
        results["google"] = await run_vendor_beeb(
            adapter, "google", brand_name, tracked_phrases
        )
    
    return results