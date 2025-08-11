"""
Real-time AI Crawler Monitoring API
Ingests logs from edge providers and provides live monitoring
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import asyncio
from collections import deque, defaultdict

from app.services.bot_detector import bot_detector

router = APIRouter()

# In-memory storage for live monitoring (replace with Redis/DB in production)
class LiveMonitor:
    def __init__(self):
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.websocket_clients = []
        self.stats = {
            "total_hits": 0,
            "bot_hits": 0,
            "on_demand_hits": 0,
            "verified_hits": 0,
            "spoofed_hits": 0,
            "by_provider": defaultdict(int),
            "by_type": defaultdict(int),
            "last_hour": deque(maxlen=3600),  # Per-second counts
            "top_paths": defaultdict(int),
            "top_bots": defaultdict(int)
        }
    
    async def add_event(self, event: Dict[str, Any]):
        """Add event and broadcast to WebSocket clients"""
        self.events.append(event)
        
        # Update stats
        self.stats["total_hits"] += 1
        if event.get("is_bot"):
            self.stats["bot_hits"] += 1
            self.stats["by_provider"][event.get("provider", "unknown")] += 1
            self.stats["by_type"][event.get("bot_type", "unknown")] += 1
            self.stats["top_bots"][event.get("bot_name", "unknown")] += 1
            
            if event.get("bot_type") == "on_demand":
                self.stats["on_demand_hits"] += 1
            if event.get("verified"):
                self.stats["verified_hits"] += 1
            if event.get("potential_spoof"):
                self.stats["spoofed_hits"] += 1
        
        self.stats["top_paths"][event.get("path", "/")] += 1
        
        # Broadcast to WebSocket clients
        await self.broadcast(event)
    
    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast event to all connected WebSocket clients"""
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send_json(event)
            except:
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            if client in self.websocket_clients:
                self.websocket_clients.remove(client)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            "total_hits": self.stats["total_hits"],
            "bot_hits": self.stats["bot_hits"],
            "on_demand_hits": self.stats["on_demand_hits"],
            "verified_hits": self.stats["verified_hits"],
            "spoofed_hits": self.stats["spoofed_hits"],
            "bot_percentage": (self.stats["bot_hits"] / max(1, self.stats["total_hits"])) * 100,
            "verification_rate": (self.stats["verified_hits"] / max(1, self.stats["bot_hits"])) * 100,
            "spoof_rate": (self.stats["spoofed_hits"] / max(1, self.stats["bot_hits"])) * 100,
            "by_provider": dict(self.stats["by_provider"]),
            "by_type": dict(self.stats["by_type"]),
            "top_paths": dict(sorted(self.stats["top_paths"].items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_bots": dict(sorted(self.stats["top_bots"].items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events"""
        return list(self.events)[-limit:]

# Global monitor instance
monitor = LiveMonitor()

# Request models
class CloudflareLogRequest(BaseModel):
    timestamp: str
    method: str
    path: str
    status: int
    user_agent: str
    client_ip: str
    country: Optional[str] = None
    colo: Optional[str] = None
    cache_status: Optional[str] = None
    bytes: Optional[int] = None
    referrer: Optional[str] = None

class VercelLogRequest(BaseModel):
    timestamp: str
    method: str
    path: str
    status: int
    user_agent: str
    client_ip: str
    region: Optional[str] = None
    duration: Optional[int] = None
    bytes: Optional[int] = None

class GenericLogRequest(BaseModel):
    timestamp: str
    method: str
    path: str
    status: int
    user_agent: str
    client_ip: str
    provider: Optional[str] = "unknown"
    metadata: Optional[Dict[str, Any]] = {}

# Ingestion endpoints
@router.post("/ingest/cloudflare")
async def ingest_cloudflare(request: CloudflareLogRequest, background_tasks: BackgroundTasks):
    """Ingest log from Cloudflare"""
    
    # Detect and classify bot
    bot_info = bot_detector.classify_bot(request.user_agent, request.client_ip)
    
    # Build event
    event = {
        **bot_info,
        "provider_type": "cloudflare",
        "method": request.method,
        "path": request.path,
        "status": request.status,
        "country": request.country,
        "colo": request.colo,
        "cache_status": request.cache_status,
        "bytes": request.bytes,
        "referrer": request.referrer,
        "raw_timestamp": request.timestamp
    }
    
    # Verify bot IP if needed
    if bot_info.get("requires_verification"):
        background_tasks.add_task(verify_and_update_event, event)
    else:
        await monitor.add_event(event)
    
    return {"status": "accepted", "is_bot": bot_info.get("is_bot", False)}

@router.post("/ingest/vercel")
async def ingest_vercel(request: VercelLogRequest, background_tasks: BackgroundTasks):
    """Ingest log from Vercel"""
    
    bot_info = bot_detector.classify_bot(request.user_agent, request.client_ip)
    
    event = {
        **bot_info,
        "provider_type": "vercel",
        "method": request.method,
        "path": request.path,
        "status": request.status,
        "region": request.region,
        "duration": request.duration,
        "bytes": request.bytes,
        "raw_timestamp": request.timestamp
    }
    
    if bot_info.get("requires_verification"):
        background_tasks.add_task(verify_and_update_event, event)
    else:
        await monitor.add_event(event)
    
    return {"status": "accepted", "is_bot": bot_info.get("is_bot", False)}

@router.post("/ingest/generic")
async def ingest_generic(request: GenericLogRequest, background_tasks: BackgroundTasks):
    """Generic ingestion endpoint for any provider"""
    
    bot_info = bot_detector.classify_bot(request.user_agent, request.client_ip)
    
    event = {
        **bot_info,
        "provider_type": request.provider,
        "method": request.method,
        "path": request.path,
        "status": request.status,
        "metadata": request.metadata,
        "raw_timestamp": request.timestamp
    }
    
    if bot_info.get("requires_verification"):
        background_tasks.add_task(verify_and_update_event, event)
    else:
        await monitor.add_event(event)
    
    return {"status": "accepted", "is_bot": bot_info.get("is_bot", False)}

async def verify_and_update_event(event: Dict[str, Any]):
    """Background task to verify bot IP and update event"""
    provider = event.get("provider")
    client_ip = event.get("client_ip")
    
    if provider and client_ip:
        verified = await bot_detector.verify_bot_ip(provider, client_ip)
        event["verified"] = verified
        
        # Check for spoofing
        event = bot_detector.detect_spoofing(event)
    
    await monitor.add_event(event)

# Monitoring endpoints
@router.get("/monitor/stats")
async def get_stats():
    """Get current monitoring statistics"""
    return monitor.get_stats()

@router.get("/monitor/events")
async def get_events(limit: int = 100):
    """Get recent events"""
    return monitor.get_recent_events(limit)

@router.get("/monitor/bots")
async def get_bot_info():
    """Get information about known bots"""
    return bot_detector.get_bot_summary()

# WebSocket endpoint for live monitoring
@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring"""
    await websocket.accept()
    monitor.websocket_clients.append(websocket)
    
    # Send initial stats
    await websocket.send_json({
        "type": "initial",
        "stats": monitor.get_stats(),
        "recent_events": monitor.get_recent_events(50)
    })
    
    try:
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        monitor.websocket_clients.remove(websocket)

# Attribution tracking
@router.post("/attribution/track")
async def track_attribution(
    session_id: str,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    referrer: Optional[str] = None
):
    """Track AI-driven traffic attribution"""
    
    # Check for AI attribution
    ai_source = None
    if utm_source == "chatgpt.com":
        ai_source = "chatgpt"
    elif utm_source and "perplexity" in utm_source.lower():
        ai_source = "perplexity"
    elif referrer and "claude.ai" in referrer:
        ai_source = "claude"
    elif referrer and "you.com" in referrer:
        ai_source = "you.com"
    
    if ai_source:
        # Store attribution (in production, save to database)
        attribution = {
            "session_id": session_id,
            "ai_source": ai_source,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "referrer": referrer,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to monitor
        await monitor.add_event({
            "type": "attribution",
            "ai_source": ai_source,
            **attribution
        })
        
        return {"attributed": True, "ai_source": ai_source}
    
    return {"attributed": False}