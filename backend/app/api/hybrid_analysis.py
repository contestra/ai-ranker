"""
Hybrid Analysis - Combines Contestra V2 (prompted-list) with BEEB (embeddings)
Provides both primary and secondary metrics in a single response
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import numpy as np
from app.llm.langchain_adapter import LangChainAdapter
from .contestra_v2_analysis import run_contestra_v2_analysis, ContestraV2Request
from .entity_extraction_beeb import run_entity_beeb, EntityBEEBRequest

router = APIRouter()

class HybridRequest(BaseModel):
    brand_name: str
    vendor: str = "openai"
    tracked_phrases: List[str] = []
    num_runs: int = 12
    top_k: int = 10
    use_canonical: bool = True

class HybridEntityResult(BaseModel):
    entity: str
    prompted_rank: int
    prompted_score: float
    prompted_frequency: int
    embedding_rank: Optional[int] = None
    embedding_similarity: Optional[float] = None
    combined_score: float
    method_agreement: str  # "high", "medium", "low"

class HybridResponse(BaseModel):
    brand: str
    vendor: str
    entities: List[HybridEntityResult]
    brand_associations: List[Dict[str, Any]]
    metadata: Dict[str, Any]

def calculate_combined_score(prompted_score: float, embedding_sim: Optional[float], 
                            prompted_weight: float = 0.7) -> float:
    """
    Calculate combined score with prompted-list as primary (70%) and embeddings as secondary (30%)
    """
    if embedding_sim is None:
        return prompted_score
    
    embedding_weight = 1 - prompted_weight
    return (prompted_score * prompted_weight) + (embedding_sim * embedding_weight)

def determine_agreement(prompted_rank: int, embedding_rank: Optional[int]) -> str:
    """
    Determine agreement level between methods
    """
    if embedding_rank is None:
        return "n/a"
    
    diff = abs(prompted_rank - embedding_rank)
    if diff <= 2:
        return "high"
    elif diff <= 5:
        return "medium"
    else:
        return "low"

@router.post("/hybrid-analysis", response_model=HybridResponse)
async def run_hybrid_analysis(request: HybridRequest):
    """
    Run both Contestra V2 (prompted-list) and BEEB (embedding) analysis
    Combine results with prompted-list as primary metric
    """
    
    adapter = LangChainAdapter()
    
    # Prepare requests for both methods
    contestra_request = ContestraV2Request(
        brand_name=request.brand_name,
        direction="brand_to_entity",
        vendor=request.vendor,
        num_runs=request.num_runs,
        top_k=request.top_k,
        tracked_phrases=request.tracked_phrases,
        use_canonical=request.use_canonical
    )
    
    beeb_request = EntityBEEBRequest(
        brand_name=request.brand_name,
        tracked_phrases=request.tracked_phrases[:2],  # Limit for performance
        vendor=request.vendor
    )
    
    # Run both analyses in parallel
    print(f"Running hybrid analysis for {request.brand_name}")
    contestra_task = run_contestra_v2_analysis(contestra_request)
    beeb_task = run_entity_beeb(beeb_request)
    
    contestra_result, beeb_result = await asyncio.gather(contestra_task, beeb_task)
    
    # Create entity mapping
    entity_map = {}
    
    # Add prompted-list results (primary)
    for i, entity in enumerate(contestra_result.entities, 1):
        entity_map[entity.name] = {
            'prompted_rank': i,
            'prompted_score': entity.weighted_score,
            'prompted_frequency': entity.frequency,
            'embedding_rank': None,
            'embedding_similarity': None
        }
    
    # Add/update with embedding results (secondary)
    for i, entity in enumerate(beeb_result.entity_associations[:30], 1):
        name = entity['entity']
        if name in entity_map:
            # Entity exists in both - update with embedding data
            entity_map[name]['embedding_rank'] = i
            entity_map[name]['embedding_similarity'] = entity['similarity']
        else:
            # Entity only in embeddings - add it
            entity_map[name] = {
                'prompted_rank': None,
                'prompted_score': 0.0,
                'prompted_frequency': 0,
                'embedding_rank': i,
                'embedding_similarity': entity['similarity']
            }
    
    # Create hybrid results
    hybrid_entities = []
    for entity_name, data in entity_map.items():
        # Calculate combined score
        prompted_score = data['prompted_score'] if data['prompted_score'] else 0.0
        embedding_sim = data['embedding_similarity']
        combined_score = calculate_combined_score(prompted_score, embedding_sim)
        
        # Determine agreement
        if data['prompted_rank'] and data['embedding_rank']:
            agreement = determine_agreement(data['prompted_rank'], data['embedding_rank'])
        else:
            agreement = "n/a"
        
        hybrid_entities.append(HybridEntityResult(
            entity=entity_name,
            prompted_rank=data['prompted_rank'] if data['prompted_rank'] else 999,
            prompted_score=prompted_score,
            prompted_frequency=data['prompted_frequency'],
            embedding_rank=data['embedding_rank'],
            embedding_similarity=data['embedding_similarity'],
            combined_score=combined_score,
            method_agreement=agreement
        ))
    
    # Sort by combined score
    hybrid_entities.sort(key=lambda x: (-x.combined_score, -x.prompted_score))
    
    # Take top 20
    top_entities = hybrid_entities[:20]
    
    # Calculate metadata
    entities_in_both = sum(1 for e in top_entities if e.prompted_rank and e.embedding_rank)
    prompted_only = sum(1 for e in top_entities if e.prompted_rank and not e.embedding_rank)
    embedding_only = sum(1 for e in top_entities if not e.prompted_rank and e.embedding_rank)
    
    high_agreement = sum(1 for e in top_entities if e.method_agreement == "high")
    medium_agreement = sum(1 for e in top_entities if e.method_agreement == "medium")
    low_agreement = sum(1 for e in top_entities if e.method_agreement == "low")
    
    metadata = {
        **contestra_result.metadata,
        "hybrid_analysis": True,
        "entities_in_both_methods": entities_in_both,
        "prompted_only_entities": prompted_only,
        "embedding_only_entities": embedding_only,
        "high_agreement_count": high_agreement,
        "medium_agreement_count": medium_agreement,
        "low_agreement_count": low_agreement,
        "agreement_percentage": (high_agreement / max(entities_in_both, 1)) * 100 if entities_in_both > 0 else 0
    }
    
    return HybridResponse(
        brand=request.brand_name,
        vendor=request.vendor,
        entities=top_entities,
        brand_associations=contestra_result.brand_associations,
        metadata=metadata
    )