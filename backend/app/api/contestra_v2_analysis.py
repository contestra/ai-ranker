"""
Contestra V2 Analysis - Prompted List with Rank Aggregation
The correct methodology for AI brand association tracking
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import json
from collections import defaultdict, Counter
import numpy as np
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

class ContestraV2Request(BaseModel):
    brand_name: str
    direction: str = "brand_to_entity"  # brand_to_entity | entity_to_brand
    vendor: str = "openai"  # openai | google | anthropic
    mode: str = "ungrounded"  # ungrounded | grounded (for Google)
    num_runs: int = 12  # Number of repeated runs
    top_k: int = 10  # Top K items to request
    tracked_phrases: List[str] = []
    use_canonical: bool = False  # Toggle for canonical entities

class EntityResult(BaseModel):
    name: str
    variants: List[str]
    frequency: int
    positions: List[int]
    avg_position: float
    weighted_score: float
    vector_similarity: Optional[float] = None  # Secondary metric

class ContestraV2Response(BaseModel):
    brand: str
    vendor: str
    mode: str
    num_runs: int
    entities: List[EntityResult]
    brand_associations: List[Dict[str, Any]] = []
    metadata: Dict[str, Any]

def create_prompt(brand_name: str, direction: str, top_k: int, mode: str = "ungrounded") -> str:
    """Create the prompt for chat-based list generation"""
    
    context = "" if mode == "ungrounded" else f"In the context of current market data and verified information, "
    
    if direction == "brand_to_entity":
        prompt = f"""{context}List the top {top_k} entities, concepts, or attributes you most strongly associate with {brand_name}.
Include products, services, competitors, industry terms, and key characteristics.
Return ONLY a JSON object in this exact format:
{{"items": [{{"name": "Entity Name", "type": "category"}}]}}
Types can be: brand, product, service, category, attribute, competitor"""
    
    else:  # entity_to_brand
        prompt = f"""{context}List the top {top_k} brands you most strongly associate with the concept "{brand_name}".
Return ONLY a JSON object in this exact format:
{{"items": [{{"name": "Brand Name", "type": "brand"}}]}}"""
    
    return prompt

def parse_llm_response(response_text: str) -> List[Dict[str, str]]:
    """Parse the LLM response to extract items"""
    try:
        # Try to extract JSON from the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            return data.get('items', [])
    except:
        pass
    
    # Fallback: extract items from text
    items = []
    lines = response_text.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('{') and not line.startswith('['):
            # Clean up common formatting
            line = line.lstrip('0123456789.-) ')
            if line:
                items.append({"name": line, "type": "unknown"})
    
    return items[:10]  # Ensure we don't exceed top_k

def calculate_borda_score(positions: List[int], num_runs: int, top_k: int) -> float:
    """
    Calculate Borda-style weighted score
    Score = Σ(K - rank + 1) / (K * runs)
    Normalized to 0-1 where 1 is best
    """
    if not positions:
        return 0.0
    
    total_score = sum(top_k - pos + 1 for pos in positions)
    max_possible = top_k * num_runs
    return total_score / max_possible if max_possible > 0 else 0.0

def canonicalize_entities(entities_by_name: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Group similar entity variants together
    Simple approach using string similarity
    """
    # For now, use exact matching with lowercase
    # TODO: Implement more sophisticated variant detection (Levenshtein, embeddings)
    canonical_map = {}
    canonical_entities = defaultdict(lambda: {
        'variants': set(),
        'positions': [],
        'frequency': 0
    })
    
    for name, data in entities_by_name.items():
        # Simple canonicalization: lowercase and strip
        canonical = name.lower().strip()
        
        # Group by canonical form
        canonical_entities[canonical]['variants'].add(name)
        canonical_entities[canonical]['positions'].extend(data['positions'])
        canonical_entities[canonical]['frequency'] += data['frequency']
    
    return canonical_entities

async def run_single_analysis(adapter: LangChainAdapter, prompt: str, vendor: str, temperature: float = 0.7) -> List[Dict[str, str]]:
    """Run a single chat probe and parse results"""
    try:
        response = await adapter.generate(
            vendor=vendor,
            prompt=prompt,
            temperature=temperature,
            max_tokens=500
        )
        
        items = parse_llm_response(response["text"])
        return items
    except Exception as e:
        print(f"Error in single run: {str(e)}")
        return []

@router.post("/contestra-v2", response_model=ContestraV2Response)
async def run_contestra_v2_analysis(request: ContestraV2Request):
    """
    Run Contestra V2 analysis using prompted lists with rank aggregation
    This is the correct approach for measuring AI brand associations
    """
    
    adapter = LangChainAdapter()
    
    # Prepare for multiple runs
    prompt = create_prompt(
        request.brand_name,
        request.direction,
        request.top_k,
        request.mode
    )
    
    print(f"\n=== Starting Contestra V2 Analysis ===")
    print(f"Brand: {request.brand_name}")
    print(f"Direction: {request.direction}")
    print(f"Vendor: {request.vendor}")
    print(f"Mode: {request.mode}")
    print(f"Runs: {request.num_runs}")
    print(f"Tracked phrases: {request.tracked_phrases}")
    
    # Collect results from multiple runs
    all_runs = []
    entities_by_name = defaultdict(lambda: {'positions': [], 'frequency': 0})
    
    # Run multiple chat probes with varying temperature for diversity
    # Note: GPT-5 only supports temperature 1.0
    if request.vendor == "openai":
        temperatures = [1.0] * request.num_runs  # GPT-5 only supports default temperature
    else:
        temperatures = [0.5, 0.7, 0.9] * (request.num_runs // 3 + 1)
        temperatures = temperatures[:request.num_runs]
    
    tasks = []
    for i in range(request.num_runs):
        temp = temperatures[i]
        task = run_single_analysis(adapter, prompt, request.vendor, temp)
        tasks.append(task)
    
    # Execute all runs in parallel
    print(f"Executing {len(tasks)} parallel runs...")
    run_results = await asyncio.gather(*tasks)
    
    # Process results from all runs
    for run_idx, items in enumerate(run_results):
        run_data = []
        for position, item in enumerate(items, 1):
            name = item.get('name', '')
            if name:
                entities_by_name[name]['positions'].append(position)
                entities_by_name[name]['frequency'] += 1
                run_data.append({'name': name, 'position': position, 'type': item.get('type', 'unknown')})
        all_runs.append(run_data)
    
    print(f"Collected {len(entities_by_name)} unique entities across {len(all_runs)} runs")
    
    # Apply canonicalization if requested
    if request.use_canonical:
        canonical_entities = canonicalize_entities(entities_by_name)
        entities_to_process = canonical_entities
    else:
        entities_to_process = entities_by_name
    
    # Calculate metrics for each entity
    entity_results = []
    for name, data in entities_to_process.items():
        if request.use_canonical:
            variants = list(data['variants'])
            display_name = max(variants, key=lambda v: entities_by_name[v]['frequency'])
        else:
            variants = [name]
            display_name = name
        
        positions = data['positions']
        frequency = data['frequency'] if request.use_canonical else len(positions)
        avg_position = np.mean(positions) if positions else 999
        weighted_score = calculate_borda_score(positions, request.num_runs, request.top_k)
        
        entity_results.append(EntityResult(
            name=display_name,
            variants=variants,
            frequency=frequency,
            positions=positions,
            avg_position=round(avg_position, 2),
            weighted_score=round(weighted_score, 3)
        ))
    
    # Sort by weighted score (primary) and frequency (secondary)
    entity_results.sort(key=lambda x: (-x.weighted_score, -x.frequency, x.avg_position))
    
    # Take top 20 for display
    top_entities = entity_results[:20]
    
    print(f"\n=== Top 10 Entities by Weighted Score ===")
    for i, entity in enumerate(top_entities[:10], 1):
        variant_str = f"({len(entity.variants)} var.)" if len(entity.variants) > 1 else ""
        print(f"{i}. {entity.name} {variant_str} - Score: {entity.weighted_score:.3f}, Freq: {entity.frequency}, Avg Pos: {entity.avg_position:.1f}")
    
    # Process tracked phrases if provided (for brand associations)
    # Always process tracked phrases regardless of direction to get brand rankings
    brand_associations = []
    if request.tracked_phrases:
        print(f"Processing {len(request.tracked_phrases)} tracked phrases for brand associations")
        for phrase in request.tracked_phrases[:2]:  # Limit to 2 for performance
            print(f"Querying brands for phrase: '{phrase}'")
            phrase_prompt = create_prompt(phrase, "entity_to_brand", request.top_k, request.mode)
            phrase_results = await run_single_analysis(adapter, phrase_prompt, request.vendor)
            print(f"Got {len(phrase_results)} brands for '{phrase}'")
            
            for position, item in enumerate(phrase_results, 1):
                brand_associations.append({
                    "phrase": phrase,
                    "brand": item.get('name', ''),
                    "position": position,
                    "type": item.get('type', 'brand')
                })
        print(f"Total brand associations: {len(brand_associations)}")
    
    # Prepare metadata
    metadata = {
        "total_unique_entities": len(entities_by_name),
        "canonical_groups": len(entities_to_process) if request.use_canonical else len(entities_by_name),
        "runs_completed": len(all_runs),
        "avg_entities_per_run": np.mean([len(run) for run in all_runs]) if all_runs else 0,
        "convergence_rate": len([e for e in entity_results if e.frequency >= request.num_runs * 0.5]) / len(entity_results) if entity_results else 0
    }
    
    return ContestraV2Response(
        brand=request.brand_name,
        vendor=request.vendor,
        mode=request.mode,
        num_runs=request.num_runs,
        entities=top_entities,
        brand_associations=brand_associations,
        metadata=metadata
    )

@router.post("/contestra-v2/compare")
async def compare_grounded_ungrounded(request: ContestraV2Request):
    """
    Run both grounded and ungrounded analysis for comparison
    Particularly useful for Google Gemini
    """
    
    results = {}
    
    # Run ungrounded
    request.mode = "ungrounded"
    ungrounded_result = await run_contestra_v2_analysis(request)
    results["ungrounded"] = ungrounded_result
    
    # Run grounded (if Google)
    if request.vendor == "google":
        request.mode = "grounded"
        grounded_result = await run_contestra_v2_analysis(request)
        results["grounded"] = grounded_result
    
    return results