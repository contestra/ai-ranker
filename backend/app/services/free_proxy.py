"""
Free proxy service using public proxy lists
No API key required - ideal for low-volume testing
"""

import httpx
import random
import asyncio
from typing import Optional, Dict, Any, List
import json

class FreeProxyService:
    """
    Uses free public proxies for country-specific requests
    Perfect for low-bandwidth API testing
    """
    
    # Free proxy API endpoints that don't require authentication
    PROXY_SOURCES = {
        'US': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=US&protocols=http%2Chttps',
            'https://www.proxy-list.download/api/v1/get?type=https&country=US'
        ],
        'GB': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=GB&protocols=http%2Chttps',
            'https://www.proxy-list.download/api/v1/get?type=https&country=GB'
        ],
        'DE': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=DE&protocols=http%2Chttps',
            'https://www.proxy-list.download/api/v1/get?type=https&country=DE'
        ],
        'CH': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=CH&protocols=http%2Chttps',
        ],
        'SG': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=SG&protocols=http%2Chttps',
        ],
        'AE': [
            'https://proxylist.geonode.com/api/proxy-list?limit=5&page=1&sort_by=lastChecked&sort_type=desc&country=AE&protocols=http%2Chttps',
        ]
    }
    
    def __init__(self):
        self.proxy_cache: Dict[str, List[str]] = {}
        self.last_fetch: Dict[str, float] = {}
        
    async def get_proxy_for_country(self, country_code: str) -> Optional[str]:
        """
        Get a working proxy for the specified country
        
        Args:
            country_code: Country code (US, GB, DE, etc.)
            
        Returns:
            Proxy URL or None if not available
        """
        
        # Check if we have cached proxies
        if country_code in self.proxy_cache and self.proxy_cache[country_code]:
            return random.choice(self.proxy_cache[country_code])
            
        # Fetch new proxies
        proxies = await self._fetch_proxies(country_code)
        if proxies:
            self.proxy_cache[country_code] = proxies
            return random.choice(proxies)
            
        return None
    
    async def _fetch_proxies(self, country_code: str) -> List[str]:
        """Fetch fresh proxy list for a country"""
        
        if country_code not in self.PROXY_SOURCES:
            # Default to US if country not supported
            country_code = 'US'
            
        proxies = []
        
        for source_url in self.PROXY_SOURCES[country_code]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(source_url, timeout=10.0)
                    
                    if 'geonode' in source_url:
                        # Parse GeoNode response
                        data = response.json()
                        for proxy in data.get('data', [])[:3]:  # Take top 3
                            proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
                            proxies.append(proxy_url)
                    else:
                        # Parse proxy-list.download response (plain text)
                        lines = response.text.strip().split('\n')
                        for line in lines[:3]:  # Take top 3
                            if ':' in line:
                                proxy_url = f"http://{line.strip()}"
                                proxies.append(proxy_url)
                                
            except Exception as e:
                print(f"Failed to fetch from {source_url}: {e}")
                continue
                
        return proxies
    
    async def make_proxied_request(
        self,
        url: str,
        country_code: str,
        method: str = "POST",
        headers: Dict[str, str] = None,
        data: Dict[str, Any] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request through a country-specific proxy
        
        Args:
            url: Target URL
            country_code: Country to route through
            method: HTTP method
            headers: Request headers
            data: Request body
            max_retries: Number of retries if proxy fails
            
        Returns:
            Response data or None if all proxies fail
        """
        
        for attempt in range(max_retries):
            proxy = await self.get_proxy_for_country(country_code)
            
            if not proxy:
                # No proxy available, make direct request
                print(f"No proxy available for {country_code}, using direct connection")
                return await self._direct_request(url, method, headers, data)
                
            try:
                proxies = {"http://": proxy, "https://": proxy}
                
                async with httpx.AsyncClient(proxies=proxies) as client:
                    if method == "POST":
                        response = await client.post(
                            url,
                            headers=headers,
                            json=data,
                            timeout=30.0
                        )
                    else:
                        response = await client.get(
                            url,
                            headers=headers,
                            timeout=30.0
                        )
                        
                    return response.json()
                    
            except Exception as e:
                print(f"Proxy {proxy} failed: {e}")
                # Remove failed proxy from cache
                if country_code in self.proxy_cache and proxy in self.proxy_cache[country_code]:
                    self.proxy_cache[country_code].remove(proxy)
                continue
                
        # All proxies failed, use direct connection
        return await self._direct_request(url, method, headers, data)
    
    async def _direct_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback to direct request"""
        
        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=90.0
                )
            else:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=90.0
                )
                
            return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current proxy service status"""
        return {
            "type": "Free Public Proxies",
            "supported_countries": list(self.PROXY_SOURCES.keys()),
            "cached_proxies": {
                country: len(proxies) 
                for country, proxies in self.proxy_cache.items()
            },
            "note": "Free proxies may be unreliable, will fallback to direct connection if needed"
        }