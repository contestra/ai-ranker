# LLM Crawlability Checker Feature

## Overview
A comprehensive tool to analyze websites for LLM crawlability and provide actionable recommendations for improving AI visibility.

## Core Functionality

### 1. Robots.txt Analysis
Check for LLM-specific user agents and their permissions:

#### Known LLM Crawlers
- **OpenAI**: `ChatGPT-User`, `GPTBot`
- **Google**: `Google-Extended` (Gemini/Bard)
- **Anthropic**: `anthropic-ai`, `Claude-Web`
- **Meta**: `FacebookBot` (for LLaMA training)
- **Common Crawl**: `CCBot` (used by many LLMs)
- **Microsoft**: `bingbot` (for Copilot/GPT integration)
- **Perplexity**: `PerplexityBot`
- **You.com**: `YouBot`

#### Analysis Points
```python
def analyze_robots_txt(url: str):
    """
    Analyze robots.txt for LLM compatibility
    """
    checks = {
        "llm_specific_rules": False,  # Has rules for LLM user agents
        "llm_allowed": False,         # LLMs have access
        "policy_pages_accessible": False,  # /policies/, /terms/, etc.
        "sitemap_declared": False,    # Sitemap URL present
        "crawl_delay": None,          # Delay value if set
        "disallow_patterns": [],      # Problematic patterns
        "recommendations": []
    }
    
    # Check for each LLM crawler
    # Check if falling back to User-agent: *
    # Analyze restrictive patterns
    # Generate recommendations
```

### 2. Content Accessibility Analysis

#### JavaScript Dependency Check
```python
def check_js_dependency(url: str):
    """
    Compare content with and without JavaScript
    """
    # Fetch with JavaScript disabled (basic HTTP)
    # Fetch with JavaScript enabled (Playwright/Selenium)
    # Compare content differences
    # Flag critical content behind JS
```

#### Content Structure Analysis
- **Plain text availability**: Is core content in HTML?
- **AJAX/SPA issues**: Content loaded dynamically?
- **Infinite scroll**: Content paginated properly?
- **Login walls**: Public content behind authentication?

### 3. Structured Data Analysis

#### Schema.org Markup
```python
def analyze_structured_data(html: str):
    """
    Check for structured data that helps LLMs understand content
    """
    checks = {
        "json_ld": False,          # JSON-LD present
        "microdata": False,        # Microdata markup
        "organization_schema": False,  # Company info
        "product_schema": False,   # Product details
        "article_schema": False,   # Article/blog structure
        "faq_schema": False,       # FAQ structured data
        "breadcrumbs": False       # Navigation structure
    }
```

### 4. Metadata Quality

#### Essential Meta Tags
- `<meta name="description">` - Clear page descriptions
- `<meta property="og:*">` - Open Graph tags
- `<meta name="author">` - Content attribution
- `<link rel="canonical">` - Canonical URLs
- `<meta name="robots">` - Page-level robot directives

### 5. Content Quality Signals

#### Readability Metrics
- **Text-to-HTML ratio**: Sufficient textual content
- **Heading structure**: Proper H1-H6 hierarchy
- **Internal linking**: Good site structure
- **External references**: Credible sources linked

### 6. Performance Metrics

#### Loading Performance
- **Time to First Byte (TTFB)**
- **Page load time**
- **Core Web Vitals** (affects crawl budget)
- **Mobile responsiveness**

## Implementation Design

### Backend API Endpoint
```python
@router.post("/api/llm-crawlability")
async def check_llm_crawlability(request: CrawlabilityRequest):
    """
    Comprehensive LLM crawlability analysis
    """
    results = {
        "url": request.url,
        "timestamp": datetime.now(),
        "scores": {
            "overall": 0,  # 0-100
            "robots_txt": 0,
            "content_access": 0,
            "structured_data": 0,
            "metadata": 0,
            "performance": 0
        },
        "issues": [],
        "recommendations": [],
        "details": {}
    }
    
    # Run all checks in parallel
    results["robots"] = await analyze_robots_txt(request.url)
    results["content"] = await check_content_accessibility(request.url)
    results["structured"] = await analyze_structured_data(request.url)
    results["metadata"] = await check_metadata(request.url)
    results["performance"] = await measure_performance(request.url)
    
    # Calculate scores
    results["scores"] = calculate_scores(results)
    
    # Generate recommendations
    results["recommendations"] = generate_recommendations(results)
    
    return results
```

### Frontend Component
```tsx
interface CrawlabilityResults {
  scores: {
    overall: number
    robots_txt: number
    content_access: number
    structured_data: number
    metadata: number
    performance: number
  }
  issues: Issue[]
  recommendations: Recommendation[]
}

export function LLMCrawlabilityChecker() {
  return (
    <div>
      <URLInput onSubmit={checkUrl} />
      <ScoreCard scores={scores} />
      <IssuesList issues={issues} severity="critical|warning|info" />
      <RecommendationsList recommendations={recommendations} />
      <DetailedReport details={details} />
    </div>
  )
}
```

## Scoring System

### Overall Score Calculation
```
Overall Score = weighted average of:
- Robots.txt compliance (25%)
- Content accessibility (25%)
- Structured data (20%)
- Metadata quality (15%)
- Performance (15%)
```

### Grade Levels
- **A+ (95-100)**: Excellent LLM optimization
- **A (90-94)**: Very good, minor improvements
- **B (80-89)**: Good, some issues to address
- **C (70-79)**: Average, significant improvements needed
- **D (60-69)**: Poor, major issues present
- **F (<60)**: Failing, critical problems blocking LLMs

## Example Recommendations

### Critical Issues
1. **No LLM access in robots.txt**
   - "Add specific rules for ChatGPT-User, Google-Extended, and anthropic-ai"
   - "Current User-agent: * rules are blocking LLM crawlers"

2. **JavaScript-only content**
   - "Core content requires JavaScript execution"
   - "Implement server-side rendering or static generation"

3. **No structured data**
   - "Add JSON-LD schema for better content understanding"
   - "Implement Organization and Product schemas"

### Warnings
1. **Restrictive robots.txt**
   - "Policy pages are blocked from crawling"
   - "Consider allowing /about, /policies, /terms"

2. **Missing metadata**
   - "Add Open Graph tags for better content representation"
   - "Include meta descriptions for all pages"

### Improvements
1. **Performance optimization**
   - "Reduce page load time (current: 5.2s, target: <3s)"
   - "Optimize images and implement lazy loading"

2. **Content structure**
   - "Improve heading hierarchy (multiple H1s found)"
   - "Add internal linking for better site navigation"

## Integration with Existing Features

### Brand Analysis Enhancement
- Check your brand's website crawlability
- Compare with competitors' crawlability scores
- Track improvements over time

### Competitive Intelligence
- Analyze competitor websites for LLM optimization
- Identify gaps and opportunities
- Benchmark against industry leaders

### Reporting
- Generate crawlability reports for clients
- Track optimization progress
- Export detailed recommendations

## Technical Requirements

### Python Dependencies
```python
# requirements.txt additions
beautifulsoup4  # HTML parsing
playwright      # JavaScript rendering
robotparser     # robots.txt parsing
schema          # Schema.org validation
urllib3         # URL fetching
```

### API Rate Limiting
- Implement caching for repeated checks
- Rate limit to prevent abuse
- Queue system for bulk analysis

## Future Enhancements

### Advanced Features
1. **Continuous Monitoring**
   - Weekly crawlability checks
   - Alert on degradation
   - Track optimization impact

2. **AI Content Analysis**
   - Check if content is AI-friendly
   - Readability scoring
   - Topic clustering

3. **Sitemap Analysis**
   - Validate sitemap structure
   - Check URL coverage
   - Identify orphaned pages

4. **Multi-language Support**
   - Check hreflang tags
   - Analyze international targeting
   - Language-specific recommendations

5. **Industry Benchmarks**
   - Compare against industry averages
   - Best-in-class examples
   - Sector-specific recommendations

## Example Output

```json
{
  "url": "https://avea-life.com",
  "scores": {
    "overall": 72,
    "robots_txt": 45,
    "content_access": 85,
    "structured_data": 60,
    "metadata": 90,
    "performance": 80
  },
  "critical_issues": [
    {
      "type": "robots_txt",
      "message": "LLM crawlers inherit restrictive User-agent: * rules",
      "impact": "High",
      "solution": "Add specific Allow: rules for ChatGPT-User, Google-Extended"
    }
  ],
  "recommendations": [
    "Add LLM-specific rules to robots.txt allowing full site access",
    "Implement JSON-LD schema for products and organization",
    "Ensure policy pages are crawlable",
    "Add FAQ schema to support pages",
    "Optimize images (current total: 8.5MB)"
  ]
}
```

## Business Value

### For Brands
- Improve AI visibility and recommendations
- Stay ahead of competitors in AI search
- Future-proof for AI-driven discovery

### For Agencies
- New service offering for clients
- Differentiate with AI optimization
- Data-driven recommendations

### For Contestra
- Unique feature in the market
- Complementary to brand tracking
- Additional revenue stream

## Implementation Timeline

### Phase 1 (Week 1-2)
- Robots.txt analyzer
- Basic scoring system
- Simple UI

### Phase 2 (Week 3-4)
- Content accessibility checks
- JavaScript dependency detection
- Structured data analysis

### Phase 3 (Week 5-6)
- Performance metrics
- Detailed recommendations
- Report generation

### Phase 4 (Week 7-8)
- Competitive analysis
- Bulk checking
- API endpoints

## Success Metrics

- Number of sites analyzed
- Average score improvements
- User engagement with recommendations
- Conversion to paid features