from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import Brand, TrackedPhrase, WeeklyMetric, PhraseResult
from app.core.prompt_runner import PromptRunner
from app.llm.langchain_adapter import LangChainAdapter

router = APIRouter()

# Pydantic models for API
class TrackedPhraseCreate(BaseModel):
    phrase: str
    category: Optional[str] = None
    priority: int = 1

class TrackedPhraseBulkCreate(BaseModel):
    phrases: List[str]
    category: Optional[str] = None

class TrackedPhraseResponse(BaseModel):
    id: int
    brand_id: int
    phrase: str
    category: Optional[str]
    priority: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PhraseRankingResponse(BaseModel):
    phrase: str
    brand_name: str
    rank_position: Optional[int]
    frequency: int
    weighted_score: float
    week_starting: str

@router.post("/brands/{brand_id}/tracked-phrases", response_model=TrackedPhraseResponse)
def create_tracked_phrase(
    brand_id: int,
    phrase_data: TrackedPhraseCreate,
    db: Session = Depends(get_db)
):
    """Create a single tracked phrase for a brand"""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    tracked_phrase = TrackedPhrase(
        brand_id=brand_id,
        phrase=phrase_data.phrase,
        category=phrase_data.category,
        priority=phrase_data.priority
    )
    
    db.add(tracked_phrase)
    db.commit()
    db.refresh(tracked_phrase)
    
    return tracked_phrase

@router.post("/brands/{brand_id}/tracked-phrases/bulk", response_model=List[TrackedPhraseResponse])
def create_tracked_phrases_bulk(
    brand_id: int,
    bulk_data: TrackedPhraseBulkCreate,
    db: Session = Depends(get_db)
):
    """Bulk create tracked phrases for a brand"""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    tracked_phrases = []
    for phrase in bulk_data.phrases:
        # Skip if phrase already exists
        existing = db.query(TrackedPhrase).filter(
            TrackedPhrase.brand_id == brand_id,
            TrackedPhrase.phrase == phrase.strip()
        ).first()
        
        if not existing:
            tracked_phrase = TrackedPhrase(
                brand_id=brand_id,
                phrase=phrase.strip(),
                category=bulk_data.category,
                priority=1
            )
            db.add(tracked_phrase)
            tracked_phrases.append(tracked_phrase)
    
    db.commit()
    for tp in tracked_phrases:
        db.refresh(tp)
    
    return tracked_phrases

@router.get("/brands/{brand_id}/tracked-phrases", response_model=List[TrackedPhraseResponse])
def get_tracked_phrases(
    brand_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all tracked phrases for a brand"""
    query = db.query(TrackedPhrase).filter(TrackedPhrase.brand_id == brand_id)
    
    if active_only:
        query = query.filter(TrackedPhrase.is_active == True)
    
    return query.order_by(TrackedPhrase.priority, TrackedPhrase.phrase).all()

@router.delete("/tracked-phrases/{phrase_id}")
def delete_tracked_phrase(phrase_id: int, db: Session = Depends(get_db)):
    """Delete a tracked phrase"""
    tracked_phrase = db.query(TrackedPhrase).filter(TrackedPhrase.id == phrase_id).first()
    if not tracked_phrase:
        raise HTTPException(status_code=404, detail="Tracked phrase not found")
    
    db.delete(tracked_phrase)
    db.commit()
    
    return {"message": "Tracked phrase deleted"}

@router.put("/tracked-phrases/{phrase_id}/toggle")
def toggle_tracked_phrase(phrase_id: int, db: Session = Depends(get_db)):
    """Toggle active status of a tracked phrase"""
    tracked_phrase = db.query(TrackedPhrase).filter(TrackedPhrase.id == phrase_id).first()
    if not tracked_phrase:
        raise HTTPException(status_code=404, detail="Tracked phrase not found")
    
    tracked_phrase.is_active = not tracked_phrase.is_active
    db.commit()
    db.refresh(tracked_phrase)
    
    return {"id": phrase_id, "is_active": tracked_phrase.is_active}

@router.get("/brands/{brand_id}/phrase-rankings/{vendor}")
def get_phrase_rankings(
    brand_id: int,
    vendor: str,  # "openai", "google", "anthropic"
    weeks: int = 8,
    db: Session = Depends(get_db)
):
    """Get rankings for all tracked phrases over time"""
    # Calculate week starting dates
    today = datetime.now().date()
    start_date = today - timedelta(weeks=weeks)
    
    # Get tracked phrases
    phrases = db.query(TrackedPhrase).filter(
        TrackedPhrase.brand_id == brand_id,
        TrackedPhrase.is_active == True
    ).all()
    
    results = {}
    for phrase in phrases:
        # Get weekly metrics for this phrase
        metrics = db.query(WeeklyMetric).filter(
            WeeklyMetric.tracked_phrase_id == phrase.id,
            WeeklyMetric.week_starting >= start_date
        ).order_by(WeeklyMetric.week_starting).all()
        
        # Get competitor brands that appear for this phrase
        competitor_metrics = db.query(
            WeeklyMetric,
            Brand.name
        ).join(
            Brand, WeeklyMetric.competitor_brand_id == Brand.id
        ).filter(
            WeeklyMetric.tracked_phrase_id == phrase.id,
            WeeklyMetric.week_starting >= start_date
        ).order_by(
            WeeklyMetric.week_starting,
            WeeklyMetric.rank_position
        ).all()
        
        phrase_data = {
            "phrase": phrase.phrase,
            "weekly_data": [],
            "top_competitors": []
        }
        
        # Group by week
        weeks_data = {}
        for metric, brand_name in competitor_metrics:
            week_str = metric.week_starting.isoformat()
            if week_str not in weeks_data:
                weeks_data[week_str] = []
            
            weeks_data[week_str].append({
                "brand": brand_name,
                "rank": metric.rank_position,
                "frequency": metric.frequency,
                "weighted_score": metric.weighted_score
            })
        
        phrase_data["weekly_data"] = weeks_data
        
        # Get top 10 competitors by frequency
        top_competitors = db.query(
            Brand.name,
            func.sum(WeeklyMetric.frequency).label('total_frequency'),
            func.avg(WeeklyMetric.rank_position).label('avg_rank')
        ).join(
            WeeklyMetric, WeeklyMetric.competitor_brand_id == Brand.id
        ).filter(
            WeeklyMetric.tracked_phrase_id == phrase.id
        ).group_by(Brand.name).order_by(
            desc('total_frequency')
        ).limit(10).all()
        
        phrase_data["top_competitors"] = [
            {
                "brand": comp.name,
                "total_frequency": comp.total_frequency,
                "avg_rank": round(comp.avg_rank, 2) if comp.avg_rank else None
            }
            for comp in top_competitors
        ]
        
        results[phrase.phrase] = phrase_data
    
    return results

@router.post("/brands/{brand_id}/run-phrase-analysis")
async def run_phrase_analysis(
    brand_id: int,
    vendor: str = "openai",
    db: Session = Depends(get_db)
):
    """Run E→B analysis for all tracked phrases"""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    phrases = db.query(TrackedPhrase).filter(
        TrackedPhrase.brand_id == brand_id,
        TrackedPhrase.is_active == True
    ).all()
    
    if not phrases:
        raise HTTPException(status_code=400, detail="No active tracked phrases")
    
    # Initialize prompt runner
    runner = PromptRunner(db)
    llm = LangChainAdapter()
    
    results = []
    for phrase in phrases:
        # Generate E→B prompts
        prompts = generate_e2b_prompts(phrase.phrase)
        
        for prompt_text in prompts[:3]:  # Run first 3 prompt variations
            try:
                # Run the prompt
                response = await llm.generate(
                    vendor=vendor,
                    prompt=prompt_text,
                    temperature=1.0 if vendor == "openai" else 0.1,
                    max_tokens=500
                )
                
                # Extract brands from response
                brands_found = extract_brands_from_response(response['text'])
                
                # Check if our brand is mentioned
                our_brand_mentioned = any(
                    alias.lower() in response['text'].lower() 
                    for alias in [brand.name] + brand.aliases
                )
                
                our_brand_position = None
                if our_brand_mentioned:
                    for i, found_brand in enumerate(brands_found, 1):
                        if any(alias.lower() in found_brand.lower() 
                               for alias in [brand.name] + brand.aliases):
                            our_brand_position = i
                            break
                
                # Store result
                result = PhraseResult(
                    tracked_phrase_id=phrase.id,
                    run_id=1,  # TODO: Create proper run
                    prompt_template=prompt_text,
                    model_vendor=vendor,
                    response_text=response['text'],
                    brands_found=brands_found,
                    target_brand_position=our_brand_position,
                    target_brand_mentioned=our_brand_mentioned
                )
                db.add(result)
                results.append({
                    "phrase": phrase.phrase,
                    "prompt": prompt_text,
                    "brands_found": brands_found,
                    "our_position": our_brand_position
                })
                
            except Exception as e:
                print(f"Error processing prompt: {e}")
    
    db.commit()
    
    return {
        "brand": brand.name,
        "phrases_analyzed": len(phrases),
        "results": results
    }

def generate_e2b_prompts(phrase: str) -> List[str]:
    """Generate Entity-to-Brand prompts for a tracked phrase"""
    templates = [
        f"List the top 10 {phrase} brands",
        f"What are the best {phrase} companies?",
        f"Recommend {phrase} products from different brands",
        f"Who are the leading {phrase} providers?",
        f"Name the most popular {phrase} solutions",
        f"Which brands offer the best {phrase}?",
        f"What companies specialize in {phrase}?",
        f"List established {phrase} manufacturers"
    ]
    return templates

def extract_brands_from_response(text: str) -> List[str]:
    """Extract brand names from LLM response"""
    brands = []
    
    # Look for numbered lists
    import re
    patterns = [
        r'\d+\.\s*([^:\n]+)',  # 1. Brand Name
        r'-\s*([^:\n]+)',       # - Brand Name
        r'\*\s*([^:\n]+)',      # * Brand Name
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        brands.extend([m.strip() for m in matches if len(m.strip()) > 2])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_brands = []
    for brand in brands:
        if brand.lower() not in seen:
            seen.add(brand.lower())
            unique_brands.append(brand)
    
    return unique_brands[:20]  # Return top 20