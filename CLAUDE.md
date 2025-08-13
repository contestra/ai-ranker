# CLAUDE.md - AI Rank & Influence Tracker

## CRITICAL: Ambient Blocks Methodology

### What are Ambient Blocks?

**Ambient Blocks** are minimal context snippets (≤350 chars) containing ultra-neutral civic/government cues that make an AI naturally infer the user's location WITHOUT mentioning brands, products, or even the industry being tested.

**The Goal**: Make the AI think "this user is in Germany" by providing tiny ambient cues (like timezone, government portal keywords, local formatting) that feel like system state or recent browsing - NOT by injecting search results.

### How Ambient Blocks Work - The Clean Method

#### 1. Build a Tiny Ambient Context Block (≤350 chars)
For Germany, include 3-5 ultra-neutral signals:
```
Ambient Context (localization only; do not cite):
- 2025-08-12 14:05, UTC+01:00
- bund.de — "Führerschein verlängern"
- 10115 Berlin • +49 30 xxxx xxxx • 12,90 €
- national weather service shows Berlin
```

#### 2. Send as SEPARATE Message (Keep Prompt Naked!)
```python
# ✅ CORRECT - Prompt stays pure:
messages = [
    {"role": "system", "content": "Answer in user's language. If locale ambiguous, use Ambient Context. Do not cite it."},
    {"role": "user", "content": ambient_block},    # Ambient signals
    {"role": "user", "content": "What is AVEA?"}   # NAKED prompt
]

# ❌ WRONG - Never concatenate:
prompt = ambient_block + "\nWhat is AVEA?"  # This contaminates the prompt!
```

#### 3. AI Naturally Infers Location
The AI sees:
- German timezone (UTC+01:00)
- German government portal (bund.de)
- German phone/postal format
- EUR currency symbol

And thinks: "User is probably in Germany" → adapts response accordingly

### What Goes in an Ambient Block?

#### ✅ INCLUDE (Civic/Neutral Only):
- **Timestamp with timezone**: `2025-08-12 14:05, UTC+01:00`
- **Government portals**: `bund.de`, `gov.uk`, `admin.ch` (domain only, no URLs)
- **Civic keywords in local language**: `"Führerschein verlängern"` (renew license)
- **Formatting samples**: `10115 Berlin • +49 30 xxxx xxxx • 12,90 €`
- **Weather stub**: `national weather service shows Berlin` (no temp for evergreen content)
- **Transit/agency acronyms**: `DB`, `SBB`, `DVLA`, `IRS`

#### ❌ NEVER INCLUDE:
- Commercial sites (Amazon, IKEA, retailers)
- Brand names or product categories
- News outlets or media brands
- Anything related to the industry being tested
- Search results or web snippets
- URLs or clickable links

### KEY PRINCIPLES

1. **Ultra-minimal (≤350 chars total)**
   - Longer blocks can steer content
   - Just enough to tilt location inference

2. **Purely civic/government signals**
   - No commercial contamination
   - Nothing that could bias brand responses

3. **Local language for authenticity**
   - German civic terms for Germany
   - Not translations or English descriptions

4. **Must be SEPARATE message**
   - Never concatenate to prompt
   - Prompt remains completely unmodified

5. **One-time use per conversation**
   - Never reuse chat threads
   - Fresh context each time

### Validation & Guardrails

1. **Leak Detection**: After response, check if any 2-3 word phrases from Ambient Block appear in output
2. **Probe Questions**: Test with "What's the VAT rate?" to confirm location inference worked
3. **Fixed Parameters**: `temperature=0`, `top_p=1`, fixed seed for reproducibility

### Current Implementation Status (Aug 12, 2025)
- ✅ Ambient Blocks fully implemented for 8 countries
- ✅ Context sent as SEPARATE message (not concatenated)
- ✅ Replaced evidence pack with clean Ambient Blocks
- ✅ All 8 countries available in frontend (DE, CH, US, GB, AE, SG, IT, FR)
- ✅ System prompt allows silent locale adoption while preventing explicit mentions
- ✅ Context sent BEFORE question (feels like prior state, not something to explain)
- ✅ Fixed GPT-5 temperature requirement (must be 1.0)

## Supported Countries for Ambient Blocks (Updated Aug 12, 2025)

### Full Local Language Support:
1. 🇩🇪 **Germany (DE)** - German throughout (bund.de, Bürgeramt, "Führerschein umtauschen")
2. 🇮🇹 **Italy (IT)** - Italian throughout (Agenzia delle Entrate, "codice fiscale richiesta")
3. 🇫🇷 **France (FR)** - French throughout (service-public.fr, "Carte d'identité renouvellement")
4. 🇦🇪 **UAE (AE)** - Arabic throughout ("الهوية والجنسية", "تجديد بطاقة الهوية الإماراتية")

### Bilingual/English:
5. 🇨🇭 **Switzerland (CH)** - German header with German/French civic terms (ch.ch, admin.ch)
6. 🇺🇸 **United States (US)** - English (state DMV/DOT, IRS, SSA, multi-timezone)
7. 🇬🇧 **United Kingdom (GB)** - English (GOV.UK, DVLA, NHS, HMRC)
8. 🇸🇬 **Singapore (SG)** - English (ICA, Singpass, CPF, HDB)

## Project Overview
AI visibility and brand strength analysis tool that measures how well AI models (GPT-5, Gemini) recognize and understand brands with geographic localization via Ambient Blocks.

## Recent Work (August 11-13, 2025)

### Fixed Critical Issues

#### 1. Windows Encoding Error with Turkish Characters ✅
**Problem**: Application crashed with `'charmap' codec can't encode character '\u0130'` when GPT-5 mentioned Turkish companies (e.g., "Türk Telekom")

**Solution**:
- Added `sanitize_for_windows()` function to replace Turkish characters (İ, ş, ğ, ç, ö, ü)
- Removed all debug print statements that could contain user data
- Applied sanitization throughout response pipeline
- Files modified: `backend/app/api/brand_entity_strength.py`, `backend/app/llm/langchain_adapter.py`

#### 2. GPT-5 Timeout Issues ✅
**Problem**: GPT-5 takes 50-90 seconds to respond, causing frontend timeouts

**Solution**:
- Increased frontend timeout to 120 seconds with AbortController
- Added backend timeout at 90 seconds with graceful fallback
- Reduced max_tokens from 4000 to 2000 for faster responses
- File modified: `frontend/src/components/EntityStrengthDashboard.tsx`

#### 3. Entity Disambiguation Logic ✅
**Problem**: System incorrectly classified brands as UNKNOWN when multiple entities shared the same name

**Solution**:
- Improved classification logic to downgrade to KNOWN_WEAK (not UNKNOWN) when disambiguation needed
- Enhanced detection of when AI talks about wrong industry
- Better handling of GPT-5's non-deterministic responses

#### 4. Per-Template Model Selection ✅ (August 13, 2025)
**Problem**: Model selection was global, changing one template's model changed all templates

**Solution**:
- Added `model_name` field to prompt_templates table
- Updated frontend to save model_name per template
- Fixed SQLAlchemy row access issue that prevented model_name from being retrieved
- Each template now maintains its own model selection independently

## Test Case: AVEA Brand

**Current Behavior**:
- GPT-5 recognizes multiple AVEA entities (Turkish telecom, US software, ventilators)
- Sometimes mentions Swiss supplements brand, sometimes doesn't
- Correctly classified as KNOWN_WEAK (60% confidence) due to disambiguation
- Shows warning about multiple entities sharing the name

**Key Finding**: AVEA Life (Swiss supplements) has minimal recognition in GPT-5

## API Keys Configuration

All keys stored in `backend/.env`:
- `OPENAI_API_KEY`: For GPT-5 access
- `GOOGLE_API_KEY`: For Gemini 2.5 Pro access  
- `FLY_API_TOKEN`: For Fly.io deployment (organization-specific for SSO)

## Running the Application

### Backend
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Note: Backend can also be run without --reload flag for production

### Frontend
```bash
cd frontend
npm run dev
```

Access at: http://localhost:3001

### Current Session Status (Aug 13, 2025)
- Frontend running on port 3001
- Backend running on port 8000
- All encoding issues resolved
- GPT-5 models working with 30-second timeout
- AVEA brand properly shows KNOWN_WEAK with disambiguation warning

## Model Support Status

**Working Models:**
- ✅ Google Gemini 2.5 Pro: Fast, reliable responses
- ✅ GPT-5, GPT-5-mini, GPT-5-nano: Working with 30s timeout (may take 15-25 seconds)
- ✅ GPT-4o: Working with timeout

**Notes:**
- GPT-5 models require temperature=1.0 (automatically set)
- Added 30-second timeout to prevent hanging on slow responses
- Background endpoint bypasses HTTP context to avoid location leaks

## Known Issues & Limitations

1. **GPT-5 Response Times**: Can take 15-25 seconds per request
2. **Non-deterministic Results**: Models give slightly different answers each time
3. **Brand Recognition**: Many smaller brands classified as UNKNOWN or WEAK
4. **Location Leaks**: Some residual leaks may occur with certain prompt patterns

## Testing Commands

Test API directly with Google Gemini (WORKING):
```python
import requests
response = requests.post(
    'http://localhost:8000/api/brand-entity-strength',
    json={
        'brand_name': 'AVEA', 
        'domain': 'avea-life.com', 
        'vendor': 'google',  # Use 'google' for Gemini 2.5 Pro
        'include_reasoning': True
    }
)
print(f"Status: {response.status_code}")
if response.ok:
    data = response.json()
    print(f"Classification: {data['classification']['label']}")
    print(f"Confidence: {data['classification']['confidence']}%")
    print(f"Disambiguation: {data['classification']['disambiguation_needed']}")
```

### Expected Results for AVEA
- **Label**: KNOWN_WEAK
- **Confidence**: 60%
- **Disambiguation**: True
- **Other entities detected**:
  - Avea (Swiss longevity supplement brand)
  - AVEA Ventilator (medical device)
  - Former Turkish mobile operator

## Important Files

- `backend/app/api/brand_entity_strength.py` - Core entity strength logic
- `frontend/src/components/EntityStrengthDashboard.tsx` - Main UI component
- `GPT5_EMPTY_RESPONSE_ISSUE.md` - Documentation of GPT-5/GPT-4o empty response issue
- `WINDOWS_ENCODING_FIX.md` - Detailed documentation of encoding fixes
- `ENTITY_DISAMBIGUATION.md` - How disambiguation detection works
- `DE_LEAK_INVESTIGATION.md` - Investigation of "DE" leak in Ambient Blocks
- `LEAK_PREVENTION_FIXES.md` - Fixes applied to prevent location disclosure

## Deployment

Deploy to Fly.io:
```bash
cd backend
flyctl deploy
```

Requires `FLY_API_TOKEN` environment variable set.

## Recommendations for Future Work

1. Implement caching to avoid repeated GPT-5 calls
2. Add batch processing for multiple brands
3. Store results in database for historical tracking
4. Consider using faster models as primary with GPT-5 as fallback
5. Add progress indicators for long-running requests

## Contact & Support

For issues or questions about this codebase, reference this CLAUDE.md file which contains the most recent context and fixes applied.

## Development Environment & Tools

### MCP Servers (Claude Development Tools)

The following MCP (Model Context Protocol) servers are available to Claude during development sessions to assist with building and testing the AI Ranker application. These are NOT part of the deployed application:

1. **sequential-thinking** - Step-by-step problem solving during development
2. **playwright** - Browser automation for testing UI features
3. **lighthouse** - Performance analysis during development
4. **fetch** - Web content retrieval for testing
5. **memory** - Persistent memory for development context
6. **filesystem** - File operations during development
7. **sqlite** - Database testing and development
8. **ref-tools** - Managing references and documentation

Note: These are Claude's development tools, not application dependencies.

### Application Dependencies

#### Frontend Libraries (Production)
- **react-hook-form** - Performant forms with minimal re-renders (reduces unnecessary component updates)
- **formik** - Alternative form library with built-in validation and field management
- **lodash.debounce** - Debounce function for input delays (prevents API calls on every keystroke)
- **use-debounce** - React hook for debouncing values/callbacks (alternative to lodash.debounce)
- **@tanstack/react-query** - Server state management, caching, background refetching (perfect for GPT-5's 50-90 second response times)
- **@tanstack/react-virtual** - Virtual scrolling for rendering only visible items in long entity lists
- **zod** - TypeScript-first schema validation for form data and API responses (NOT for website schema/SEO checking)

Installation command used:
```bash
cd frontend && npm install react-hook-form formik lodash.debounce use-debounce @tanstack/react-query @tanstack/react-virtual zod
```

Use Cases:
- Form validation and handling without performance issues
- Debouncing search inputs to reduce API calls
- Caching AI model responses to avoid repeated expensive calls
- Virtualizing long lists of brands/entities for better performance
- Type-safe validation of API requests and responses

## Schema.org Extraction & Validation Tool (Added Aug 11, 2025)

### Overview
Created a comprehensive Schema.org JSON-LD extraction and validation tool using Puppeteer and Zod to analyze website structured data, particularly for Organization and Product schemas.

### Files Created
- `frontend/src/lib/schemaExtractor.ts` - TypeScript schema extractor with Zod validation
- `backend/app/services/schema_extractor.py` - Python version with Pydantic validation
- `backend/test_schema_extraction.js` - Test script for schema analysis

### Key Features

#### 1. Organization Schema Support
- Full support for complex Organization schemas with @graph structures
- Handles @id references for linked data
- Supports business identifiers (tax IDs, registration numbers)
- Industry classifications (ISIC, NAICS)
- Organizational hierarchy (parent/sub organizations)
- Founder information with Person schemas
- **Disambiguation support** - Critical for brands like AVEA that share names with other companies
- Alternate names and legal names
- Contact points and social media links

#### 2. Product Schema Support
Supports 15+ product types including:
- Standard Product
- **DietarySupplement** (with active ingredients, dosage, safety info)
- Drug, MedicalDevice
- SoftwareApplication, WebApplication
- Book, Movie, Game, FoodProduct
- Vehicle, IndividualProduct, ProductModel

#### 3. Validation & Scoring System
- Quality scoring (0-100) based on completeness
- Type-specific validation (e.g., ingredients required for supplements)
- Bonus points for advanced features:
  - @id for linked data (+5 points)
  - disambiguatingDescription (+5 points)
  - Brand relationships (+3 points)
  - Organizational structure (+3 points)
- Detailed warnings for missing recommended fields
- Error reporting for invalid schemas

#### 4. AVEA-Specific Optimizations
The tool is optimized to recognize AVEA's sophisticated schema implementation:
- Detects and rewards disambiguation descriptions
- Handles complex @graph with multiple entities
- Validates DietarySupplement products like Biomind
- Recognizes Swiss business identifiers
- Supports multi-national subsidiary structure

### Usage Example
```javascript
const { SchemaExtractor } = require('./schemaExtractor');

const extractor = new SchemaExtractor();
await extractor.init();
const results = await extractor.analyzeWebsite('https://www.avea-life.com');

// Results include:
// - Overall score (0-100)
// - Validated Organization schemas
// - Validated Product/DietarySupplement schemas
// - Warnings and recommendations
// - Linked data relationships
```

### Why This Matters for AI Ranking
Well-structured Schema.org data helps AI models:
1. **Disambiguate brands** - Critical when multiple entities share a name
2. **Understand relationships** - Parent companies, subsidiaries, brands
3. **Identify products accurately** - Especially for specialized types like supplements
4. **Extract business information** - Legal entities, locations, identifiers
5. **Build knowledge graphs** - Through @id linking and references

### Testing
Run the test script to analyze any website:
```bash
node backend/test_schema_extraction.js
```

This tool helps ensure websites have properly structured data that AI models can understand, improving brand visibility and reducing ambiguity in AI responses.

### Development Notes
- MCP servers listed above are Claude's development tools, configured globally in Claude Code
- The `.claude/settings.local.json` file contains permission settings for various commands during development
- These tools help Claude build and test features but are not part of the deployed application

## Prompt Tracking Feature (Added August 12, 2025)

### Overview
Added comprehensive prompt tracking system to test how AI models respond to prompts about brands across different countries and grounding modes.

### Features Implemented
1. **Template Management**
   - Create, edit, copy, and delete prompt templates
   - Save prompt configurations for reuse
   - Support for multiple countries and grounding modes per template

2. **Multi-Country Testing**
   - Currently uses location context in prompts (e.g., "Location context: US")
   - **NOTE**: Does NOT use actual proxy/VPN for geo-located requests
   - Countries supported: US, GB, DE, CH, AE, SG

3. **Grounding Modes**
   - **Model Knowledge Only**: Uses only the model's training data
   - **Grounded (Web Search)**: Uses model's native web search capability
   - Can test both modes simultaneously for comparison

4. **Model Selection**
   - GPT-5, GPT-5 Mini, GPT-5 Nano (note: return empty responses via API)
   - GPT-4o, GPT-4o Mini (legacy)
   - Gemini 2.5 Pro, Gemini 2.5 Flash (recommended, working)

5. **Analytics Dashboard**
   - Overall mention rate and confidence scores
   - Comparison by grounding mode
   - Comparison by country
   - Test run history with template names (not just IDs)

### Technical Implementation
- **Backend**: FastAPI endpoints in `app/api/prompt_tracking.py`
- **Database**: SQLAlchemy models supporting both SQLite (local) and PostgreSQL (production)
- **Frontend**: React component `PromptTracking.tsx` with full CRUD operations
- **API Routes**:
  - GET/POST `/api/prompt-tracking/templates`
  - PUT/DELETE `/api/prompt-tracking/templates/{id}`
  - POST `/api/prompt-tracking/run`
  - GET `/api/prompt-tracking/analytics/{brand_name}`

### Geographic Testing Implementation

**Fundamental Truth**: Raw APIs (OpenAI, Gemini) **do NOT localize by caller IP**. Consumer apps show differences because they use location signals + auto-grounding.

**Current Implementation**: Basic location context in prompts (e.g., "Location context: US")
- ✅ Base Model (NONE) option now available for control testing
- ⚠️ Simple context approach doesn't replicate real user experience
- 📋 Ready for evidence pack implementation

**Proper Implementation**: See [GEO_LOCATION_AI_TESTING.md](./GEO_LOCATION_AI_TESTING.md) for complete guide.

**Testing Modes**:
1. **Base Model Testing (NONE)** - Control baseline ✅ IMPLEMENTED
   - Pure model response, no geographic influence
   - Fixed: temperature=0, seed=42, top_p=1
   - Expect identical outputs when system_fingerprint matches
   
2. **Evidence Pack Mode** - Replicate consumer apps 🚧 TODO
   - 3-5 neutral snippets (≤600 tokens) as separate message
   - Country-specific sources: health portals, retailers, news
   - NO directives ("use CHF"), only neutral facts
   
3. **Legacy Location Context** - Current simple implementation ✅ WORKING
   - Adds "Location context: {country}" to prompt
   - Temporary until evidence packs implemented

**Key Implementation Path** - Country-Scoped Evidence Priming with Context Blocks:
1. **Search with country parameters**: Google (`gl=ch`, `hl=de`, `lr=lang_de`) or Bing (`mkt=de-CH`)
2. **Build minimal evidence pack**: 3-5 snippets, 300-600 tokens total (≤20% of token budget)
   - Government/health sites
   - Local retailers with prices in CHF/EUR/etc
   - Major local news sources
   - Each snippet only 1-2 lines
3. **CRITICAL - Use Evidence Priming via Context Blocks**: 
   - Send evidence as **separate message** in API payload
   - Keep user prompt "naked" and unmodified
   - Add evidence as additional message in the messages array
   - Use **evidence priming** (neutral facts) NOT instruction priming (directives like "use CHF")
   - Do NOT concatenate to the prompt text
4. **Let model naturally incorporate**: Local prices, regulations, and sources guide the response

**Correct Implementation Example (OpenAI)**:
```python
messages = [
    {"role": "system", "content": "Answer the question. Consider Context only if relevant."},
    {"role": "user", "content": "name top 10 longevity supplements"},  # NAKED prompt
    {"role": "user", "content": "Context:\n- (Migros.ch): Longevity from CHF 89.90...\n- (bag.admin.ch): Swiss Federal Office recommends..."}  # SEPARATE message
]
```

This exactly replicates what consumer apps do - they vary the search sources by location via separate context, not by modifying the model or prompt itself.

### Key Insights from Research
1. **Proxies are useless for LLM APIs** - They authenticate by key, not IP
2. **Proxies ARE useful for retrieval** - SERPs and retailer pages DO vary by country
3. **Regional endpoints (EU/US)** - For data residency, NOT content localization
4. **Headers don't work** - CF-IPCountry, Accept-Language don't affect API responses
5. **Instruction vs Evidence priming** - Heavy steering vs light touch neutral facts

### Implementation Architecture (6-Country Testing)
**Recommended**: Edge router (Cloudflare) + Regional Lambda functions
- US: us-east-1, UK: eu-west-2, DE: eu-central-1
- CH: eu-central-2, UAE: me-central-1, SG: ap-southeast-1
- Cost: ~$0 at 100 tests/day (within free tiers)

### Known Limitations & Status
1. ✅ Base Model testing implemented (NONE country option)
2. 🚧 Evidence pack implementation pending (currently using simple context)
3. ⚠️ GPT-5 models return empty responses (use Gemini)
4. 📋 System_fingerprint tracking ready in schema, not yet utilized
5. 🔄 Need N=10 repeats per country for statistical significance