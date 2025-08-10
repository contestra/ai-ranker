from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Metric, Brand, Run, Experiment, WeeklyMetric, TrackedPhrase
from app.core.weekly_aggregator import WeeklyAggregator

router = APIRouter()

@router.get("/overview/{brand_id}")
def get_brand_overview(brand_id: int, db: Session = Depends(get_db)):
    latest_metric = db.query(Metric).filter(
        Metric.brand_id == brand_id
    ).order_by(Metric.created_at.desc()).first()
    
    if not latest_metric:
        return {
            "representation_score": 0,
            "mention_rate": 0,
            "avg_rank": None,
            "trend": "stable"
        }
    
    week_ago = datetime.now() - timedelta(days=7)
    previous_metric = db.query(Metric).filter(
        Metric.brand_id == brand_id,
        Metric.created_at < week_ago
    ).order_by(Metric.created_at.desc()).first()
    
    trend = "stable"
    if previous_metric:
        if latest_metric.weighted_score > previous_metric.weighted_score * 1.1:
            trend = "up"
        elif latest_metric.weighted_score < previous_metric.weighted_score * 0.9:
            trend = "down"
    
    return {
        "representation_score": latest_metric.weighted_score,
        "mention_rate": latest_metric.mention_rate,
        "avg_rank": latest_metric.avg_rank,
        "confidence_interval": [latest_metric.ci_low, latest_metric.ci_high],
        "trend": trend
    }

@router.get("/trends/{brand_id}")
def get_brand_trends(brand_id: int, days: int = 30, db: Session = Depends(get_db)):
    start_date = datetime.now() - timedelta(days=days)
    
    metrics = db.query(
        func.date(Metric.created_at).label('date'),
        func.avg(Metric.mention_rate).label('avg_mention_rate'),
        func.avg(Metric.weighted_score).label('avg_score')
    ).filter(
        Metric.brand_id == brand_id,
        Metric.created_at >= start_date
    ).group_by(func.date(Metric.created_at)).all()
    
    return [{
        "date": m.date.isoformat() if m.date else None,
        "mention_rate": m.avg_mention_rate,
        "weighted_score": m.avg_score
    } for m in metrics]

@router.get("/competitors/{brand_id}")
def get_competitor_comparison(brand_id: int, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand or not brand.category:
        return []
    
    competitors = db.query(Brand).filter(
        Brand.id != brand_id,
        Brand.category.overlap(brand.category)
    ).all()
    
    results = []
    for competitor in competitors:
        latest_metric = db.query(Metric).filter(
            Metric.brand_id == competitor.id
        ).order_by(Metric.created_at.desc()).first()
        
        if latest_metric:
            results.append({
                "brand_name": competitor.name,
                "brand_id": competitor.id,
                "weighted_score": latest_metric.weighted_score,
                "mention_rate": latest_metric.mention_rate
            })
    
    return sorted(results, key=lambda x: x["weighted_score"], reverse=True)

@router.get("/grounded-gap/{brand_id}")
def get_grounded_gap(brand_id: int, db: Session = Depends(get_db)):
    grounded_metrics = db.query(Metric).join(Run).filter(
        Metric.brand_id == brand_id,
        Run.grounded == True
    ).order_by(Metric.created_at.desc()).first()
    
    ungrounded_metrics = db.query(Metric).join(Run).filter(
        Metric.brand_id == brand_id,
        Run.grounded == False
    ).order_by(Metric.created_at.desc()).first()
    
    if not grounded_metrics or not ungrounded_metrics:
        return {"gap": 0, "recommendation": "Insufficient data"}
    
    gap = grounded_metrics.mention_rate - ungrounded_metrics.mention_rate
    
    recommendation = "Brand representation is balanced"
    if gap > 0.1:
        recommendation = "Focus on improving entity grounding (Wikipedia, Wikidata, schema.org)"
    elif gap < -0.1:
        recommendation = "Focus on improving content/PR/SEO footprint"
    
    return {
        "grounded_rate": grounded_metrics.mention_rate,
        "ungrounded_rate": ungrounded_metrics.mention_rate,
        "gap": gap,
        "recommendation": recommendation
    }

@router.get("/top-entities/{brand_id}")
def get_top_entities(brand_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get top entities associated with the brand (B→E)"""
    aggregator = WeeklyAggregator(db)
    return aggregator.get_top_entities_for_brand(brand_id, limit)

@router.get("/top-brands/{brand_id}")
def get_top_brands(brand_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get top brands appearing for tracked phrases (E→B)"""
    aggregator = WeeklyAggregator(db)
    return aggregator.get_top_brands_for_phrases(brand_id, limit)

@router.get("/weekly-trends/{brand_id}/{tracked_phrase_id}")
def get_weekly_trends(
    brand_id: int,
    tracked_phrase_id: int,
    weeks: int = 8,
    db: Session = Depends(get_db)
):
    """Get weekly trend data for a specific tracked phrase"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks * 7)
    
    # Get weekly metrics
    metrics = db.query(
        WeeklyMetric,
        Brand.name
    ).join(
        Brand, WeeklyMetric.competitor_brand_id == Brand.id
    ).filter(
        WeeklyMetric.tracked_phrase_id == tracked_phrase_id,
        WeeklyMetric.week_starting >= start_date
    ).order_by(
        WeeklyMetric.week_starting,
        WeeklyMetric.frequency.desc()
    ).all()
    
    # Group by brand and week
    brand_trends = {}
    for metric, brand_name in metrics:
        if brand_name not in brand_trends:
            brand_trends[brand_name] = {
                "brand": brand_name,
                "data": [],
                "total_frequency": 0
            }
        
        brand_trends[brand_name]["data"].append({
            "week": metric.week_starting.isoformat(),
            "rank": metric.rank_position,
            "frequency": metric.frequency
        })
        brand_trends[brand_name]["total_frequency"] += metric.frequency
    
    # Sort by total frequency and take top 10
    sorted_brands = sorted(
        brand_trends.values(),
        key=lambda x: x["total_frequency"],
        reverse=True
    )[:10]
    
    return sorted_brands