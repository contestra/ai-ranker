"""
Weekly Tracking System for BEEB Analysis
Stores and retrieves time-series data for entity and brand rankings
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

router = APIRouter()

# Create data directory if it doesn't exist
DATA_DIR = Path("data/weekly_tracking")
DATA_DIR.mkdir(parents=True, exist_ok=True)

class WeeklyDataPoint(BaseModel):
    week_start: str  # ISO date string
    rank: int  # 1-10, where 1 is best
    frequency: int  # Number of mentions
    variance: Optional[float] = None

class EntityTracking(BaseModel):
    entity: str
    data_points: List[WeeklyDataPoint]
    total_frequency: int
    avg_rank: float
    variance: float

class BrandTracking(BaseModel):
    brand: str
    data_points: List[WeeklyDataPoint]
    total_frequency: int
    avg_rank: float
    variance: float

class WeeklyTrackingRequest(BaseModel):
    brand_name: str
    vendor: str
    entity_rankings: Dict[str, int]  # entity -> rank
    brand_rankings: Dict[str, Dict[str, int]]  # phrase -> {brand -> rank}

class WeeklyTrackingResponse(BaseModel):
    brand_name: str
    vendor: str
    entity_tracking: List[EntityTracking]
    phrase_tracking: Dict[str, List[BrandTracking]]

def get_week_start(date: datetime = None) -> str:
    """Get the Monday of the current week"""
    if date is None:
        date = datetime.now()
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    return monday.strftime("%Y-%m-%d")

def load_tracking_data(brand_name: str, vendor: str) -> Dict:
    """Load existing tracking data from file"""
    file_path = DATA_DIR / f"{brand_name.replace(' ', '_')}_{vendor}.json"
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {
        "brand_name": brand_name,
        "vendor": vendor,
        "entity_tracking": {},
        "phrase_tracking": {}
    }

def save_tracking_data(brand_name: str, vendor: str, data: Dict):
    """Save tracking data to file"""
    file_path = DATA_DIR / f"{brand_name.replace(' ', '_')}_{vendor}.json"
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

@router.post("/weekly-tracking/update")
async def update_weekly_tracking(request: WeeklyTrackingRequest):
    """
    Update weekly tracking data with new rankings
    """
    week_start = get_week_start()
    
    # Load existing data
    tracking_data = load_tracking_data(request.brand_name, request.vendor)
    
    # Update entity tracking
    if "entity_tracking" not in tracking_data:
        tracking_data["entity_tracking"] = {}
    
    for entity, rank in request.entity_rankings.items():
        if entity not in tracking_data["entity_tracking"]:
            tracking_data["entity_tracking"][entity] = []
        
        # Check if we already have data for this week
        existing_week = False
        for point in tracking_data["entity_tracking"][entity]:
            if point["week_start"] == week_start:
                point["rank"] = rank
                point["frequency"] = point.get("frequency", 0) + 1
                existing_week = True
                break
        
        if not existing_week:
            tracking_data["entity_tracking"][entity].append({
                "week_start": week_start,
                "rank": rank,
                "frequency": 1
            })
    
    # Update phrase/brand tracking
    if "phrase_tracking" not in tracking_data:
        tracking_data["phrase_tracking"] = {}
    
    for phrase, brand_rankings in request.brand_rankings.items():
        if phrase not in tracking_data["phrase_tracking"]:
            tracking_data["phrase_tracking"][phrase] = {}
        
        for brand, rank in brand_rankings.items():
            if brand not in tracking_data["phrase_tracking"][phrase]:
                tracking_data["phrase_tracking"][phrase][brand] = []
            
            # Check if we already have data for this week
            existing_week = False
            for point in tracking_data["phrase_tracking"][phrase][brand]:
                if point["week_start"] == week_start:
                    point["rank"] = rank
                    point["frequency"] = point.get("frequency", 0) + 1
                    existing_week = True
                    break
            
            if not existing_week:
                tracking_data["phrase_tracking"][phrase][brand].append({
                    "week_start": week_start,
                    "rank": rank,
                    "frequency": 1
                })
    
    # Save updated data
    save_tracking_data(request.brand_name, request.vendor, tracking_data)
    
    return {"status": "success", "week": week_start}

@router.get("/weekly-tracking/{brand_name}/{vendor}", response_model=WeeklyTrackingResponse)
async def get_weekly_tracking(brand_name: str, vendor: str):
    """
    Get weekly tracking data for visualization
    """
    tracking_data = load_tracking_data(brand_name, vendor)
    
    # Process entity tracking
    entity_tracking = []
    for entity, data_points in tracking_data.get("entity_tracking", {}).items():
        if data_points:
            total_freq = sum(p.get("frequency", 1) for p in data_points)
            ranks = [p["rank"] for p in data_points]
            avg_rank = sum(ranks) / len(ranks) if ranks else 0
            
            # Calculate variance
            if len(ranks) > 1:
                mean = avg_rank
                variance = sum((r - mean) ** 2 for r in ranks) / len(ranks)
            else:
                variance = 0
            
            entity_tracking.append(EntityTracking(
                entity=entity,
                data_points=[WeeklyDataPoint(**p) for p in data_points],
                total_frequency=total_freq,
                avg_rank=round(avg_rank, 2),
                variance=round(variance, 2)
            ))
    
    # Sort by average rank (best first)
    entity_tracking.sort(key=lambda x: x.avg_rank)
    
    # Process phrase tracking
    phrase_tracking = {}
    for phrase, brands_data in tracking_data.get("phrase_tracking", {}).items():
        brand_tracking = []
        for brand, data_points in brands_data.items():
            if data_points:
                total_freq = sum(p.get("frequency", 1) for p in data_points)
                ranks = [p["rank"] for p in data_points]
                avg_rank = sum(ranks) / len(ranks) if ranks else 0
                
                # Calculate variance
                if len(ranks) > 1:
                    mean = avg_rank
                    variance = sum((r - mean) ** 2 for r in ranks) / len(ranks)
                else:
                    variance = 0
                
                brand_tracking.append(BrandTracking(
                    brand=brand,
                    data_points=[WeeklyDataPoint(**p) for p in data_points],
                    total_frequency=total_freq,
                    avg_rank=round(avg_rank, 2),
                    variance=round(variance, 2)
                ))
        
        # Sort by average rank (best first)
        brand_tracking.sort(key=lambda x: x.avg_rank)
        phrase_tracking[phrase] = brand_tracking[:10]  # Top 10 brands per phrase
    
    return WeeklyTrackingResponse(
        brand_name=brand_name,
        vendor=vendor,
        entity_tracking=entity_tracking[:10],  # Top 10 entities
        phrase_tracking=phrase_tracking
    )

@router.post("/weekly-tracking/generate-sample")
async def generate_sample_data(brand_name: str = "AVEA Life", vendor: str = "openai"):
    """
    Generate sample weekly tracking data for testing
    """
    # Generate 4 weeks of sample data
    weeks = []
    current_date = datetime.now()
    for i in range(4):
        week_date = current_date - timedelta(weeks=3-i)
        weeks.append(get_week_start(week_date))
    
    tracking_data = {
        "brand_name": brand_name,
        "vendor": vendor,
        "entity_tracking": {},
        "phrase_tracking": {}
    }
    
    # Sample entities for AVEA Life
    entities = {
        "AVEA": [2, 1, 1, 2],  # Ranks over 4 weeks
        "telecommunications": [3, 4, 3, 3],
        "longevity": [5, 4, 4, 3],
        "supplements": [4, 5, 5, 4],
        "Turkey": [6, 7, 8, 7],
        "wellness": [7, 6, 6, 5],
        "anti-aging": [8, 8, 7, 6],
        "vitamins": [9, 9, 9, 8]
    }
    
    for entity, ranks in entities.items():
        tracking_data["entity_tracking"][entity] = []
        for week, rank in zip(weeks, ranks):
            tracking_data["entity_tracking"][entity].append({
                "week_start": week,
                "rank": rank,
                "frequency": 5 - rank // 2  # Higher rank = more frequency
            })
    
    # Sample phrase tracking
    phrases = {
        "best longevity supplements": {
            "Life Extension": [1, 1, 2, 1],
            "Thorne Research": [2, 3, 1, 2],
            "NOW Foods": [3, 2, 3, 3],
            "AVEA Life": [8, 7, 6, 5],  # Your brand improving
            "Garden of Life": [4, 4, 4, 4]
        },
        "Swiss supplements": {
            "AVEA Life": [5, 4, 3, 2],  # Better performance here
            "Burgerstein": [1, 1, 1, 1],
            "A.Vogel": [2, 2, 2, 3],
            "Biotta": [3, 3, 4, 4]
        }
    }
    
    for phrase, brands in phrases.items():
        tracking_data["phrase_tracking"][phrase] = {}
        for brand, ranks in brands.items():
            tracking_data["phrase_tracking"][phrase][brand] = []
            for week, rank in zip(weeks, ranks):
                tracking_data["phrase_tracking"][phrase][brand].append({
                    "week_start": week,
                    "rank": rank,
                    "frequency": 10 - rank  # Higher rank = more frequency
                })
    
    # Save the sample data
    save_tracking_data(brand_name, vendor, tracking_data)
    
    return {"status": "success", "message": f"Generated sample data for {brand_name} ({vendor})"}