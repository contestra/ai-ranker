"""
Real-time AI Bot Detection and Verification Service
"""

import json
import re
import ipaddress
import socket
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from datetime import datetime, timedelta
import asyncio

class BotDetector:
    def __init__(self):
        # Load bot registry
        registry_path = Path(__file__).parent.parent / "data" / "bot_registry.json"
        with open(registry_path, 'r') as f:
            self.registry = json.load(f)
        
        # Cache for IP ranges (refresh every hour)
        self.ip_cache = {}
        self.cache_timestamp = {}
        
        # Precompile regex patterns
        self.ua_patterns = {}
        for provider, bots in self.registry["bots"].items():
            for bot_key, bot_info in bots.items():
                pattern = bot_info.get("ua_pattern")
                if pattern:
                    self.ua_patterns[f"{provider}_{bot_key}"] = re.compile(pattern, re.IGNORECASE)
    
    def classify_bot(self, user_agent: str, client_ip: str = None) -> Dict[str, Any]:
        """
        Classify a user agent as a bot and determine its type
        Returns bot info including name, type, provider, and verification status
        """
        
        # Check against known bot patterns
        for key, pattern in self.ua_patterns.items():
            if pattern.search(user_agent):
                # Split at first underscore to handle multi-word bot names
                provider, bot_key = key.split('_', 1)
                bot_info = self.registry["bots"][provider][bot_key]
                
                result = {
                    "is_bot": True,
                    "provider": provider,
                    "bot_name": bot_info["name"],
                    "bot_type": bot_info["type"],  # indexing, on_demand, or training
                    "purpose": bot_info["purpose"],
                    "robots_token": bot_info.get("robots_token"),
                    "verified": False,
                    "verification_method": bot_info["verification"]["method"],
                    "user_agent": user_agent,
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Mark as requiring verification if IP provided
                if client_ip and bot_info["verification"]["method"] != "none":
                    result["requires_verification"] = True
                
                return result
        
        # Not a known bot
        return {
            "is_bot": False,
            "user_agent": user_agent,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def verify_bot_ip(self, provider: str, client_ip: str) -> bool:
        """
        Verify if the IP belongs to the claimed bot provider
        """
        if not client_ip:
            return False
        
        # Get verification method for this provider
        bots = self.registry["bots"].get(provider, {})
        if not bots:
            return False
        
        # Get first bot's verification method (they should all be the same per provider)
        first_bot = next(iter(bots.values()))
        method = first_bot["verification"]["method"]
        
        if method == "none":
            return True  # No verification available
        
        elif method == "ip_range":
            # Check against static IP ranges
            ranges = self.registry["ip_ranges"].get(provider, [])
            return self._check_ip_in_ranges(client_ip, ranges)
        
        elif method == "ip_json":
            # Fetch dynamic IP list from provider
            source_url = first_bot["verification"]["source"]
            ip_list = await self._fetch_ip_list(provider, source_url)
            return self._check_ip_in_list(client_ip, ip_list)
        
        elif method == "reverse_dns":
            # Verify via reverse DNS lookup
            domain = first_bot["verification"].get("domain")
            return self._verify_reverse_dns(client_ip, domain)
        
        return False
    
    def _check_ip_in_ranges(self, ip: str, ranges: List[str]) -> bool:
        """Check if IP is in any of the CIDR ranges"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for cidr in ranges:
                if ip_obj in ipaddress.ip_network(cidr):
                    return True
        except:
            pass
        return False
    
    def _check_ip_in_list(self, ip: str, ip_list: List[str]) -> bool:
        """Check if IP is in a list of IPs"""
        return ip in ip_list
    
    async def _fetch_ip_list(self, provider: str, url: str) -> List[str]:
        """Fetch IP list from provider's JSON endpoint with caching"""
        
        # Check cache
        cache_key = f"{provider}_ips"
        if cache_key in self.ip_cache:
            cache_time = self.cache_timestamp.get(cache_key)
            if cache_time and (datetime.utcnow() - cache_time) < timedelta(hours=1):
                return self.ip_cache[cache_key]
        
        # Fetch fresh data
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract IPs based on provider format
                    if provider == "perplexity":
                        # Perplexity format: {"ipv4": ["1.2.3.4", ...], "ipv6": [...]}
                        ips = data.get("ipv4", []) + data.get("ipv6", [])
                    else:
                        # Generic format - assume list of IPs
                        ips = data if isinstance(data, list) else []
                    
                    # Cache the result
                    self.ip_cache[cache_key] = ips
                    self.cache_timestamp[cache_key] = datetime.utcnow()
                    return ips
        except Exception as e:
            print(f"Error fetching IP list for {provider}: {e}")
        
        return []
    
    def _verify_reverse_dns(self, ip: str, expected_domain: str) -> bool:
        """Verify IP via reverse DNS lookup"""
        try:
            # Reverse DNS lookup
            hostname = socket.gethostbyaddr(ip)[0]
            
            # Forward DNS lookup to verify
            resolved_ips = socket.gethostbyname_ex(hostname)[2]
            
            # Check if the original IP is in the resolved IPs
            # and hostname matches expected domain
            if ip in resolved_ips and expected_domain in hostname:
                return True
        except:
            pass
        return False
    
    def detect_spoofing(self, bot_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential spoofing attempts
        """
        if not bot_info.get("is_bot"):
            return bot_info
        
        # If verification was required but failed
        if bot_info.get("requires_verification") and not bot_info.get("verified"):
            bot_info["potential_spoof"] = True
            bot_info["spoof_confidence"] = "high"
            bot_info["spoof_reason"] = f"User-Agent claims to be {bot_info['bot_name']} but IP {bot_info['client_ip']} is not verified"
        
        return bot_info
    
    def get_bot_summary(self) -> Dict[str, Any]:
        """Get summary of all known bots"""
        summary = {
            "total_bots": 0,
            "by_type": {"indexing": 0, "on_demand": 0, "training": 0},
            "by_provider": {},
            "providers": []
        }
        
        for provider, bots in self.registry["bots"].items():
            provider_info = {
                "name": provider,
                "bots": []
            }
            
            for bot_key, bot_info in bots.items():
                summary["total_bots"] += 1
                bot_type = bot_info["type"]
                summary["by_type"][bot_type] = summary["by_type"].get(bot_type, 0) + 1
                summary["by_provider"][provider] = summary["by_provider"].get(provider, 0) + 1
                
                provider_info["bots"].append({
                    "name": bot_info["name"],
                    "type": bot_type,
                    "purpose": bot_info["purpose"]
                })
            
            summary["providers"].append(provider_info)
        
        return summary

# Singleton instance
bot_detector = BotDetector()