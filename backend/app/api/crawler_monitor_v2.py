"""
Real-time AI Crawler Monitoring API V2
Multi-tenant version with PostgreSQL storage and domain separation
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import json
import asyncio

from app.database import get_db
from app.models import Domain, BotEvent, Brand
from app.services.bot_detector import bot_detector

router = APIRouter()

# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # domain -> [websockets]
    
    async def connect(self, websocket: WebSocket, domain: str):
        await websocket.accept()
        if domain not in self.active_connections:
            self.active_connections[domain] = []
        self.active_connections[domain].append(websocket)
    
    def disconnect(self, websocket: WebSocket, domain: str):
        if domain in self.active_connections:
            self.active_connections[domain].remove(websocket)
            if not self.active_connections[domain]:
                del self.active_connections[domain]
    
    async def send_to_domain(self, message: dict, domain: str):
        if domain in self.active_connections:
            disconnected = []
            for connection in self.active_connections[domain]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[domain].remove(conn)

manager = ConnectionManager()

# Request models
class GenericLogRequest(BaseModel):
    timestamp: str
    domain: str  # Now required to identify the source
    method: str
    path: str
    status: int
    user_agent: str
    client_ip: str
    provider: Optional[str] = "unknown"
    metadata: Optional[Dict[str, Any]] = {}

# Ingestion endpoint with domain support
@router.post("/ingest/generic")
async def ingest_generic_v2(
    request: GenericLogRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generic ingestion endpoint with multi-tenant support"""
    
    # Find or create domain
    domain = db.query(Domain).filter(Domain.url == request.domain).first()
    
    if not domain:
        # Try to find brand and create domain
        # For now, we'll skip unknown domains
        return {"status": "error", "message": "Unknown domain. Please register domain first."}
    
    # Detect and classify bot
    bot_info = bot_detector.classify_bot(request.user_agent, request.client_ip)
    
    # Create bot event in database
    event = BotEvent(
        domain_id=domain.id,
        brand_id=domain.brand_id,
        is_bot=bot_info.get("is_bot", False),
        bot_name=bot_info.get("bot_name"),
        bot_type=bot_info.get("bot_type"),
        provider=bot_info.get("provider", request.provider),
        method=request.method,
        path=request.path,
        status=request.status,
        user_agent=request.user_agent,
        client_ip=request.client_ip,
        timestamp=datetime.fromisoformat(request.timestamp.replace('Z', '+00:00')),
        event_metadata=request.metadata
    )
    
    # Verify bot IP if needed
    if bot_info.get("requires_verification"):
        background_tasks.add_task(verify_and_update_event, event.id, db)
    
    db.add(event)
    db.commit()
    
    # Update domain stats
    domain.total_bot_hits += 1 if bot_info.get("is_bot") else 0
    if bot_info.get("is_bot"):
        domain.last_bot_hit = datetime.utcnow()
    db.commit()
    
    # Send real-time update via WebSocket
    await manager.send_to_domain({
        "type": "new_event",
        **bot_info,
        "path": request.path,
        "timestamp": request.timestamp
    }, request.domain)
    
    return {"status": "accepted", "is_bot": bot_info.get("is_bot", False)}

# Get stats for a specific domain
@router.get("/monitor/stats/{domain_url}")
async def get_domain_stats(
    domain_url: str,
    hours: int = Query(24, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    """Get monitoring statistics for a specific domain"""
    
    # Get domain
    domain = db.query(Domain).filter(Domain.url == domain_url).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Time filter
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Get stats
    total_hits = db.query(BotEvent).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.timestamp >= since
        )
    ).count()
    
    bot_hits = db.query(BotEvent).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.is_bot == True,
            BotEvent.timestamp >= since
        )
    ).count()
    
    on_demand_hits = db.query(BotEvent).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.bot_type == "on_demand",
            BotEvent.timestamp >= since
        )
    ).count()
    
    verified_hits = db.query(BotEvent).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.verified == True,
            BotEvent.timestamp >= since
        )
    ).count()
    
    spoofed_hits = db.query(BotEvent).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.potential_spoof == True,
            BotEvent.timestamp >= since
        )
    ).count()
    
    # Aggregations
    by_provider = db.query(
        BotEvent.provider,
        func.count(BotEvent.id).label('count')
    ).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.is_bot == True,
            BotEvent.timestamp >= since
        )
    ).group_by(BotEvent.provider).all()
    
    by_type = db.query(
        BotEvent.bot_type,
        func.count(BotEvent.id).label('count')
    ).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.is_bot == True,
            BotEvent.timestamp >= since
        )
    ).group_by(BotEvent.bot_type).all()
    
    top_paths = db.query(
        BotEvent.path,
        func.count(BotEvent.id).label('count')
    ).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.timestamp >= since
        )
    ).group_by(BotEvent.path).order_by(func.count(BotEvent.id).desc()).limit(10).all()
    
    top_bots = db.query(
        BotEvent.bot_name,
        func.count(BotEvent.id).label('count')
    ).filter(
        and_(
            BotEvent.domain_id == domain.id,
            BotEvent.is_bot == True,
            BotEvent.timestamp >= since
        )
    ).group_by(BotEvent.bot_name).order_by(func.count(BotEvent.id).desc()).limit(10).all()
    
    return {
        "domain": domain_url,
        "time_range_hours": hours,
        "total_hits": total_hits,
        "bot_hits": bot_hits,
        "on_demand_hits": on_demand_hits,
        "verified_hits": verified_hits,
        "spoofed_hits": spoofed_hits,
        "bot_percentage": (bot_hits / max(1, total_hits)) * 100,
        "verification_rate": (verified_hits / max(1, bot_hits)) * 100,
        "spoof_rate": (spoofed_hits / max(1, bot_hits)) * 100,
        "by_provider": {item[0]: item[1] for item in by_provider},
        "by_type": {item[0]: item[1] for item in by_type},
        "top_paths": {item[0]: item[1] for item in top_paths},
        "top_bots": {item[0]: item[1] for item in top_bots}
    }

# Get recent events for a domain
@router.get("/monitor/events/{domain_url}")
async def get_domain_events(
    domain_url: str,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    bot_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get recent events for a specific domain"""
    
    # Get domain
    domain = db.query(Domain).filter(Domain.url == domain_url).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Build query
    query = db.query(BotEvent).filter(BotEvent.domain_id == domain.id)
    
    if bot_only:
        query = query.filter(BotEvent.is_bot == True)
    
    # Get events
    events = query.order_by(BotEvent.timestamp.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": event.id,
            "is_bot": event.is_bot,
            "bot_name": event.bot_name,
            "bot_type": event.bot_type,
            "provider": event.provider,
            "method": event.method,
            "path": event.path,
            "status": event.status,
            "user_agent": event.user_agent,
            "client_ip": event.client_ip,
            "verified": event.verified,
            "potential_spoof": event.potential_spoof,
            "timestamp": event.timestamp.isoformat()
        }
        for event in events
    ]

# Get all domains for a brand
@router.get("/monitor/brand/{brand_id}/domains")
async def get_brand_domains_stats(
    brand_id: int,
    db: Session = Depends(get_db)
):
    """Get all domains and their stats for a brand"""
    
    domains = db.query(Domain).filter(Domain.brand_id == brand_id).all()
    
    results = []
    for domain in domains:
        # Get quick stats for each domain
        bot_hits_24h = db.query(BotEvent).filter(
            and_(
                BotEvent.domain_id == domain.id,
                BotEvent.is_bot == True,
                BotEvent.timestamp >= datetime.utcnow() - timedelta(hours=24)
            )
        ).count()
        
        results.append({
            "id": domain.id,
            "url": domain.url,
            "is_trackable": domain.is_trackable,
            "technology": domain.technology,
            "total_bot_hits": domain.total_bot_hits,
            "bot_hits_24h": bot_hits_24h,
            "last_bot_hit": domain.last_bot_hit.isoformat() if domain.last_bot_hit else None
        })
    
    return results

# WebSocket endpoint for real-time monitoring of a specific domain
@router.websocket("/ws/monitor/{domain_url}")
async def websocket_monitor_domain(
    websocket: WebSocket,
    domain_url: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time monitoring of a specific domain"""
    
    # Verify domain exists
    domain = db.query(Domain).filter(Domain.url == domain_url).first()
    if not domain:
        await websocket.close(code=4004, reason="Domain not found")
        return
    
    await manager.connect(websocket, domain_url)
    
    # Send initial stats
    stats = await get_domain_stats(domain_url, 24, db)
    recent_events = await get_domain_events(domain_url, 50, 0, False, db)
    
    await websocket.send_json({
        "type": "initial",
        "stats": stats,
        "recent_events": recent_events
    })
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, domain_url)

# Background task to verify bot IP
async def verify_and_update_event(event_id: int, db: Session):
    """Background task to verify bot IP and update event"""
    event = db.query(BotEvent).filter(BotEvent.id == event_id).first()
    if not event:
        return
    
    # Verify IP
    if event.provider and event.client_ip:
        verified = await bot_detector.verify_bot_ip(event.provider, event.client_ip)
        event.verified = verified
        
        # Check for spoofing
        if not verified and event.is_bot:
            event.potential_spoof = True
            event.spoof_reason = f"IP {event.client_ip} not in {event.provider} ranges"
    
    db.commit()
    
    # Send update via WebSocket
    domain = db.query(Domain).filter(Domain.id == event.domain_id).first()
    if domain:
        await manager.send_to_domain({
            "type": "event_updated",
            "event_id": event.id,
            "verified": event.verified,
            "potential_spoof": event.potential_spoof
        }, domain.url)