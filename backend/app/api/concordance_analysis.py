"""
Concordance Analysis - Compare prompted-list rankings vs embedding similarity
Helps identify agreement/disagreement between the two methodologies
Fixed: Handle NaN/Inf values in metrics
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import numpy as np
import asyncio
from scipy.stats import spearmanr, kendalltau
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings
from .contestra_v2_analysis import run_contestra_v2_analysis, ContestraV2Request
from .entity_extraction_beeb import run_entity_beeb, EntityBEEBRequest

router = APIRouter()

class ConcordanceRequest(BaseModel):
    brand_name: str
    vendor: str = "openai"
    tracked_phrases: List[str] = []
    num_runs: int = 6  # Fewer runs for faster comparison
    top_k: int = 10

class EntityComparison(BaseModel):
    entity: str
    prompted_rank: Optional[int]
    prompted_score: Optional[float]
    embedding_rank: Optional[int]
    embedding_similarity: Optional[float]
    rank_difference: Optional[int]
    agreement_level: str  # "strong", "moderate", "weak", "disagreement"

class ConcordanceMetrics(BaseModel):
    spearman_correlation: float
    kendall_tau: float
    rank_agreement_percentage: float
    top_5_overlap: float
    top_10_overlap: float
    mean_rank_difference: float

class ConcordanceResponse(BaseModel):
    brand: str
    vendor: str
    entity_comparisons: List[EntityComparison]
    metrics: ConcordanceMetrics
    insights: List[str]
    prompted_only: List[str]  # Entities only in prompted lists
    embedding_only: List[str]  # Entities only in embeddings
    
def calculate_agreement_level(rank_diff: int) -> str:
    """Determine agreement level based on rank difference"""
    if rank_diff == 0:
        return "perfect"
    elif rank_diff <= 2:
        return "strong"
    elif rank_diff <= 5:
        return "moderate"
    elif rank_diff <= 10:
        return "weak"
    else:
        return "disagreement"

def calculate_concordance_metrics(comparisons: List[EntityComparison]) -> ConcordanceMetrics:
    """Calculate concordance metrics between two ranking methods"""
    
    # Filter to entities present in both methods
    both_present = [c for c in comparisons if c.prompted_rank and c.embedding_rank]
    
    if len(both_present) < 2:
        return ConcordanceMetrics(
            spearman_correlation=0.0,
            kendall_tau=0.0,
            rank_agreement_percentage=0.0,
            top_5_overlap=0.0,
            top_10_overlap=0.0,
            mean_rank_difference=999.0  # Use large value instead of inf
        )
    
    prompted_ranks = [c.prompted_rank for c in both_present]
    embedding_ranks = [c.embedding_rank for c in both_present]
    
    # Calculate correlations (handle edge cases)
    try:
        spearman_corr, _ = spearmanr(prompted_ranks, embedding_ranks)
        if np.isnan(spearman_corr) or np.isinf(spearman_corr):
            spearman_corr = 0.0
    except:
        spearman_corr = 0.0
    
    try:
        kendall_corr, _ = kendalltau(prompted_ranks, embedding_ranks)
        if np.isnan(kendall_corr) or np.isinf(kendall_corr):
            kendall_corr = 0.0
    except:
        kendall_corr = 0.0
    
    # Calculate agreement percentage (within 3 ranks)
    agreements = sum(1 for c in both_present if abs(c.rank_difference) <= 3)
    agreement_pct = (agreements / len(both_present)) * 100 if both_present else 0
    
    # Calculate top-K overlap
    prompted_top5 = set(c.entity for c in comparisons if c.prompted_rank and c.prompted_rank <= 5)
    embedding_top5 = set(c.entity for c in comparisons if c.embedding_rank and c.embedding_rank <= 5)
    top5_overlap = len(prompted_top5 & embedding_top5) / max(len(prompted_top5), len(embedding_top5), 1) * 100
    
    prompted_top10 = set(c.entity for c in comparisons if c.prompted_rank and c.prompted_rank <= 10)
    embedding_top10 = set(c.entity for c in comparisons if c.embedding_rank and c.embedding_rank <= 10)
    top10_overlap = len(prompted_top10 & embedding_top10) / max(len(prompted_top10), len(embedding_top10), 1) * 100
    
    # Mean rank difference
    if both_present and any(c.rank_difference is not None for c in both_present):
        valid_diffs = [abs(c.rank_difference) for c in both_present if c.rank_difference is not None]
        mean_diff = np.mean(valid_diffs) if valid_diffs else 999.0
    else:
        mean_diff = 999.0  # Use large value instead of inf
    
    return ConcordanceMetrics(
        spearman_correlation=float(spearman_corr),
        kendall_tau=float(kendall_corr),
        rank_agreement_percentage=float(agreement_pct),
        top_5_overlap=float(top5_overlap),
        top_10_overlap=float(top10_overlap),
        mean_rank_difference=float(mean_diff)
    )

def generate_insights(metrics: ConcordanceMetrics, comparisons: List[EntityComparison]) -> List[str]:
    """Generate insights from concordance analysis"""
    insights = []
    
    # Overall correlation insight
    if metrics.spearman_correlation > 0.7:
        insights.append("✅ Strong agreement between prompted-lists and embeddings (ρ > 0.7)")
    elif metrics.spearman_correlation > 0.4:
        insights.append("⚠️ Moderate agreement between methods - some divergence detected")
    else:
        insights.append("❌ Weak agreement - the methods produce substantially different rankings")
    
    # Top-K overlap
    if metrics.top_5_overlap >= 80:
        insights.append(f"✅ High consistency in top 5 entities ({metrics.top_5_overlap:.0f}% overlap)")
    elif metrics.top_5_overlap >= 50:
        insights.append(f"⚠️ Moderate top-5 overlap ({metrics.top_5_overlap:.0f}%) - check for disambiguation issues")
    else:
        insights.append(f"❌ Low top-5 overlap ({metrics.top_5_overlap:.0f}%) - methods disagree on key associations")
    
    # Find major disagreements
    major_disagreements = [c for c in comparisons if c.rank_difference and abs(c.rank_difference) > 10]
    if major_disagreements:
        entities = ", ".join([c.entity for c in major_disagreements[:3]])
        insights.append(f"🔍 Major ranking disagreements for: {entities}")
    
    # Entities unique to each method
    prompted_only = [c.entity for c in comparisons if c.prompted_rank and not c.embedding_rank]
    embedding_only = [c.entity for c in comparisons if c.embedding_rank and not c.prompted_rank]
    
    if prompted_only:
        insights.append(f"💭 Prompted-lists found unique entities: {', '.join(prompted_only[:3])}")
    if embedding_only:
        insights.append(f"🔢 Embeddings found unique entities: {', '.join(embedding_only[:3])}")
    
    # Mean rank difference
    if metrics.mean_rank_difference <= 2:
        insights.append("✅ Rankings are highly consistent (avg difference ≤ 2 positions)")
    elif metrics.mean_rank_difference <= 5:
        insights.append(f"⚠️ Average rank difference of {metrics.mean_rank_difference:.1f} positions")
    else:
        insights.append(f"❌ Large average rank difference ({metrics.mean_rank_difference:.1f} positions)")
    
    return insights

@router.post("/concordance", response_model=ConcordanceResponse)
async def analyze_concordance(request: ConcordanceRequest):
    """
    Run concordance analysis comparing prompted-list vs embedding methods
    """
    
    # Run both analyses in parallel
    contestra_request = ContestraV2Request(
        brand_name=request.brand_name,
        direction="brand_to_entity",
        vendor=request.vendor,
        num_runs=request.num_runs,
        top_k=request.top_k,
        tracked_phrases=request.tracked_phrases,
        use_canonical=True
    )
    
    beeb_request = EntityBEEBRequest(
        brand_name=request.brand_name,
        tracked_phrases=request.tracked_phrases[:2],  # Limit for performance
        vendor=request.vendor
    )
    
    # Run both analyses
    contestra_task = run_contestra_v2_analysis(contestra_request)
    beeb_task = run_entity_beeb(beeb_request)
    
    contestra_result, beeb_result = await asyncio.gather(contestra_task, beeb_task)
    
    # Create entity comparison mapping
    entity_map = {}
    
    # Add prompted-list results
    for i, entity in enumerate(contestra_result.entities[:20], 1):
        entity_map[entity.name] = {
            'prompted_rank': i,
            'prompted_score': entity.weighted_score,
            'embedding_rank': None,
            'embedding_similarity': None
        }
    
    # Add embedding results
    for i, entity in enumerate(beeb_result.entity_associations[:20], 1):
        name = entity['entity']
        if name in entity_map:
            entity_map[name]['embedding_rank'] = i
            entity_map[name]['embedding_similarity'] = entity['similarity']
        else:
            entity_map[name] = {
                'prompted_rank': None,
                'prompted_score': None,
                'embedding_rank': i,
                'embedding_similarity': entity['similarity']
            }
    
    # Create comparison list
    comparisons = []
    for entity, data in entity_map.items():
        rank_diff = None
        if data['prompted_rank'] and data['embedding_rank']:
            rank_diff = abs(data['prompted_rank'] - data['embedding_rank'])
        
        agreement = calculate_agreement_level(rank_diff) if rank_diff is not None else "n/a"
        
        # Clean up any NaN/Inf values before creating the comparison
        prompted_score = data['prompted_score'] if data['prompted_score'] and not np.isnan(data['prompted_score']) else 0.0
        embedding_sim = data['embedding_similarity']
        if embedding_sim is not None and (np.isnan(embedding_sim) or np.isinf(embedding_sim)):
            embedding_sim = 0.0
        
        comparisons.append(EntityComparison(
            entity=entity,
            prompted_rank=data['prompted_rank'],
            prompted_score=float(prompted_score),
            embedding_rank=data['embedding_rank'],
            embedding_similarity=float(embedding_sim) if embedding_sim is not None else None,
            rank_difference=rank_diff,
            agreement_level=agreement
        ))
    
    # Sort by prompted rank first, then embedding rank
    comparisons.sort(key=lambda x: (x.prompted_rank or 999, x.embedding_rank or 999))
    
    # Calculate metrics
    metrics = calculate_concordance_metrics(comparisons)
    
    # Generate insights
    insights = generate_insights(metrics, comparisons)
    
    # Identify unique entities
    prompted_only = [c.entity for c in comparisons if c.prompted_rank and not c.embedding_rank]
    embedding_only = [c.entity for c in comparisons if c.embedding_rank and not c.prompted_rank]
    
    return ConcordanceResponse(
        brand=request.brand_name,
        vendor=request.vendor,
        entity_comparisons=comparisons[:30],  # Top 30 for display
        metrics=metrics,
        insights=insights,
        prompted_only=prompted_only[:10],
        embedding_only=embedding_only[:10]
    )

@router.post("/concordance/batch")
async def batch_concordance(brands: List[str], vendor: str = "openai"):
    """
    Run concordance analysis for multiple brands
    """
    results = []
    
    for brand in brands[:5]:  # Limit to 5 brands
        try:
            result = await analyze_concordance(ConcordanceRequest(
                brand_name=brand,
                vendor=vendor,
                num_runs=3  # Fewer runs for batch
            ))
            results.append({
                "brand": brand,
                "correlation": result.metrics.spearman_correlation,
                "top_5_overlap": result.metrics.top_5_overlap,
                "mean_difference": result.metrics.mean_rank_difference
            })
        except Exception as e:
            results.append({
                "brand": brand,
                "error": str(e)
            })
    
    return {
        "results": results,
        "summary": {
            "avg_correlation": np.mean([r.get("correlation", 0) for r in results if "correlation" in r]),
            "avg_overlap": np.mean([r.get("top_5_overlap", 0) for r in results if "top_5_overlap" in r])
        }
    }