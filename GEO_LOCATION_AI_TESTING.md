# Geographic Location Testing for AI Models - Complete Guide

## Executive Summary

Testing how AI models respond differently based on geographic location is complex. Consumer apps (ChatGPT, Gemini) show location-based differences, but the underlying APIs behave differently. This document consolidates everything we've learned about proper geo-testing for AI responses.

## Key Findings

### 1. Consumer Apps vs APIs - Critical Differences

#### Consumer Apps (ChatGPT, Gemini Apps)
- **DO use location** even with "grounding/web off"
- Estimate location from IP address (country/state/city level)
- May auto-search without explicit user request
- This explains why "top longevity supplements" differs between Switzerland and Germany
- Gemini can also use Google Account Home/Work addresses or precise device location if permitted

#### APIs (OpenAI API, Gemini API) - The Truth
- **NO automatic IP-based localization** with tools off
- **NO geographic differences** when properly controlled
- Same prompt + same parameters = same output from anywhere
- Web search/grounding must be explicitly enabled as a tool
- Without tools configured, there's no auto-grounding
- Any observed differences are due to:
  - **Different backend variants** (check `system_fingerprint`)
  - **Not fixing randomness** (temperature, seed, top_p)
  - **Different endpoints** (api.openai.com vs eu.api.openai.com)
  - NOT geography

### 2. Proving API Consistency - Controlled Experiment

To definitively prove APIs don't vary by country:

1. **Fix randomness:** Set `temperature=0`, `top_p=1`, and fixed `seed`
2. **Log backend variant:** Store `system_fingerprint` from response
3. **Use same endpoint:** Don't mix api.openai.com with eu.api.openai.com
4. **Fire simultaneously:** Send identical payloads from all regions
5. **Run N=10 repeats per country** and compare:
   - Exact match percentage
   - Levenshtein/character distance
   - "Top-N items" overlap (for list prompts)
   - Semantic cosine similarity (optional)
6. **Expected results:**
   - If fingerprints match + fixed randomness = **identical outputs**
   - If fingerprints differ = backend drift, not geography
   - If outputs differ with same fingerprint + seed = bug worth reporting

**Critical insight**: Regional endpoints (EU/US/Asia) exist for **data residency & latency**, NOT for changing the model's "local answers."

### 3. Why Proxies Don't Work for AI APIs (But Do Help for Retrieval)

**For LLM API calls - Proxies are useless:**
1. **Authentication via API keys** - OpenAI/Google authenticate by key, not IP
2. **No geo-targeted responses** - APIs don't serve different content by region
3. **Model consistency** - Same model version responds identically regardless of request origin
4. **May trigger WAF/rate limits** and add fragility

**For retrieval tier - Proxies ARE useful:**
- SERPs, retailer pages, and news sites **DO vary by country/IP**
- Use proxies or official search APIs to gather **local evidence**
- Feed small excerpts to the model as context
- Datacenter proxies are fine; residential is overkill unless sites block DC IPs

### 3. What Actually Affects AI Responses by Region

#### In Consumer Apps
- IP-based location estimation
- Automatic web search with location-aware results
- Account-based location (Google Home/Work addresses)
- Device location (if permitted)

#### In APIs
Only these factors create geographic differences:
- **Explicit location context** in prompts
- **Country-scoped search results** fed as context
- **Regional compliance filtering** (rare, mostly for regulated content)
- **Model version differences** (tracked via `system_fingerprint`)

## Proven Approaches for Geographic Testing

### Approach 0: Base Model Testing (Control Baseline)

**Purpose**: Establish the true baseline response without any geographic influence.

**Implementation**:
```python
def test_base_model(prompt):
    """Test with NO geographic context - pure model response"""
    
    # Fixed parameters for reproducibility
    messages = [
        {"role": "user", "content": prompt}  # ONLY the naked prompt
    ]
    
    response = openai.chat.completions.create(
        model="gpt-4",
        temperature=0,      # Deterministic
        top_p=1,
        seed=42,           # Fixed seed
        messages=messages
    )
    
    # Log critical metadata
    return {
        "content": response.choices[0].message.content,
        "system_fingerprint": response.system_fingerprint,
        "model": response.model,
        "created": response.created
    }
```

**This is your control group** - what the model says with zero geographic influence. Any differences in country tests should be compared against this baseline.

### Approach 1: Region-Pinned Compute with Edge Router (Implementation Blueprint)

**Architecture for 6-country testing (US, UK, DE, CH, UAE, SG):**

1. **Edge router** (Cloudflare Worker) receives `{prompt, test_id}` and fans out to six region functions
2. **Region functions** (AWS Lambda) deployed in:
   ```yaml
   AWS Lambda Regions:
     US: us-east-1
     UK: eu-west-2  
     Germany: eu-central-1
     Switzerland: eu-central-2 (Zurich)
     UAE: me-central-1
     Singapore: ap-southeast-1
   ```

**Cost**: Effectively **$0** at ~100 tests/day
- AWS Lambda: 1M requests + 400k GB-seconds free/month
- Cloudflare Workers: Generous free tier for orchestration
- Token payloads are small; egress negligible

**Two modes per run:**
1. **API-only baseline:** No context, tools off, fixed randomness → store text + `system_fingerprint`
2. **Country-aware mode:** Add 3-5 bullet evidence pack (tools still off) → store text + `system_fingerprint`

**Benefits**:
- True geographic origin for proving base model consistency
- Simple "deploy once per region," scales to zero
- Clean separation of control vs country-aware tests

### Approach 2: Country-Scoped Retrieval (Recommended)

Replicate what consumer apps actually do - vary the sources, not the prompt. This approach uses a minimal "evidence pack" of 3-5 short, country-specific snippets.

#### Building the Evidence Pack - Minimal Heuristics

**Core principles to avoid over-steering:**
- **3-5 bullets only**, 1-2 lines each
- **≤600 tokens total** (ideally ≤20% of total token budget)
- **No instructions** - No "use CHF," no "focus on Swiss brands"
- **Neutral facts only** - Titles, dates, and 1-2 line snippets

**Source diversity (mix these):**
1. **Government/health portal** - National health authority or medical guidelines
2. **Major local publisher/clinic** - Established news outlet or medical institution
3. **Large retailer/pharmacy** - Major chain with local pricing
4. **Local ccTLDs preferred** - .ch, .de, .co.uk, .sg, .ae domains
5. **Natural local language** - German for CH/DE, Arabic for UAE where appropriate

#### Retrieval Strategies for Evidence Packs

**Option 1: Search APIs (Recommended)**
```python
COUNTRY_SEARCH_PARAMS = {
    'US': {
        'google': {'gl': 'us', 'hl': 'en', 'lr': 'lang_en'},
        'bing': {'mkt': 'en-US'}
    },
    'GB': {
        'google': {'gl': 'uk', 'hl': 'en', 'lr': 'lang_en'},
        'bing': {'mkt': 'en-GB'}
    },
    'DE': {
        'google': {'gl': 'de', 'hl': 'de', 'lr': 'lang_de'},
        'bing': {'mkt': 'de-DE'}
    },
    'CH': {
        'google': {'gl': 'ch', 'hl': 'de', 'lr': 'lang_de'},
        'bing': {'mkt': 'de-CH'}  # or fr-CH, it-CH
    },
    'AE': {
        'google': {'gl': 'ae', 'hl': 'en', 'lr': 'lang_en|lang_ar'},
        'bing': {'mkt': 'en-AE'}  # or ar-AE
    },
    'SG': {
        'google': {'gl': 'sg', 'hl': 'en', 'lr': 'lang_en'},
        'bing': {'mkt': 'en-SG'}
    }
}
```

**Option 2: Proxy-based Retrieval (For live pages only)**
- Use lightweight datacenter proxies (~$1-3.50/GB)
- Only for fetching SERPs/retailer pages, NOT for LLM API calls
- Residential proxies overkill unless sites block DC IPs

**Costs:**
- Google Programmable Search: 100 queries/day free, then $5/1000
- Bing Web Search: Check current pricing tiers
- Proxy usage: Minimal at this scale (fetching snippets only)

#### Implementation Example - Context Blocks as Separate Messages

**CRITICAL**: The evidence pack must be sent as a **separate message** in the API payload, NOT concatenated to the user's prompt. This keeps the prompt "naked" and unmodified.

```python
def build_country_evidence_pack(query, country):
    """Build minimal evidence pack for country-specific context"""
    
    # Step 1: Search with country parameters
    params = COUNTRY_SEARCH_PARAMS[country]['google']
    search_results = google_search(
        q=query,
        gl=params['gl'],
        hl=params['hl'], 
        lr=params['lr'],
        num=5
    )
    
    # Step 2: Filter and extract snippets
    evidence_pack = []
    seen_domains = set()
    
    for result in search_results:
        # Dedupe domains
        domain = extract_domain(result.url)
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        
        # Extract 1-2 line snippet
        snippet = extract_snippet(result, max_chars=220)
        
        # Format neutrally
        evidence_pack.append(
            f"- ({result.title} — {domain} — {result.date}): {snippet}"
        )
        
        if len(evidence_pack) >= 5:
            break
    
    return "\n".join(evidence_pack)

def ask_model_with_country_context(prompt, country):
    """Call API with country-scoped evidence using SEPARATE messages"""
    
    # Get evidence pack
    evidence = build_country_evidence_pack(prompt, country)
    
    # Neutral system prompt - no country mention
    system_prompt = """Answer the user's question. Consider the optional 
    Context notes if they are relevant and trustworthy; otherwise rely 
    on your general knowledge. Do not assume any country unless the 
    Context implies it."""
    
    # Build messages array - KEEP PROMPT NAKED
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}  # NAKED PROMPT - unmodified!
    ]
    
    # Add evidence as SEPARATE message (context block)
    if evidence:
        messages.append({
            "role": "user",  # Another user message, NOT concatenated
            "content": f"Context:\n{evidence}"
        })
    
    # Call with fixed parameters
    return openai.chat.completions.create(
        model="gpt-4",
        temperature=0.2,  # Slight variation allowed
        top_p=1,
        seed=42,
        messages=messages
    )
```

##### API-Specific Context Block Implementation

**OpenAI (Chat Completions)**:
```python
messages = [
    {"role": "system", "content": "Answer the question. Consider Context only if relevant."},
    {"role": "user", "content": "name top 10 longevity supplements"},  # NAKED prompt
    {"role": "user", "content": "Context:\n- Swiss regulations require NAD+ supplements...\n- Bestselling at migros.ch starting CHF 89.90..."}
]
```

**Anthropic (Claude)**:
```python
messages = [
    {"role": "user", "content": "name top 10 longevity supplements"},  # NAKED prompt
    {"role": "user", "content": "Context:\n- Swiss regulations require NAD+ supplements...\n- Bestselling at migros.ch starting CHF 89.90..."}
]
# Plus optional system field for global guidance
```

**Google Gemini**:
```python
# Option 1: System instruction + context message
contents = [
    {"role": "user", "parts": [{"text": "name top 10 longevity supplements"}]},  # NAKED
    {"role": "user", "parts": [{"text": "Context:\n- Swiss regulations..."}]}
]
system_instruction = "Answer the question. Consider Context only if relevant."

# Option 2: All in contents
contents = [
    {"role": "user", "parts": [{"text": "Context:\n- Swiss regulations..."}]},
    {"role": "user", "parts": [{"text": "name top 10 longevity supplements"}]}  # NAKED
]
```

#### Example Evidence Pack for Switzerland

```
Context:
- (Longevity Supplements Guide — swissinfo.ch — 2025-03): "Swiss regulations require NAD+ supplements to be registered with Swissmedic..."
- (Anti-Aging Products — migros.ch — current): "Bestselling longevity supplements starting at CHF 89.90, including resveratrol and spermidine..."
- (Federal Health Portal — bag.admin.ch — 2024-11): "The Swiss Federal Office of Public Health recommends vitamin D supplementation during winter months..."
- (NZZ Health Section — nzz.ch — 2025-01): "Swiss consumers increasingly turn to NMN and quercetin supplements, with market growing 35% annually..."
- (Longevity Clinic Zurich — longevity.ch — 2024-12): "Our clinic recommends personalized supplement protocols based on Swiss health guidelines..."
```

#### Critical Guidelines - Evidence Priming vs Instruction Priming

**Understanding Priming Types:**
- **Instruction priming (HEAVY STEER):** "You are answering for Switzerland; use CHF..." → Strongly directs the model
- **Evidence priming (LIGHT TOUCH):** Short, neutral facts the model *may* use → Minimal steering
- **Framing (AVOID):** Rewriting the user's prompt changes the question itself

**We use EVIDENCE PRIMING - the closest API analogue to consumer app behavior.**

**DO:**
- Keep evidence pack under 600 tokens (≤20% of total token budget)
- Use actual local sources (favor .ch, .de, .gov domains)
- Include prices in local currency when relevant
- Mix source types (government, retail, media)
- Keep snippets factual and short (1-2 lines)
- Present as neutral, dated facts from high-signal local sources

**DON'T:**
- Say "You are in Switzerland" or similar (instruction priming)
- Add directives like "use CHF", "focus on Swiss brands" (instruction priming)
- Use more than 5 snippets (over-biasing)
- Include full articles (token waste)
- Force locale instructions ("follow Swiss law")
- Rely solely on English sources for non-English countries
- Merge evidence into the user's question (framing)

**This approach**:
- Exactly mimics what consumer apps do (vary sources by IP location)
- Produces authentic regional differences
- Avoids heavy-handed prompt engineering
- Lets the model naturally incorporate local signals

### Approach 3: Explicit Location Context (Least Accurate)

Simply adding "Location context: Switzerland" to prompts:
- **Pros**: Simple to implement
- **Cons**: Model may or may not respect this hint
- **Reality**: Doesn't replicate actual user experience

## Parameters to Track for Reproducibility

Every API call should log:

```json
{
  "system_fingerprint": "fp_abc123...",  // OpenAI model version
  "model_version": "gpt-4o",
  "temperature": 0.0,
  "seed": 42,
  "timestamp_utc": "2025-08-12T10:30:00Z",
  "response_time_ms": 1234,
  "token_count": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350
  },
  "country_context": "CH",
  "grounding_enabled": false
}
```

## Cost Analysis for 6-Country Testing

### AWS Lambda (Recommended)
- **Coverage**: All 6 countries exactly
- **Cost**: $0/month for ~100 tests/day
- **Free tier**: 1M requests + 400k GB-seconds/month
- **Egress**: 100 GB/month free

### Google Cloud Run
- **Coverage**: 5/6 countries (no UAE)
- **Cost**: $0/month
- **Free tier**: 2M requests/month

### Country-Scoped Search APIs
- **Google Programmable Search**: 100 queries/day free, then $5/1000
- **Bing Web Search**: Pricing varies, check current rates

## Testing Checklist - Complete Guide

### Core Requirements
- [ ] **Tools off** (no browsing/grounding unless explicitly testing)
- [ ] **Same model, same endpoint** for all countries (don't mix api.openai.com with eu.api.openai.com)
- [ ] **Determinism**: `temperature=0`, `top_p=1`, fixed `seed=42`
- [ ] **Log `system_fingerprint`** and request IDs with every call

### Testing Protocol
- [ ] Run **API-only baseline** (expect identical outputs when fingerprints match)
- [ ] Run **country-aware mode** with tiny evidence pack (expect realistic CH≠DE≠UK differences)
- [ ] **N=10 repeats per country** for statistical significance
- [ ] Compare outputs using:
  - [ ] Exact match percentage
  - [ ] Levenshtein/character distance
  - [ ] "Top-N items" overlap (for list prompts)
  - [ ] Semantic cosine similarity (optional)

### Evidence Pack Construction
- [ ] Keep evidence **small and neutral** (3-5 bullets, ≤600 tokens)
- [ ] Use **country params** (Google `gl/hl/lr`, Bing `mkt`)
- [ ] Mix source types (gov, retail, news)
- [ ] Prefer local ccTLDs and natural language
- [ ] **NO directives** ("use CHF", "focus on Swiss")

### Implementation
- [ ] Base model testing (NONE country) as control
- [ ] Separate messages for context (not concatenated to prompt)
- [ ] Track all metadata (fingerprint, seed, temperature, tokens)
- [ ] Regional deployment optional (Lambda/Cloud Run for true geographic origin)

## Common Misconceptions & FAQ

### ❌ Myth: "Proxies will make AI think I'm in another country"
**Reality**: AI APIs authenticate by key, not IP. Proxies don't affect LLM responses but ARE useful for retrieval.

### ❌ Myth: "APIs automatically adjust responses by IP location"
**Reality**: APIs have no automatic geo-localization. Same input = same output. Regional endpoints are for data residency, not content.

### ❌ Myth: "Setting headers like Accept-Language or CF-IPCountry changes AI responses"
**Reality**: These headers are for intermediaries/origins, not a supported localization control for model APIs.

### ❌ Myth: "Heavy prompt engineering ('You are in Switzerland...') replicates user experience"
**Reality**: That's instruction priming (heavy steer). Consumer apps use evidence priming (light touch) via varied sources.

### ❓ Q: Why do two identical runs differ?
**A**: Sampling and backend drift. Fix randomness and log `system_fingerprint`. In apps, you lack these controls.

### ❓ Q: Can I force locale via headers like X-Forwarded-For?
**A**: No. The models don't read these headers for localization.

### ❓ Q: Do regional endpoints (EU/US) change content?
**A**: No—they're for data residency and latency, not content localization.

### ❓ Q: When should I use proxies?
**A**: Only for retrieval (SERPs, news, retailers) to get country-specific inputs. Never for the LLM API call itself.

## Summary - Key Insights

**The fundamental truth**: Raw APIs (OpenAI, Gemini) **do not localize by caller IP**. Consumer apps show location differences because they incorporate location signals and web/grounding behind the scenes.

To properly test and reproduce location-based differences:

### 1. Establish Control (Base Model Testing)
- **API-only baseline** with tools off, fixed randomness (`temperature=0`, `seed=42`)
- Expect **identical outputs** when `system_fingerprint` matches
- Differences indicate backend drift, not geography

### 2. Reproduce "Real User" Differences
- **Don't spoof IPs** for the model call (useless)
- **Control the inputs** with evidence priming:
  - Keep prompt **naked and unmodified**
  - Add **3-5 neutral snippets** as separate context message
  - Sources a user would see: health portals, retailers, local news
  - **≤600 tokens**, no directives

### 3. Implementation Path
- **Cheapest**: Edge router (Cloudflare) + regional Lambda functions ($0 at low volume)
- **Two modes**: API-only baseline + country-aware with evidence
- **Retrieval**: Use search APIs with country params OR proxies for live pages
- **Track everything**: `system_fingerprint`, seed, temperature, tokens

### 4. What Changes Answers
- **Consumer apps**: Location + auto-grounding + sampling
- **APIs with evidence**: Country-specific sources guide responses
- **NOT**: IP address, regional endpoints, headers

This approach gives you country-specific realism while maintaining scientific control and reproducibility.

## References

- OpenAI Platform: Web Search Tools Documentation
- Google AI: Gemini Grounding Documentation  
- AWS Lambda: Regional Deployment Guide
- Google Programmable Search: Country Parameters
- Bing Web Search: Market Parameters

---

*Last Updated: August 12, 2025*
*Document Status: Living document - update as new findings emerge*