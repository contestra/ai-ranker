"""
BEEB (Brand-Entity Embedding Benchmark) Implementation
Based on Dejan.ai methodology for measuring brand positioning in LLM vector spaces
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
import numpy as np
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

class EmbeddingAnalysisRequest(BaseModel):
    brand_name: str
    tracked_phrases: List[str]
    test_entities: List[str] = None  # Optional list of entities to test

class EmbeddingAnalysisResponse(BaseModel):
    brand: str
    top_entities: List[Dict[str, Any]]  # B→E: Entities associated with brand
    top_brands: List[Dict[str, Any]]    # E→B: Brands associated with phrases
    
def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))

@router.post("/embedding-analysis", response_model=EmbeddingAnalysisResponse)
async def run_embedding_analysis(request: EmbeddingAnalysisRequest):
    """
    Perform BEEB analysis using vector embeddings and cosine similarity
    """
    
    # Check if we have API keys for embeddings
    if not settings.openai_api_key and not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="No embedding API keys configured. Please set OPENAI_API_KEY or GOOGLE_API_KEY"
        )
    
    adapter = LangChainAdapter()
    
    # Determine which embedding provider to use
    vendor = "openai" if settings.openai_api_key else "google"
    
    brand_name = request.brand_name
    tracked_phrases = request.tracked_phrases[:10]  # Limit to avoid rate limits
    
    # Default test entities if not provided
    if not request.test_entities:
        # Common entities for longevity/supplement brands
        test_entities = [
            # Product categories
            "supplements", "vitamins", "nutrition", "wellness", "health",
            "longevity", "anti-aging", "biohacking", "healthspan", "lifespan",
            
            # Specific compounds
            "NMN", "NAD+", "resveratrol", "collagen", "omega-3",
            "probiotics", "antioxidants", "CoQ10", "quercetin", "spermidine",
            
            # Attributes
            "quality", "premium", "science-backed", "research", "clinical",
            "natural", "organic", "vegan", "Swiss", "European",
            
            # Concepts
            "cellular health", "mitochondria", "telomeres", "autophagy", "senescence",
            "oxidative stress", "inflammation", "metabolism", "energy", "vitality"
        ]
    else:
        test_entities = request.test_entities
    
    # Test competitor brands - DON'T include user's brand in test list
    test_brands = [
        # Well-known longevity/supplement brands
        "Elysium Health", "Tru Niagen", "Life Extension", "Thorne Research",
        "Pure Encapsulations", "NOW Foods", "Jarrow Formulas", "Garden of Life",
        "Vital Proteins", "Athletic Greens", "Ritual", "HUM Nutrition",
        "Timeline Nutrition", "ProHealth Longevity",
        "Renue By Science", "Double Wood Supplements", "Alive By Science",
        "Solgar", "Nature Made", "Nutricost"
    ]
    
    # Add user's brand separately to test its position
    test_brands.append(brand_name)
    
    try:
        # Get brand embedding (for B→E analysis)
        brand_embedding = await adapter.get_embedding(vendor, brand_name)
        brand_vec = np.array(brand_embedding)
        
        # B→E Analysis: Find entities most similar to the brand
        entity_similarities = []
        for entity in test_entities:
            entity_embedding = await adapter.get_embedding(vendor, entity)
            entity_vec = np.array(entity_embedding)
            
            similarity = cosine_similarity(brand_vec, entity_vec)
            entity_similarities.append({
                "entity": entity,
                "similarity": similarity
            })
        
        # Sort by similarity and create top entities list
        entity_similarities.sort(key=lambda x: x["similarity"], reverse=True)
        top_entities = []
        
        for i, item in enumerate(entity_similarities[:20]):
            # Calculate frequency based on similarity (higher similarity = higher frequency)
            frequency = int(50 * item["similarity"])  # Scale to reasonable frequency
            
            # Average position inversely related to similarity
            avg_position = 1 + (1 - item["similarity"]) * 5
            
            # Weighted score is the similarity itself
            weighted_score = item["similarity"]
            
            top_entities.append({
                "entity": item["entity"],
                "frequency": max(1, frequency),
                "avg_position": round(avg_position, 2),
                "weighted_score": round(weighted_score, 3)
            })
        
        # E→B Analysis: Find brands most similar to tracked phrases
        brand_phrase_scores = {}
        
        for phrase in tracked_phrases:
            phrase_embedding = await adapter.get_embedding(vendor, phrase)
            phrase_vec = np.array(phrase_embedding)
            
            for test_brand in test_brands:
                if test_brand not in brand_phrase_scores:
                    brand_phrase_scores[test_brand] = []
                
                brand_test_embedding = await adapter.get_embedding(vendor, test_brand)
                brand_test_vec = np.array(brand_test_embedding)
                
                similarity = cosine_similarity(phrase_vec, brand_test_vec)
                brand_phrase_scores[test_brand].append(similarity)
        
        # Average the scores for each brand across all phrases
        brand_avg_scores = []
        for brand, scores in brand_phrase_scores.items():
            if scores:
                avg_score = np.mean(scores)
                brand_avg_scores.append({
                    "brand": brand,
                    "similarity": avg_score
                })
        
        # Sort by average similarity
        brand_avg_scores.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Create top brands list
        top_brands = []
        for i, item in enumerate(brand_avg_scores[:20]):
            # Calculate metrics based on similarity
            frequency = int(40 * item["similarity"])
            avg_position = 1 + (1 - item["similarity"]) * 6
            weighted_score = item["similarity"]
            
            top_brands.append({
                "brand": item["brand"],
                "frequency": max(1, frequency),
                "avg_position": round(avg_position, 2),
                "weighted_score": round(weighted_score, 3)
            })
        
        return {
            "brand": brand_name,
            "top_entities": top_entities,
            "top_brands": top_brands
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during embedding analysis: {str(e)}"
        )