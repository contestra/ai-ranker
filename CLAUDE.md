# CLAUDE.md - AI Rank & Influence Tracker

## 🚨 WINDOWS USERS: ALWAYS SET UTF-8 ENCODING FIRST! 🚨

### BEFORE DOING ANYTHING ELSE ON WINDOWS:
```bash
set PYTHONUTF8=1
```

**This prevents 90% of "Unicode/encoding" errors!** Without this, you'll see:
- `'charmap' codec can't encode character '\u2713'` (checkmarks)
- `'charmap' codec can't encode character '\u0130'` (Turkish İ)
- `'charmap' codec can't encode character '\u20ac'` (Euro €)

**Common triggers:**
- Using ✓ or ✗ symbols in print statements
- AI responses with international brands
- Currency symbols (€, £, ¥)
- Any non-ASCII characters

**The fix is ALWAYS the same:** Set `PYTHONUTF8=1` before running Python!

### Python Script UTF-8 Handling

**CRITICAL**: When writing Python scripts on Windows that print Unicode characters (emojis, checkmarks, etc.):

1. **Option 1 - Configure stdout for UTF-8** (Preferred):
```python
# Add at the top of any script that prints Unicode
import sys, io
sys.stdout.reconfigure(encoding='utf-8')  # Python 3.7+
# OR for Python < 3.7:
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

2. **Option 2 - Replace non-ASCII characters**:
```python
# Instead of: print("✅ Success")
# Use: print("[SUCCESS]")
# Or strip: text.encode('ascii', errors='replace').decode('ascii')
```

**DO NOT**: Keep removing emojis and re-adding them in a loop. Either configure UTF-8 properly or use ASCII-only text.

---

## 🚨 CRITICAL: NO FALLBACK TO DIRECT API ALLOWED

### ABSOLUTE RULE: Fallback = System Failure
**See [CRITICAL_NO_FALLBACK_ALLOWED.md](./CRITICAL_NO_FALLBACK_ALLOWED.md) for details**

---

## 🚨 CRITICAL: Shell Context on Windows - DO NOT RUN FROM GIT BASH!

### The #1 Authentication Problem: Shell Context Mismatch

**NEVER run Claude Code or the backend from Git Bash on Windows!**

**The Problem:**
- PowerShell creates ADC at: `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- Git Bash looks for ADC at: `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
- **These are DIFFERENT locations!**

**Result:** "Your default credentials were not found" error even when ADC exists!

### The FASTEST FIX - Explicit ADC Path

```powershell
# In PowerShell - Bypass ALL path confusion
$env:GOOGLE_APPLICATION_CREDENTIALS = "$env:APPDATA\gcloud\application_default_credentials.json"

# Why this works:
# - Google libraries check this env var FIRST
# - Bypasses Bash/MSYS search paths entirely
# - No symlinks needed (which often fail on Windows)
# - Works from any shell after setting
```

### Where to Run Claude Code on Windows:
✅ **PowerShell** (RECOMMENDED)
✅ **Windows Command Prompt** (cmd.exe)
✅ **Windows Terminal with PowerShell profile**

❌ **NEVER from:**
- Git Bash (unless you set GOOGLE_APPLICATION_CREDENTIALS explicitly)
- WSL (Windows Subsystem for Linux)
- MinGW
- Cygwin

### The Golden Rule:
**Set GOOGLE_APPLICATION_CREDENTIALS explicitly to bypass all path issues!**

If you must use different shells:
1. Always set `GOOGLE_APPLICATION_CREDENTIALS` to the Windows ADC path
2. This makes ADC work from ANY shell context
3. No symlinks needed (they often fail anyway)

**See [AUTHENTICATION.md](./AUTHENTICATION.md) for complete details and workarounds**

---

## 🔐 AUTHENTICATION - CRITICAL RULES

### 🚨 CRITICAL AUTHENTICATION REQUIREMENTS:

#### 1. MUST Grant TokenCreator Permission (Most Common Error!)
```powershell
# THIS IS REQUIRED - Without it, you get "Permission iam.serviceAccounts.getAccessToken denied"
$SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
$USER = gcloud config get account  # Should be l@contestra.com

gcloud iam service-accounts add-iam-policy-binding $SA `
  --role="roles/iam.serviceAccountTokenCreator" `
  --member="user:$USER" `
  --project contestra-ai

# Verify it worked:
gcloud auth print-access-token --impersonate-service-account=$SA
```

#### 2. Use PowerShell on Windows (Not Git Bash/WSL)
- Git Bash/WSL causes ADC to be written to wrong location
- Must do everything in ONE PowerShell window
- **CRITICAL**: Backend MUST also run in PowerShell, not Git Bash!
- ADC paths are different: PowerShell uses `C:\Users\...\AppData\Roaming\gcloud\`
- Git Bash looks for ADC at `/c/Users/.../.config/gcloud/` (won't find Windows ADC!)

#### 3. CLI Impersonation is OK in PowerShell (Updated Understanding)
```powershell
# This WORKS in interactive PowerShell (after granting TokenCreator):
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com

# But for headless/CI, use environment variable:
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"
```

### ⚠️ For authentication issues with Vertex AI or OpenAI:
**DO NOT** attempt to fix authentication issues directly. Instead:
1. **IMMEDIATELY** use the `vertex-auth-guardian` agent via the Task tool
2. This specialized agent knows to AVOID CLI-level impersonation
3. It uses the correct env var approach that actually works

**Example:**
```
If you see: "Vertex AI Authentication error", "ADC missing/expired", "Reauthentication required"
→ Use Task tool with subagent_type="vertex-auth-guardian"
```

### Quick Fix Script:
Use `RUN_THIS_TO_FIX_VERTEX.bat` which:
- Removes CLI impersonation first (critical!)
- Sets up ADC properly
- Uses environment variables for impersonation
- Sets persistent env vars with `setx`

---

## Latest Update (August 18, 2025) - Complete UI Testing & Authentication Documentation

### ✅ Session Achievements

**1. UI Restoration & Testing**:
- Fixed broken Prompt Configuration Builder after shadcn updates
- Verified GPT-5 shows 3 grounding modes (OFF, PREFERRED, REQUIRED)
- Verified Gemini shows 2 grounding modes (Model Knowledge Only, Grounded)
- Template metadata display working (SHA-256, canonical JSON, system parameters)
- Results tab functional with proper status tracking

**2. Authentication Fixed & Documented**:
- Resolved Vertex AI authentication using proper ADC + Service Account impersonation
- Created comprehensive **[AUTHENTICATION.md](./AUTHENTICATION.md)** merging all master documents
- Key lesson: Use standard `gcloud auth application-default login` (even though it says "Sign in to gcloud CLI")
- Set `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=vertex-runner@contestra-ai.iam.gserviceaccount.com`
- No service account keys, no raw OAuth URLs

**3. Documentation Consolidated**:
- Merged 4 separate authentication documents into single source of truth
- Added debugging tools, OIDC helper scripts, and clear DO/DON'T guidelines
- Included both local development and production (Fly.io WIF) setup

**Current System Status**:
- Frontend: Running on port 3001 ✅
- Backend: Running on port 8000 with proper env vars ✅
- Authentication: ADC configured with SA impersonation ✅
- UI: All features functional and tested ✅

---

## Previous Update (August 18, 2025) - UI Restoration & Prompt Builder Fix

### 🔧 Session Summary
**Task**: Fixed broken UI after shadcn component updates that removed the prompt configuration builder functionality.

**Problems Solved**:
1. ✅ **Prompt Builder Restored**: Created PromptTrackingFixed.tsx with complete configuration builder
2. ✅ **Grounding Modes Fixed**: GPT models now show OFF/PREFERRED/REQUIRED, Gemini shows Model Knowledge Only/Grounded
3. ✅ **Metadata Display**: Added all missing metadata (SHA-256 hashes, canonical JSON, system parameters)
4. ✅ **Template Management**: Copy, expand, and run operations all working
5. ✅ **Simultaneous Runs**: Fixed global loading state that prevented running multiple templates

**Key Implementation Details**:
- **Component**: `frontend/src/components/PromptTrackingFixed.tsx` - Complete rewrite with all features
- **Templates Tab**: Shows canonical JSON, SHA-256, temperature/seed/top_p, provider badges
- **Results Tab**: Displays provenance strips, grounding metadata, citations, cross-linking
- **Configuration Builder**: Select countries, grounding modes, models to generate immutable prompts

**Current Status**:
- Frontend: Running on port 3001 ✅
- Backend: Running on port 8000 ✅
- UI: Fully functional with real API data ✅
- Vertex Auth: Needs reauthentication (fallback to direct API working)

**Note**: System is operational despite Vertex auth issue - falls back to direct Gemini API for non-grounded queries.

---

## Previous Update (August 17, 2025 Evening) - UI Enhancements with Shadcn/UI ✅

### 🎨 Professional UI Upgrade Complete
**Major Achievement**: Transformed the Prompt Tracking interface with shadcn/ui components for a modern, professional experience.

**What's New**:
- **Shadcn/UI Integration**: Added 9 components (Card, Sheet, Accordion, Badge, etc.)
- **Enhanced Templates Tab**: Provider badges, run statistics, expandable configuration drawer
- **Enhanced Results Tab**: Provenance strips, citations, cross-linking to templates
- **Null Safety**: Fixed all runtime errors with proper TypeScript handling
- **Empty States**: Graceful fallbacks when no data exists

**Key Features**:
- ✅ Expandable drawers (600px Sheet components) for detailed views
- ✅ Accordion sections for organized metadata display
- ✅ Color-coded provider badges (green=OpenAI, blue=Vertex)
- ✅ SHA-256 hash display for configuration integrity
- ✅ Clickable citations with external link icons
- ✅ Cross-navigation between templates and results

**Critical Fix**: Frontend MUST run on port 3001 (`npm run dev -- -p 3001`), port 3000 is occupied.

**Testing Note**: Playwright MCP configured but requires session restart to activate. Use for automated testing in next session.

See `UI_ENHANCEMENTS_IMPLEMENTATION.md` for complete implementation details.

## Previous Update (August 17, 2025 Afternoon) - Grounding & Routing FULLY FIXED ✅

### 🚀 CRITICAL FIXES COMPLETED - System Fully Operational

**Major Issues Resolved**:
1. **Citation Validation Error** ✅ - Vertex citations now properly coerced from strings to dicts
2. **Model Routing Bug** ✅ - gemini-2.5-pro no longer sent to OpenAI (was causing 404 errors)
3. **Grounding Flag Propagation** ✅ - Templates with web mode now properly activate grounding

**Solution Components**:
- **Model Registry** (`app/llm/model_registry.py`) - Single source of truth for routing
- **Defensive Validators** - Citations auto-convert to proper format
- **Provider Guards** - Prevent models from being sent to wrong API
- **Explicit Routing** - Models route by provider, not ad-hoc string matching

**Working Models**:
- ✅ gemini-2.5-pro (Vertex + Grounding)
- ✅ gemini-2.0-flash (Vertex + Grounding)  
- ✅ gpt-5 models (OpenAI + Web Search)
- ✅ Frontend Templates & Results tabs

See `GROUNDING_AND_ROUTING_FIX_COMPLETE.md` for implementation details.

## Previous Update (August 17, 2025 AM) - Vertex AI ADC Setup & Import Refactoring ✅

### 🎯 Major Fix: Vertex AI Now Working Locally with ADC
**Problem Solved**: Vertex AI was falling back to direct API due to missing Application Default Credentials

**Solution Implemented**:
1. **Set up ADC locally**: Run `gcloud auth application-default login` and authenticate
2. **Fixed citations bug**: Citations from Vertex were strings, now properly formatted as dicts
3. **Backend restart with ADC**: Export `GOOGLE_APPLICATION_CREDENTIALS` to point to ADC file

**Result**: Vertex AI now works locally with proper grounding support! 🎉

### 🔧 Import Path Standardization
**Problem**: Duplicate adapter files causing confusion (`app/llm/vertex_genai_adapter.py` vs `app/llm/adapters/vertex_genai_adapter.py`)

**Solution Implemented**:
1. **Standardized imports**: All files now use `from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter`
2. **Deprecation warning**: Old path shows warning to encourage migration
3. **Backward compatibility**: Shim file ensures old imports still work
4. **Sanity test**: Created test to verify both paths return same class

**Files Updated**:
- `langchain_adapter.py`, `health.py`, `test_vertex_grounding.py` - Updated imports
- `app/llm/vertex_genai_adapter.py` - Now a deprecation shim with warning
- `app/llm/adapters/vertex_genai_adapter.py` - The real implementation (source of truth)

### 🐛 Citations Fix in Vertex Adapter
**Problem**: Vertex was returning citations as strings, but RunResult model expects dicts
**Solution**: Modified `_vertex_grounding_signals()` to format citations as:
```python
{
    "uri": "https://...",
    "title": "Page Title",
    "source": "web_search"
}
```

## Previous Update (August 16, 2025) - Finish Reason Tracking & Vertex Fallback ✅

### 🎯 Major Enhancement: Response Metadata Tracking
**Problem Solved**: Users couldn't understand why prompts failed (token exhaustion, content filtering, etc.)

**What Was Implemented**:
- Added `finish_reason` and `content_filtered` tracking to database and API
- Frontend displays clear visual indicators for response issues
- Yellow warning boxes explain token exhaustion, content filtering, or normal completion
- Warning icons in run list for quick identification of problematic runs

**Technical Details**:
- Database: Added `finish_reason` (TEXT) and `content_filtered` (BOOLEAN) columns to `prompt_results`
- Backend: Captures metadata from model responses (GPT-5 and Gemini)
- Frontend: Visual indicators with helpful messages about token starvation (GPT-5 needs 4000+ tokens)
- API: Returns metadata in `/api/prompt-tracking/results/{run_id}` endpoint

## Previous Update (August 15, 2025) - Production-Grade LLM Architecture ✅

### 🚀 Complete Rewrite Following ChatGPT's Production Standards - IMPLEMENTED

**Current State**: Successfully implemented ChatGPT's reference architecture for unified grounding + JSON schema enforcement across OpenAI and Vertex.

**Key Architecture Components**:
- ✅ **Clean Architecture**: Separate types, adapters, orchestrator (no more monolithic files!)
- ✅ **Type Safety**: Full Pydantic models for all requests/responses
- ✅ **Fail-Closed Semantics**: REQUIRED mode enforces grounding or fails
- ✅ **SDK Workarounds**: Using `extra_body` for missing features (not raw HTTP)
- ✅ **Complete Test Suite**: Mocked providers, no network calls

**Implementation Files**:
```
backend/app/llm/
├── adapters/
│   ├── types.py                         # Shared Pydantic models ✅
│   ├── openai_production.py             # OpenAI Responses adapter ✅  
│   └── vertex_genai_adapter.py          # Vertex GenAI adapter ✅
├── orchestrator.py                      # LLMOrchestrator ✅
├── langchain_orchestrator_bridge.py     # Backward compatibility bridge ✅
└── tests/
    └── test_adapters.py                 # Complete pytest suite (14 tests, all passing) ✅
```

**Key Improvements from ChatGPT**:
1. **GroundingMode enum**: REQUIRED/PREFERRED/OFF with fail-closed semantics
2. **Unified interface**: Same API for both OpenAI and Vertex
3. **Production patterns**: Structured logging, correlation IDs, BigQuery schemas
4. **No degradation**: If grounding_mode=REQUIRED and no search occurs, raises exception
5. **Clean separation**: Each component has single responsibility

### ✅ Working Solution Implemented

**Configuration That Works**:
- **Region**: `europe-west4` (fully operational)
- **Models**: `gemini-2.5-pro`, `gemini-2.5-flash` (both working perfectly)
- **Project**: `contestra-ai`
- **Authentication**: Application Default Credentials (ADC)

#### Vertex GenAI Adapter (`backend/app/llm/vertex_genai_adapter.py`)
```python
from google import genai
from google.genai import types

class VertexGenAIAdapter:
    def __init__(self, project="contestra-ai", location="europe-west4"):
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location  # Uses europe-west4 directly
        )
    
    async def analyze_with_gemini(self, prompt, use_grounding=False, context=None):
        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            seed=42
        )
        
        if use_grounding:
            # Vertex uses GoogleSearch(), not google_search_retrieval
            config.tools = [types.Tool(google_search=types.GoogleSearch())]
        
        # Use Gemini 2.5 models directly - they work in europe-west4
        # gemini-2.5-pro and gemini-2.5-flash are both available
        response = self.client.models.generate_content(
            model=model_name,  # gemini-2.5-pro or gemini-2.5-flash
            contents=messages,
            config=config
        )
```

### 🎯 Test Results with Vertex AI

**Prompt**: "List the top 10 longevity supplement brands"

| Country | Grounding | Status | AVEA Mentioned | Response Time |
|---------|-----------|--------|----------------|---------------|
| CH | web | ✅ SUCCESS | **Yes (2 times!)** | ~15s |
| US | web | ✅ SUCCESS | No | ~18s |
| CH | none | ✅ SUCCESS | No | ~8s |
| US | none | ✅ SUCCESS | No | ~8s |

**KEY ACHIEVEMENT**: AVEA brand successfully detected with grounding enabled in Switzerland!

### 🔍 Current Implementation Status

#### Working Configuration:
1. **europe-west4 region**: Full access to Gemini 2.5 models
2. **Models available**: `gemini-2.5-pro` and `gemini-2.5-flash` (without version suffixes)
3. **Grounding**: Working perfectly with GoogleSearch tool
4. **Authentication**: ADC working correctly

#### What We Learned:
- **Gemini 2.5 models ARE available** in europe-west4 (use without -002 suffix)
- **Don't use `global` location** - causes permission errors

## ⚠️ CRITICAL: Windows Unicode/Encoding Issues

### The Problem
On Windows, Python defaults to the system's code page (often cp1252) which cannot handle Unicode characters like Turkish İ, ş, ğ, ç, ö, ü or special symbols. This causes frequent crashes with errors like:
- `'charmap' codec can't encode character '\u0130'`
- `'charmap' codec can't encode character '\u00fc'`

### The Solution - ALWAYS DO THIS ON WINDOWS:

#### 1. Set Environment Variable BEFORE Running Python:
```bash
# PowerShell
$env:PYTHONUTF8=1
python script.py

# Command Prompt
set PYTHONUTF8=1
python script.py

# Or permanently in Windows System Settings
PYTHONUTF8=1
```

#### 2. For Backend Server:
```bash
# ALWAYS start the backend with UTF-8 encoding enabled
set PYTHONUTF8=1
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 3. In Code - When Writing Files:
```python
# ALWAYS specify encoding when opening files
with open('file.txt', 'w', encoding='utf-8') as f:
    f.write(content)

# For JSON files
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
```

#### 4. For Print Statements:
```python
# Either set PYTHONUTF8=1 or sanitize output
def sanitize_for_windows(text):
    """Remove problematic Unicode characters for Windows console"""
    replacements = {
        'İ': 'I', 'ı': 'i', 'ş': 's', 'ğ': 'g',
        'ç': 'c', 'ö': 'o', 'ü': 'u', 'Ş': 'S',
        'Ğ': 'G', 'Ç': 'C', 'Ö': 'O', 'Ü': 'U'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# Use when debugging
print(sanitize_for_windows(ai_response))
```

### Common Places This Occurs:
1. **AI responses** containing international brands/companies (e.g., "Türk Telekom")
2. **Ambient Location Signals** with Unicode characters (€, £, ü, ö, ä)
3. **Debug print statements** in development
4. **Log files** without encoding specified
5. **JSON serialization** without ensure_ascii=False

### Prevention Checklist:
- ✅ **ALWAYS** set `PYTHONUTF8=1` before running ANY Python script
- ✅ Start every Python session with `set PYTHONUTF8=1` on Windows
- ✅ Avoid using Unicode symbols (✓, ✗, €, etc.) in print statements
- ✅ Always use `encoding='utf-8'` when opening files
- ✅ Remove debug print statements before production
- ✅ Use logging with proper encoding configuration
- ✅ Test with international characters during development

### Quick Rule for Claude/AI Assistants:
**On Windows, ALWAYS prefix Python commands with:**
```bash
set PYTHONUTF8=1 && python script.py
```
This prevents the "Unicode issue strikes again!" problem that happens 100+ times per day!
- **Model names are specific**: Use exact names like `gemini-2.5-pro`, not `gemini-2.5-pro-002`
- **Grounding works great**: Server-side execution with GoogleSearch tool

### 📊 Current Production Status

#### ✅ Fully Working Components
- **Vertex AI with Grounding**: Operational in europe-west4
- **Automatic Fallback**: Falls back to direct API if Vertex fails
- **ALS (Ambient Location Signals)**: 100% success rate
- **Prompt Tracking**: Complete with bundle deduplication
- **Entity Strength Analysis**: Working with disambiguation
- **No Manual Tool Loops**: Server-side execution eliminates timeouts

#### 🛠️ Configuration Details

**Google Cloud Setup**:
```bash
# Project: contestra-ai
# Region: europe-west4 (REQUIRED)
# User: l@contestra.com (Owner + Vertex AI User)
# Authentication: ADC (Application Default Credentials)
```

**Test Commands**:
```bash
# Test Vertex grounding directly
cd backend && python test_vertex_grounding.py

# Test with different regions
cd backend && python test_vertex_eu.py
```

### 🚨 Important Architecture Notes

1. **TWO Vertex Adapters Exist** (needs consolidation):
   - `/app/llm/vertex_genai_adapter.py` - Used by Templates tab (working)
   - `/app/llm/adapters/vertex_genai_adapter.py` - Used by Grounding Test tab (needs region fix)
2. **Use europe-west4**: Never change to `global` - it causes permission errors
3. **Gemini 2.5 models work perfectly**: Both Pro and Flash variants are fully operational
4. **Grounding is server-side**: No manual tool loops needed

**The system is fully operational - Gemini 2.5 models work great with grounding!**

## Previous Update (August 14, 2025) - Bundle-Aware Template Deduplication

### 🎯 Major Enhancement: Templates as Run Bundles
**Problem Solved**: Templates now properly represent complete run configurations, not just prompt text.

**What Changed**:
- Templates are now deduplicated based on the **entire configuration bundle**:
  - Prompt text + Model + Countries + Grounding modes + Prompt type
- Same prompt with different models = **different templates** (allowed)
- Copy operations work intelligently without false duplicate warnings

**Implementation Details**:

#### Hash Calculation (`backend/app/services/prompt_hasher.py`)
```python
calculate_bundle_hash(
    prompt_text="What are the best supplements?",
    model_name="gpt-5",
    countries=["US", "CH"],
    grounding_modes=["web", "none"],
    prompt_type="recognition"
) → SHA256 hash of normalized bundle
```

**Normalizations Applied**:
- Countries: Uppercase, sorted, UK→GB, NONE for base model
- Grounding modes: Canonical mapping (none/web)
- Prompt text: Whitespace collapsed
- Prompt type: Lowercase, defaults to "custom"

#### Test Matrix
| Scenario | Same Prompt | Same Model | Same Countries | Same Modes | Same Type | Result |
|----------|------------|------------|----------------|------------|-----------|---------|
| Exact duplicate | ✓ | ✓ | ✓ | ✓ | ✓ | **409 Blocked** |
| Different model | ✓ | ✗ | ✓ | ✓ | ✓ | **201 Allowed** |
| Different countries | ✓ | ✓ | ✗ | ✓ | ✓ | **201 Allowed** |
| Different modes | ✓ | ✓ | ✓ | ✗ | ✓ | **201 Allowed** |
| Different type | ✓ | ✓ | ✓ | ✓ | ✗ | **201 Allowed** |

#### Frontend UX Improvements
- **Real-time duplicate checking** with visual indicators
- **Copy operation intelligence**: No false warnings when copying templates
- **Similar template detection**: Shows templates with same text but different configs
- **Actionable duplicate warnings**: "Run Existing" and "View Template" buttons

#### API Changes
- `/api/prompt-tracking/templates/check-duplicate` now returns:
  ```json
  {
    "exact_match": false,
    "same_text_diff_config": true,
    "closest": [
      {
        "template_id": "123",
        "name": "Brand Recognition",
        "model_id": "gpt-4o",
        "countries": ["US"],
        "similarity": "same_prompt"
      }
    ]
  }
  ```

**Files Modified**:
- `backend/app/services/prompt_hasher.py` - Bundle-aware hashing
- `backend/app/api/prompt_tracking.py` - Updated endpoints
- `frontend/src/components/PromptTracking.tsx` - Enhanced UX

## Latest Status (August 14, 2025)

### 🚀 Prompter V7 FINAL - Production-Ready Implementation
**Status**: FINAL specification with ALL fixes applied, ready for immediate implementation

**Implementation Files**:
- `FINAL_PROMPTER_UPGRADE_PROMPT_V7.md` - **FINAL production-ready spec** (USE THIS)
- `prompter_router_min.py` - **Complete working starter router** (drop-in ready!)
- `conftest.py` + `test_prompter_router_min.py` - **Complete test suite** (all green!)

**Documentation**:
- `PROMPTER_V7_STARTER_ROUTER.md` - How to use the starter router
- `PROMPTER_V7_TEST_SUITE.md` - Test suite documentation
- `PROMPTER_V6_ROLLOUT_CHECKLIST.md` - Complete deployment guide
- `PROMPTER_V4_PRODUCTION_COMPONENTS.md` - Drop-in implementation modules
- `PROMPTER_INTEGRATION_PLAN.md` - Step-by-step integration guide
- `SYSTEM_INTEGRITY_RULES.md` - Mandatory feature isolation rules

**V7 FINAL Fixes (production-ready)**:
1. ✅ **Request models defined** - `CreateTemplateRequest` and `RunTemplateRequest` included
2. ✅ **Endpoint paths flattened** - Fixed double-path issue (`/api/prompt-templates/templates`)
3. ✅ **SQLite detection bulletproof** - Returns strict boolean, no None
4. ✅ **Provider version consistency** - Result key matches version row, no disagreement
5. ✅ **Fingerprint extraction complete** - Handles Anthropic model_id explicitly
6. ✅ **Redis idempotency restored** - Optional probe guard prevents thundering herd
7. ✅ **Async/sync safety** - `inspect.isawaitable()` guards adapter calls
8. ✅ **Pydantic tolerance** - Handles both dict and Pydantic `inference_params`
9. ✅ **Provider inference robust** - Handles o3, o4, omni-* modern models
10. ✅ **All imports included** - No missing dependencies
11. ✅ **Idempotent indexes** - All use `IF NOT EXISTS`
12. ✅ **Complete implementation** - Ready to copy-paste and run

**Architecture Highlights**:
- Multi-brand support via `workspace_id` (references brands table)
- Config hash excludes aliases and workspace (pure generation config)
- Version tracking per provider fingerprint
- Full audit trail with `analysis_config` for future alias support
- Templates deduplicated by `(org_id, workspace_id, config_hash)`

## Previous Status (August 13, 2025)

### ✅ Gemini Metadata Capture Implemented
- **OpenAI**: Captures `system_fingerprint` for reproducibility
- **Gemini**: Captures `modelVersion` as fingerprint, `responseId` in metadata
- **Seed Support**: Both providers now support seed parameter
- **Test Coverage**: All methods tested and working
- See `GEMINI_FINGERPRINT_UPGRADE.md` for future enhancement path

### ✅ ALL LOCALE TESTS PASSING - 100% SUCCESS RATE
- **Countries Tab**: All 8 countries showing green checkmarks
- **Test Coverage**: US 🇺🇸, FR 🇫🇷, DE 🇩🇪, IT 🇮🇹, GB 🇬🇧, CH 🇨🇭, SG 🇸🇬, AE 🇦🇪
- **Parser Robustness**: Handles all AI model variations perfectly

### Key Parser Improvements (August 13)
1. **JSON Extraction**: Handles code fences `\`\`\`json` and finds first valid object
2. **VAT Normalization**: 
   - US accepts "none", "no", "n/a", "0%" 
   - Comma decimals: 8,1% → 8.1%
   - Prefix stripping: TVA/VAT/GST/IVA removed
3. **Plug Type Mapping**:
   - Schuko → F, BS 1363 → G
   - NEMA 1-15 → A, NEMA 5-15 → B
   - CEE 7/16/Europlug → C
   - CEI 23-50 → L, SEV 1011 → J
4. **Emergency Parsing**: 
   - Extracts from prose: "112 européen" → ["112"]
   - Country-specific validation rules

### Test Results
- 16/16 test cases pass (100%)
- Code fence JSON parsing works
- String plug types work (tipo L, Schuko, BS 1363)
- All US variations pass (none, n/a, 0%)

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

## MISSION-CRITICAL COMPONENTS - DO NOT MODIFY

### ⚠️ CRITICAL: These components must NEVER be modified without explicit permission

The following components are mission-critical to the Ambient Blocks methodology and have been carefully calibrated through extensive testing. Any modification to these can break the entire ALS (Ambient Location Signals) system:

#### 1. System Prompts for ALS
**Files**: 
- `backend/app/llm/langchain_adapter.py` (lines 180-186, 292-296)

**Current System Prompt** (DO NOT CHANGE):
```
Answer the user's question directly and naturally.
You may use any ambient context provided only to infer locale and set defaults (language variants, units, currency, regulatory framing).
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not state or imply country/region/city names unless the user explicitly asks.
Do not preface with anything about training data or location. Produce the answer only.
```

This prompt has been carefully crafted to:
- Allow silent locale adoption from ALS
- Prevent explicit location mentions that would reveal the test
- Maintain natural responses without preambles
- Work consistently across GPT-5 and Gemini models

#### 2. ALS Templates
**Files**:
- `backend/app/services/als/als_templates.py` - NEVER modify Unicode escape sequences
- `backend/app/services/als/als_templates_unicode.py` - Unicode validation version
- `backend/app/services/als/als_templates_ascii.py` - ASCII fallback (deprecated)

**Critical Elements**:
- Unicode characters (ü, ö, ä, €, £, etc.) are ESSENTIAL for ALS to work
- Character encoding must use proper escape sequences (\u00fc for ü, \u20ac for €)
- Template structure (≤350 chars) is precisely calibrated
- Civic keywords and formatting examples are locale-specific signals

#### 3. Message Ordering for ALS
**Location**: `langchain_adapter.py` methods `analyze_with_gemini()` and `analyze_with_gpt4()`

**Critical Order** (DO NOT CHANGE):
1. System prompt (if ALS context provided)
2. ALS context as HumanMessage (ambient signals)
3. User's actual question as HumanMessage (naked prompt)

This ordering makes the ALS feel like prior system state rather than part of the question.

#### 4. Temperature Settings for GPT-5
**Location**: `langchain_adapter.py` line 273

GPT-5 models REQUIRE `temperature=1.0` - any other value causes empty responses.
The code automatically sets this regardless of requested temperature.

#### 5. Background Runner Thread Isolation
**File**: `backend/app/services/background_runner.py`

The thread-based execution with new event loops is critical for preventing HTTP context leaks.
DO NOT modify the threading or event loop creation logic.

### Why These Are Mission-Critical

1. **System Prompts**: Control how models interpret ALS without revealing the test
2. **ALS Templates**: Provide precise civic signals for locale inference
3. **Unicode Characters**: Essential for authentic locale signaling
4. **Message Ordering**: Makes ALS feel like ambient context, not instructions
5. **Temperature Settings**: GPT-5 won't work without exact 1.0 temperature
6. **Thread Isolation**: Prevents geographic information from HTTP headers leaking into responses

### Testing Before Any Changes

If you absolutely must modify these components:
1. Test with all 8 countries (DE, CH, US, GB, AE, SG, IT, FR)
2. Run probe questions (VAT rate, plug type, emergency numbers)
3. Check for location leaks in responses
4. Verify Unicode characters display correctly
5. Test both GPT-5 and Gemini models
6. Run at least 10 iterations to check consistency

Remember: These components took weeks to calibrate. A single character change can break everything.

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

### Major Feature: Countries Tab with ALS Locale Testing (August 13, 2025)

#### Added Countries Management System
- Created 5th tab "Countries" in the Prompt Tracking interface
- Database table for managing supported countries (8 initial countries)
- Full CRUD API endpoints for country management
- Support for 8 countries: DE, CH, FR, IT, US, GB, AE, SG

#### Implemented Composite JSON Probe System
**Approach**: Localized language probes with deterministic JSON output
- Single composite probe per country in local language
- German for DE/CH, French for FR, Italian for IT, Arabic for AE, English for US/GB/SG
- All probes request JSON format: `{"vat_percent":"<>","plug":"<>","emergency":["<>"]}`
- Reduces API calls from 3 to 1 per test

#### Enhanced Parser Tolerance
**VAT Parsing**:
- Handles comma decimals: "8,1" → "8.1%"
- Adds missing %: "20" → "20%"
- Removes spaces: "20 %" → "20%"
- Special US handling for "no federal VAT"

**Plug Type Parsing**:
- Case-insensitive matching
- Removes prefixes: "Type", "Typ", "Tipo"
- Handles multiple plugs: "L/F", "L,F", "L and F"
- Comprehensive plug support per country:
  - Germany: F, C (Schuko + Europlug)
  - Switzerland: J, C
  - France: E, F, C
  - Italy: L, F, C
  - UK: G only
  - UAE: G, C, D
  - US: A, B
  - Singapore: G

**Emergency Number Parsing**:
- Extracts all 2-4 digit numbers
- Handles various separators: comma, slash, "and"
- Only requires primary number for pass
- Complete emergency numbers for each country

#### Visual Progress Indicators
- Shows test progress (1/1 for composite probe)
- Displays current probe being tested ("Locale Check")
- Prevents duplicate concurrent tests
- Traffic light status (green/yellow/red)

#### System Guardrails
- Explicit instruction: "Do not name countries/regions/cities or use country codes"
- Prevents location leakage in AI responses
- Allows locale inference without explicit mentions

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

### Current Session Status (Aug 14, 2025 - Evening Update)

#### Resolved: Prompt Tracking Model Display Issue
**Issue**: Results tab was showing "gemini" for all runs even when some templates used GPT-5
**Root Cause**: Backend server had crashed/hung causing CORS errors that prevented proper data fetching
**Solution**: Restarted backend server
**Verification**: 
- Database correctly stores model_name for each run
- API correctly returns model_name in responses  
- Frontend correctly displays run.model_name
- Runs now show correct models (gpt-5 for GPT-5 templates, gemini for Gemini templates)

### Current Session Status (Aug 14, 2025)

#### ⚠️ CHECKPOINT: System Stable Before Prompter Upgrade
**This commit represents a fully working system before major Prompter feature rebuild**

##### System Status
- Frontend running on port 3001
- Backend running on port 8000
- All core features operational
- **ALS feature**: ✅ Working perfectly with all 8 countries (DO NOT MODIFY)
- **Entity strength analysis**: ✅ Operational
- **Brand tracking**: ✅ Functional
- **Prompt integrity hashing**: ✅ SHA256 system implemented

##### Recent Implementations (Aug 11-14, 2025)
1. **Gemini Metadata Capture**: Successfully capturing model fingerprints
2. **Prompt Hashing System**: SHA256 integrity checking implemented
3. **Database Linkage**: 186 results properly linked to hashed prompts
4. **System Health Monitoring**: All services reporting healthy
5. **Locale Testing**: 100% success rate across all 8 countries

##### Known Issues Being Addressed
- **Prompter has 17+ duplicate prompts** (same config, different names)
- No model fingerprint visibility in UI
- Cannot track prompt performance across model updates

##### Upcoming Changes (Prompter Upgrade V3)
- Will DROP and rebuild ONLY: prompt_templates, prompt_runs, prompt_results
- Will ADD: prompt_versions table for model version tracking
- Will PRESERVE: ALS tables, brands, entity_mentions, countries, and ALL other features
- Implementing workspace (brand) scoped deduplication
- Config hash for generation settings only (aliases stay out)
- analysis_config field for future alias detection
- Clean slate approach - no migration of existing prompt data needed

##### Implementation Resources Ready
- FINAL_PROMPTER_UPGRADE_PROMPT_V3.md: Complete specification with workspace support
- PROMPTER_INTEGRATION_PLAN.md: Step-by-step integration guide
- Production-ready modules provided: canonicalize.py, provider_probe.py
- Comprehensive testing protocol included

## Model Support Status (UPDATED Aug 16, 2025)

**⚠️ CRITICAL: GPT-5 TOKEN REQUIREMENTS (FIXED)**
GPT-5 models require **4000+ tokens** for complex reasoning queries. Without sufficient tokens, GPT-5's reasoning models consume all tokens internally and produce empty output.

**RECOMMENDED MODELS:**
- ✅ **Gemini 2.5 Pro, Gemini 2.5 Flash**: Full support, no token issues
- ✅ **GPT-5 models**: Work perfectly with 4000 tokens allocated (now fixed in code)
- ✅ **GPT-4o**: Works as fallback

**DO NOT USE:**
- ❌ Gemini 1.5 Pro/Flash - No grounding support
- ❌ Gemini 2.0 Flash - Limited grounding, use 2.5 instead

**GPT-5 Test Results (Aug 16, 2025 - FINAL):**
- With 2000 tokens: Many complex queries return empty
- With 4000-6000 tokens: ALL queries work perfectly!

**Examples with proper token allocation:**
- ✅ "List the top 10 longevity supplement brands" → Works
- ✅ "What are the most trusted longevity supplement brands?" → **Works with 4000+ tokens!**
- ✅ "What are the most trusted ecommerce companies?" → **Works with 4000+ tokens!**
- ✅ "What are the most trusted tech companies?" → **Works with 4000+ tokens!**

**Key Finding**: There is NO content filtering! GPT-5 just needs more tokens for complex reasoning. Queries asking for "most trusted" evaluations require 3000-4000 tokens because the model performs extensive internal reasoning before generating output.

**ALS Locale Inference Verified:**
- ✅ Both GPT-5 and Gemini correctly adopt locale context
- ✅ Tested with German locale - all probes passed:
  - VAT rate: Returns 19% (German rate)
  - Plug type: Returns Type F/Schuko (German standard)
  - Emergency: Returns 112/110 (European/German numbers)

**Notes:**
- GPT-5 models require temperature=1.0 (automatically set)
- GPT-5 uses `max_completion_tokens` parameter (not `max_tokens`)
- 60-second timeout for GPT-5, 30-second for others
- Background endpoint bypasses HTTP context to avoid location leaks

## Known Issues & Limitations

1. **GPT-5 Response Times**: Takes 25-30 seconds per request (normal behavior)
2. **Non-deterministic Results**: Models give slightly different answers each time
3. **Brand Recognition**: Many smaller brands classified as UNKNOWN or WEAK
4. **Architecture Duplication**: Two vertex adapters exist (needs consolidation)

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

### Prompter V7 Documentation
- `PROMPTER_V7_FINAL_COMPLETE.md` - 🏆 **START HERE** - The definitive solution summary
- `PROMPTER_V7_COMPLETE_SOLUTION_SUMMARY.md` - Complete solution overview
- `FINAL_PROMPTER_UPGRADE_PROMPT_V7.md` - Complete V7 specification with all fixes
- `PROMPTER_V6_ROLLOUT_CHECKLIST.md` - Comprehensive deployment checklist
- `PROMPTER_V7_STARTER_ROUTER.md` - Documentation for starter router implementation
- `PROMPTER_V7_TEST_SUITE.md` - Complete pytest test coverage documentation
- `PROMPTER_V7_ALEMBIC_MIGRATION.md` - PostgreSQL database migration guide
- `PROMPTER_V7_TESTING_AND_SQLITE_PARITY.md` - Testing infrastructure and SQLite dev support
- `PROMPTER_V7_OBSERVABILITY_DASHBOARDS.md` - Grafana and DataDog monitoring dashboards
- `PROMPTER_V7_PROMETHEUS_METRICS.md` - Prometheus metrics module documentation
- `PROMPTER_V7_ROUTER_WITH_METRICS.md` - Updated router with integrated metrics
- `PROMPTER_V7_INSTRUMENTED_SERVICE_LAYER.md` - Service layer with probe metrics
- `PROMPTER_V7_FAKE_LLM_INTEGRATION.md` - Fake LLM for complete local testing
- `PROMPTER_V7_FINAL_TEST_ENHANCEMENTS.md` - Enhanced tests with fingerprint validation
- `PROMPTER_V7_DEVELOPER_TOOLS.md` - Makefile and development automation

### Prompter V7 Implementation Files
- `prompter_router_min.py` - Complete working FastAPI router implementation
- `prompter_router_min v2.py` - Router with integrated Prometheus metrics
- `prompter_router_min_v3.py` - **LATEST** - Router with metrics + fake LLM integration
- `prompt_versions.py` - Instrumented ensure-version service with probe metrics
- `provider_probe.py` - Stubbed provider probe for development
- `conftest.py` - Pytest configuration with mocked provider probes
- `test_prompter_router_min.py` - End-to-end tests for all endpoints
- `test_prompter_router_min_v2.py` - Enhanced tests with fingerprint and metrics validation
- `test_metrics_smoke.py` - Prometheus endpoint smoke test
- `requirements-dev.txt` - All development dependencies
- `Makefile` - Developer automation and convenience commands
- `v7_prompt_upgrade_20250814141329.py` - Alembic migration for PostgreSQL
- `test_alembic_v7_migration.py` - PostgreSQL migration round-trip test
- `sqlite_v7_parity.sql` - SQLite schema for development parity
- `apply_sqlite_v7.py` - Script to apply SQLite schema
- `test_sqlite_v7_parity.py` - SQLite schema verification test

### Prompter V7 Observability
- `grafana_prompter_rollout_dashboard.json` - Grafana dashboard for Prometheus metrics
- `datadog_prompter_rollout_dashboard.json` - DataDog dashboard configuration
- `observability_readme.md` - Quick setup guide for monitoring
- `prompter_metrics.py` - Complete Prometheus metrics module with middleware
- `METRICS_INTEGRATION_PATCH.md` - Instructions for wiring metrics into the application

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

## ⚠️ MANDATORY: Production Standards & System Integrity

### Production Standards (NEW - August 15, 2025)
**CRITICAL**: Read PRODUCTION_STANDARDS.md before writing ANY code.

**Core Rule**: Always build production-grade from day one. No hacks, no "proof of concepts" that need rewriting.

Key requirements:
- **Type safety**: Use Pydantic models, never raw dicts
- **Clean architecture**: Separate types, adapters, orchestrators
- **Fail-closed semantics**: Critical features must fail safely
- **Use SDK properly**: Leverage `extra_body` for missing features, don't bypass SDK
- **Production patterns**: Structured logging, monitoring, analytics-ready

### System Integrity Rules
**CRITICAL**: Before making ANY changes, you MUST read SYSTEM_INTEGRITY_RULES.md

This is a suite of integrated features, not a single application. When working on one feature, you MUST NOT break others. The golden rule: **"Fix one thing, break nothing else"**

See SYSTEM_INTEGRITY_RULES.md for:
- Feature boundaries and isolation rules
- List of files that belong to each feature
- Shared components that require extreme caution
- Testing mandate after any changes
- Historical incidents to avoid repeating

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