"""
LLM Crawlability Checker - Analyze websites for AI/LLM accessibility
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Any, Optional
import asyncio
import aiohttp
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import json
from datetime import datetime
from .llm_crawlability_advanced import (
    run_advanced_checks,
    detect_cdn_waf,
    check_no_js_content,
    check_meta_headers,
    check_llms_txt
)

router = APIRouter()

# Known LLM user agents - Updated based on official documentation
LLM_USER_AGENTS = {
    "openai": ["GPTBot", "ChatGPT-User", "OAI-SearchBot"],  # GPTBot (training), ChatGPT-User (browsing), OAI-SearchBot (search indexing)
    "anthropic": ["ClaudeBot", "Claude-User", "Claude-SearchBot"],  # ClaudeBot (training/index), Claude-User (on-demand), Claude-SearchBot (search)
    "google": ["Google-Extended"],  # Usage control for Gemini (not a crawler)
    "apple": ["Applebot-Extended"],  # Usage control for Apple AI (not a crawler)
    "amazon": ["Amazonbot"],  # Amazon's crawler
    "meta": ["FacebookBot"],  # Meta/Facebook crawler
    "common_crawl": ["CCBot"],  # Common Crawl - used by many LLMs
    "microsoft": ["bingbot"],  # Microsoft Bing
    "perplexity": ["PerplexityBot"],  # Perplexity AI
    "you": ["YouBot"],  # You.com
}

# Critical paths that should be accessible
CRITICAL_PATHS = [
    "/",
    "/about",
    "/products",
    "/services",
    "/policies",
    "/terms",
    "/privacy",
    "/contact",
]

# Problematic patterns in robots.txt
PROBLEMATIC_PATTERNS = [
    "/api/",
    "/admin/",
    "/private/",
    "/*.json$",
    "/*.xml$",
]


class CrawlabilityRequest(BaseModel):
    url: HttpUrl
    check_content: bool = False  # Whether to fetch and analyze page content
    check_performance: bool = False  # Whether to measure performance
    run_advanced: bool = False  # Whether to run advanced checks (CDN, JS, meta, llms.txt)


class RobotsAnalysis(BaseModel):
    has_llm_rules: bool
    llm_access: Dict[str, bool]  # Per LLM agent
    explicit_llm_agents: List[str]  # Agents explicitly mentioned in robots.txt
    wildcard_allowed_agents: List[str]  # Agents allowed via wildcard
    critical_paths_blocked: List[str]
    policies_blocked: bool  # Flag if /policies/ is blocked
    sitemap_url: Optional[str]
    crawl_delay: Optional[float]
    warnings: List[str]
    recommendations: List[str]
    score: int  # 0-100
    raw_text: Optional[str] = None  # Raw robots.txt for analysis


class CrawlabilityResponse(BaseModel):
    url: str
    timestamp: datetime
    robots_analysis: Optional[RobotsAnalysis]
    overall_score: int
    grade: str
    critical_issues: List[Dict[str, str]]
    recommendations: List[str]
    advanced_checks: Optional[Dict[str, Any]] = None  # CDN, JS, meta, llms.txt results
    corrected_robots: Optional[str] = None  # Corrected robots.txt with LLM optimizations


async def fetch_robots_txt(base_url: str) -> Optional[str]:
    """Fetch robots.txt content from a website"""
    robots_url = urljoin(base_url, "/robots.txt")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(robots_url, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 404:
                    return None
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to fetch robots.txt: HTTP {response.status}"
                    )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Timeout fetching robots.txt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching robots.txt: {str(e)}")


def analyze_robots_content(robots_txt: str, base_url: str) -> RobotsAnalysis:
    """Analyze robots.txt content for LLM compatibility"""
    
    # Parse robots.txt
    rp = RobotFileParser()
    rp.parse(robots_txt.splitlines())
    
    # Check LLM access and track explicit vs wildcard
    llm_access = {}
    has_llm_rules = False
    explicit_llm_agents = []
    wildcard_allowed_agents = []
    
    for provider, agents in LLM_USER_AGENTS.items():
        for agent in agents:
            # Check if this specific agent is mentioned in robots.txt
            if agent.lower() in robots_txt.lower():
                has_llm_rules = True
                explicit_llm_agents.append(agent)
            
            # Check if agent can fetch root
            can_fetch = rp.can_fetch(agent, "/")
            llm_access[f"{provider}_{agent}"] = can_fetch
            
            # If allowed but not explicit, it's via wildcard
            if can_fetch and agent not in explicit_llm_agents:
                wildcard_allowed_agents.append(agent)
    
    # Check critical paths
    critical_paths_blocked = []
    policies_blocked = False
    
    for path in CRITICAL_PATHS:
        # Check with a common LLM agent
        if not rp.can_fetch("ChatGPT-User", path):
            critical_paths_blocked.append(path)
            if path == "/policies":
                policies_blocked = True
    
    # Also check for explicit /policies/ disallow in robots.txt
    if not policies_blocked:
        for line in robots_txt.splitlines():
            line_lower = line.lower().strip()
            if line_lower.startswith("disallow:") and "/policies" in line_lower:
                policies_blocked = True
                if "/policies" not in critical_paths_blocked:
                    critical_paths_blocked.append("/policies")
    
    # Extract sitemap URL
    sitemap_url = None
    for line in robots_txt.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            break
    
    # Extract crawl delay
    crawl_delay = rp.crawl_delay("*")
    
    # Generate warnings and recommendations
    warnings = []
    recommendations = []
    
    # Check if LLMs have no specific rules and fall back to *
    if not has_llm_rules:
        # Check if * is restrictive
        if not rp.can_fetch("*", "/"):
            warnings.append("User-agent: * is blocking the root path - LLMs cannot access your site")
            recommendations.append("Add specific Allow rules for LLM user agents")
        else:
            # Site is accessible - this is perfectly fine! Don't warn, just suggest
            # NO WARNING - this is completely valid
            recommendations.append("✅ Status: LLM-crawlable by default (wildcard allow)")
            recommendations.append("Optional: Add explicit groups for GPTBot, ChatGPT-User, OAI-SearchBot, Claude*, and usage controls (Google-Extended, Applebot-Extended) so your intent is unambiguous and resilient to future changes")
    
    # Check if any LLMs are blocked
    blocked_llms = [name for name, allowed in llm_access.items() if not allowed]
    if blocked_llms:
        warnings.append(f"Following LLM agents are blocked: {', '.join(blocked_llms)}")
        
        # Special warnings for critical bots
        if "openai_OAI-SearchBot" in blocked_llms:
            warnings.append("OAI-SearchBot is blocked - ChatGPT Search won't be able to discover and cite your content")
            recommendations.append("Allow OAI-SearchBot to enable ChatGPT Search indexing")
        
        if "openai_ChatGPT-User" in blocked_llms:
            warnings.append("ChatGPT-User is blocked - Users won't be able to browse your site through ChatGPT")
            recommendations.append("Allow ChatGPT-User for user-initiated browsing")
        
        if "anthropic_Claude-User" in blocked_llms:
            warnings.append("Claude-User is blocked - Users won't be able to browse your site through Claude")
            recommendations.append("Allow Claude-User for on-demand fetch requests")
    
    # Check critical paths
    if critical_paths_blocked:
        warnings.append(f"Critical paths blocked: {', '.join(critical_paths_blocked)}")
        recommendations.append("Allow access to policy pages and main content areas")
    
    # Specific warning for /policies/ block
    if policies_blocked:
        warnings.append("⚠️ /policies/ is blocked - this prevents LLMs from discovering returns, shipping, and terms pages")
        recommendations.append("Remove 'Disallow: /policies/' and localized variants to improve discoverability")
    
    # Check for sitemap
    if not sitemap_url:
        recommendations.append("Add a Sitemap declaration to help crawlers discover content")
    else:
        # Check for host mismatch between analyzed URL and sitemap
        from urllib.parse import urlparse
        analyzed_host = urlparse(base_url).netloc
        sitemap_host = urlparse(sitemap_url).netloc if sitemap_url.startswith('http') else None
        
        if sitemap_host and sitemap_host != analyzed_host:
            # Check if it's just www vs non-www
            if analyzed_host.replace('www.', '') == sitemap_host.replace('www.', ''):
                recommendations.append(f"ℹ️ Note: Analyzed {analyzed_host} but sitemap points to {sitemap_host} - ensure consistent redirects")
            else:
                warnings.append(f"Host mismatch: Analyzed {analyzed_host} but sitemap points to {sitemap_host}")
                recommendations.append("Ensure apex/www redirect consistently and sitemap matches serving host")
    
    # NEW SCORING SYSTEM - More fair and granular
    score = 0
    
    # 1. Robots posture (20 points max)
    # Check for major LLM blocks first
    major_llms = ["openai_GPTBot", "openai_ChatGPT-User", "openai_OAI-SearchBot", 
                  "anthropic_ClaudeBot", "anthropic_Claude-User", "anthropic_Claude-SearchBot"]
    major_blocked = [name for name in major_llms if name in llm_access and not llm_access[name]]
    
    if major_blocked:
        # Major LLMs explicitly blocked - this is critical
        score += 0  # No points for robots posture
    elif rp.can_fetch("*", "/"):
        # Wildcard is open - that's PERFECT for LLMs!
        score += 20  # FULL POINTS - this is completely valid
        # No penalty for missing explicit rules when already open
    else:
        # Wildcard is restrictive
        if has_llm_rules:
            # Has explicit LLM rules even though * is restrictive
            allowed_llms = sum(1 for allowed in llm_access.values() if allowed)
            score += min(20, int((allowed_llms / len(llm_access)) * 20))
        else:
            # Restrictive * and no LLM rules = limited points
            score += 5  # Some points since site exists and is reachable
    
    # 2. Sitemap presence (10 points)
    if sitemap_url:
        score += 10
    else:
        score += 0  # Missing sitemap
    
    # 3. No critical paths blocked (10 points)
    if not critical_paths_blocked:
        score += 10
    else:
        # Partial credit based on how many paths are blocked
        score += max(0, 10 - len(critical_paths_blocked))
    
    # Note: No-JS content, WAF, headers will be scored in the main function
    # This gives us 40 points from robots.txt analysis
    
    return RobotsAnalysis(
        has_llm_rules=has_llm_rules,
        llm_access=llm_access,
        explicit_llm_agents=explicit_llm_agents,
        wildcard_allowed_agents=wildcard_allowed_agents,
        critical_paths_blocked=critical_paths_blocked,
        policies_blocked=policies_blocked,
        sitemap_url=sitemap_url,
        crawl_delay=crawl_delay,
        warnings=warnings,
        recommendations=recommendations,
        score=score,
        raw_text=robots_txt  # Include raw text for analysis
    )


def generate_corrected_robots(original_robots: str, base_url: str) -> str:
    """
    Generate a corrected version of the robots.txt with LLM optimizations
    Following best practices with comments on separate lines
    """
    lines = original_robots.splitlines()
    corrected_lines = []
    
    # Track what we've seen
    has_llm_rules = False
    has_sitemap = False
    existing_disallow_rules = []
    existing_allow_rules = []
    existing_adsbot_rules = []  # Track existing adsbot-google rules
    current_user_agent = None
    sitemap_url = None
    header_lines = []
    in_header_block = False
    in_adsbot_section = False
    
    # Check if this is a Shopify site with header block
    has_shopify_header = any('Robots & Agent policy' in line or 'Checkouts are for humans' in line for line in lines[:20])
    
    # Parse existing robots.txt
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Capture Shopify header block if present
        if has_shopify_header and i < 20:
            # Look for box drawing characters or header content
            if '━' in line or '┃' in line or '┏' in line or '┗' in line or 'Robots & Agent policy' in line or 'Checkouts are for humans' in line or 'Terms of Service' in line:
                header_lines.append(line)
                in_header_block = True
                continue
            elif in_header_block and line_stripped.startswith('#'):
                header_lines.append(line)
                continue
            else:
                in_header_block = False
        
        # Check for LLM user agents
        if line_stripped.lower().startswith('user-agent:'):
            in_adsbot_section = False  # Reset when we see a new user agent
            current_user_agent = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ''
            if any(agent in current_user_agent for agent in ['ChatGPT', 'GPTBot', 'OAI-SearchBot', 'Claude', 'anthropic', 'Google-Extended']):
                has_llm_rules = True
            elif 'adsbot' in current_user_agent.lower():
                in_adsbot_section = True
                existing_adsbot_rules.append(line_stripped)
        
        # Track rules for different user agents
        if in_adsbot_section and not line_stripped.lower().startswith('user-agent:'):
            # Capture all adsbot-google rules
            if line_stripped and not line_stripped.startswith('#'):
                existing_adsbot_rules.append(line_stripped)
        elif current_user_agent == '*':
            # Track Disallow/Allow rules for User-agent: *
            if line_stripped.lower().startswith('disallow:'):
                existing_disallow_rules.append(line_stripped)
            elif line_stripped.lower().startswith('allow:'):
                existing_allow_rules.append(line_stripped)
        
        # Check for sitemap
        if line_stripped.lower().startswith('sitemap:'):
            has_sitemap = True
            sitemap_url = line_stripped
    
    # Build corrected robots.txt
    # First, add any Shopify header block
    if header_lines:
        corrected_lines.extend(header_lines)
        corrected_lines.append("")
    
    corrected_lines.append("# ====== LLM/AI CRAWLERS — EXPLICIT ALLOW ======")
    corrected_lines.append("# OpenAI")
    corrected_lines.append("User-agent: GPTBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("# User-initiated browsing")
    corrected_lines.append("User-agent: ChatGPT-User")
    corrected_lines.append("Allow: /")
    corrected_lines.append("# ChatGPT Search indexing (critical)")
    corrected_lines.append("User-agent: OAI-SearchBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("")
    
    # Add Anthropic crawlers
    corrected_lines.append("# Anthropic")
    corrected_lines.append("User-agent: ClaudeBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("User-agent: Claude-User")
    corrected_lines.append("Allow: /")
    corrected_lines.append("User-agent: Claude-SearchBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("")
    
    # Add usage controls
    corrected_lines.append("# Usage controls (not crawlers)")
    corrected_lines.append("# Google-Extended controls Gemini usage, not crawling")
    corrected_lines.append("User-agent: Google-Extended")
    corrected_lines.append("Allow: /")
    corrected_lines.append("# Applebot-Extended controls Apple AI usage, not crawling")
    corrected_lines.append("User-agent: Applebot-Extended")
    corrected_lines.append("Allow: /")
    corrected_lines.append("")
    
    # Add other AI crawlers
    corrected_lines.append("# Other AI crawlers")
    corrected_lines.append("User-agent: Amazonbot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("User-agent: CCBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("User-agent: PerplexityBot")
    corrected_lines.append("Allow: /")
    corrected_lines.append("# Perplexity-User may ignore robots.txt for user-initiated fetches")
    corrected_lines.append("User-agent: Perplexity-User")
    corrected_lines.append("Allow: /")
    corrected_lines.append("")
    
    # Add baseline SEO rules
    corrected_lines.append("# ====== SEO-ORIENTED DEFAULTS ======")
    
    # Check if there are existing disallow rules
    if existing_disallow_rules:
        # Keep existing SEO rules but remove /policies/ blocks
        corrected_lines.append("User-agent: *")
        for rule in existing_disallow_rules:
            # Skip /policies/ blocks
            if "/policies" not in rule.lower():
                corrected_lines.append(rule)
        for rule in existing_allow_rules:
            corrected_lines.append(rule)
        corrected_lines.append("# NOTE: policies are intentionally NOT disallowed")
    else:
        # No existing rules - default to open access
        corrected_lines.append("User-agent: *")
        corrected_lines.append("Disallow:")
        corrected_lines.append("# Note: Add specific disallows for /cart, /checkout, /admin if this is an e-commerce site")
    
    corrected_lines.append("")
    
    # ALWAYS include AdsBot rules - ANY site might run Google Ads
    # AdsBot ignores wildcard (*) rules, must be named explicitly
    corrected_lines.append("# Google Ads landing-page crawler (required for Google Ads)")
    
    if existing_adsbot_rules:
        # Preserve existing rules
        for rule in existing_adsbot_rules:
            corrected_lines.append(rule)
    else:
        # Add default AdsBot rules for all sites
        corrected_lines.append("User-agent: AdsBot-Google")
        if any("/checkout" in rule.lower() or "/cart" in rule.lower() for rule in existing_disallow_rules):
            # E-commerce site - disallow checkout/cart pages
            corrected_lines.append("Disallow: /checkout")
            corrected_lines.append("Disallow: /checkouts/")
            corrected_lines.append("Disallow: /carts")
            corrected_lines.append("Disallow: /orders")
        else:
            # Non-ecommerce - allow everything by default
            corrected_lines.append("Disallow:")
        
        # Also add mobile variant
        corrected_lines.append("")
        corrected_lines.append("# Mobile web variant")
        corrected_lines.append("User-agent: AdsBot-Google-Mobile")
        if any("/checkout" in rule.lower() or "/cart" in rule.lower() for rule in existing_disallow_rules):
            corrected_lines.append("Disallow: /checkout")
            corrected_lines.append("Disallow: /checkouts/")
            corrected_lines.append("Disallow: /carts")
            corrected_lines.append("Disallow: /orders")
        else:
            corrected_lines.append("Disallow:")
    
    corrected_lines.append("")
    
    # Optional: Add Mediapartners-Google for AdSense sites
    corrected_lines.append("# AdSense crawler (optional - only if you run AdSense)")
    corrected_lines.append("# User-agent: Mediapartners-Google")
    corrected_lines.append("# Disallow:")
    corrected_lines.append("")
    
    # Add sitemap at the end
    corrected_lines.append("# Discovery")
    if sitemap_url:
        corrected_lines.append(sitemap_url)
    else:
        corrected_lines.append(f"Sitemap: {base_url}/sitemap.xml")
    
    return '\n'.join(corrected_lines)


def calculate_grade(score: int) -> str:
    """Convert numeric score to letter grade
    A ≥ 90, B 80-89, C 70-79, D 60-69, F < 60
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


@router.post("/llm-crawlability", response_model=CrawlabilityResponse)
async def check_llm_crawlability(request: CrawlabilityRequest):
    """
    Analyze a website's crawlability for LLMs/AI systems
    """
    
    base_url = str(request.url)
    
    # Fetch and analyze robots.txt
    robots_txt = await fetch_robots_txt(base_url)
    
    if robots_txt is None:
        # No robots.txt found - this means everything is OPEN which is great!
        robots_analysis = RobotsAnalysis(
            has_llm_rules=False,
            llm_access={f"{p}_{a}": True for p, agents in LLM_USER_AGENTS.items() for a in agents},
            explicit_llm_agents=[],  # No explicit rules
            wildcard_allowed_agents=[agent for agents in LLM_USER_AGENTS.values() for agent in agents],  # All via default
            critical_paths_blocked=[],
            policies_blocked=False,
            sitemap_url=None,
            crawl_delay=None,
            warnings=[],  # No warnings - this is fine!
            recommendations=[
                "Consider adding a robots.txt with sitemap declaration (optional)",
                "Explicit LLM agent rules provide clarity but aren't required when fully open"
            ],
            score=30  # 20 for open access + 10 for no blocked paths, missing 10 for sitemap
        )
    else:
        robots_analysis = analyze_robots_content(robots_txt, base_url)
    
    # Run advanced checks if requested
    advanced_results = None
    if request.run_advanced:
        try:
            advanced_results = await run_advanced_checks(base_url)
        except Exception as e:
            print(f"Advanced checks failed: {str(e)}")
            advanced_results = {"error": str(e)}
    
    # NEW SCORING RUBRIC IMPLEMENTATION
    # Starting with robots.txt score (40 points max from robots analysis)
    overall_score = robots_analysis.score
    
    # Add scores from advanced checks if available
    if advanced_results and "error" not in advanced_results:
        
        # 4. No-JS content (25 points)
        no_js = advanced_results.get("no_js_content", {})
        if no_js.get("content_accessible") and no_js.get("word_count", 0) >= 100:
            # Good amount of content without JS
            if no_js.get("has_main_heading"):
                overall_score += 25  # Full points - content and structure available
            else:
                overall_score += 20  # Most points - content available but missing h1
        elif no_js.get("word_count", 0) >= 50:
            overall_score += 15  # Partial content available
        else:
            overall_score += 0  # No meaningful content without JS
            
        # 5. WAF friendliness (20 points) - based on actual agent tests
        agent_tests = advanced_results.get("user_agent_tests", {})
        waf_severity = advanced_results.get("cdn_waf", {}).get("severity", "info")
        
        if agent_tests:
            # Count how many verified LLM agents have access
            verified_agents = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User", "Claude-SearchBot"]
            accessible_count = 0
            tested_count = 0
            
            for agent in verified_agents:
                if agent in agent_tests:
                    tested_count += 1
                    if agent_tests[agent].get("overall_accessible"):
                        accessible_count += 1
            
            if tested_count > 0:
                # Score based on percentage of accessible agents
                overall_score += int((accessible_count / tested_count) * 20)
            else:
                # No verified agents tested
                overall_score += 15  # Give partial credit
        else:
            # No agent tests performed, score based on WAF severity
            if waf_severity == "info":
                overall_score += 18  # Likely OK
            elif waf_severity == "medium":
                overall_score += 10  # Some issues
            else:
                overall_score += 5  # Significant blocking likely
                
        # 6. Rights & headers (15 points)
        meta = advanced_results.get("meta_headers", {})
        # Note: We're checking the headers on the actual URL, not robots.txt
        if not meta.get("has_noindex") and not meta.get("has_noai"):
            overall_score += 15  # No blocking headers
        elif meta.get("has_noindex"):
            # Check if this is just on robots.txt (which is fine)
            if "/robots.txt" in str(request.url):
                overall_score += 15  # noindex on robots.txt is OK
                recommendations.append("Note: noindex on robots.txt is fine, verify it's not on HTML pages")
            else:
                overall_score += 0  # Critical - noindex on actual content
        elif meta.get("has_noai"):
            overall_score += 5  # AI-specific blocking
        else:
            overall_score += 10  # Some issues but not critical
            
        # 7. Discoverability bonus (10 points)
        if advanced_results.get("llms_txt", {}).get("exists"):
            overall_score += 5  # Has llms.txt
        if advanced_results.get("sitemap_quality", {}).get("has_about"):
            overall_score += 5  # Has discoverable about/policy pages
    else:
        # No advanced checks, give benefit of doubt for some categories
        overall_score += 20  # Assume content is accessible
        overall_score += 15  # Assume no blocking headers
        
    # Cap at 100
    overall_score = min(100, overall_score)
    
    # Determine critical issues (more nuanced now)
    critical_issues = []
    
    # Check if wildcard is open first
    wildcard_open = robots_analysis.score >= 20 and not any("blocking the root path" in w for w in robots_analysis.warnings)
    
    if robots_analysis.warnings:
        for warning in robots_analysis.warnings:
            if "blocking the root path" in warning and "cannot access" in warning:
                # Only critical if actually blocking access
                critical_issues.append({
                    "type": "robots_txt",
                    "severity": "critical",
                    "message": warning,
                    "solution": "Add Allow: / for LLM user agents or open wildcard access"
                })
            elif "explicitly disallowed" in warning and any(llm in warning for llm in ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot"]):
                # Major LLMs explicitly blocked - this is critical
                critical_issues.append({
                    "type": "robots_txt", 
                    "severity": "critical",
                    "message": warning,
                    "solution": "Remove disallow rules for major LLM crawlers"
                })
            elif "OAI-SearchBot is blocked" in warning:
                # Important for ChatGPT Search
                critical_issues.append({
                    "type": "robots_txt",
                    "severity": "high",
                    "message": warning,
                    "solution": "Allow OAI-SearchBot for ChatGPT Search indexing"
                })
            elif "blocked" in warning and ("ChatGPT-User" in warning or "Claude-User" in warning):
                # User browsing agents blocked
                critical_issues.append({
                    "type": "robots_txt",
                    "severity": "medium",
                    "message": warning,
                    "solution": "Consider allowing user-initiated browsing agents"
                })
    
    # Don't create critical issues for missing explicit rules when wildcard is open
    if not robots_analysis.has_llm_rules and wildcard_open:
        # This is NOT a critical issue - just informational
        pass  # No critical issue added
    
    # Generate corrected robots.txt based on their actual file
    corrected_robots = None
    if robots_txt:
        corrected_robots = generate_corrected_robots(robots_txt, base_url)
    
    # Add advanced checks results to recommendations
    if advanced_results and "error" not in advanced_results:
        # Add conditional CDN/WAF recommendations (already generated based on actual blocking)
        cdn_recs = advanced_results.get("cdn_waf", {}).get("recommendations", [])
        robots_analysis.recommendations.extend(cdn_recs)
        
        # Add no-JS recommendations
        no_js_recs = advanced_results.get("no_js_content", {}).get("recommendations", [])
        robots_analysis.recommendations.extend(no_js_recs)
        
        # Add meta/header warnings
        meta_warnings = advanced_results.get("meta_headers", {}).get("warnings", [])
        for warning in meta_warnings:
            critical_issues.append({
                "type": "meta_headers",
                "severity": "high" if "noindex" in warning else "medium",
                "message": warning,
                "solution": "Review and update meta tags and HTTP headers"
            })
    
    # Generate summary message based on grade
    grade = calculate_grade(overall_score)
    if grade == "A":
        summary = "Excellent LLM crawlability with minor polish items."
    elif grade == "B":
        summary = "Strong posture; a few optimizations recommended."
    elif grade == "C":
        summary = "Workable, but improvements will materially help LLMs."
    elif grade == "D":
        summary = "Significant blockers; address the criticals first."
    else:
        summary = "Critical issues prevent reliable LLM discovery."
    
    # Add summary to response (extend the model if needed)
    response = CrawlabilityResponse(
        url=base_url,
        timestamp=datetime.now(),
        robots_analysis=robots_analysis,
        overall_score=overall_score,
        grade=grade,
        critical_issues=critical_issues,
        recommendations=robots_analysis.recommendations,
        advanced_checks=advanced_results,
        corrected_robots=corrected_robots
    )
    
    # Add summary as first recommendation
    if summary:
        response.recommendations.insert(0, f"📊 {summary}")
    
    return response


@router.post("/llm-crawlability/compare")
async def compare_crawlability(urls: List[HttpUrl]):
    """
    Compare LLM crawlability across multiple websites
    """
    
    results = []
    for url in urls[:5]:  # Limit to 5 URLs for safety
        try:
            result = await check_llm_crawlability(CrawlabilityRequest(url=url))
            results.append(result)
        except Exception as e:
            results.append({
                "url": str(url),
                "error": str(e),
                "overall_score": 0,
                "grade": "F"
            })
    
    # Sort by score
    results.sort(key=lambda x: x.overall_score if hasattr(x, 'overall_score') else 0, reverse=True)
    
    return {
        "comparison": results,
        "best": results[0] if results else None,
        "worst": results[-1] if results else None,
        "average_score": sum(r.overall_score if hasattr(r, 'overall_score') else 0 for r in results) / len(results) if results else 0
    }


# Example enhanced robots.txt for LLM optimization (following best practices)
EXAMPLE_LLM_OPTIMIZED_ROBOTS = """
# ====== LLM/AI CRAWLERS — EXPLICIT ALLOW ======
# OpenAI
User-agent: GPTBot
Allow: /
# User-initiated browsing
User-agent: ChatGPT-User
Allow: /
# ChatGPT Search indexing (critical)
User-agent: OAI-SearchBot
Allow: /

# Anthropic
User-agent: ClaudeBot
Allow: /
User-agent: Claude-User
Allow: /
User-agent: Claude-SearchBot
Allow: /

# Usage controls (not crawlers)
# Google-Extended controls Gemini usage, not crawling
User-agent: Google-Extended
Allow: /
# Applebot-Extended controls Apple AI usage, not crawling
User-agent: Applebot-Extended
Allow: /

# Other AI crawlers
User-agent: Amazonbot
Allow: /
User-agent: CCBot
Allow: /
User-agent: PerplexityBot
Allow: /
# Perplexity-User may ignore robots.txt for user-initiated fetches
User-agent: Perplexity-User
Allow: /

# ====== GOOGLE ADS CRAWLERS (REQUIRED FOR ADS) ======
# AdsBot ignores wildcard (*) rules - must be named explicitly
User-agent: AdsBot-Google
Disallow:

# Mobile web variant
User-agent: AdsBot-Google-Mobile
Disallow:

# Optional: AdSense crawler (uncomment if you run AdSense)
# User-agent: Mediapartners-Google
# Disallow:

# ====== BASELINE (SEO) ======
# For e-commerce sites, use these disallows:
User-agent: *
Disallow: /api/
Disallow: /admin/
Disallow: /cart
Disallow: /checkout
Disallow: /account
Disallow: /search
Disallow: /collections/*sort_by*
Disallow: /collections/*filter*
Allow: /policies/
Allow: /terms/
Allow: /about/
Allow: /products/
Allow: /services/

# Discovery
Sitemap: https://example.com/sitemap.xml
"""