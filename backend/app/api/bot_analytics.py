"""
Bot traffic analytics API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import Domain, DailyBotStats, WeeklyBotTrends
from app.services.stats_aggregator import stats_aggregator

router = APIRouter()

class DateRange(BaseModel):
    start_date: date
    end_date: date

@router.post("/domains/{domain_id}/aggregate-stats")
async def trigger_aggregation(
    domain_id: int,
    date_range: Optional[DateRange] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Manually trigger stats aggregation for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    if date_range:
        # Aggregate for specific date range
        current_date = date_range.start_date
        while current_date <= date_range.end_date:
            background_tasks.add_task(
                stats_aggregator.aggregate_daily_stats,
                domain_id,
                current_date,
                db
            )
            current_date += timedelta(days=1)
    else:
        # Aggregate for yesterday (most common use case)
        yesterday = date.today() - timedelta(days=1)
        background_tasks.add_task(
            stats_aggregator.aggregate_daily_stats,
            domain_id,
            yesterday,
            db
        )
    
    return {"message": "Aggregation triggered", "domain": domain.url}

@router.get("/domains/{domain_id}/daily-stats")
async def get_daily_stats(
    domain_id: int,
    days: int = Query(7, description="Number of days to retrieve"),
    db: Session = Depends(get_db)
):
    """Get daily statistics for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Get or create stats for the date range
    stats = []
    current_date = start_date
    while current_date <= end_date:
        daily_stat = db.query(DailyBotStats).filter(
            DailyBotStats.domain_id == domain_id,
            DailyBotStats.date == current_date
        ).first()
        
        if not daily_stat and current_date <= date.today():
            # Aggregate missing data
            daily_stat = stats_aggregator.aggregate_daily_stats(domain_id, current_date, db)
        
        if daily_stat:
            stats.append({
                "date": daily_stat.date.isoformat(),
                "total_hits": daily_stat.total_hits,
                "bot_hits": daily_stat.bot_hits,
                "human_hits": daily_stat.human_hits,
                "on_demand_hits": daily_stat.on_demand_hits,
                "indexing_hits": daily_stat.indexing_hits,
                "training_hits": daily_stat.training_hits,
                "bot_percentage": daily_stat.bot_percentage,
                "top_bot": max(daily_stat.by_bot.items(), key=lambda x: x[1])[0] if daily_stat.by_bot else None,
                "top_provider": max(daily_stat.by_provider.items(), key=lambda x: x[1])[0] if daily_stat.by_provider else None
            })
        else:
            # No data for future dates
            stats.append({
                "date": current_date.isoformat(),
                "total_hits": 0,
                "bot_hits": 0,
                "human_hits": 0,
                "on_demand_hits": 0,
                "indexing_hits": 0,
                "training_hits": 0,
                "bot_percentage": 0,
                "top_bot": None,
                "top_provider": None
            })
        
        current_date += timedelta(days=1)
    
    return {
        "domain": domain.url,
        "period": f"{days} days",
        "stats": stats
    }

@router.get("/domains/{domain_id}/historical-data")
async def get_historical_data(
    domain_id: int,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: Session = Depends(get_db)
):
    """Get historical data for charts and analysis"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Validate date range
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    if (end_date - start_date).days > 90:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 90 days")
    
    data = stats_aggregator.get_historical_data(domain_id, start_date, end_date, db)
    
    return {
        "domain": domain.url,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": data
    }

@router.get("/domains/{domain_id}/weekly-trends")
async def get_weekly_trends(
    domain_id: int,
    weeks: int = Query(4, description="Number of weeks to retrieve"),
    db: Session = Depends(get_db)
):
    """Get weekly trends for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Calculate week starts (Monday)
    today = date.today()
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    
    trends = []
    for i in range(weeks):
        week_start = current_week_start - timedelta(weeks=i)
        
        trend = db.query(WeeklyBotTrends).filter(
            WeeklyBotTrends.domain_id == domain_id,
            WeeklyBotTrends.week_start == week_start
        ).first()
        
        if not trend and week_start <= today:
            # Calculate missing trends
            trend = stats_aggregator.aggregate_weekly_trends(domain_id, week_start, db)
        
        if trend:
            trends.append({
                "week_start": trend.week_start.isoformat(),
                "week_end": trend.week_end.isoformat(),
                "total_hits": trend.total_hits,
                "bot_hits": trend.bot_hits,
                "growth_rate": trend.growth_rate,
                "top_bot": trend.top_bot,
                "top_provider": trend.top_provider,
                "peak_day": trend.peak_day,
                "peak_hour": trend.peak_hour,
                "avg_daily_hits": trend.avg_daily_hits,
                "on_demand_percentage": trend.on_demand_percentage
            })
    
    return {
        "domain": domain.url,
        "weeks": weeks,
        "trends": trends
    }

@router.get("/domains/{domain_id}/bot-breakdown")
async def get_bot_breakdown(
    domain_id: int,
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get detailed bot breakdown for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Aggregate bot data across the period
    all_bots = {}
    all_providers = {}
    all_types = {"on_demand": 0, "indexing": 0, "training": 0}
    
    stats = db.query(DailyBotStats).filter(
        DailyBotStats.domain_id == domain_id,
        DailyBotStats.date >= start_date,
        DailyBotStats.date <= end_date
    ).all()
    
    for stat in stats:
        # Aggregate bots
        if stat.by_bot:
            for bot, count in stat.by_bot.items():
                all_bots[bot] = all_bots.get(bot, 0) + count
        
        # Aggregate providers
        if stat.by_provider:
            for provider, count in stat.by_provider.items():
                all_providers[provider] = all_providers.get(provider, 0) + count
        
        # Aggregate types
        all_types["on_demand"] += stat.on_demand_hits
        all_types["indexing"] += stat.indexing_hits
        all_types["training"] += stat.training_hits
    
    # Sort and format results
    top_bots = sorted(
        [{"name": bot, "hits": count} for bot, count in all_bots.items()],
        key=lambda x: x["hits"],
        reverse=True
    )[:20]
    
    provider_breakdown = sorted(
        [{"provider": provider, "hits": count} for provider, count in all_providers.items()],
        key=lambda x: x["hits"],
        reverse=True
    )
    
    return {
        "domain": domain.url,
        "period": f"{days} days",
        "top_bots": top_bots,
        "by_provider": provider_breakdown,
        "by_type": all_types,
        "total_bot_hits": sum(all_bots.values())
    }

@router.get("/domains/{domain_id}/hourly-pattern")
async def get_hourly_pattern(
    domain_id: int,
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get hourly traffic pattern for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Aggregate hourly data
    hourly_totals = [0] * 24
    
    stats = db.query(DailyBotStats).filter(
        DailyBotStats.domain_id == domain_id,
        DailyBotStats.date >= start_date,
        DailyBotStats.date <= end_date
    ).all()
    
    for stat in stats:
        if stat.hourly_distribution:
            for hour, count in enumerate(stat.hourly_distribution):
                hourly_totals[hour] += count
    
    # Find peak hours
    peak_hour = hourly_totals.index(max(hourly_totals)) if any(hourly_totals) else None
    
    return {
        "domain": domain.url,
        "period": f"{days} days",
        "hourly_pattern": hourly_totals,
        "peak_hour": peak_hour,
        "peak_hour_hits": max(hourly_totals) if hourly_totals else 0
    }

@router.post("/aggregate-all-domains")
async def aggregate_all_domains(
    background_tasks: BackgroundTasks,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Trigger aggregation for all domains (admin endpoint)"""
    
    if not target_date:
        target_date = date.today() - timedelta(days=1)
    
    background_tasks.add_task(
        stats_aggregator.aggregate_all_domains_daily,
        target_date,
        db
    )
    
    return {
        "message": "Aggregation triggered for all domains",
        "date": target_date.isoformat()
    }