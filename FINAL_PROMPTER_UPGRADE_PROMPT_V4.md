# FINAL PROMPTER UPGRADE IMPLEMENTATION PROMPT V4
## With Critical Production Fixes & Dev/Prod Parity

## CRITICAL SAFETY REQUIREMENTS

### ⚠️ MANDATORY PRE-FLIGHT CHECKLIST
Before ANY implementation:
1. [ ] Read SYSTEM_INTEGRITY_RULES.md completely
2. [ ] Understand that ALS is mission-critical and MUST NOT be touched
3. [ ] Confirm understanding of feature boundaries
4. [ ] Acknowledge that breaking other features is unacceptable

### 🚫 DO NOT MODIFY THESE FILES/FEATURES
- **ALS Feature**: `backend/app/services/als/` (ALL files)
- **System Prompts**: Lines 180-186, 292-296 in langchain_adapter.py
- **Shared Models**: brands table (READ-ONLY, can reference with FK)
- **Entity Strength**: brand_entity_strength.py, EntityStrengthDashboard.tsx
- **Core LLM**: Only modify langchain_adapter.py for Prompter-specific needs

---

## IMPLEMENTATION SPECIFICATION V4 (PRODUCTION-READY)

**Role**: Senior Platform Engineer implementing Prompt Deduplication with Multi-Brand Support  
**Principle**: Fix the Prompter feature without breaking ANYTHING else  
**Stack**: FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev), React, TypeScript  
**Current State**: System fully operational, 17+ duplicate prompts need fixing

### OBJECTIVE (V4 - Production Hardened)
Implement intelligent prompt deduplication that:
1. **Blocks duplicates by config_hash within each brand workspace**
2. Creates new **prompt_version** when provider version key changes
3. **Scopes all templates to workspaces** (brands) for multi-brand support
4. Keeps **aliases OUT of config hash** for future plug-and-play analysis
5. Maintains complete audit trail with analysis_config
6. **Ensures dev/prod parity** with UUID strings in both environments

### KEY ARCHITECTURE
- **Workspace** = Brand (each brand is a workspace)
- **Templates**: Deduplicated by (org_id, workspace_id, config_hash)
- **Versions**: Hang off templates, one per provider version key
- **Analysis**: Stored in results, not in template hash
- **IDs**: UUID strings in both SQLite and PostgreSQL for parity

---

## TECHNICAL IMPLEMENTATION V4

### Phase 1: Database Schema with Dev/Prod Parity

#### SQLite Schema (Development) - FIXED
```sql
-- Drop old Prompter tables (NO CASCADE in SQLite)
DROP TABLE IF EXISTS prompt_results;
DROP TABLE IF EXISTS prompt_runs;
DROP TABLE IF EXISTS prompt_versions;
DROP TABLE IF EXISTS prompt_templates;

-- Templates with UUID strings for dev/prod parity
CREATE TABLE prompt_templates (
  id TEXT PRIMARY KEY,  -- UUID string for parity with Postgres
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,  -- References brands.id (UUID string)
  name TEXT NOT NULL,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,  -- JSON array as text
  model_id TEXT NOT NULL,
  inference_params TEXT NOT NULL,  -- JSON as text
  tools_spec TEXT,  -- JSON as text
  response_format TEXT,  -- JSON as text
  grounding_profile_id TEXT,
  grounding_snapshot_id TEXT,
  retrieval_params TEXT,
  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);

-- Partial unique index for active templates only (modern SQLite supports this)
CREATE UNIQUE INDEX ux_templates_org_ws_confighash_active
ON prompt_templates (org_id, workspace_id, config_hash)
WHERE deleted_at IS NULL;

-- Fallback if SQLite version doesn't support partial indexes:
-- CREATE UNIQUE INDEX ux_templates_org_ws_confighash 
-- ON prompt_templates (org_id, workspace_id, config_hash);
-- Then enforce deleted_at IS NULL in application layer

-- Versions with UUID strings
CREATE TABLE prompt_versions (
  id TEXT PRIMARY KEY,  -- UUID string
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,
  template_id TEXT REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMP,
  first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ux_versions_org_ws_tpl_providerkey
ON prompt_versions (org_id, workspace_id, template_id, provider_version_key);

-- Results with UUID strings and clarified columns
CREATE TABLE prompt_results (
  id TEXT PRIMARY KEY,  -- UUID string
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,
  template_id TEXT REFERENCES prompt_templates(id),
  version_id TEXT REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,  -- Raw OpenAI value
  request TEXT NOT NULL,  -- Full request JSON
  response TEXT NOT NULL,  -- Full response JSON
  analysis_config TEXT,  -- {scope, alias_snapshot_id, entities_checked, timestamp}
  rendered_prompt_hash TEXT,  -- Hash of the RENDERED prompt with runtime vars
  run_country TEXT,  -- The specific country for this execution
  used_grounding BOOLEAN,  -- Whether grounding was actually used
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
CREATE INDEX ix_results_workspace ON prompt_results (workspace_id, created_at DESC);
```

#### PostgreSQL Schema (Production) - ENHANCED
```sql
-- Drop old Prompter tables with CASCADE (PostgreSQL supports it)
DROP TABLE IF EXISTS prompt_results CASCADE;
DROP TABLE IF EXISTS prompt_runs CASCADE;
DROP TABLE IF EXISTS prompt_versions CASCADE;
DROP TABLE IF EXISTS prompt_templates CASCADE;

-- Templates with workspace (brand) scoping
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,  -- FK to brands.id
  name TEXT NOT NULL,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT[] NOT NULL,
  model_id TEXT NOT NULL,
  inference_params JSONB NOT NULL,
  tools_spec JSONB,
  response_format JSONB,
  grounding_profile_id UUID,
  grounding_snapshot_id TEXT,
  retrieval_params JSONB,
  config_hash TEXT NOT NULL,
  config_canonical_json JSONB NOT NULL,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT fk_templates_workspace 
    FOREIGN KEY (workspace_id) 
    REFERENCES brands(id) 
    ON DELETE RESTRICT  -- Prevent accidental cascade
);

-- Partial unique index for active templates only
CREATE UNIQUE INDEX ux_templates_org_ws_confighash_active
ON prompt_templates (org_id, workspace_id, config_hash)
WHERE deleted_at IS NULL;

-- Versions with workspace scoping
CREATE TABLE prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  template_id UUID REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMPTZ,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX ux_versions_org_ws_tpl_providerkey
ON prompt_versions (org_id, workspace_id, template_id, provider_version_key);

-- Results with clarified columns
CREATE TABLE prompt_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  template_id UUID REFERENCES prompt_templates(id),
  version_id UUID REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request JSONB NOT NULL,  -- Full request
  response JSONB NOT NULL,  -- Full response
  analysis_config JSONB,  -- {scope, alias_snapshot_id, entities_checked, timestamp}
  rendered_prompt_hash TEXT,  -- Hash of the RENDERED prompt
  run_country TEXT,  -- Specific country for this execution
  used_grounding BOOLEAN,  -- Whether grounding was used
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
CREATE INDEX ix_results_workspace ON prompt_results (workspace_id, created_at DESC);
```

### Phase 2: Service Layer (NEW - Avoids Route Recursion)

```python
# backend/app/services/prompter/prompt_versions.py
# Service functions to avoid route recursion

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

class PromptVersionService:
    """Service layer for version management - used by routes"""
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID string for both SQLite and PostgreSQL"""
        return str(uuid.uuid4())
    
    @staticmethod
    async def upsert_provider_version(
        db: Session,
        template: Any,
        probe_func: callable = None
    ) -> Dict[str, Any]:
        """
        Capture and upsert version for a template.
        Used by both ensure_version route and run_template route.
        """
        # Use provided probe or default to ProviderProbe
        if probe_func is None:
            from app.services.prompter.provider_probe import ProviderProbe
            probe_func = ProviderProbe.capture_fingerprint
        
        # Capture fingerprint
        provider, version_key, raw_fingerprint = await probe_func(
            model_id=template.model_id,
            config=json.loads(template.config_canonical_json)
        )
        
        # UPSERT version
        version = db.query(PromptVersion).filter(
            PromptVersion.org_id == template.org_id,
            PromptVersion.workspace_id == template.workspace_id,
            PromptVersion.template_id == template.id,
            PromptVersion.provider_version_key == version_key
        ).first()
        
        if not version:
            version = PromptVersion(
                id=PromptVersionService.generate_uuid(),
                org_id=template.org_id,
                workspace_id=template.workspace_id,
                template_id=template.id,
                provider=provider,
                provider_version_key=version_key,
                model_id=template.model_id,
                fingerprint_captured_at=datetime.utcnow()
            )
            db.add(version)
        else:
            version.last_seen_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "version_id": version.id,
            "workspace_id": template.workspace_id,
            "provider": provider,
            "provider_version_key": version_key,
            "captured_at": version.fingerprint_captured_at
        }
```

### Phase 3: Config Hash Implementation (UNCHANGED - Already Correct)

```python
# backend/app/services/prompter/canonicalize.py
# Keep EXACTLY as in V3 - preserves newlines, deep sorts, rounds floats

import hashlib
import json
import re
from typing import Dict, Any, List, Optional

class PromptConfigHasher:
    """
    Deterministic hashing for GENERATION config only.
    
    IMPORTANT: The following are NOT included in hash:
    - workspace_id (brand scope, but not generation config)
    - org_id (tenant scope, but not generation config) 
    - brand names or aliases (analysis concern)
    - runtime variables (substituted at execution)
    """
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text - PRESERVE NEWLINES"""
        if not text:
            return ""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse spaces/tabs but keep newlines
        text = re.sub(r"[ \t]+", " ", text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    @staticmethod
    def normalize_countries(countries: List[str]) -> List[str]:
        """Normalize country codes"""
        if not countries:
            return []
        normalized = []
        for country in countries:
            country = country.upper().strip()
            if country == 'UK':
                country = 'GB'
            normalized.append(country)
        return sorted(normalized)
    
    @staticmethod
    def _round_floats(obj: Any, decimals: int = 4) -> Any:
        """Recursively round all floats to 4 decimal places"""
        if isinstance(obj, float):
            return round(obj, decimals)
        elif isinstance(obj, list):
            return [PromptConfigHasher._round_floats(x, decimals) for x in obj]
        elif isinstance(obj, dict):
            return {k: PromptConfigHasher._round_floats(v, decimals) 
                   for k, v in obj.items()}
        return obj
    
    @staticmethod
    def _deep_sort(obj: Any) -> Any:
        """Deep sort dictionaries, preserve list order"""
        if isinstance(obj, dict):
            return {k: PromptConfigHasher._deep_sort(obj[k]) 
                   for k in sorted(obj.keys())}
        elif isinstance(obj, list):
            # Preserve order for tools_spec!
            return [PromptConfigHasher._deep_sort(x) for x in obj]
        return obj
    
    @classmethod
    def calculate_config_hash(
        cls,
        system_instructions: str,
        user_prompt_template: str,
        country_set: List[str],
        model_id: str,
        inference_params: Dict[str, Any],
        tools_spec: Optional[List[Dict]] = None,
        response_format: Optional[Dict] = None,
        grounding_profile_id: Optional[str] = None,
        grounding_snapshot_id: Optional[str] = None,
        retrieval_params: Optional[Dict] = None,
        # NOTE: workspace_id NOT here - it's scope, not config
        # NOTE: brand names NOT here - they're analysis, not generation
    ) -> tuple[str, Dict]:
        """
        Calculate deterministic hash for GENERATION config only.
        Returns: (hash, canonical_dict)
        """
        canonical = {
            "system_instructions": cls.normalize_text(system_instructions or ""),
            "user_prompt_template": cls.normalize_text(user_prompt_template),
            "country_set": cls.normalize_countries(country_set),
            "model_id": model_id.strip() if model_id else "",
            "inference_params": cls._deep_sort(
                cls._round_floats(inference_params or {})
            ),
            "tools_spec": cls._deep_sort(tools_spec or []),  # List stays list
            "response_format": cls._deep_sort(response_format or {}),
            "grounding_profile_id": grounding_profile_id or "",
            "grounding_snapshot_id": grounding_snapshot_id or "",
            "retrieval_params": cls._deep_sort(
                cls._round_floats(retrieval_params or {})
            ),
        }
        
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        hash_value = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        return hash_value, canonical
```

### Phase 4: API Updates with Service Layer

```python
# backend/app/api/prompt_tracking.py
# Updated to use service layer and UUID strings

from typing import Optional
from app.services.prompter.prompt_versions import PromptVersionService
from app.services.prompter.canonicalize import PromptConfigHasher

@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db)
):
    """Create template with workspace (brand) scoping"""
    # Get org_id and workspace_id
    org_id = request.org_id or "default"
    workspace_id = request.workspace_id  # REQUIRED - brand scope
    
    if not workspace_id:
        raise HTTPException(400, "workspace_id (brand) is required")
    
    # Verify workspace exists and user has access (READ-ONLY check on brands table)
    brand = db.query(Brand).filter(Brand.id == workspace_id).first()
    if not brand:
        raise HTTPException(404, "Brand/workspace not found")
    
    # Calculate config hash (workspace NOT in hash)
    config_hash, canonical = PromptConfigHasher.calculate_config_hash(
        system_instructions=request.system_instructions,
        user_prompt_template=request.user_prompt_template,
        country_set=request.country_set,
        model_id=request.model_id,
        inference_params=request.inference_params.dict() if request.inference_params else {},
        tools_spec=request.tools_spec,
        response_format=request.response_format,
        grounding_profile_id=request.grounding_profile_id,
        grounding_snapshot_id=request.grounding_snapshot_id,
        retrieval_params=request.retrieval_params
    )
    
    # Check for duplicate within org + workspace (active only)
    existing = db.query(PromptTemplate).filter(
        PromptTemplate.org_id == org_id,
        PromptTemplate.workspace_id == workspace_id,
        PromptTemplate.config_hash == config_hash,
        PromptTemplate.deleted_at.is_(None)  # Active only check
    ).first()
    
    if existing:
        # Return 409 Conflict
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEMPLATE_EXISTS",
                "template_id": existing.id,
                "template_name": existing.name,
                "workspace_id": workspace_id,
                "message": f"Identical configuration already exists in brand {brand.name}"
            }
        )
    
    # Create new template with UUID
    template = PromptTemplate(
        id=PromptVersionService.generate_uuid(),  # UUID string
        org_id=org_id,
        workspace_id=workspace_id,
        name=request.name,
        system_instructions=request.system_instructions,
        user_prompt_template=request.user_prompt_template,
        country_set=json.dumps(request.country_set) if isinstance(db.bind.dialect.name, 'sqlite') else request.country_set,
        model_id=request.model_id,
        inference_params=json.dumps(request.inference_params.dict()) if isinstance(db.bind.dialect.name, 'sqlite') else request.inference_params.dict(),
        tools_spec=json.dumps(request.tools_spec) if isinstance(db.bind.dialect.name, 'sqlite') else request.tools_spec,
        response_format=json.dumps(request.response_format) if isinstance(db.bind.dialect.name, 'sqlite') else request.response_format,
        grounding_profile_id=request.grounding_profile_id,
        grounding_snapshot_id=request.grounding_snapshot_id,
        retrieval_params=json.dumps(request.retrieval_params) if isinstance(db.bind.dialect.name, 'sqlite') else request.retrieval_params,
        config_hash=config_hash,
        config_canonical_json=json.dumps(canonical) if isinstance(db.bind.dialect.name, 'sqlite') else canonical,
        created_by=request.created_by,
        created_at=datetime.utcnow()
    )
    db.add(template)
    db.commit()
    
    return {
        "id": template.id,
        "workspace_id": workspace_id,
        "config_hash": config_hash
    }

@router.post("/templates/{template_id}/ensure-version")
async def ensure_version(
    template_id: str,  # UUID string
    db: Session = Depends(get_db)
):
    """Capture version with workspace scoping - uses service layer"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Use service layer to avoid recursion
    version_info = await PromptVersionService.upsert_provider_version(
        db=db,
        template=template
    )
    
    return version_info

@router.post("/templates/{template_id}/run")
async def run_template(
    template_id: str,  # UUID string
    request: RunTemplateRequest,
    db: Session = Depends(get_db)
):
    """Execute template and store result with analysis_config"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Use service layer for version management (no recursion)
    version_info = await PromptVersionService.upsert_provider_version(
        db=db,
        template=template
    )
    version_id = version_info["version_id"]
    
    # Execute prompt (actual implementation with LangChain)
    from app.llm.langchain_adapter import LangChainAdapter
    adapter = LangChainAdapter()
    
    # Prepare the full request
    full_request = {
        "template_id": template_id,
        "workspace_id": template.workspace_id,
        "model_id": template.model_id,
        "country": request.country,
        "brand_name": request.brand_name,
        "runtime_vars": request.runtime_vars,
        "use_grounding": request.use_grounding
    }
    
    # Execute based on provider
    if template.model_id.startswith('gpt'):
        response = await adapter.analyze_with_gpt4(
            request.rendered_prompt,  # Assume prompt is rendered with vars
            model_name=template.model_id,
            **json.loads(template.config_canonical_json)["inference_params"]
        )
    elif 'gemini' in template.model_id.lower():
        response = await adapter.analyze_with_gemini(
            request.rendered_prompt,
            **json.loads(template.config_canonical_json)["inference_params"]
        )
    else:
        # Anthropic or other
        response = {"content": "Provider not implemented", "metadata": {}}
    
    # Extract the full response and fingerprint
    full_response = response
    system_fingerprint = response.get("system_fingerprint") or \
                        response.get("metadata", {}).get("modelVersion")
    
    # Prepare analysis config for future alias detection
    analysis_config = {
        "scope": request.analysis_scope or "brand",
        "alias_snapshot_id": None,  # Will be filled when alias system is built
        "entities_checked": [request.brand_name] if request.brand_name else [],
        "matching_rules": "exact",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Calculate rendered prompt hash (with runtime vars)
    import hashlib
    rendered_prompt_hash = hashlib.sha256(
        request.rendered_prompt.encode('utf-8')
    ).hexdigest() if request.rendered_prompt else None
    
    # Store result with workspace and analysis config
    result = PromptResult(
        id=PromptVersionService.generate_uuid(),
        org_id=template.org_id,
        workspace_id=template.workspace_id,
        template_id=template_id,
        version_id=version_id,
        provider_version_key=version_info["provider_version_key"],
        system_fingerprint=system_fingerprint,
        request=json.dumps(full_request) if isinstance(db.bind.dialect.name, 'sqlite') else full_request,
        response=json.dumps(full_response) if isinstance(db.bind.dialect.name, 'sqlite') else full_response,
        analysis_config=json.dumps(analysis_config) if isinstance(db.bind.dialect.name, 'sqlite') else analysis_config,
        rendered_prompt_hash=rendered_prompt_hash,
        run_country=request.country,
        used_grounding=request.use_grounding,
        created_at=datetime.utcnow()
    )
    db.add(result)
    db.commit()
    
    return {"result_id": result.id, "version_id": version_id}
```

### Phase 5: Frontend Updates (UUID String Support)

```typescript
// Updated to handle UUID strings instead of integers

interface Template {
  id: string;  // UUID string
  workspace_id: string;  // UUID string
  name: string;
  config_hash: string;
  // ...
}

interface TemplateFormData {
  workspace_id: string;  // UUID string - Required brand selection
  name: string;
  // ... other fields
}

// Rest of frontend remains the same as V3
```

### Phase 6: Enhanced Testing with Concurrency

```python
# test_prompter_upgrade_v4.py

import asyncio
import concurrent.futures
from datetime import datetime
import uuid

def test_uuid_parity():
    """Verify UUID strings work in both SQLite and PostgreSQL"""
    template_id = str(uuid.uuid4())
    
    # Create template with UUID
    template = create_template(
        id=template_id,
        name="UUID Test",
        workspace_id=str(uuid.uuid4()),
        prompt_text="Test"
    )
    
    assert template['id'] == template_id
    assert isinstance(template['id'], str)
    print("✅ UUID string parity working")

def test_parallel_create_same_config():
    """Parallel creates of same (org, workspace, config_hash) → exactly one row"""
    workspace_id = str(uuid.uuid4())
    config = {
        "prompt_text": "Parallel test",
        "model_id": "gpt-4o",
        "countries": ["US"]
    }
    
    def create_attempt(name):
        return create_template(
            name=name,
            workspace_id=workspace_id,
            **config
        )
    
    # Try to create 10 templates concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_attempt, f"Test {i}") for i in range(10)]
        results = [f.result() for f in futures]
    
    # Exactly one should succeed
    successes = [r for r in results if 'id' in r]
    conflicts = [r for r in results if r.get('code') == 'TEMPLATE_EXISTS']
    
    assert len(successes) == 1, "Exactly one create should succeed"
    assert len(conflicts) == 9, "Nine creates should be blocked"
    print("✅ Parallel deduplication working")

def test_soft_delete_recreate():
    """Test recreation after soft delete with partial index"""
    workspace_id = str(uuid.uuid4())
    config = {"prompt_text": "Soft delete test", "model_id": "gpt-4o"}
    
    # Create template
    t1 = create_template("First", workspace_id=workspace_id, **config)
    assert t1['id'] is not None
    
    # Soft delete it
    soft_delete_template(t1['id'])
    
    # Create again with same config - should succeed
    t2 = create_template("Second", workspace_id=workspace_id, **config)
    assert t2['id'] is not None
    assert t2['id'] != t1['id']
    print("✅ Soft delete + recreate working")

def test_service_layer_no_recursion():
    """Verify service layer prevents route recursion"""
    template = create_template("Service Test", workspace_id=str(uuid.uuid4()))
    
    # Run template (which calls service layer, not route)
    result = run_template(template['id'], country="US")
    
    # Should have version_id from service layer
    assert result['version_id'] is not None
    print("✅ Service layer prevents recursion")

# Run all V4 tests
if __name__ == "__main__":
    print("=" * 60)
    print("PROMPTER V4 TESTS - Production Ready")
    print("=" * 60)
    
    # New V4 tests
    test_uuid_parity()
    test_parallel_create_same_config()
    test_soft_delete_recreate()
    test_service_layer_no_recursion()
    
    # V3 tests still apply
    test_workspace_isolation()
    test_version_isolation_by_workspace()
    test_analysis_config_storage()
    test_workspace_required()
    
    # Critical unchanged features
    test_als_still_works()
    test_brands_table_unchanged()
    
    print("\n🎉 All V4 tests passed! Production ready!")
```

---

## KEY FIXES IN V4

### Critical Production Fixes
1. ✅ **SQLite CASCADE removed** - No CASCADE in DROP TABLE for SQLite
2. ✅ **UUID string parity** - Both SQLite and PostgreSQL use UUID strings
3. ✅ **Partial index for soft-delete** - Proper unique constraint with deleted_at
4. ✅ **Service layer** - No route recursion, clean separation
5. ✅ **Defined variables** - All result fields properly populated

### Consistency Improvements  
6. ✅ **Column clarity** - rendered_prompt_hash, run_country, used_grounding
7. ✅ **FK constraint** - ON DELETE RESTRICT for brand reference
8. ✅ **JSON handling** - Consistent load/dump for SQLite TEXT fields
9. ✅ **Config canonicalization** - Confirmed list order, dict sorting, float rounding

### Testing Enhancements
10. ✅ **Parallel create test** - Ensures exactly one succeeds
11. ✅ **Soft-delete test** - Verifies partial index works
12. ✅ **UUID parity test** - Confirms dev/prod compatibility
13. ✅ **Service layer test** - No recursion verification

---

## DEPLOYMENT CHECKLIST V4

### Pre-Deployment
- [ ] Check SQLite version supports partial indexes (3.8.0+)
- [ ] Verify UUID generation works in both environments
- [ ] All V4 tests pass including concurrency tests
- [ ] ALS tested with all 8 countries
- [ ] Entity Strength tested
- [ ] Service layer properly imported

### Post-Deployment  
- [ ] Monitor for UUID string issues
- [ ] Verify soft-delete + recreate works
- [ ] Check parallel requests handled correctly
- [ ] Confirm ALS still works
- [ ] Monitor for any JSON encoding issues

---

## SUCCESS CRITERIA V4

1. ✅ Duplicates blocked within each brand workspace
2. ✅ Same config allowed across different brands  
3. ✅ Model versions tracked and visible
4. ✅ Analysis config ready for future aliases
5. ✅ Dev/prod parity with UUID strings
6. ✅ Concurrent creates handled properly
7. ✅ Soft-delete + recreate works
8. ✅ ALS still works perfectly
9. ✅ No other features affected

---

## FINAL REMINDER

**Golden Rule**: "Fix one thing, break nothing else"

V4 is production-hardened with all critical fixes from the review. The UUID string parity ensures seamless dev/prod deployment, the service layer prevents route recursion, and the partial index handles soft-delete correctly.