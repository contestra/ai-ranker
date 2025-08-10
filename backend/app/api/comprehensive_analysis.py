"""
Comprehensive BEEB Analysis
Combines real AI responses with embedding analysis
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Set
from pydantic import BaseModel
import numpy as np
import re
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

class ComprehensiveAnalysisRequest(BaseModel):
    brand_name: str
    tracked_phrases: List[str]

class ComprehensiveAnalysisResponse(BaseModel):
    brand: str
    discovered_entities: List[str]  # Entities found in AI responses
    top_entities: List[Dict[str, Any]]  # B→E: Entities associated with brand
    top_brands: List[Dict[str, Any]]    # E→B: Brands associated with phrases
    analysis_results: List[Dict[str, Any]]  # Raw AI responses

def extract_entities_from_text(text: str) -> Set[str]:
    """Extract potential entities from AI response text"""
    entities = set()
    
    # Common supplement/health entities to look for
    entity_patterns = [
        r'\b(NMN|NAD\+?|resveratrol|collagen|omega-?3|CoQ10|quercetin|spermidine)\b',
        r'\b(supplement[s]?|vitamin[s]?|mineral[s]?|antioxidant[s]?|probiotic[s]?)\b',
        r'\b(longevity|anti-?aging|healthspan|lifespan|wellness|health)\b',
        r'\b(cellular|mitochondri[a|al]|telomere[s]?|autophagy|senescence)\b',
        r'\b(energy|vitality|metabolism|inflammation|oxidative stress)\b',
        r'\b(premium|quality|science-?backed|clinical|research|natural|organic|vegan)\b',
        r'\b(Swiss|European|American|Japanese)\b',
    ]
    
    text_lower = text.lower()
    for pattern in entity_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            entity = match.group(0).strip()
            # Normalize common variations
            entity = entity.replace('-', ' ').replace('+', ' plus')
            entities.add(entity)
    
    # Also extract capitalized words that might be brand/product names
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    for word in capitalized:
        if len(word) > 3 and word not in ['The', 'This', 'That', 'These', 'Those']:
            entities.add(word.lower())
    
    return entities

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))

@router.post("/comprehensive-analysis", response_model=ComprehensiveAnalysisResponse)
async def run_comprehensive_analysis(request: ComprehensiveAnalysisRequest):
    """
    1. Query AI models about the brand and phrases
    2. Extract entities from responses
    3. Calculate embeddings for discovered entities
    4. Perform BEEB analysis
    """
    
    if not settings.openai_api_key and not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="No API keys configured. Please set OPENAI_API_KEY or GOOGLE_API_KEY"
        )
    
    adapter = LangChainAdapter()
    brand_name = request.brand_name
    tracked_phrases = request.tracked_phrases[:5]  # Limit to avoid rate limits
    
    # Determine available vendors
    available_vendors = []
    if settings.openai_api_key:
        available_vendors.append("openai")
    if settings.google_api_key:
        available_vendors.append("google")
    
    # Step 1: Query AI models about the brand and phrases
    all_entities = set()
    all_brands = set()
    analysis_results = []
    
    # Query about the brand itself (B→E)
    for vendor in available_vendors:
        try:
            # Ask about the brand
            brand_prompt = f"""Tell me about {brand_name}. What are they known for? 
What products or services do they offer? What makes them unique in their market?
Keep your response concise but informative."""

            response = await adapter.generate(
                vendor=vendor,
                prompt=brand_prompt,
                temperature=0.3,
                max_tokens=300 if vendor != "google" else None
            )
            
            # Extract entities from response
            entities_found = extract_entities_from_text(response["text"])
            all_entities.update(entities_found)
            
            # Store the analysis result
            analysis_results.append({
                "query": f"About {brand_name}",
                "vendor": vendor,
                "response": response["text"][:500],  # Truncate for storage
                "entities_found": list(entities_found)[:10]
            })
            
        except Exception as e:
            print(f"Error querying {vendor} about brand: {str(e)}")
    
    # Query about tracked phrases (E→B)
    for phrase in tracked_phrases:
        for vendor in available_vendors:
            try:
                # Ask for recommendations
                phrase_prompt = f"""A customer asks: "{phrase}"
                
Please recommend the top 5-7 brands or products that best match this query.
Also mention key features or benefits these products offer.
Keep your response informative but concise."""

                response = await adapter.generate(
                    vendor=vendor,
                    prompt=phrase_prompt,
                    temperature=0.3,
                    max_tokens=300 if vendor != "google" else None
                )
                
                text = response["text"]
                
                # Extract brands (numbered items)
                brands_found = []
                lines = text.split('\n')
                for line in lines:
                    match = re.match(r'^(?:\s*)?(?:\d+\.|\-|\*|•)\s+([^:,]+)', line.strip())
                    if match:
                        brand = match.group(1).strip()
                        brand = brand.rstrip('.,;:')
                        if brand and len(brand) > 2 and len(brand) < 50:
                            brands_found.append(brand)
                            all_brands.add(brand)
                
                # Extract entities from response
                entities_found = extract_entities_from_text(text)
                all_entities.update(entities_found)
                
                # Check if user's brand was mentioned
                brand_mentioned = any(brand_name.lower() in b.lower() for b in brands_found)
                
                analysis_results.append({
                    "query": phrase,
                    "vendor": vendor,
                    "response": text[:500],
                    "brands_found": brands_found[:6],
                    "entities_found": list(entities_found)[:10],
                    "brand_mentioned": brand_mentioned
                })
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Error querying {vendor} for '{phrase}': {str(e)}")
    
    # Step 2: Calculate embeddings for discovered entities and brands
    embedding_vendor = "openai" if settings.openai_api_key else "google"
    
    # Get brand embedding
    brand_embedding = await adapter.get_embedding(embedding_vendor, brand_name)
    brand_vec = np.array(brand_embedding)
    
    # B→E Analysis: Calculate similarity between brand and discovered entities
    entity_similarities = []
    for entity in list(all_entities)[:30]:  # Limit to top 30 entities
        try:
            entity_embedding = await adapter.get_embedding(embedding_vendor, entity)
            entity_vec = np.array(entity_embedding)
            
            similarity = cosine_similarity(brand_vec, entity_vec)
            entity_similarities.append({
                "entity": entity,
                "similarity": similarity
            })
        except Exception as e:
            print(f"Error getting embedding for entity '{entity}': {str(e)}")
    
    # Sort by similarity
    entity_similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Create top entities list
    top_entities = []
    for i, item in enumerate(entity_similarities[:20]):
        # Convert similarity to display metrics
        frequency = int(50 * item["similarity"])
        avg_position = 1 + (1 - item["similarity"]) * 5
        weighted_score = item["similarity"]
        
        top_entities.append({
            "entity": item["entity"],
            "frequency": max(1, frequency),
            "avg_position": round(avg_position, 2),
            "weighted_score": round(weighted_score, 3)
        })
    
    # E→B Analysis: Calculate similarity between phrases and discovered brands
    brand_phrase_scores = {}
    
    for phrase in tracked_phrases:
        try:
            phrase_embedding = await adapter.get_embedding(embedding_vendor, phrase)
            phrase_vec = np.array(phrase_embedding)
            
            for test_brand in list(all_brands)[:20]:  # Test discovered brands
                if test_brand not in brand_phrase_scores:
                    brand_phrase_scores[test_brand] = []
                
                brand_test_embedding = await adapter.get_embedding(embedding_vendor, test_brand)
                brand_test_vec = np.array(brand_test_embedding)
                
                similarity = cosine_similarity(phrase_vec, brand_test_vec)
                brand_phrase_scores[test_brand].append(similarity)
        except Exception as e:
            print(f"Error calculating brand similarities for '{phrase}': {str(e)}")
    
    # Average the scores
    brand_avg_scores = []
    for brand, scores in brand_phrase_scores.items():
        if scores:
            avg_score = np.mean(scores)
            brand_avg_scores.append({
                "brand": brand,
                "similarity": avg_score
            })
    
    # Sort by similarity
    brand_avg_scores.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Create top brands list
    top_brands = []
    for i, item in enumerate(brand_avg_scores[:20]):
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
        "discovered_entities": list(all_entities)[:50],  # Return discovered entities
        "top_entities": top_entities,
        "top_brands": top_brands,
        "analysis_results": analysis_results
    }