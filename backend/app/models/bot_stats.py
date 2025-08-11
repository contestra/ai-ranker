"""
Bot traffic statistics models for historical data
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date

from app.database import Base

class DailyBotStats(Base):
    """Daily aggregated statistics for bot traffic per domain"""
    __tablename__ = "daily_bot_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    # Traffic metrics
    total_hits = Column(Integer, default=0)
    bot_hits = Column(Integer, default=0)
    human_hits = Column(Integer, default=0)
    
    # Bot type breakdown
    on_demand_hits = Column(Integer, default=0)  # Live queries (ChatGPT-User, etc.)
    indexing_hits = Column(Integer, default=0)   # Search indexing bots
    training_hits = Column(Integer, default=0)   # Training data collection
    
    # Verification metrics
    verified_hits = Column(Integer, default=0)
    spoofed_hits = Column(Integer, default=0)
    
    # Provider breakdown (stored as JSON)
    by_provider = Column(JSON)  # {"openai": 50, "perplexity": 30, ...}
    by_bot = Column(JSON)       # {"ChatGPT-User": 25, "PerplexityBot": 30, ...}
    
    # Top content
    top_paths = Column(JSON)    # [{"path": "/blog/ai-article", "hits": 25}, ...]
    top_referrers = Column(JSON) # [{"referrer": "chat.openai.com", "hits": 20}, ...]
    
    # Hourly distribution (24 integers)
    hourly_distribution = Column(JSON)  # [5, 3, 2, 4, 8, 12, ...] hits per hour
    
    # Calculated percentages
    bot_percentage = Column(Float, default=0.0)
    verification_rate = Column(Float, default=0.0)
    spoof_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="daily_stats")
    
    # Unique constraint to ensure one record per domain per day
    __table_args__ = (
        UniqueConstraint('domain_id', 'date', name='_domain_date_uc'),
    )


class WeeklyBotTrends(Base):
    """Weekly trends and insights"""
    __tablename__ = "weekly_bot_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    week_start = Column(Date, nullable=False, index=True)
    week_end = Column(Date, nullable=False)
    
    # Week over week changes
    total_hits = Column(Integer, default=0)
    bot_hits = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0)  # Percentage change from previous week
    
    # Top performers
    top_bot = Column(String)  # Most active bot this week
    top_provider = Column(String)  # Most active provider
    top_content = Column(String)  # Most visited path
    
    # New bots detected
    new_bots = Column(JSON)  # List of newly seen bots this week
    
    # Insights
    peak_day = Column(String)  # Day with most traffic
    peak_hour = Column(Integer)  # Hour with most traffic (0-23)
    
    # Aggregated metrics
    avg_daily_hits = Column(Float, default=0.0)
    on_demand_percentage = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="weekly_trends")
    
    __table_args__ = (
        UniqueConstraint('domain_id', 'week_start', name='_domain_week_uc'),
    )


class BotProvider(Base):
    """Registry of AI bot providers and their bots"""
    __tablename__ = "bot_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # "openai", "perplexity", etc.
    display_name = Column(String)  # "OpenAI", "Perplexity AI"
    website = Column(String)
    color = Column(String)  # For UI display "#10B981"
    
    # Known bots for this provider
    known_bots = Column(JSON)  # ["ChatGPT-User", "GPTBot", ...]
    
    # Statistics
    total_hits_alltime = Column(Integer, default=0)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)