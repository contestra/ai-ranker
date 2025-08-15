# Production Standards - MANDATORY

**Created**: August 15, 2025  
**Updated**: August 15, 2025 - Added ChatGPT's complete reference architecture
**Purpose**: Prevent hack-and-slash coding. Always build production-grade from the start.

## Core Principles

### 1. NO HACKING - Build Production-Grade from Day One
- **Never** create "proof of concept" code that needs rewriting
- **Never** cram everything into one file
- **Never** use raw dicts when Pydantic models are appropriate
- **Always** think about deployment, monitoring, and maintenance

### 2. Architecture First
```
✅ CORRECT Structure:
app/
├── models/          # Pydantic models, type definitions
├── adapters/        # Provider-specific implementations
├── orchestrators/   # Business logic coordination
├── api/            # FastAPI routes
└── services/       # Shared services

❌ WRONG:
- Everything in one file
- No type safety
- Mixed concerns
```

### 3. Type Safety is NON-NEGOTIABLE
```python
# ✅ CORRECT
from pydantic import BaseModel
class RunRequest(BaseModel):
    run_id: str
    provider: str
    grounding_mode: GroundingMode

# ❌ WRONG
def process(data: dict):  # What's in data? Who knows!
    pass
```

### 4. Error Handling Patterns
```python
# ✅ CORRECT - Fail closed for critical features
if grounding_mode == GroundingMode.REQUIRED and not grounded_effective:
    raise RuntimeError("Grounding required but not achieved")

# ❌ WRONG - Silent failures
if error:
    return {"error": "something went wrong"}
```

### 5. SDK Usage Over Raw HTTP
```python
# ✅ CORRECT - Use SDK with extra_body for missing features
client.responses.create(
    model="gpt-5",
    extra_body={"text": {"format": schema}}  # Work around SDK limitations
)

# ❌ WRONG - Bypass SDK entirely
requests.post("https://api.openai.com/v1/responses", ...)
```

## Production Checklist

Before writing ANY code, ensure:

- [ ] **Types defined** - Pydantic models for all data structures
- [ ] **Clean separation** - Each file has ONE responsibility
- [ ] **Error handling** - Fail-closed semantics for critical paths
- [ ] **Logging** - Structured logging with correlation IDs
- [ ] **Monitoring** - Metrics, traces, health checks
- [ ] **Testing** - Unit tests, integration tests, contract tests
- [ ] **Documentation** - Docstrings, type hints, README
- [ ] **Configuration** - Environment-based, validated at startup
- [ ] **Analytics ready** - BigQuery/DataDog schemas defined

## Examples from ChatGPT's Superior Approach

### 1. Grounding Modes (Semantic Safety)
```python
class GroundingMode(str, Enum):
    REQUIRED = "required"     # Fail if not grounded
    PREFERRED = "preferred"   # Try to ground, fallback OK
    OFF = "off"              # Explicitly ungrounded
```

### 2. Clean Adapter Pattern
```python
class OpenAIResponsesAdapter:
    def run(self, req: RunRequest) -> RunResult:
        # Single responsibility: OpenAI interaction
        # Input/output contracts defined
        # Error semantics clear
```

### 3. Orchestration Layer
```python
class LLMOrchestrator:
    async def run(self, req: RunRequest) -> RunResult:
        # Routes to correct adapter
        # Handles provider selection
        # Consistent interface
```

## Anti-Patterns to AVOID

### 1. Test Scripts as Production Code
❌ Creating `test_complete_system.py` with print statements
✅ Build proper services with structured logging

### 2. Monolithic Adapters
❌ One file with analyze_with_responses, analyze_with_responses_sync_fallback, etc.
✅ Clean separation: types, adapters, orchestrators

### 3. Console-Driven Development
❌ Using print() for debugging
✅ Structured logging with log levels

### 4. Ad-hoc Error Handling
❌ Try/except with generic error messages
✅ Specific exception types with actionable messages

## The ChatGPT Standard

When ChatGPT provides code, notice:
1. **Type safety** - Everything is typed
2. **Single responsibility** - Each component does ONE thing
3. **Production patterns** - Error handling, logging, monitoring hooks
4. **Analytics-ready** - BigQuery schema included
5. **Extensible** - Easy to add new providers/features

## Enforcement

**BEFORE WRITING CODE**, ask:
1. Would ChatGPT write it this way?
2. Is this production-ready on day one?
3. Will this scale to 1000 requests/second?
4. Can another developer understand this in 6 months?
5. Are all failure modes handled?

If ANY answer is "no", redesign before coding.

## ChatGPT's Complete Reference Architecture

### File Structure
```
app/llm/
├── adapters/
│   ├── types.py                    # Shared Pydantic models
│   ├── openai_responses_adapter.py # OpenAI Responses API adapter
│   └── vertex_genai_adapter.py     # Vertex GenAI adapter
├── langchain_adapter.py            # LLMOrchestrator
└── tests/
    └── test_adapters.py            # Complete pytest suite
```

### Key Components from ChatGPT's Solution

#### 1. Type-Safe Request/Response Models
- `RunRequest` with all parameters typed
- `RunResult` with comprehensive response data
- `GroundingMode` enum with semantic safety
- `LocaleProbeSchema` for structured outputs

#### 2. Clean Adapter Pattern
- Single responsibility per adapter
- Consistent interface across providers
- Fail-closed semantics for REQUIRED mode
- SDK workarounds via `extra_body`

#### 3. Production Features
- Structured logging with correlation IDs
- Token usage tracking
- Latency measurements
- Citation extraction
- System fingerprint capture
- BigQuery-ready data structures

#### 4. Test Coverage
- Mocked SDK clients (no network calls)
- REQUIRED vs OFF semantics validation
- JSON enforcement verification
- Grounding detection tests
- Orchestrator routing tests

### Implementation Checklist
- [ ] Create `adapters/vertex_genai_adapter.py` following ChatGPT's spec
- [ ] Update `langchain_adapter.py` to use LLMOrchestrator
- [ ] Create comprehensive test suite
- [ ] Integrate with existing prompt tracking
- [ ] Update frontend for 4-column grid
- [ ] Add BigQuery logging
- [ ] Deploy and monitor

## References
- Clean Architecture by Robert Martin
- Domain-Driven Design by Eric Evans
- Site Reliability Engineering by Google
- The Twelve-Factor App methodology
- **ChatGPT's Production Architecture** (August 15, 2025)

---
Remember: **There is no such thing as temporary code in production systems.**