from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from collections import defaultdict

from app.models import (
    Brand, TrackedPhrase, WeeklyMetric, PhraseResult,
    Entity, Mention, Completion, Prompt, Run
)

class WeeklyAggregator:
    """Aggregates metrics into weekly summaries for trend tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_week_start(self, date_obj: date) -> date:
        """Get the Monday of the week for a given date"""
        days_since_monday = date_obj.weekday()
        return date_obj - timedelta(days=days_since_monday)
    
    def aggregate_phrase_metrics(self, brand_id: int, weeks_back: int = 8):
        """Aggregate E→B metrics for tracked phrases"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks_back * 7)
        
        # Get tracked phrases
        phrases = self.db.query(TrackedPhrase).filter(
            TrackedPhrase.brand_id == brand_id,
            TrackedPhrase.is_active == True
        ).all()
        
        for phrase in phrases:
            # Get all phrase results within date range
            results = self.db.query(PhraseResult).filter(
                PhraseResult.tracked_phrase_id == phrase.id,
                PhraseResult.created_at >= start_date
            ).all()
            
            # Group by week and brand
            weekly_data = defaultdict(lambda: defaultdict(list))
            
            for result in results:
                week_start = self.get_week_start(result.created_at.date())
                
                # Process each brand found
                for i, brand_name in enumerate(result.brands_found or [], 1):
                    # Try to match to existing brand
                    competitor = self.db.query(Brand).filter(
                        func.lower(Brand.name) == func.lower(brand_name)
                    ).first()
                    
                    if not competitor:
                        # Check aliases
                        competitor = self.db.query(Brand).filter(
                            func.lower(func.unnest(Brand.aliases)).contains(func.lower(brand_name))
                        ).first()
                    
                    if competitor:
                        weekly_data[week_start][competitor.id].append(i)
            
            # Create or update weekly metrics
            for week_start, brands_data in weekly_data.items():
                for competitor_id, positions in brands_data.items():
                    # Calculate metrics
                    frequency = len(positions)
                    avg_position = sum(positions) / len(positions)
                    weighted_score = self.calculate_weighted_score(frequency, avg_position)
                    
                    # Check if metric exists
                    metric = self.db.query(WeeklyMetric).filter(
                        WeeklyMetric.brand_id == brand_id,
                        WeeklyMetric.tracked_phrase_id == phrase.id,
                        WeeklyMetric.competitor_brand_id == competitor_id,
                        WeeklyMetric.week_starting == week_start
                    ).first()
                    
                    if metric:
                        # Update existing
                        metric.frequency = frequency
                        metric.rank_position = int(avg_position)
                        metric.weighted_score = weighted_score
                    else:
                        # Create new
                        metric = WeeklyMetric(
                            brand_id=brand_id,
                            tracked_phrase_id=phrase.id,
                            competitor_brand_id=competitor_id,
                            week_starting=week_start,
                            frequency=frequency,
                            rank_position=int(avg_position),
                            weighted_score=weighted_score
                        )
                        self.db.add(metric)
        
        self.db.commit()
    
    def aggregate_brand_associations(self, brand_id: int, weeks_back: int = 8):
        """Aggregate B→E metrics for brand associations"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks_back * 7)
        
        brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            return
        
        # Get all runs for this brand within date range
        runs = self.db.query(Run).filter(
            Run.brand_id == brand_id,
            Run.started_at >= start_date
        ).all()
        
        # Group entities by week
        weekly_entities = defaultdict(lambda: defaultdict(int))
        
        for run in runs:
            # Get all mentions from this run
            mentions = self.db.query(
                Mention,
                Entity,
                Completion,
                Prompt
            ).join(
                Entity, Mention.entity_id == Entity.id
            ).join(
                Completion, Mention.completion_id == Completion.id
            ).join(
                Prompt, Completion.prompt_id == Prompt.id
            ).filter(
                Prompt.run_id == run.id
            ).all()
            
            week_start = self.get_week_start(run.started_at.date())
            
            for mention, entity, completion, prompt in mentions:
                # Skip if it's the brand itself
                if entity.canonical_id == brand_id:
                    continue
                
                weekly_entities[week_start][entity.id] += 1
        
        # Create or update weekly metrics
        for week_start, entities_data in weekly_entities.items():
            for entity_id, frequency in entities_data.items():
                # Check if metric exists
                metric = self.db.query(WeeklyMetric).filter(
                    WeeklyMetric.brand_id == brand_id,
                    WeeklyMetric.entity_id == entity_id,
                    WeeklyMetric.week_starting == week_start,
                    WeeklyMetric.tracked_phrase_id.is_(None)
                ).first()
                
                if metric:
                    metric.entity_frequency = frequency
                else:
                    metric = WeeklyMetric(
                        brand_id=brand_id,
                        entity_id=entity_id,
                        week_starting=week_start,
                        entity_frequency=frequency
                    )
                    self.db.add(metric)
        
        self.db.commit()
    
    def calculate_weighted_score(
        self, 
        frequency: int, 
        avg_position: float,
        max_position: int = 10
    ) -> float:
        """Calculate weighted score as shown in airank.dejan.ai"""
        if avg_position > max_position:
            return 0.0
        
        # Position weight (inverse - better position = higher weight)
        pos_weight = max(0, 1 - (avg_position - 1) / max_position)
        
        # Frequency weight (normalize to 0-1 assuming max 10 mentions per week)
        freq_weight = min(frequency / 10, 1.0)
        
        # Combined weighted score (0-1 scale, multiply by 100 for percentage)
        return freq_weight * pos_weight
    
    def get_top_entities_for_brand(
        self, 
        brand_id: int, 
        limit: int = 20
    ) -> List[Dict]:
        """Get top entities associated with a brand (B→E)"""
        # Get aggregated entity frequencies
        results = self.db.query(
            Entity.label,
            func.sum(WeeklyMetric.entity_frequency).label('total_frequency'),
            func.avg(WeeklyMetric.entity_rank).label('avg_position')
        ).join(
            WeeklyMetric, WeeklyMetric.entity_id == Entity.id
        ).filter(
            WeeklyMetric.brand_id == brand_id,
            WeeklyMetric.entity_frequency.isnot(None)
        ).group_by(
            Entity.id, Entity.label
        ).order_by(
            func.sum(WeeklyMetric.entity_frequency).desc()
        ).limit(limit).all()
        
        entities = []
        for result in results:
            weighted_score = self.calculate_weighted_score(
                result.total_frequency,
                result.avg_position or 5.0
            )
            
            entities.append({
                "entity": result.label,
                "frequency": result.total_frequency,
                "avg_position": round(result.avg_position, 2) if result.avg_position else None,
                "weighted_score": round(weighted_score, 3)
            })
        
        return entities
    
    def get_top_brands_for_phrases(
        self, 
        brand_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """Get top brands appearing for tracked phrases (E→B)"""
        # Get all tracked phrases for this brand
        phrase_ids = self.db.query(TrackedPhrase.id).filter(
            TrackedPhrase.brand_id == brand_id,
            TrackedPhrase.is_active == True
        ).subquery()
        
        # Get aggregated brand frequencies
        results = self.db.query(
            Brand.name,
            func.sum(WeeklyMetric.frequency).label('total_frequency'),
            func.avg(WeeklyMetric.rank_position).label('avg_position')
        ).join(
            WeeklyMetric, WeeklyMetric.competitor_brand_id == Brand.id
        ).filter(
            WeeklyMetric.tracked_phrase_id.in_(phrase_ids)
        ).group_by(
            Brand.id, Brand.name
        ).order_by(
            func.sum(WeeklyMetric.frequency).desc()
        ).limit(limit).all()
        
        brands = []
        for result in results:
            weighted_score = self.calculate_weighted_score(
                result.total_frequency,
                result.avg_position or 5.0
            )
            
            brands.append({
                "brand": result.name,
                "frequency": result.total_frequency,
                "avg_position": round(result.avg_position, 2) if result.avg_position else None,
                "weighted_score": round(weighted_score, 3)
            })
        
        return brands