# CLAUDE.md - AI Rank & Influence Tracker

## Project Overview
AI visibility and brand strength analysis tool that measures how well AI models (GPT-5, Gemini) recognize and understand brands.

## Recent Work (August 11, 2025)

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

### Current Session Status (Aug 11, 2025)
- Frontend running on port 3001 (bash_1)
- Backend running on port 8000 (bash_10)
- All encoding issues resolved
- **IMPORTANT**: All GPT-5 models return empty responses
- **SOLUTION**: Using Google Gemini 2.5 Pro (works perfectly)
- AVEA brand properly shows KNOWN_WEAK with disambiguation warning

## Critical Issue: OpenAI Models Return Empty Responses

**ALL GPT-5 models return empty strings:**
- gpt-5, gpt-5-mini, gpt-5-nano: Empty responses
- gpt-4o, gpt-4-turbo: Also empty through API (but work in direct OpenAI client tests)

**Working Solution:**
- Google Gemini 2.5 Pro: ✅ Returns proper responses
- Frontend defaults to Gemini
- See `GPT5_EMPTY_RESPONSE_ISSUE.md` for full details

## Known Issues & Limitations

1. **OpenAI Models Broken**: All OpenAI models return empty responses through our API
2. **Non-deterministic Results**: Models give slightly different answers each time
3. **Brand Recognition**: Many smaller brands classified as UNKNOWN or WEAK

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

## MCP Servers & Tools Configuration

### Connected MCP Servers

The following MCP (Model Context Protocol) servers are configured and connected in Claude Code:

1. **sequential-thinking** - `npx @modelcontextprotocol/server-sequential-thinking`
   - Step-by-step problem solving and reasoning

2. **playwright** - `npx @playwright/mcp`
   - Advanced browser automation with accessibility tree

3. **lighthouse** - `npx @danielsogl/lighthouse-mcp`
   - Website performance, accessibility, and UX analysis

4. **fetch** - `npx @kazuph/mcp-fetch`
   - Web content downloading and conversion

5. **memory** - `npx @modelcontextprotocol/server-memory`
   - Knowledge graph and persistent memory storage

6. **filesystem** - `npx @modelcontextprotocol/server-filesystem`
   - File operations across Documents, Projects, Downloads, Desktop

7. **sqlite** - `npx mcp-sqlite C:\Users\leedr\Projects\test.db`
   - Database operations with test.db file

8. **ref-tools** - `npx @ref-tools/ref-tools-mcp`
   - Reference management and citation tools
   - GitHub: https://github.com/ref-tools/ref-tools-mcp
   - Useful for tracking sources and references in brand analysis

### Local Dependencies

#### Browser Automation
- **puppeteer** (^24.16.1) - Browser automation library

#### Performance & Forms Libraries (Installed Aug 11, 2025)
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

### Notes
- MCP servers are configured globally in Claude Code, not in the project-specific `.claude/settings.local.json`
- The `.claude/settings.local.json` file contains permission settings for various commands