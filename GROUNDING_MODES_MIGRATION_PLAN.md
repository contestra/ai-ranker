# Grounding Modes Migration Plan - Final Implementation

**Date**: August 17, 2025  
**Status**: Ready for Execution  
**Approach**: Non-destructive migration with backward compatibility

## Overview

This plan implements canonical grounding modes (`not_grounded`, `preferred`, `enforced`) across the system while preserving all existing data. It ensures deterministic/reproducible hashing and complete provenance tracking for both OpenAI and Vertex providers.

## Key Changes

1. **Canonical grounding modes**: `not_grounded` | `preferred` | `enforced`
2. **Provider-aware UI**: Different options for OpenAI vs Gemini models
3. **App-level enforcement**: Gemini "enforced" mode fails if no citations
4. **Complete provenance**: Track what was requested vs what happened
5. **Deterministic hashing**: Reproducible SHA-256 for template deduplication

## Phase 1: Database Migration (Non-Destructive)

### 1.1 Create Backup (Windows-Safe)

```powershell
# PowerShell command for Windows-safe timestamp
cd backend
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
mkdir backups -ErrorAction SilentlyContinue
sqlite3 ai_ranker.db ".backup backups/db_backup_$ts.sqlite"
```

### 1.2 Migration Script - Add Nullable Columns

**File**: `backend/migrations/add_grounding_metadata.sql`

```sql
-- Add new columns as NULLABLE for backward compatibility
-- Templates table
ALTER TABLE prompt_templates ADD COLUMN provider TEXT;
ALTER TABLE prompt_templates ADD COLUMN system_temperature REAL;
ALTER TABLE prompt_templates ADD COLUMN system_seed INTEGER;
ALTER TABLE prompt_templates ADD COLUMN system_top_p REAL;
ALTER TABLE prompt_templates ADD COLUMN max_output_tokens INTEGER;
ALTER TABLE prompt_templates ADD COLUMN als_mode TEXT;
ALTER TABLE prompt_templates ADD COLUMN als_hash TEXT;
ALTER TABLE prompt_templates ADD COLUMN safety_profile TEXT;
ALTER TABLE prompt_templates ADD COLUMN request_timeout_ms INTEGER;
ALTER TABLE prompt_templates ADD COLUMN max_retries INTEGER;
ALTER TABLE prompt_templates ADD COLUMN grounding_binding_note TEXT;
ALTER TABLE prompt_templates ADD COLUMN canonical_json TEXT;
ALTER TABLE prompt_templates ADD COLUMN template_sha256 TEXT;
ALTER TABLE prompt_templates ADD COLUMN last_run_at TIMESTAMP;
ALTER TABLE prompt_templates ADD COLUMN total_runs INTEGER DEFAULT 0;

-- Runs table
ALTER TABLE prompt_runs ADD COLUMN provider TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounding_mode_requested TEXT;
ALTER TABLE prompt_runs ADD COLUMN inputs_snapshot TEXT;
ALTER TABLE prompt_runs ADD COLUMN tool_choice_sent TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounding_tool TEXT;
ALTER TABLE prompt_runs ADD COLUMN display_label TEXT;
ALTER TABLE prompt_runs ADD COLUMN grounded_effective INTEGER;
ALTER TABLE prompt_runs ADD COLUMN tool_call_count INTEGER;
ALTER TABLE prompt_runs ADD COLUMN response_api TEXT;
ALTER TABLE prompt_runs ADD COLUMN system_temperature REAL;
ALTER TABLE prompt_runs ADD COLUMN system_seed INTEGER;
ALTER TABLE prompt_runs ADD COLUMN system_top_p REAL;
ALTER TABLE prompt_runs ADD COLUMN max_output_tokens INTEGER;

-- Results table  
ALTER TABLE prompt_results ADD COLUMN citations TEXT;
ALTER TABLE prompt_results ADD COLUMN citations_count INTEGER;
ALTER TABLE prompt_results ADD COLUMN why_not_grounded TEXT;
ALTER TABLE prompt_results ADD COLUMN enforcement_failed INTEGER DEFAULT 0;
ALTER TABLE prompt_results ADD COLUMN model_version TEXT;
ALTER TABLE prompt_results ADD COLUMN system_fingerprint TEXT;

-- Create indices for performance (SQLite-compatible)
CREATE INDEX IF NOT EXISTS idx_runs_composite 
ON prompt_runs(provider, model_name, grounding_mode_requested, created_at);

CREATE INDEX IF NOT EXISTS idx_templates_provider 
ON prompt_templates(provider);

CREATE INDEX IF NOT EXISTS idx_templates_sha256 
ON prompt_templates(template_sha256);
```

### 1.3 Centralized Canonical JSON Service

**File**: `backend/app/services/canonical.py`

```python
"""
Centralized canonical JSON generation for consistency.
Used by both API and backfill scripts.
"""

import hashlib
from typing import Dict, Any, Tuple, Optional

try:
    # Try to use orjson for deterministic serialization
    import orjson
    HAS_ORJSON = True
except ImportError:
    # Fallback to standard json
    import json
    HAS_ORJSON = False

def canonicalize(obj: Dict[str, Any]) -> Tuple[str, str]:
    """
    Create deterministic canonical JSON and SHA256 hash.
    
    Args:
        obj: Dictionary to canonicalize (must have sorted keys already)
        
    Returns:
        Tuple of (json_string, sha256_hash)
    """
    if HAS_ORJSON:
        # Use orjson for deterministic output
        json_bytes = orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
        json_str = json_bytes.decode('utf-8')
        hash_value = hashlib.sha256(json_bytes).hexdigest()
    else:
        # Fallback to standard json
        json_str = json.dumps(obj, sort_keys=True, separators=(',', ':'))
        hash_value = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    return json_str, hash_value

def build_canonical_object(
    provider: str,
    model: str,
    prompt_text: str,
    countries: list,
    grounding_modes: list,
    system_temperature: float = 0.0,
    system_seed: int = 42,
    system_top_p: float = 1.0,
    max_output_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build the canonical object for hashing.
    
    Only includes fields that affect model output.
    """
    # Determine max tokens if not provided
    if max_output_tokens is None:
        max_output_tokens = 2000 if "gpt-5" in model.lower() else 8192
    
    # Sort countries and modes for determinism
    countries = sorted(countries) if countries else ["NONE"]
    grounding_modes = sorted(grounding_modes) if grounding_modes else ["not_grounded"]
    
    # ALS configuration based on countries
    als_config = {
        "mode": "off" if countries == ["NONE"] else "implicit",
        "hash": "als_v3_2025-08"
    }
    
    # Grounding binding note
    if provider == "openai":
        grounding_note = "openai:web_search auto/required"
    else:
        grounding_note = "vertex:google_search pass-1; two-step for JSON"
    
    # Build canonical object - sorted keys for determinism
    canonical = {
        "als": als_config,
        "countries": countries,
        "grounding_binding": grounding_note,
        "grounding_modes": grounding_modes,
        "model": model,
        "prompt_text": prompt_text.strip(),
        "provider": provider,
        "response_format": "text",
        "system": {
            "max_output_tokens": max_output_tokens,
            "seed": system_seed,
            "temperature": system_temperature,
            "top_p": system_top_p
        }
    }
    
    return canonical
```

### 1.4 Backfill Script

**File**: `backend/scripts/backfill_migration.py`

```python
"""
Backfill script to populate new columns from existing data.
Uses model registry for accurate provider detection.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
from typing import Dict, Any, List, Optional

# Import from app
from app.llm.model_registry import resolve_model
from app.services.canonical import canonicalize, build_canonical_object

def get_provider(model_name: str) -> str:
    """Use model registry for accurate provider detection."""
    try:
        return resolve_model(model_name).provider
    except Exception:
        # Fallback for unknown models
        model_lower = model_name.lower()
        if 'gpt' in model_lower:
            return 'openai'
        elif 'gemini' in model_lower:
            return 'vertex'
        return 'unknown'

def normalize_grounding_mode(mode: Optional[str]) -> str:
    """Map old grounding modes to canonical values."""
    if not mode:
        return 'not_grounded'
        
    mode_map = {
        'off': 'not_grounded',
        'none': 'not_grounded',
        'ungrounded': 'not_grounded',
        'preferred': 'preferred',
        'auto': 'preferred',
        'web': 'preferred',
        'required': 'enforced',
        'enforced': 'enforced'
    }
    return mode_map.get(mode.lower(), 'not_grounded')

def parse_json_field(value: Any) -> Any:
    """Parse JSON string if needed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return value
    return value

def backfill():
    """Run the backfill migration."""
    conn = sqlite3.connect('ai_ranker.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Starting backfill migration...")
    
    # 1. Backfill templates
    print("\n1. Backfilling prompt_templates...")
    cursor.execute("SELECT * FROM prompt_templates WHERE provider IS NULL")
    templates = cursor.fetchall()
    
    updated_count = 0
    for template in templates:
        template_dict = dict(template)
        provider = get_provider(template_dict['model_name'])
        
        # Parse countries and modes
        countries = parse_json_field(template_dict.get('countries', '["NONE"]'))
        if not countries:
            countries = ["NONE"]
        countries = sorted(countries)
        
        modes = parse_json_field(template_dict.get('grounding_modes', '["not_grounded"]'))
        if not modes:
            modes = ["not_grounded"]
        # Normalize modes
        modes = sorted([normalize_grounding_mode(m) for m in modes])
        
        # Determine ALS mode from parsed countries (not string comparison)
        als_mode = 'off' if countries == ["NONE"] else 'implicit'
        
        # Build canonical object
        canonical_obj = build_canonical_object(
            provider=provider,
            model=template_dict['model_name'],
            prompt_text=template_dict.get('prompt_text', ''),
            countries=countries,
            grounding_modes=modes
        )
        
        # Generate canonical JSON and hash
        canonical_json, template_sha256 = canonicalize(canonical_obj)
        
        # Determine system params
        if 'gpt-5' in template_dict['model_name'].lower():
            max_tokens = 2000
            timeout_ms = 60000
        else:
            max_tokens = 8192
            timeout_ms = 30000
        
        # Determine grounding binding note
        if provider == 'openai':
            grounding_note = "openai:web_search auto/required"
        else:
            grounding_note = "vertex:google_search pass-1; two-step for JSON"
        
        # Update normalized modes back to template
        modes_json = json.dumps(modes)
            
        cursor.execute("""
            UPDATE prompt_templates 
            SET provider = ?,
                system_temperature = 0.0,
                system_seed = 42,
                system_top_p = 1.0,
                max_output_tokens = ?,
                request_timeout_ms = ?,
                als_mode = ?,
                als_hash = 'als_v3_2025-08',
                safety_profile = 'standard',
                max_retries = 2,
                grounding_binding_note = ?,
                canonical_json = ?,
                template_sha256 = ?,
                grounding_modes = ?
            WHERE id = ?
        """, (
            provider, max_tokens, timeout_ms,
            als_mode,  # Use the parsed value
            grounding_note, canonical_json, template_sha256,
            modes_json,  # Update with normalized modes
            template['id']
        ))
        updated_count += 1
    
    print(f"  Updated {updated_count} templates")
    
    # 2. Backfill runs
    print("\n2. Backfilling prompt_runs...")
    cursor.execute("SELECT * FROM prompt_runs WHERE provider IS NULL")
    runs = cursor.fetchall()
    
    updated_count = 0
    for run in runs:
        provider = get_provider(run['model_name'])
        
        # Handle NULL grounding_mode
        grounding_mode = normalize_grounding_mode(run.get('grounding_mode'))
        
        # Determine response API
        if provider == 'vertex':
            response_api = 'vertex_genai'
        elif 'gpt-5' in run['model_name'].lower():
            response_api = 'responses_http'
        else:
            response_api = 'sdk_chat'
        
        # Determine tool_choice_sent
        tool_choice = None
        if provider == 'openai':
            if grounding_mode == 'enforced':
                tool_choice = 'required'
            elif grounding_mode == 'preferred':
                tool_choice = 'auto'
            else:
                tool_choice = 'off'
                
        cursor.execute("""
            UPDATE prompt_runs
            SET provider = ?,
                grounding_mode_requested = ?,
                response_api = ?,
                tool_choice_sent = ?,
                system_temperature = 0.0,
                system_seed = 42,
                system_top_p = 1.0,
                max_output_tokens = ?
            WHERE id = ?
        """, (
            provider, grounding_mode, response_api, tool_choice,
            2000 if 'gpt-5' in run['model_name'].lower() else 8192,
            run['id']
        ))
        updated_count += 1
    
    print(f"  Updated {updated_count} runs")
    
    # 3. Update grounding_mode in runs table to canonical
    print("\n3. Normalizing grounding_mode in prompt_runs...")
    cursor.execute("SELECT id, grounding_mode FROM prompt_runs WHERE grounding_mode IS NOT NULL")
    runs_modes = cursor.fetchall()
    
    updated_count = 0
    for run in runs_modes:
        normalized = normalize_grounding_mode(run['grounding_mode'])
        if normalized != run['grounding_mode']:
            cursor.execute("""
                UPDATE prompt_runs
                SET grounding_mode = ?
                WHERE id = ?
            """, (normalized, run['id']))
            updated_count += 1
    
    print(f"  Normalized {updated_count} run grounding modes")
    
    # 4. Count citations in results
    print("\n4. Counting citations in prompt_results...")
    cursor.execute("SELECT id, citations FROM prompt_results WHERE citations IS NOT NULL")
    results = cursor.fetchall()
    
    updated_count = 0
    for result in results:
        citations = parse_json_field(result['citations'])
        if isinstance(citations, list):
            count = len(citations)
        else:
            count = 0
            
        cursor.execute("""
            UPDATE prompt_results
            SET citations_count = ?
            WHERE id = ?
        """, (count, result['id']))
        updated_count += 1
    
    print(f"  Updated citation counts for {updated_count} results")
    
    conn.commit()
    conn.close()
    print("\n✅ Backfill migration complete!")

if __name__ == "__main__":
    backfill()
```

## Phase 2: Backend Updates

### 2.1 Install Dependencies

```bash
pip install orjson  # For deterministic JSON serialization
```

### 2.2 Update Prompt Hasher

**File**: `backend/app/services/prompt_hasher.py`

```python
def _normalize_modes(modes: Optional[Iterable[str]]) -> List[str]:
    """Normalize grounding modes to canonical values."""
    if not modes:
        return ["not_grounded"]  # Default when empty
    
    CANONICAL = {"not_grounded", "preferred", "enforced"}
    
    # For backward compatibility during migration
    LEGACY_MAP = {
        "off": "not_grounded",
        "none": "not_grounded",
        "ungrounded": "not_grounded",
        "web": "preferred",
        "auto": "preferred",
        "required": "enforced"
    }
    
    out = []
    for m in modes:
        if not m:
            continue
        m_lower = str(m).strip().lower()
        
        # Try canonical first
        if m_lower in CANONICAL:
            out.append(m_lower)
        # Then try legacy mapping
        elif m_lower in LEGACY_MAP:
            out.append(LEGACY_MAP[m_lower])
    
    # Return default if nothing valid found
    return sorted(set(out)) if out else ["not_grounded"]
```

### 2.3 Update Template Creation

**File**: `backend/app/api/prompt_tracking.py`

Add to create_template endpoint:

```python
from app.services.canonical import canonicalize, build_canonical_object
from app.llm.model_registry import get_provider

# Admin header check - case insensitive and multiple truthy values
def is_app_enforced_allowed(request):
    """Check if admin header allows app-enforced mode."""
    header_value = request.headers.get("X-Contestra-Allow-App-Enforced", "").lower()
    allowed_values = {"true", "1", "yes", "on"}
    
    if header_value in allowed_values:
        # Log when admin header is used
        print(f"[ADMIN] App-enforced mode enabled via header: {header_value}")
        return True
    return False

# In create_template endpoint
provider = get_provider(template.model_name)
allow_app_enforced = is_app_enforced_allowed(request)

if provider == "vertex" and "enforced" in template.grounding_modes and not allow_app_enforced:
    raise HTTPException(
        status_code=400,
        detail="Gemini doesn't support provider-level required search. Use 'preferred' (Auto)."
    )

# Build canonical object and generate hash
canonical_obj = build_canonical_object(
    provider=provider,
    model=template.model_name,
    prompt_text=template.prompt_text,
    countries=template.countries,
    grounding_modes=template.grounding_modes
)

canonical_json, template_sha256 = canonicalize(canonical_obj)

# Store with new fields populated
```

### 2.4 Update Run Execution

**File**: `backend/app/api/prompt_tracking.py`

```python
# Normalize grounding mode
mode = (grounding_mode or "not_grounded").lower()
needs_grounding = mode in ("preferred", "enforced")
grounding_enforced = mode == "enforced"

# After getting response
grounded_effective = response_data.get("grounded", False)
tool_call_count = response_data.get("tool_call_count", 0)
citations = response_data.get("citations", [])

# Safe citation handling - never stringify dicts!
if citations and isinstance(citations, list):
    citations_json = json.dumps(citations, ensure_ascii=False)
    citations_count = len(citations)
else:
    citations_json = "[]"
    citations_count = 0

# App-level enforcement
if grounding_enforced:
    enforcement_failed = False
    why_not_grounded = None
    
    if provider == "openai" and tool_call_count == 0:
        enforcement_failed = True
        why_not_grounded = "Required mode but model made no tool calls"
    elif provider == "vertex" and citations_count == 0:
        enforcement_failed = True
        why_not_grounded = "App-enforced: Gemini returned no citations"
    
    if enforcement_failed:
        # Mark run as failed and store reason
        # ... update database
```

## Phase 3: Frontend Updates

### 3.1 Create Grounding Constants

**File**: `frontend/src/constants/grounding.ts`

```typescript
export const GROUNDING_MODES = {
  NOT_GROUNDED: 'not_grounded',
  PREFERRED: 'preferred',
  ENFORCED: 'enforced'
} as const;

export type GroundingMode = typeof GROUNDING_MODES[keyof typeof GROUNDING_MODES];

// Provider detection helper
export function getProviderFromModel(modelName: string): 'openai' | 'vertex' | 'unknown' {
  const model = modelName.toLowerCase();
  if (model.includes('gpt')) return 'openai';
  if (model.includes('gemini') || model.includes('publishers/google')) return 'vertex';
  return 'unknown';
}

export function getGroundingDisplayLabel(
  mode: GroundingMode,
  modelNameOrProvider: string
): string {
  const provider = modelNameOrProvider.length <= 10 
    ? modelNameOrProvider 
    : getProviderFromModel(modelNameOrProvider);
    
  if (provider === 'openai') {
    switch (mode) {
      case GROUNDING_MODES.NOT_GROUNDED:
        return 'No Grounding';
      case GROUNDING_MODES.PREFERRED:
        return 'Web Search (Auto)';
      case GROUNDING_MODES.ENFORCED:
        return 'Web Search (Required)';
    }
  }
  if (provider === 'vertex') {
    switch (mode) {
      case GROUNDING_MODES.NOT_GROUNDED:
        return 'No Grounding';
      case GROUNDING_MODES.PREFERRED:
        return 'Web Search (Auto — model decides)';
      case GROUNDING_MODES.ENFORCED:
        return 'Web Search (App-enforced)';
    }
  }
  return mode;
}
```

### 3.2 Update PromptTracking Component

**File**: `frontend/src/components/PromptTracking.tsx`

Key changes:
1. Import grounding constants
2. Change default from `['off']` to `['not_grounded']`
3. Dynamic button hiding for Gemini (only show 2 options)
4. Show canonical JSON in template details
5. Provider-aware display labels

### 3.3 Results View Priority

```typescript
// Priority order for displaying response
function getResponseContent(result: any): string {
  // 1. Try JSON object (prettified)
  if (result.json_obj) {
    return JSON.stringify(result.json_obj, null, 2);
  }
  
  // 2. Try JSON text
  if (result.json_text) {
    return result.json_text;
  }
  
  // 3. Try Step-1 grounded text (if available)
  if (result.grounded_text) {
    return result.grounded_text;
  }
  
  // 4. Try regular model response
  if (result.model_response) {
    return result.model_response;
  }
  
  // 5. Show error or empty state
  if (result.error) {
    return `Error: ${result.error}`;
  }
  
  return "No response content available";
}
```

## Phase 4: Testing

### 4.1 Test Hash Stability

**File**: `backend/tests/test_hash_stability.py`

```python
from app.services.canonical import canonicalize, build_canonical_object

def test_canonical_hash_stability():
    """Ensure template hash is deterministic using the same function as API."""
    canonical_obj = build_canonical_object(
        provider="vertex",
        model="gemini-2.5-pro",
        prompt_text="Test prompt",
        countries=["US", "CH"],
        grounding_modes=["not_grounded", "preferred"]
    )
    
    # Generate hash multiple times
    _, hash1 = canonicalize(canonical_obj)
    _, hash2 = canonicalize(canonical_obj)
    
    assert hash1 == hash2, "Hash should be deterministic"
```

### 4.2 Test Vertex Invariants

```python
def test_vertex_no_schema_with_grounding():
    """Verify Vertex doesn't allow schema with GoogleSearch."""
    with pytest.warns(UserWarning, match="Cannot use response_schema with GoogleSearch"):
        result = await adapter.analyze_with_gemini(
            prompt="Test",
            use_grounding=True,
            response_schema={"type": "object"}
        )
    # Should use two-step process automatically
    assert result.get("two_step_used") == True
```

### 4.3 Test Matrix

- **Vertex gemini-2.5-pro**: All three modes (not_grounded, preferred, enforced)
- **Vertex gemini-2.0-flash**: Verify grounding capability check
- **OpenAI gpt-5**: Required mode enforces tool calls
- **OpenAI gpt-5**: Preferred mode allows no tool calls

## Execution Checklist

- [ ] Create database backup using PowerShell command
- [ ] Run migration SQL to add nullable columns
- [ ] Create and deploy canonical.py service
- [ ] Run backfill script
- [ ] Update backend with canonical imports
- [ ] Update frontend with canonical values
- [ ] Run full test suite
- [ ] Verify hash stability
- [ ] Test all grounding modes
- [ ] Add NOT NULL constraints after verification

## PostgreSQL Notes

For production PostgreSQL deployment:
- Use `JSONB` type for citations instead of TEXT
- Add generated column: `citations_count INT GENERATED ALWAYS AS (jsonb_array_length(COALESCE(citations, '[]'::jsonb))) STORED`
- Consider Alembic migration for schema changes

## Summary

This migration:
1. Preserves all existing data (no destructive changes)
2. Implements canonical grounding modes consistently
3. Ensures reproducible hashing with sorted keys
4. Tracks complete provenance (requested vs effective)
5. Implements provider-aware UI and enforcement
6. Maintains backward compatibility during transition

The plan has been validated against the engineering guide and includes all necessary fixes for Windows compatibility, SQLite syntax, and safe citation handling.