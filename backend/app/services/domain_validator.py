"""
Domain validation and technology detection service
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import re

class DomainValidator:
    """Validates domains and detects their technology stack"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Ranker-Validator/1.0)'
        }
        
        # Technology signatures - order matters! Check Shopify before WordPress
        self.tech_signatures = {
            'shopify': {
                'headers': ['X-Shopify-Stage', 'X-ShopId'],
                'html': ['cdn.shopify.com', 'myshopify.com', 'Shopify.theme', 'Shopify.shop'],
                'message': 'Shopify platform detected - cannot track server-side'
            },
            'wordpress': {
                'headers': [],  # Don't rely on PHP header as many sites use PHP
                'html': ['wp-content/', 'wp-includes/', '/wp-json/'],  # More specific paths
                'message': 'WordPress detected - compatible with plugin'
            },
            'wix': {
                'html': ['wix.com', 'static.wixstatic.com'],
                'message': 'Wix platform detected - cannot track server-side'
            },
            'squarespace': {
                'html': ['squarespace.com', 'sqsp.net'],
                'message': 'Squarespace detected - cannot track server-side'
            },
            'webflow': {
                'html': ['webflow.com', 'assets-global.website-files.com'],
                'message': 'Webflow detected - limited tracking options'
            },
            'vercel': {
                'headers': ['X-Vercel-Id'],
                'message': 'Vercel deployment - can use log drains'
            },
            'netlify': {
                'headers': ['X-Nf-Request-Id'],
                'message': 'Netlify deployment - can use log drains'
            },
            'cloudflare': {
                'headers': ['CF-Ray', 'CF-Cache-Status'],
                'message': 'Cloudflare CDN detected - can use Workers if you control it'
            }
        }
        
        # Platforms that can't be tracked
        self.untrackable_platforms = ['shopify', 'wix', 'squarespace', 'wordpress.com']
    
    def normalize_domain(self, domain: str) -> str:
        """Normalize domain input (remove https://, trailing slash, etc.)"""
        # Remove protocol if present
        domain = re.sub(r'^https?://', '', domain)
        # Remove www. if present
        domain = re.sub(r'^www\.', '', domain)
        # Remove trailing slash
        domain = domain.rstrip('/')
        return domain.lower()
    
    def extract_subdomain(self, domain: str) -> Tuple[str, str]:
        """Extract subdomain and main domain"""
        parts = domain.split('.')
        if len(parts) > 2:
            # Has subdomain
            subdomain = '.'.join(parts[:-2])
            main_domain = '.'.join(parts[-2:])
            return subdomain, main_domain
        return '', domain
    
    async def detect_technology(self, domain: str) -> Dict[str, Any]:
        """Detect the technology stack of a domain"""
        url = f"https://{domain}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=10.0, follow_redirects=True)
                
                # Check headers
                headers = dict(response.headers)
                html = response.text[:50000]  # First 50KB
                
                detected_tech = []
                is_trackable = True
                tracking_methods = []
                messages = []
                
                # First check for actual Shopify store (not just CDN references)
                # Look for multiple Shopify indicators, not just one CDN reference
                shopify_indicators = sum([
                    'myshopify.com' in html.lower(),
                    'shopify.theme' in html.lower(),
                    'shopify.shop' in html.lower(), 
                    'shopify-assets' in html.lower(),
                    '/cdn/shop/' in html.lower(),  # Shopify CDN path pattern
                    html.lower().count('cdn.shopify.com') > 3,  # Multiple CDN references, not just one image
                    'x-shopify-stage' in [h.lower() for h in headers.keys()],
                    'x-shopid' in [h.lower() for h in headers.keys()],
                    headers.get('powered-by', '').lower() == 'shopify'
                ])
                
                # Debug logging
                if domain == "avea-life.com":
                    print(f"Debug Shopify detection for {domain}:")
                    print(f"  Headers: x-shopid={('x-shopid' in [h.lower() for h in headers.keys()])}, powered-by={headers.get('powered-by', '')}")
                    print(f"  Shopify indicators: {shopify_indicators}")
                
                # Check Shopify headers FIRST (most definitive)
                if ('x-shopid' in [h.lower() for h in headers.keys()] or 
                    headers.get('powered-by', '').lower() == 'shopify' or
                    shopify_indicators >= 2):
                    detected_tech.append('shopify')
                    messages.append(self.tech_signatures['shopify']['message'])
                    is_trackable = False
                
                # Check for WordPress (only if NOT Shopify)
                elif any(pattern in html.lower() for pattern in ['wp-content/', 'wp-includes/', '/wp-json/']):
                    detected_tech.append('wordpress')
                    messages.append(self.tech_signatures['wordpress']['message'])
                    tracking_methods.append('wordpress_plugin')
                    is_trackable = True
                
                # Check other platforms
                else:
                    for tech, signatures in self.tech_signatures.items():
                        if tech in ['shopify', 'wordpress']:  # Already checked
                            continue
                            
                        detected = False
                        
                        # Check headers
                        if 'headers' in signatures and signatures['headers']:
                            for header in signatures['headers']:
                                if ':' in header:
                                    # Check header value
                                    h_name, h_value = header.split(':', 1)
                                    if headers.get(h_name, '').strip().startswith(h_value.strip()):
                                        detected = True
                                        break
                                else:
                                    # Just check if header exists
                                    if header in headers:
                                        detected = True
                                        break
                        
                        # Check HTML content
                        if not detected and 'html' in signatures:
                            for pattern in signatures['html']:
                                if pattern.lower() in html.lower():
                                    detected = True
                                    break
                        
                        if detected:
                            detected_tech.append(tech)
                            messages.append(signatures['message'])
                            
                            # Check if platform is untrackable
                            if tech in self.untrackable_platforms:
                                is_trackable = False
                            else:
                                # Add appropriate tracking method
                                if tech == 'vercel':
                                    tracking_methods.append('vercel_logs')
                                elif tech == 'netlify':
                                    tracking_methods.append('netlify_logs')
                                elif tech == 'cloudflare':
                                    tracking_methods.append('cloudflare_workers')
                
                # Check for WordPress.com specifically (untrackable)
                if 'wordpress.com' in html.lower():
                    is_trackable = False
                    detected_tech.append('wordpress.com')
                    messages.append('WordPress.com hosted - cannot install plugins')
                
                # If no specific tech detected, it's likely custom
                if not detected_tech:
                    detected_tech.append('custom')
                    tracking_methods.append('direct_integration')
                    messages.append('Custom platform - various tracking options available')
                
                return {
                    'success': True,
                    'domain': domain,
                    'url': url,
                    'is_trackable': is_trackable,
                    'technology': detected_tech,
                    'tracking_methods': tracking_methods,
                    'messages': messages,
                    'status_code': response.status_code,
                    'server': headers.get('Server', 'Unknown'),
                    'cdn': 'cloudflare' if 'CF-Ray' in headers else None
                }
                
        except httpx.ConnectError:
            return {
                'success': False,
                'domain': domain,
                'error': 'Could not connect to domain',
                'is_trackable': False
            }
        except httpx.TimeoutException:
            return {
                'success': False,
                'domain': domain,
                'error': 'Domain request timed out',
                'is_trackable': False
            }
        except Exception as e:
            return {
                'success': False,
                'domain': domain,
                'error': str(e),
                'is_trackable': False
            }
    
    async def validate_domain(self, domain: str) -> Dict[str, Any]:
        """Full domain validation with technology detection"""
        # Normalize the domain
        normalized = self.normalize_domain(domain)
        subdomain, main_domain = self.extract_subdomain(normalized)
        
        # Detect technology
        tech_result = await self.detect_technology(normalized)
        
        # Build validation result
        result = {
            'domain': normalized,
            'subdomain': subdomain,
            'main_domain': main_domain,
            'full_url': f"https://{normalized}",
            **tech_result
        }
        
        # Add recommendations
        if result.get('is_trackable'):
            if 'wordpress' in result.get('technology', []):
                result['recommendation'] = 'Install the AI Crawler Monitor WordPress plugin'
            elif 'cloudflare' in result.get('technology', []):
                result['recommendation'] = 'Set up Cloudflare Worker or use WordPress plugin if applicable'
            elif 'vercel' in result.get('technology', []):
                result['recommendation'] = 'Configure Vercel log drains'
            else:
                result['recommendation'] = 'Contact support for integration options'
        else:
            result['recommendation'] = 'Consider using a trackable subdomain (e.g., blog.yourdomain.com on WordPress)'
        
        return result
    
    async def validate_multiple(self, domains: list[str]) -> list[Dict[str, Any]]:
        """Validate multiple domains concurrently"""
        tasks = [self.validate_domain(domain) for domain in domains]
        return await asyncio.gather(*tasks)

# Singleton instance
domain_validator = DomainValidator()