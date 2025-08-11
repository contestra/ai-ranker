"""
Advanced LLM Crawlability Features
- CDN/WAF detection
- No-JS content testing
- Meta/headers check
- llms.txt detection
"""

from typing import Dict, List, Any, Optional, Tuple
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

async def detect_cdn_waf(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Detect CDN/WAF providers - recommendations added later based on actual blocking
    """
    result = {
        "cdn_provider": None,
        "waf_detected": False,
        "cloudflare": False,
        "akamai": False,
        "fastly": False,
        "aws_cloudfront": False,
        "platform": None,
        "recommendations": []
    }
    
    try:
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            headers = response.headers
            
            # Check for Cloudflare (detection only, no recommendations yet)
            if any(key.lower().startswith('cf-') for key in headers) or 'cloudflare' in headers.get('Server', '').lower():
                result["cloudflare"] = True
                result["cdn_provider"] = "Cloudflare"
                result["waf_detected"] = True
                
                # Check if this is a Shopify site
                if 'x-shopify-stage' in headers or 'x-shardid' in headers:
                    result["platform"] = "Shopify"
            
            # Check server header for CDN signatures (detection only)
            server = headers.get('Server', '').lower()
            x_powered_by = headers.get('X-Powered-By', '').lower()
            
            if 'akamai' in server or 'akamaighost' in headers.get('X-Akamai-Request-ID', ''):
                result["akamai"] = True
                result["cdn_provider"] = "Akamai"
                result["waf_detected"] = True
            elif 'fastly' in headers.get('X-Served-By', '').lower():
                result["fastly"] = True
                result["cdn_provider"] = "Fastly"
            elif 'cloudfront' in headers.get('Via', '').lower():
                result["aws_cloudfront"] = True
                result["cdn_provider"] = "AWS CloudFront"
            
            # Check for generic WAF signatures
            if any(h in headers for h in ['X-WAF-Score', 'X-Security-Policy', 'X-Frame-Options']):
                result["waf_detected"] = True
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def test_user_agent_access(base_url: str, user_agents: List[Tuple[str, str]], test_paths: List[str] = ["/"]) -> Dict[str, Any]:
    """
    Test if specific user agents can access the site across multiple paths
    """
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for agent_name, agent_string in user_agents:
            agent_results = {
                "paths_tested": 0,
                "paths_accessible": 0,
                "paths_blocked": 0,
                "status_codes": [],
                "overall_accessible": False,
                "overall_blocked": False,
                "challenged": False
            }
            
            for path in test_paths:
                try:
                    test_url = urljoin(base_url, path)
                    headers = {'User-Agent': agent_string}
                    async with session.get(test_url, headers=headers, timeout=10, allow_redirects=True) as response:
                        status = response.status
                        agent_results["paths_tested"] += 1
                        agent_results["status_codes"].append(status)
                        
                        if status == 200:
                            agent_results["paths_accessible"] += 1
                        elif status in [403, 429]:
                            agent_results["paths_blocked"] += 1
                        elif status == 503:
                            text = await response.text()
                            if 'challenge' in text.lower() or 'cloudflare' in text.lower():
                                agent_results["challenged"] = True
                                agent_results["paths_blocked"] += 1
                                
                except Exception as e:
                    agent_results["error"] = str(e)
            
            # Determine overall status
            if agent_results["paths_tested"] > 0:
                agent_results["overall_accessible"] = agent_results["paths_accessible"] >= (agent_results["paths_tested"] / 2)
                agent_results["overall_blocked"] = agent_results["paths_blocked"] >= (agent_results["paths_tested"] / 2)
            
            results[agent_name] = agent_results
    
    return results


async def check_no_js_content(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Check if critical content is available without JavaScript
    """
    result = {
        "content_accessible": False,
        "word_count": 0,
        "has_main_heading": False,
        "has_structured_data": False,
        "has_meta_description": False,
        "has_og_tags": False,
        "critical_content_missing": [],
        "recommendations": []
    }
    
    try:
        # Fetch without JavaScript (basic HTTP GET)
        async with session.get(url, timeout=10) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check for main content
            body_text = soup.get_text(separator=' ', strip=True)
            result["word_count"] = len(body_text.split())
            result["content_accessible"] = result["word_count"] > 100
            
            # Check for H1
            h1_tags = soup.find_all('h1')
            result["has_main_heading"] = len(h1_tags) > 0
            
            # Check for structured data (JSON-LD)
            json_ld = soup.find_all('script', type='application/ld+json')
            result["has_structured_data"] = len(json_ld) > 0
            
            # Check meta tags
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            result["has_meta_description"] = meta_desc is not None
            
            # Check Open Graph tags
            og_tags = soup.find_all('meta', property=re.compile('^og:'))
            result["has_og_tags"] = len(og_tags) > 0
            
            # Check for common JS-only indicators
            if result["word_count"] < 100:
                result["critical_content_missing"].append("Main content (less than 100 words found)")
                result["recommendations"].append("Implement server-side rendering (SSR) or static generation")
            
            if not result["has_main_heading"]:
                result["critical_content_missing"].append("H1 heading")
                result["recommendations"].append("Ensure H1 tags are in initial HTML")
            
            if not result["has_structured_data"]:
                result["critical_content_missing"].append("JSON-LD structured data")
                result["recommendations"].append("Add JSON-LD schema markup to initial HTML")
            
            # Check for React/Vue/Angular indicators
            if '<div id="root"></div>' in html and result["word_count"] < 50:
                result["spa_detected"] = True
                result["recommendations"].append("Consider Next.js/Nuxt.js for SSR/SSG")
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_meta_headers(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Check for meta tags and headers that might block crawlers
    IMPORTANT: Should check actual HTML pages, not robots.txt
    """
    result = {
        "has_noindex": False,
        "has_nofollow": False,
        "has_noarchive": False,
        "has_noai": False,
        "has_tdm_reservation": False,
        "robots_meta_content": None,
        "x_robots_tag": None,
        "checked_url": url,
        "is_robots_txt": "/robots.txt" in url.lower(),
        "warnings": [],
        "recommendations": []
    }
    
    try:
        async with session.get(url, timeout=10) as response:
            headers = response.headers
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check X-Robots-Tag header
            x_robots = headers.get('X-Robots-Tag', '')
            if x_robots:
                result["x_robots_tag"] = x_robots
                if 'noindex' in x_robots.lower():
                    result["has_noindex"] = True
                    if result["is_robots_txt"]:
                        # noindex on robots.txt is common and harmless
                        result["warnings"].append("X-Robots-Tag 'noindex' on robots.txt (harmless)")
                    else:
                        # noindex on actual content is critical
                        result["warnings"].append("X-Robots-Tag header contains 'noindex' - LLMs cannot index this page")
                        result["recommendations"].append("Remove 'noindex' from X-Robots-Tag on HTML pages")
                if 'nofollow' in x_robots.lower():
                    result["has_nofollow"] = True
                    if not result["is_robots_txt"]:
                        result["warnings"].append("X-Robots-Tag header contains 'nofollow'")
            
            # Check meta robots tag
            robots_meta = soup.find('meta', attrs={'name': 'robots'})
            if robots_meta:
                content = robots_meta.get('content', '').lower()
                result["robots_meta_content"] = content
                if 'noindex' in content:
                    result["has_noindex"] = True
                    result["warnings"].append("Meta robots tag contains 'noindex'")
                    result["recommendations"].append("Remove 'noindex' from meta robots tag for LLM accessibility")
                if 'nofollow' in content:
                    result["has_nofollow"] = True
                    result["warnings"].append("Meta robots tag contains 'nofollow'")
                if 'noarchive' in content:
                    result["has_noarchive"] = True
                    result["warnings"].append("Meta robots tag contains 'noarchive'")
            
            # Check for AI-specific meta tags
            noai_meta = soup.find('meta', attrs={'name': 'noai'})
            if noai_meta:
                result["has_noai"] = True
                result["warnings"].append("Found 'noai' meta tag (non-standard AI blocking)")
                
            # Check for TDM Reservation
            tdm_meta = soup.find('meta', attrs={'name': 'tdm-reservation'})
            tdm_header = headers.get('tdm-reservation')
            if tdm_meta or tdm_header:
                result["has_tdm_reservation"] = True
                result["warnings"].append("TDM Reservation protocol detected (rights reservation)")
            
            # Check for googlebot-specific meta
            googlebot_meta = soup.find('meta', attrs={'name': 'googlebot'})
            if googlebot_meta:
                result["googlebot_meta"] = googlebot_meta.get('content', '')
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_llms_txt(base_url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Check for /llms.txt file (proposed standard for LLM instructions)
    """
    result = {
        "exists": False,
        "content": None,
        "size": 0,
        "links": [],
        "sections": [],
        "recommendations": []
    }
    
    llms_url = urljoin(base_url, "/llms.txt")
    
    try:
        async with session.get(llms_url, timeout=10) as response:
            if response.status == 200:
                result["exists"] = True
                content = await response.text()
                result["content"] = content[:1000]  # First 1000 chars
                result["size"] = len(content)
                
                # Extract links
                url_pattern = re.compile(r'https?://[^\s]+')
                result["links"] = url_pattern.findall(content)
                
                # Extract sections (lines starting with #)
                section_pattern = re.compile(r'^#\s*(.+)$', re.MULTILINE)
                result["sections"] = section_pattern.findall(content)
                
                # Check for key information
                if '/policies' in content.lower() or '/terms' in content.lower():
                    result["has_policy_links"] = True
                if '/about' in content.lower() or 'company' in content.lower():
                    result["has_company_info"] = True
                    
            elif response.status == 404:
                result["recommendations"].append("Consider adding /llms.txt to provide LLM-specific instructions")
                result["recommendations"].append("Include links to key pages: About, Products, Policies, FAQ")
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_sitemap_quality(base_url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Check sitemap quality and coverage
    """
    result = {
        "exists": False,
        "urls_count": 0,
        "has_policies": False,
        "has_products": False,
        "has_about": False,
        "has_blog": False,
        "recommendations": []
    }
    
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    
    try:
        async with session.get(sitemap_url, timeout=10) as response:
            if response.status == 200:
                result["exists"] = True
                content = await response.text()
                
                # Count URLs
                result["urls_count"] = content.count('<url>')
                
                # Check for important sections
                content_lower = content.lower()
                result["has_policies"] = '/policies' in content_lower or '/terms' in content_lower
                result["has_products"] = '/products' in content_lower or '/collections' in content_lower
                result["has_about"] = '/about' in content_lower
                result["has_blog"] = '/blog' in content_lower or '/news' in content_lower
                
                if not result["has_policies"]:
                    result["recommendations"].append("Add policy pages to sitemap")
                if not result["has_about"]:
                    result["recommendations"].append("Add About/Company pages to sitemap")
                    
    except Exception as e:
        result["error"] = str(e)
        result["recommendations"].append("Ensure sitemap.xml is accessible")
    
    return result


def generate_waf_recommendations(cdn_waf: Dict[str, Any], user_agent_tests: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate conditional WAF/CDN recommendations based on actual blocking evidence
    """
    recommendations = []
    severity = "info"
    
    # Verified bots list (Cloudflare maintains these)
    verified_bots = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User", "Claude-SearchBot"]
    # Unverified or delisted bots
    unverified_bots = ["PerplexityBot", "Perplexity-User"]
    
    if not cdn_waf.get("cloudflare"):
        # Not Cloudflare, don't mention SBFM
        if cdn_waf.get("akamai"):
            recommendations.append("Akamai detected. If LLMs are blocked, configure Bot Manager.")
        elif cdn_waf.get("fastly"):
            recommendations.append("Fastly detected. If LLMs are blocked, update VCL configuration.")
        elif cdn_waf.get("aws_cloudfront"):
            recommendations.append("CloudFront detected. If LLMs are blocked, adjust AWS WAF rules.")
        return {"recommendations": recommendations, "severity": severity}
    
    # Cloudflare detected - check actual blocking
    blocked_verified = []
    blocked_unverified = []
    accessible_count = 0
    
    for bot_name in verified_bots:
        if bot_name in user_agent_tests:
            test_result = user_agent_tests[bot_name]
            if test_result.get("overall_blocked") or test_result.get("challenged"):
                blocked_verified.append(bot_name)
            elif test_result.get("overall_accessible"):
                accessible_count += 1
    
    for bot_name in unverified_bots:
        if bot_name in user_agent_tests:
            test_result = user_agent_tests[bot_name]
            if test_result.get("overall_blocked") or test_result.get("challenged"):
                blocked_unverified.append(bot_name)
    
    # Decision logic based on evidence
    if len(blocked_verified) >= 2:
        # Multiple verified bots blocked - this is high severity
        severity = "high"
        recommendations.append(f"⚠️ Cloudflare is blocking verified bots ({', '.join(blocked_verified[:3])})")
        
        if cdn_waf.get("platform") == "Shopify":
            recommendations.append("Contact Shopify support about LLM crawler access")
        else:
            recommendations.append("Enable 'Allow Verified Bots' in Super Bot Fight Mode (Pro/Business)")
            recommendations.append("On Free plan: Disable Bot Fight Mode or upgrade to control bot access")
    
    elif len(blocked_verified) == 1:
        # One verified bot blocked - medium severity
        severity = "medium"
        recommendations.append(f"⚠️ {blocked_verified[0]} is being blocked by Cloudflare")
        recommendations.append("Consider enabling 'Allow Verified Bots' if more bots are affected")
    
    elif accessible_count >= 3:
        # Most verified bots working fine - just informational
        severity = "info"
        recommendations.append("✅ Cloudflare detected; verified bots appear to have access")
        recommendations.append("No action needed unless you see 403/429 errors in logs")
    
    else:
        # Insufficient data or mixed results
        severity = "info"
        recommendations.append("Cloudflare detected. Monitor bot access in your logs.")
    
    # Handle unverified/delisted bots separately
    if blocked_unverified:
        recommendations.append(f"ℹ️ Unverified bots blocked: {', '.join(blocked_unverified)}")
        recommendations.append("SBFM 'Verified Bots' won't help these; use WAF custom rules if needed")
    
    return {"recommendations": recommendations, "severity": severity}


async def run_advanced_checks(url: str) -> Dict[str, Any]:
    """
    Run all advanced crawlability checks with conditional WAF recommendations
    """
    results = {
        "cdn_waf": {},
        "no_js_content": {},
        "meta_headers": {},
        "llms_txt": {},
        "sitemap_quality": {},
        "user_agent_tests": {},
        "waf_recommendations": {}
    }
    
    # Comprehensive user agents to test - both verified and unverified
    test_agents = [
        # Verified bots (on Cloudflare's list)
        ("GPTBot", "GPTBot/1.0"),
        ("ChatGPT-User", "ChatGPT-User/1.0 (+https://openai.com/gptbot)"),
        ("OAI-SearchBot", "OAI-SearchBot/1.0 (+https://openai.com/searchbot)"),
        ("ClaudeBot", "ClaudeBot/1.0 (+https://anthropic.com/claude/crawling)"),
        ("Claude-User", "Claude-User/1.0 (+https://anthropic.com)"),
        ("Claude-SearchBot", "Claude-SearchBot/1.0 (+https://anthropic.com)"),
        # Unverified/delisted bots
        ("PerplexityBot", "PerplexityBot/1.0"),
        # Baseline comparison
        ("Googlebot", "Googlebot/2.1 (+http://www.google.com/bot.html)")
    ]
    
    # Test multiple paths to get better signal
    test_paths = ["/", "/about", "/products", "/services"]
    
    async with aiohttp.ClientSession() as session:
        # Run checks in parallel
        cdn_task = detect_cdn_waf(url, session)
        no_js_task = check_no_js_content(url, session)
        meta_task = check_meta_headers(url, session)
        llms_task = check_llms_txt(url, session)
        sitemap_task = check_sitemap_quality(url, session)
        agent_task = test_user_agent_access(url, test_agents, test_paths[:2])  # Test 2 paths for speed
        
        # Gather all results
        results["cdn_waf"], results["no_js_content"], results["meta_headers"], \
        results["llms_txt"], results["sitemap_quality"], results["user_agent_tests"] = \
            await asyncio.gather(cdn_task, no_js_task, meta_task, llms_task, sitemap_task, agent_task)
        
        # Generate conditional WAF recommendations based on actual blocking
        waf_rec = generate_waf_recommendations(results["cdn_waf"], results["user_agent_tests"])
        results["waf_recommendations"] = waf_rec
        
        # Update CDN/WAF recommendations with conditional ones
        results["cdn_waf"]["recommendations"] = waf_rec["recommendations"]
        results["cdn_waf"]["severity"] = waf_rec["severity"]
    
    return results