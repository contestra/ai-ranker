"""
Evidence Pack Builder for Geographic Testing
Builds country-specific context using search results to replicate consumer app behavior
"""

import asyncio
import httpx
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import os
from app.config import settings

class EvidencePackBuilder:
    """
    Builds minimal evidence packs for country-specific testing.
    Uses 3-5 short snippets from local sources to provide light-touch context.
    """
    
    # Country-specific search parameters
    COUNTRY_PARAMS = {
        'US': {
            'google': {'gl': 'us', 'hl': 'en', 'lr': 'lang_en'},
            'bing': {'mkt': 'en-US'},
            'domains': ['.com', '.gov', '.org'],
            'language': 'en'
        },
        'GB': {
            'google': {'gl': 'uk', 'hl': 'en', 'lr': 'lang_en'},
            'bing': {'mkt': 'en-GB'},
            'domains': ['.co.uk', '.gov.uk', '.nhs.uk'],
            'language': 'en'
        },
        'DE': {
            'google': {'gl': 'de', 'hl': 'de', 'lr': 'lang_de'},
            'bing': {'mkt': 'de-DE'},
            'domains': ['.de', '.com.de'],
            'language': 'de'
        },
        'CH': {
            'google': {'gl': 'ch', 'hl': 'de', 'lr': 'lang_de'},
            'bing': {'mkt': 'de-CH'},
            'domains': ['.ch', '.swiss'],
            'language': 'de'  # Could also be fr, it depending on region
        },
        'AE': {
            'google': {'gl': 'ae', 'hl': 'en', 'lr': 'lang_en|lang_ar'},
            'bing': {'mkt': 'en-AE'},
            'domains': ['.ae', '.gov.ae'],
            'language': 'en'  # or 'ar'
        },
        'SG': {
            'google': {'gl': 'sg', 'hl': 'en', 'lr': 'lang_en'},
            'bing': {'mkt': 'en-SG'},
            'domains': ['.sg', '.gov.sg', '.com.sg'],
            'language': 'en'
        }
    }
    
    # Source type priorities for diverse evidence
    SOURCE_PRIORITIES = [
        'government',    # Health authorities, regulatory bodies
        'retail',        # Major retailers, pharmacies
        'news',          # Established news outlets
        'medical',       # Hospitals, clinics, research
        'industry'       # Trade publications, industry sites
    ]
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'google_search_api_key', None)
        self.google_cx = getattr(settings, 'google_search_cx', None)
        self.bing_api_key = getattr(settings, 'bing_search_api_key', None)
        self.exa_api_key = getattr(settings, 'exa_api_key', None)
        
    async def build_evidence_pack(
        self, 
        query: str, 
        country: str,
        max_snippets: int = 5,
        max_tokens: int = 600
    ) -> str:
        """
        Build a minimal evidence pack for country-specific context.
        
        Args:
            query: The search query (e.g., "longevity supplements")
            country: Country code (US, GB, DE, CH, AE, SG)
            max_snippets: Maximum number of snippets (default 5)
            max_tokens: Maximum token count (default 600)
            
        Returns:
            Formatted evidence pack as a string
        """
        
        if country not in self.COUNTRY_PARAMS:
            return ""  # No evidence for unsupported countries
        
        # Get search results
        search_results = await self._search_with_country_params(query, country)
        
        if not search_results:
            return ""
        
        # Filter and format snippets
        evidence_pack = self._format_evidence_pack(
            search_results, 
            country, 
            max_snippets,
            max_tokens
        )
        
        return evidence_pack
    
    async def _search_with_country_params(
        self, 
        query: str, 
        country: str
    ) -> List[Dict]:
        """
        Search using country-specific parameters.
        Falls back to mock data if API keys not configured.
        """
        
        params = self.COUNTRY_PARAMS[country]
        
        # Try Exa.ai first (best for semantic search and cheapest)
        if self.exa_api_key:
            try:
                return await self._exa_search(query, country, params)
            except Exception as e:
                print(f"Exa search failed: {e}")
        
        # Try Google Custom Search API second
        if self.google_api_key and self.google_cx:
            try:
                return await self._google_search(query, params['google'])
            except Exception as e:
                print(f"Google search failed: {e}")
        
        # Try Bing Search API as fallback
        if self.bing_api_key:
            try:
                return await self._bing_search(query, params['bing'])
            except Exception as e:
                print(f"Bing search failed: {e}")
        
        # Fallback to mock data for testing
        return self._get_mock_results(query, country)
    
    async def _exa_search(self, query: str, country: str, params: Dict) -> List[Dict]:
        """Execute Exa.ai search with country filters to get LOCAL results."""
        async with httpx.AsyncClient() as client:
            # Get country-specific domains to search
            country_domains = {
                'CH': ['.ch', '.swiss', 'migros.ch', 'coop.ch', 'nzz.ch'],
                'US': ['.com', '.gov', '.org', 'cvs.com', 'walgreens.com'],
                'GB': ['.co.uk', '.gov.uk', 'boots.com', 'bbc.co.uk'],
                'DE': ['.de', 'dm.de', 'rossmann.de', 'spiegel.de'],
                'AE': ['.ae', '.gov.ae', 'gulfnews.com'],
                'SG': ['.sg', '.com.sg', 'straitstimes.com']
            }
            
            # Use domains to get LOCAL results (what users in that country would see)
            include_domains = country_domains.get(country, None)
            
            # Just use the query as-is - no country names, no filtering
            # We want organic results from that location
            response = await client.post(
                'https://api.exa.ai/search',
                headers={'x-api-key': self.exa_api_key},
                json={
                    'query': query,  # Clean query, no modifications
                    'num_results': 10,
                    'include_domains': include_domains,  # Get results from local domains
                    'use_autoprompt': True,  # Let Exa optimize
                    'type': 'auto',  # Let Exa choose best type
                    'contents': {
                        'text': True,
                        'highlights': True
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = self._parse_exa_results(data)
                
                # Return whatever we get - NO FILTERING
                # Real users see all kinds of results
                if len(results) >= 3:
                    return results[:5]  # Just take top 5
                else:
                    # Fall back to mock data if we get too few results
                    print(f"Exa returned too few results for {country}, using mock data")
                    return self._get_mock_results(query, country)
                    
            else:
                raise Exception(f"Exa API error: {response.status_code}")
    
    def _parse_exa_results(self, data: Dict) -> List[Dict]:
        """Parse Exa search results."""
        results = []
        for item in data.get('results', []):
            # Use highlights if available, otherwise use text snippet
            snippet = ''
            if item.get('highlights'):
                snippet = ' '.join(item['highlights'][:2])  # Use first 2 highlights
            elif item.get('text'):
                snippet = item['text'][:300]
            
            results.append({
                'title': item.get('title', ''),
                'snippet': snippet,
                'url': item.get('url', ''),
                'domain': self._extract_domain(item.get('url', '')),
                'date': item.get('published_date', 'current')
            })
        return results
    
    async def _google_search(self, query: str, params: Dict) -> List[Dict]:
        """Execute Google Custom Search API request."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://www.googleapis.com/customsearch/v1',
                params={
                    'key': self.google_api_key,
                    'cx': self.google_cx,
                    'q': query,
                    'num': 10,
                    **params
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_google_results(data)
            else:
                raise Exception(f"Google API error: {response.status_code}")
    
    async def _bing_search(self, query: str, params: Dict) -> List[Dict]:
        """Execute Bing Search API request."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://api.bing.microsoft.com/v7.0/search',
                headers={'Ocp-Apim-Subscription-Key': self.bing_api_key},
                params={
                    'q': query,
                    'count': 10,
                    **params
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_bing_results(data)
            else:
                raise Exception(f"Bing API error: {response.status_code}")
    
    def _parse_google_results(self, data: Dict) -> List[Dict]:
        """Parse Google search results."""
        results = []
        for item in data.get('items', []):
            results.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('link', ''),
                'domain': self._extract_domain(item.get('link', '')),
                'date': self._extract_date(item)
            })
        return results
    
    def _parse_bing_results(self, data: Dict) -> List[Dict]:
        """Parse Bing search results."""
        results = []
        for item in data.get('webPages', {}).get('value', []):
            results.append({
                'title': item.get('name', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('url', ''),
                'domain': self._extract_domain(item.get('url', '')),
                'date': item.get('dateLastCrawled', '').split('T')[0] if item.get('dateLastCrawled') else None
            })
        return results
    
    def _get_mock_results(self, query: str, country: str) -> List[Dict]:
        """
        Generate mock results for testing without API keys.
        Returns country-specific mock data.
        """
        
        # Mock data by country
        mock_data = {
            'CH': [
                {
                    'title': 'Longevity Supplements Guide - Swiss Federal Office',
                    'snippet': 'Swiss regulations require NAD+ supplements to be registered with Swissmedic. Vitamin D supplementation recommended during winter months.',
                    'domain': 'bag.admin.ch',
                    'date': '2025-03'
                },
                {
                    'title': 'Anti-Aging Products - Migros',
                    'snippet': 'Bestselling longevity supplements starting at CHF 89.90, including resveratrol and spermidine from Swiss suppliers.',
                    'domain': 'migros.ch',
                    'date': 'current'
                },
                {
                    'title': 'NZZ Health Section - Longevity Market',
                    'snippet': 'Swiss consumers increasingly turn to NMN and quercetin supplements, with market growing 35% annually according to latest research.',
                    'domain': 'nzz.ch',
                    'date': '2025-01'
                }
            ],
            'US': [
                {
                    'title': 'FDA Guidance on Anti-Aging Supplements',
                    'snippet': 'FDA does not approve dietary supplements for anti-aging. Consumers should consult healthcare providers before use.',
                    'domain': 'fda.gov',
                    'date': '2024-12'
                },
                {
                    'title': 'Top Longevity Supplements - CVS Pharmacy',
                    'snippet': 'Popular longevity supplements from $29.99. NAD+ boosters, resveratrol, and CoQ10 available online and in stores.',
                    'domain': 'cvs.com',
                    'date': 'current'
                }
            ],
            'DE': [
                {
                    'title': 'Langlebigkeits-Ergänzungen - Apotheken Umschau',
                    'snippet': 'NMN und NAD+ Booster werden in deutschen Apotheken immer beliebter. Preise ab 45 Euro pro Monat.',
                    'domain': 'apotheken-umschau.de',
                    'date': '2025-02'
                }
            ]
        }
        
        # Return country-specific mock data or generic if not available
        return mock_data.get(country, [
            {
                'title': f'Health Supplements in {country}',
                'snippet': f'Local market for longevity supplements growing. Check with local health authorities for regulations.',
                'domain': f'health.{country.lower()}',
                'date': '2025-01'
            }
        ])
    
    def _format_evidence_pack(
        self, 
        results: List[Dict], 
        country: str,
        max_snippets: int,
        max_tokens: int
    ) -> str:
        """
        Format search results into a minimal evidence pack.
        
        Returns formatted string with 3-5 short, neutral snippets.
        """
        
        if not results:
            return ""
        
        # Deduplicate by domain
        seen_domains = set()
        unique_results = []
        
        for result in results:
            domain = result['domain']
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_results.append(result)
                
                if len(unique_results) >= max_snippets:
                    break
        
        # Format as search results (more natural presentation)
        evidence_lines = []
        evidence_lines.append("Recent information from web searches:")
        evidence_lines.append("")  # blank line
        
        for i, result in enumerate(unique_results, 1):
            # Truncate snippet to ~220 chars (about 1-2 lines)
            snippet = result['snippet'][:220].strip()
            if len(result['snippet']) > 220:
                snippet = snippet.rsplit(' ', 1)[0] + '...'
            
            # More natural format without explicit location hints
            evidence_lines.append(f"{i}. {snippet}")
            evidence_lines.append(f"   Source: {result['domain']}")
            evidence_lines.append("")  # blank line between entries
        
        # Join with newlines
        evidence_pack = '\n'.join(evidence_lines)
        
        # Rough token estimation (1 token ≈ 4 chars)
        estimated_tokens = len(evidence_pack) // 4
        
        # Trim if exceeds token limit
        if estimated_tokens > max_tokens:
            # Remove last items until under limit
            while evidence_lines and estimated_tokens > max_tokens:
                evidence_lines.pop()
                evidence_pack = '\n'.join(evidence_lines)
                estimated_tokens = len(evidence_pack) // 4
        
        return evidence_pack
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain
        except:
            return 'unknown'
    
    def _extract_date(self, item: Dict) -> Optional[str]:
        """Extract date from search result if available."""
        # Try various date fields
        for field in ['datePublished', 'dateModified', 'dateCreated']:
            if field in item:
                date_str = item[field]
                try:
                    # Parse and format date
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    return date_str[:7]  # Return YYYY-MM format
                except:
                    pass
        return None
    
    def classify_source_type(self, domain: str) -> str:
        """
        Classify the source type based on domain.
        Used for ensuring diverse source types in evidence pack.
        """
        
        domain_lower = domain.lower()
        
        # Government/regulatory
        if any(gov in domain_lower for gov in ['.gov', '.admin.', 'federal', 'ministry']):
            return 'government'
        
        # Medical/health
        if any(med in domain_lower for med in ['hospital', 'clinic', 'medical', 'health', '.nhs.']):
            return 'medical'
        
        # Retail/pharmacy
        if any(retail in domain_lower for retail in ['pharmacy', 'apotheke', 'migros', 'coop', 'cvs', 'walgreens', 'boots']):
            return 'retail'
        
        # News
        if any(news in domain_lower for news in ['news', 'times', 'post', 'guardian', 'nzz', 'bbc', 'cnn']):
            return 'news'
        
        # Default to industry
        return 'industry'


# Singleton instance
evidence_pack_builder = EvidencePackBuilder()