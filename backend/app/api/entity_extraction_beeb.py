"""
Entity Extraction BEEB Implementation
The correct approach: Query chat API first, extract entities, then measure embeddings
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Set
from pydantic import BaseModel
import numpy as np
import spacy
import re
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

# Load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

class EntityBEEBRequest(BaseModel):
    brand_name: str
    tracked_phrases: List[str]
    vendor: str = None  # Optional: specific vendor

class EntityBEEBResponse(BaseModel):
    brand: str
    vendor: str
    extracted_entities: List[str]  # Raw entities from chat response
    entity_associations: List[Dict[str, Any]]  # Entities with embedding scores
    brand_associations: List[Dict[str, Any]]  # Brands for tracked phrases

def extract_entities_from_text(text: str) -> Set[str]:
    """
    Extract entities from text using spaCy NER and pattern matching
    """
    entities = set()
    
    # Use spaCy NER
    doc = nlp(text)
    
    # Extract named entities
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT", "PERSON", "GPE", "LOC"]:
            entities.add(ent.text)
    
    # Extract noun phrases that might be services/products
    for chunk in doc.noun_chunks:
        # Skip single common words
        if len(chunk.text.split()) > 1 or chunk.text.lower() not in ['it', 'they', 'this', 'that']:
            entities.add(chunk.text)
    
    # Pattern matching for specific types
    patterns = [
        r'\b(?:mobile|network|data|internet|telecom\w*)\s+\w+',  # Telecom terms
        r'\b\w+\s+(?:service|services|solution|solutions|package|packages)\b',  # Services
        r'\b\w+\s+(?:coverage|support|plan|plans)\b',  # Support terms
        r'\b(?:customer|technical|mobile|network)\s+\w+',  # Compound terms
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.update(matches)
    
    # Clean up entities
    cleaned_entities = set()
    for entity in entities:
        # Clean up the entity
        entity = entity.strip()
        # Skip very short or very long entities
        if 2 < len(entity) < 50:
            cleaned_entities.add(entity)
    
    return cleaned_entities

def normalize_entities(entities: Set[str]) -> List[str]:
    """
    Normalize and deduplicate entities
    """
    normalized = {}
    
    for entity in entities:
        # Create a normalized key for deduplication
        key = entity.lower().strip()
        
        # Keep the better formatted version
        if key not in normalized or len(entity) > len(normalized[key]):
            normalized[key] = entity
    
    return list(normalized.values())

@router.post("/entity-beeb", response_model=EntityBEEBResponse)
async def run_entity_beeb(request: EntityBEEBRequest):
    """
    Correct BEEB implementation:
    1. Query chat API about the brand
    2. Extract entities from response
    3. Calculate embedding similarities
    """
    
    vendor = request.vendor or ("openai" if settings.openai_api_key else "google")
    adapter = LangChainAdapter()
    
    # Step 1: Query chat API about the brand
    print(f"\n=== Step 1: Querying {vendor} about {request.brand_name} ===")
    
    # Single prompt for speed and simplicity
    prompts = [
        f"List the top 10 things you associate with {request.brand_name}",
    ]
    
    all_entities = set()
    all_text = ""
    
    for prompt in prompts:
        try:
            response = await adapter.generate(
                vendor=vendor,
                prompt=prompt,
                temperature=0.3,
                max_tokens=300 if vendor != "google" else None
            )
            
            text = response["text"]
            all_text += " " + text
            print(f"\nPrompt: {prompt}")
            print(f"Response excerpt: {text[:200]}...")
            
            # Extract entities from this response
            entities = extract_entities_from_text(text)
            all_entities.update(entities)
            
        except Exception as e:
            print(f"Error querying {vendor}: {str(e)}")
    
    # Normalize entities
    extracted_entities = normalize_entities(all_entities)
    print(f"\n=== Step 2: Extracted {len(extracted_entities)} entities ===")
    for entity in extracted_entities[:20]:
        print(f"  - {entity}")
    
    # Step 3: Calculate embedding similarities for extracted entities
    print(f"\n=== Step 3: Calculating embedding similarities ===")
    
    # Get brand embedding
    brand_embedding = await adapter.get_embedding(vendor, request.brand_name)
    brand_vec = np.array(brand_embedding)
    
    # Normalize brand vector
    brand_norm = np.linalg.norm(brand_vec)
    if brand_norm > 0:
        brand_vec = brand_vec / brand_norm
    
    entity_associations = []
    
    for entity in extracted_entities[:15]:  # Limit to top 15 for performance
        try:
            # Get entity embedding
            entity_embedding = await adapter.get_embedding(vendor, entity)
            entity_vec = np.array(entity_embedding)
            
            # Normalize entity vector
            entity_norm = np.linalg.norm(entity_vec)
            if entity_norm > 0:
                entity_vec = entity_vec / entity_norm
            
            # Calculate dot product (cosine similarity for normalized vectors)
            similarity = float(np.dot(brand_vec, entity_vec))
            
            entity_associations.append({
                "entity": entity,
                "similarity": similarity,
                "frequency": 1,  # Placeholder
                "avg_position": 1 + (1 - similarity) * 9,  # Convert to 1-10 scale
                "weighted_score": similarity
            })
            
        except Exception as e:
            print(f"Error getting embedding for '{entity}': {str(e)}")
    
    # Sort by similarity
    entity_associations.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Take top 20
    top_entities = entity_associations[:20]
    
    print(f"\n=== Top 10 Entity Associations for {request.brand_name} ===")
    for i, entity in enumerate(top_entities[:10]):
        print(f"  {i+1}. {entity['entity']}: {entity['similarity']:.3f}")
    
    # Step 4: For tracked phrases, find associated brands
    brand_associations = []
    
    # Process tracked phrases only for OpenAI to avoid Google quota issues
    if vendor == "openai" and len(request.tracked_phrases) > 0:
        for phrase in request.tracked_phrases[:2]:  # Limit to 2 phrases for performance
            try:
                prompt = f"What are the top 10 brands for '{phrase}'? List only brand names."
                response = await adapter.generate(
                    vendor=vendor,
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=200 if vendor != "google" else None
                )
            
            # Extract brand names from response
            brands = extract_entities_from_text(response["text"])
            
            for brand in list(brands)[:10]:
                # Get brand embedding and calculate similarity to phrase
                try:
                    brand_embedding = await adapter.get_embedding(vendor, brand)
                    phrase_embedding = await adapter.get_embedding(vendor, phrase)
                    
                    brand_vec = np.array(brand_embedding)
                    phrase_vec = np.array(phrase_embedding)
                    
                    # Normalize
                    brand_norm = np.linalg.norm(brand_vec)
                    phrase_norm = np.linalg.norm(phrase_vec)
                    
                    if brand_norm > 0 and phrase_norm > 0:
                        brand_vec = brand_vec / brand_norm
                        phrase_vec = phrase_vec / phrase_norm
                        similarity = float(np.dot(brand_vec, phrase_vec))
                        
                        brand_associations.append({
                            "brand": brand,
                            "phrase": phrase,
                            "similarity": similarity,
                            "frequency": 1,
                            "avg_position": 1 + (1 - similarity) * 9,
                            "weighted_score": similarity
                        })
                except Exception as e:
                    print(f"Error processing brand '{brand}': {str(e)}")
                    
        except Exception as e:
            print(f"Error processing phrase '{phrase}': {str(e)}")
    
    # Aggregate and sort brand associations
    brand_scores = {}
    for assoc in brand_associations:
        brand = assoc["brand"]
        if brand not in brand_scores:
            brand_scores[brand] = []
        brand_scores[brand].append(assoc["similarity"])
    
    top_brands = []
    for brand, scores in brand_scores.items():
        avg_score = sum(scores) / len(scores)
        top_brands.append({
            "brand": brand,
            "similarity": avg_score,
            "frequency": len(scores),
            "avg_position": 1 + (1 - avg_score) * 9,
            "weighted_score": avg_score
        })
    
    top_brands.sort(key=lambda x: x["similarity"], reverse=True)
    top_brands = top_brands[:20]
    
    return EntityBEEBResponse(
        brand=request.brand_name,
        vendor=vendor,
        extracted_entities=[e["entity"] for e in top_entities],
        entity_associations=top_entities,
        brand_associations=top_brands
    )