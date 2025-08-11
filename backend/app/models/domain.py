"""
Domain model for tracking multiple domains per brand
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Domain(Base):
    __tablename__ = "domains"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Domain info
    url = Column(String, nullable=False)  # e.g., "avea-life.com" (without https://)
    full_url = Column(String)  # e.g., "https://avea-life.com"
    subdomain = Column(String)  # e.g., "insights" for insights.avea-life.com
    
    # Tracking status
    is_trackable = Column(Boolean, default=True)
    tracking_method = Column(String)  # "wordpress_plugin", "cloudflare", "vercel", etc.
    technology = Column(String)  # "wordpress", "shopify", "custom", etc.
    technology_details = Column(JSON)  # Additional tech stack info
    
    # Validation
    validation_status = Column(String)  # "pending", "valid", "invalid"
    validation_message = Column(String)  # Why it can't be tracked
    last_validated = Column(DateTime)
    
    # Stats
    total_bot_hits = Column(Integer, default=0)
    last_bot_hit = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    brand = relationship("Brand", back_populates="domains")
    bot_events = relationship("BotEvent", back_populates="domain")
    daily_stats = relationship("DailyBotStats", back_populates="domain", cascade="all, delete-orphan")
    weekly_trends = relationship("WeeklyBotTrends", back_populates="domain", cascade="all, delete-orphan")

class BotEvent(Base):
    """Track individual bot hits with domain association"""
    __tablename__ = "bot_events"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Bot info
    is_bot = Column(Boolean, default=False)
    bot_name = Column(String)  # "ChatGPT-User", "PerplexityBot", etc.
    bot_type = Column(String)  # "on_demand", "indexing", "training"
    provider = Column(String)  # "openai", "perplexity", "anthropic", etc.
    
    # Request info
    method = Column(String)  # GET, POST, etc.
    path = Column(String)  # /products, /blog/post-1, etc.
    status = Column(Integer)  # 200, 404, etc.
    user_agent = Column(String)
    client_ip = Column(String)
    
    # Verification
    verified = Column(Boolean, default=False)
    potential_spoof = Column(Boolean, default=False)
    spoof_reason = Column(String)
    
    # Additional data
    country = Column(String)
    referrer = Column(String)
    event_metadata = Column(JSON)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="bot_events")
    brand = relationship("Brand", back_populates="bot_events")