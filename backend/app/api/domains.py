"""
Domain management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Brand, Domain
from app.services.domain_validator import domain_validator

router = APIRouter()

# Request/Response models
class DomainCreate(BaseModel):
    url: str  # User enters: "avea-life.com" or "insights.avea-life.com"
    
class DomainUpdate(BaseModel):
    is_trackable: Optional[bool] = None
    tracking_method: Optional[str] = None
    
class DomainResponse(BaseModel):
    id: int
    brand_id: int
    url: str
    full_url: str
    subdomain: str
    is_trackable: bool
    technology: Optional[str]
    technology_details: Optional[dict]
    tracking_method: Optional[str]
    validation_status: str
    validation_message: Optional[str]
    total_bot_hits: int
    last_bot_hit: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class DomainValidation(BaseModel):
    domain: str
    is_trackable: bool
    technology: List[str]
    tracking_methods: List[str]
    messages: List[str]
    recommendation: str
    success: bool
    error: Optional[str] = None

# Domain management endpoints
@router.post("/brands/{brand_id}/domains", response_model=DomainResponse)
async def add_domain(
    brand_id: int,
    domain_data: DomainCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Add a domain to a brand with automatic validation"""
    
    # Check brand exists
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Normalize domain
    normalized = domain_validator.normalize_domain(domain_data.url)
    
    # Check if domain already exists for this brand
    existing = db.query(Domain).filter(
        Domain.brand_id == brand_id,
        Domain.url == normalized
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists for this brand")
    
    # Extract subdomain
    subdomain, main_domain = domain_validator.extract_subdomain(normalized)
    
    # Create domain record
    domain = Domain(
        brand_id=brand_id,
        url=normalized,
        full_url=f"https://{normalized}",
        subdomain=subdomain,
        validation_status="pending"
    )
    
    db.add(domain)
    db.commit()
    db.refresh(domain)
    
    # Schedule async validation
    background_tasks.add_task(validate_and_update_domain, domain.id, db)
    
    return domain

@router.get("/brands/{brand_id}/domains", response_model=List[DomainResponse])
def get_brand_domains(brand_id: int, db: Session = Depends(get_db)):
    """Get all domains for a brand"""
    domains = db.query(Domain).filter(Domain.brand_id == brand_id).all()
    return domains

@router.delete("/domains/{domain_id}")
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    """Delete a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    db.delete(domain)
    db.commit()
    return {"message": "Domain deleted"}

@router.post("/validate", response_model=DomainValidation)
async def validate_domain(data: DomainCreate):
    """Validate a domain without saving it"""
    normalized = domain_validator.normalize_domain(data.url)
    result = await domain_validator.validate_domain(normalized)
    return result

@router.post("/domains/validate-multiple", response_model=List[DomainValidation])
async def validate_multiple_domains(urls: List[str]):
    """Validate multiple domains at once"""
    results = await domain_validator.validate_multiple(urls)
    return results

@router.get("/domains/{domain_id}/stats")
def get_domain_stats(
    domain_id: int,
    db: Session = Depends(get_db)
):
    """Get bot traffic statistics for a domain"""
    from sqlalchemy import func
    from app.models import BotEvent
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Get stats
    total_hits = db.query(BotEvent).filter(BotEvent.domain_id == domain_id).count()
    bot_hits = db.query(BotEvent).filter(
        BotEvent.domain_id == domain_id,
        BotEvent.is_bot == True
    ).count()
    
    on_demand_hits = db.query(BotEvent).filter(
        BotEvent.domain_id == domain_id,
        BotEvent.bot_type == "on_demand"
    ).count()
    
    # Top bots
    top_bots = db.query(
        BotEvent.bot_name,
        func.count(BotEvent.id).label('count')
    ).filter(
        BotEvent.domain_id == domain_id,
        BotEvent.is_bot == True
    ).group_by(BotEvent.bot_name).order_by(func.count(BotEvent.id).desc()).limit(10).all()
    
    # Top paths
    top_paths = db.query(
        BotEvent.path,
        func.count(BotEvent.id).label('count')
    ).filter(
        BotEvent.domain_id == domain_id
    ).group_by(BotEvent.path).order_by(func.count(BotEvent.id).desc()).limit(10).all()
    
    return {
        "domain": domain.url,
        "total_hits": total_hits,
        "bot_hits": bot_hits,
        "on_demand_hits": on_demand_hits,
        "bot_percentage": (bot_hits / max(1, total_hits)) * 100,
        "top_bots": [{"name": bot, "count": count} for bot, count in top_bots],
        "top_paths": [{"path": path, "count": count} for path, count in top_paths]
    }

# Background task to validate domain
async def validate_and_update_domain(domain_id: int, db: Session):
    """Background task to validate domain and update its status"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        return
    
    # Validate domain
    result = await domain_validator.validate_domain(domain.url)
    
    # Update domain record
    domain.is_trackable = result.get('is_trackable', False)
    domain.technology = ','.join(result.get('technology', []))
    domain.technology_details = result
    domain.validation_status = 'valid' if result.get('success') else 'invalid'
    domain.validation_message = result.get('recommendation', '')
    domain.last_validated = datetime.utcnow()
    
    if result.get('tracking_methods'):
        domain.tracking_method = result['tracking_methods'][0]
    
    db.commit()