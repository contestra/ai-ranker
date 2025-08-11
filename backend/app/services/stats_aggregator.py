"""
Service to aggregate bot traffic statistics daily
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import json

from app.models import Domain, BotEvent, DailyBotStats, WeeklyBotTrends
from app.database import get_db

class StatsAggregator:
    """Aggregates bot traffic statistics for historical analysis"""
    
    def aggregate_daily_stats(self, domain_id: int, target_date: date, db: Session) -> DailyBotStats:
        """
        Aggregate statistics for a specific domain and date
        """
        # Check if stats already exist
        existing = db.query(DailyBotStats).filter(
            and_(
                DailyBotStats.domain_id == domain_id,
                DailyBotStats.date == target_date
            )
        ).first()
        
        if existing:
            # Update existing record
            stats = existing
        else:
            # Create new record
            stats = DailyBotStats(
                domain_id=domain_id,
                date=target_date
            )
            db.add(stats)
        
        # Define date range (UTC)
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        # Get all events for this domain and date
        events = db.query(BotEvent).filter(
            and_(
                BotEvent.domain_id == domain_id,
                BotEvent.timestamp >= start_time,
                BotEvent.timestamp <= end_time
            )
        ).all()
        
        # Calculate basic metrics
        stats.total_hits = len(events)
        stats.bot_hits = sum(1 for e in events if e.is_bot)
        stats.human_hits = stats.total_hits - stats.bot_hits
        
        # Bot type breakdown
        stats.on_demand_hits = sum(1 for e in events if e.bot_type == 'on_demand')
        stats.indexing_hits = sum(1 for e in events if e.bot_type == 'indexing')
        stats.training_hits = sum(1 for e in events if e.bot_type == 'training')
        
        # Verification metrics
        stats.verified_hits = sum(1 for e in events if e.verified)
        stats.spoofed_hits = sum(1 for e in events if e.potential_spoof)
        
        # Provider breakdown
        by_provider = {}
        by_bot = {}
        for event in events:
            if event.is_bot and event.provider:
                by_provider[event.provider] = by_provider.get(event.provider, 0) + 1
            if event.is_bot and event.bot_name:
                by_bot[event.bot_name] = by_bot.get(event.bot_name, 0) + 1
        
        stats.by_provider = by_provider
        stats.by_bot = by_bot
        
        # Top paths
        path_counts = {}
        for event in events:
            if event.path:
                path_counts[event.path] = path_counts.get(event.path, 0) + 1
        
        top_paths = sorted(
            [{"path": path, "hits": count} for path, count in path_counts.items()],
            key=lambda x: x["hits"],
            reverse=True
        )[:10]
        stats.top_paths = top_paths
        
        # Top referrers
        referrer_counts = {}
        for event in events:
            if event.referrer:
                referrer_counts[event.referrer] = referrer_counts.get(event.referrer, 0) + 1
        
        top_referrers = sorted(
            [{"referrer": ref, "hits": count} for ref, count in referrer_counts.items()],
            key=lambda x: x["hits"],
            reverse=True
        )[:10]
        stats.top_referrers = top_referrers
        
        # Hourly distribution
        hourly = [0] * 24
        for event in events:
            if event.is_bot:
                hour = event.timestamp.hour
                hourly[hour] += 1
        stats.hourly_distribution = hourly
        
        # Calculate percentages
        if stats.total_hits > 0:
            stats.bot_percentage = (stats.bot_hits / stats.total_hits) * 100
        else:
            stats.bot_percentage = 0
            
        if stats.bot_hits > 0:
            stats.verification_rate = (stats.verified_hits / stats.bot_hits) * 100
            stats.spoof_rate = (stats.spoofed_hits / stats.bot_hits) * 100
        else:
            stats.verification_rate = 0
            stats.spoof_rate = 0
        
        db.commit()
        return stats
    
    def aggregate_all_domains_daily(self, target_date: date, db: Session) -> List[DailyBotStats]:
        """
        Aggregate daily stats for all active domains
        """
        domains = db.query(Domain).all()
        results = []
        
        for domain in domains:
            try:
                stats = self.aggregate_daily_stats(domain.id, target_date, db)
                results.append(stats)
            except Exception as e:
                print(f"Error aggregating stats for domain {domain.url}: {e}")
                continue
        
        return results
    
    def aggregate_weekly_trends(self, domain_id: int, week_start: date, db: Session) -> WeeklyBotTrends:
        """
        Calculate weekly trends for a domain
        """
        week_end = week_start + timedelta(days=6)
        
        # Check if trends already exist
        existing = db.query(WeeklyBotTrends).filter(
            and_(
                WeeklyBotTrends.domain_id == domain_id,
                WeeklyBotTrends.week_start == week_start
            )
        ).first()
        
        if existing:
            trends = existing
        else:
            trends = WeeklyBotTrends(
                domain_id=domain_id,
                week_start=week_start,
                week_end=week_end
            )
            db.add(trends)
        
        # Get daily stats for the week
        daily_stats = db.query(DailyBotStats).filter(
            and_(
                DailyBotStats.domain_id == domain_id,
                DailyBotStats.date >= week_start,
                DailyBotStats.date <= week_end
            )
        ).all()
        
        if daily_stats:
            # Calculate totals
            trends.total_hits = sum(s.total_hits for s in daily_stats)
            trends.bot_hits = sum(s.bot_hits for s in daily_stats)
            
            # Find peak day
            peak_day_stats = max(daily_stats, key=lambda s: s.bot_hits)
            trends.peak_day = peak_day_stats.date.strftime('%A')
            
            # Find peak hour across all days
            hourly_totals = [0] * 24
            for stats in daily_stats:
                if stats.hourly_distribution:
                    for hour, count in enumerate(stats.hourly_distribution):
                        hourly_totals[hour] += count
            
            if any(hourly_totals):
                trends.peak_hour = hourly_totals.index(max(hourly_totals))
            
            # Calculate averages
            trends.avg_daily_hits = trends.bot_hits / len(daily_stats)
            
            # Find top bot and provider
            all_bots = {}
            all_providers = {}
            
            for stats in daily_stats:
                if stats.by_bot:
                    for bot, count in stats.by_bot.items():
                        all_bots[bot] = all_bots.get(bot, 0) + count
                if stats.by_provider:
                    for provider, count in stats.by_provider.items():
                        all_providers[provider] = all_providers.get(provider, 0) + count
            
            if all_bots:
                trends.top_bot = max(all_bots, key=all_bots.get)
            if all_providers:
                trends.top_provider = max(all_providers, key=all_providers.get)
            
            # Calculate on-demand percentage
            on_demand_total = sum(s.on_demand_hits for s in daily_stats)
            if trends.bot_hits > 0:
                trends.on_demand_percentage = (on_demand_total / trends.bot_hits) * 100
            
            # Calculate growth rate (compare to previous week)
            prev_week_start = week_start - timedelta(days=7)
            prev_week_end = prev_week_start + timedelta(days=6)
            
            prev_week_stats = db.query(func.sum(DailyBotStats.bot_hits)).filter(
                and_(
                    DailyBotStats.domain_id == domain_id,
                    DailyBotStats.date >= prev_week_start,
                    DailyBotStats.date <= prev_week_end
                )
            ).scalar() or 0
            
            if prev_week_stats > 0:
                trends.growth_rate = ((trends.bot_hits - prev_week_stats) / prev_week_stats) * 100
            else:
                trends.growth_rate = 100 if trends.bot_hits > 0 else 0
        
        db.commit()
        return trends
    
    def get_historical_data(
        self, 
        domain_id: int, 
        start_date: date, 
        end_date: date, 
        db: Session
    ) -> Dict:
        """
        Get historical data for charts and analysis
        """
        daily_stats = db.query(DailyBotStats).filter(
            and_(
                DailyBotStats.domain_id == domain_id,
                DailyBotStats.date >= start_date,
                DailyBotStats.date <= end_date
            )
        ).order_by(DailyBotStats.date).all()
        
        # Prepare data for charts
        dates = []
        bot_hits = []
        human_hits = []
        on_demand = []
        indexing = []
        training = []
        
        for stat in daily_stats:
            dates.append(stat.date.isoformat())
            bot_hits.append(stat.bot_hits)
            human_hits.append(stat.human_hits)
            on_demand.append(stat.on_demand_hits)
            indexing.append(stat.indexing_hits)
            training.append(stat.training_hits)
        
        # Aggregate provider data
        all_providers = {}
        for stat in daily_stats:
            if stat.by_provider:
                for provider, count in stat.by_provider.items():
                    if provider not in all_providers:
                        all_providers[provider] = []
                    all_providers[provider].append(count)
        
        return {
            "dates": dates,
            "bot_hits": bot_hits,
            "human_hits": human_hits,
            "by_type": {
                "on_demand": on_demand,
                "indexing": indexing,
                "training": training
            },
            "by_provider": all_providers,
            "summary": {
                "total_bot_hits": sum(bot_hits),
                "total_human_hits": sum(human_hits),
                "avg_daily_bots": sum(bot_hits) / max(len(bot_hits), 1),
                "peak_day": dates[bot_hits.index(max(bot_hits))] if bot_hits else None
            }
        }

# Singleton instance
stats_aggregator = StatsAggregator()