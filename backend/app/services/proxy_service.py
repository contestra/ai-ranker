"""
Proxy service for geo-located API requests
Supports multiple free/low-cost proxy providers
"""

import httpx
import json
from typing import Optional, Dict, Any
from app.config import settings

class ProxyService:
    """Handle geo-located requests through proxy services"""
    
    # Country code mapping for proxy services
    COUNTRY_MAPPING = {
        'US': 'us',
        'GB': 'gb',
        'DE': 'de', 
        'CH': 'ch',
        'AE': 'ae',
        'SG': 'sg',
        'FR': 'fr',
        'CA': 'ca',
        'AU': 'au',
        'JP': 'jp'
    }
    
    def __init__(self):
        self.scraperapi_key = settings.scraperapi_key
        self.proxy_enabled = settings.proxy_enabled
        
    async def make_request_with_proxy(
        self, 
        url: str,
        method: str = "POST",
        headers: Dict[str, str] = None,
        data: Dict[str, Any] = None,
        country_code: str = "US"
    ) -> Dict[str, Any]:
        """
        Make an API request through a proxy service from a specific country
        
        Args:
            url: Target API endpoint
            method: HTTP method
            headers: Request headers
            data: Request body
            country_code: Country to route request through
            
        Returns:
            API response
        """
        
        # If proxy is disabled or no API key, make direct request
        if not self.proxy_enabled or not self.scraperapi_key:
            return await self._direct_request(url, method, headers, data)
            
        # Map country code
        country = self.COUNTRY_MAPPING.get(country_code, 'us')
        
        # Option 1: ScraperAPI (1000 free requests/month)
        if self.scraperapi_key:
            return await self._scraperapi_request(url, method, headers, data, country)
            
        # Fallback to direct request
        return await self._direct_request(url, method, headers, data)
    
    async def _scraperapi_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
        country: str
    ) -> Dict[str, Any]:
        """Make request through ScraperAPI with country selection"""
        
        # ScraperAPI endpoint
        proxy_url = "http://api.scraperapi.com"
        
        # Build params
        params = {
            'api_key': self.scraperapi_key,
            'url': url,
            'country_code': country,
            'keep_headers': 'true'  # Preserve our headers
        }
        
        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(
                    proxy_url,
                    params=params,
                    headers=headers,
                    json=data,
                    timeout=120.0  # Longer timeout for proxy
                )
            else:
                response = await client.get(
                    proxy_url,
                    params=params,
                    headers=headers,
                    timeout=120.0
                )
                
            return response.json()
    
    async def _direct_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make direct request without proxy"""
        
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
    
    def get_proxy_status(self) -> Dict[str, Any]:
        """Get current proxy configuration status"""
        return {
            "enabled": self.proxy_enabled,
            "provider": "ScraperAPI" if self.scraperapi_key else None,
            "supported_countries": list(self.COUNTRY_MAPPING.keys()),
            "free_tier": "1000 requests/month" if self.scraperapi_key else None
        }


# Alternative free proxy services to consider:

class AlternativeProxies:
    """
    Documentation of alternative free/cheap proxy services
    """
    
    @staticmethod
    def proxyscrape_setup():
        """
        ProxyScrape: 1000 free API requests/month
        Sign up at: https://proxyscrape.com/free-proxy-api
        
        Usage:
        GET https://api.proxyscrape.com/v2/?request=get&protocol=http&country={country}&format=json
        """
        pass
    
    @staticmethod
    def proxycrawl_setup():
        """
        Crawlbase (formerly ProxyCrawl): 1000 free credits
        Sign up at: https://crawlbase.com/
        
        Usage:
        GET https://api.crawlbase.com/?token=YOUR_TOKEN&url={url}&country={country}
        """
        pass
    
    @staticmethod
    def free_proxy_list():
        """
        Free Proxy Lists (no signup required but less reliable)
        - https://www.proxy-list.download/api/v1/get?type=http&country={country}
        - https://proxylist.geonode.com/api/proxy-list?country={country}&limit=1&page=1&sort_by=lastChecked&sort_type=desc
        
        Note: These are less reliable but completely free
        """
        pass