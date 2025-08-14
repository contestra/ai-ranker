# FINAL PROMPTER UPGRADE IMPLEMENTATION PROMPT V2
## With Critical Corrections from Review

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
- **Shared Models**: brands, countries, entity_mentions tables
- **Entity Strength**: brand_entity_strength.py, EntityStrengthDashboard.tsx
- **Core LLM**: Only modify langchain_adapter.py for Prompter-specific needs

---

## IMPLEMENTATION SPECIFICATION (CORRECTED)

**Role**: Senior Platform Engineer implementing Prompt Deduplication System  
**Principle**: Fix the Prompter feature without breaking ANYTHING else  
**Stack**: FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev), React, TypeScript  
**Current State**: System fully operational, 17+ duplicate prompts need fixing

### OBJECTIVE (CORRECTED)
Implement intelligent prompt deduplication that:
1. **Blocks duplicates by config_hash ONLY** (not config + version)
2. Creates new **prompt_version** when provider version key changes
3. Makes model versions visible throughout UI
4. Maintains complete audit trail with full request/response JSON

### KEY CORRECTION
- **Templates**: Deduplicated by config_hash alone
- **Versions**: Hang off templates, one per provider version key
- **Multi-tenancy**: All tables need org_id (even if single-tenant initially)

---

## TECHNICAL IMPLEMENTATION (CORRECTED)

### Phase 1: Database Schema - DUAL SUPPORT

#### SQLite Schema (Development)
```sql
-- Templates with org_id
CREATE TABLE prompt_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',  -- For future multi-tenancy
  name TEXT NOT NULL,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,  -- JSON array as text
  model_id TEXT NOT NULL,
  inference_params TEXT NOT NULL,  -- JSON as text
  tools_spec TEXT,  -- JSON as text
  response_format TEXT,  -- JSON as text
  grounding_profile_id TEXT,
  grounding_snapshot_id TEXT,  -- ADDED: was missing
  retrieval_params TEXT,  -- ADDED: was missing
  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);

-- SQLite doesn't support partial indexes well, enforce in app
CREATE UNIQUE INDEX ux_templates_org_confighash 
ON prompt_templates (org_id, config_hash);

-- Versions with org_id
CREATE TABLE prompt_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',
  template_id INTEGER REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMP,
  first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (org_id, template_id, provider_version_key)
);

-- Results with full audit trail
CREATE TABLE prompt_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',
  template_id INTEGER REFERENCES prompt_templates(id),
  version_id INTEGER REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,  -- Raw OpenAI value
  request TEXT NOT NULL,  -- Full request JSON
  response TEXT NOT NULL,  -- Full response JSON
  prompt_hash TEXT,
  brand_name TEXT,
  country TEXT,
  grounding_used BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
```

#### PostgreSQL Schema (Production)
```sql
-- Templates with UUID and JSONB
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  name TEXT NOT NULL,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT[] NOT NULL,  -- Array type
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
  deleted_at TIMESTAMPTZ
);

-- Partial unique index for active templates only
CREATE UNIQUE INDEX ux_templates_org_confighash_active
ON prompt_templates (org_id, config_hash)
WHERE deleted_at IS NULL;

-- Versions
CREATE TABLE prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  template_id UUID REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMPTZ,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX ux_versions_org_tpl_providerkey
ON prompt_versions (org_id, template_id, provider_version_key);

-- Results with audit trail
CREATE TABLE prompt_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  template_id UUID REFERENCES prompt_templates(id),
  version_id UUID REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request JSONB NOT NULL,  -- Full request
  response JSONB NOT NULL,  -- Full response
  prompt_hash TEXT,
  brand_name TEXT,
  country TEXT,
  grounding_used BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
```

### Phase 2: Config Hash Implementation (CORRECTED)

```python
# backend/app/services/prompt_config_hasher.py
import hashlib
import json
import re
from typing import Dict, Any, List, Optional

class PromptConfigHasher:
    """
    Deterministic hashing for prompt configurations.
    CORRECTED: Preserves newlines, deep sorts JSON, includes all params
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
        return sorted(normalized)  # Sort for determinism
    
    @staticmethod
    def _round_floats(obj: Any, decimals: int = 4) -> Any:
        """Recursively round all floats"""
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
        grounding_snapshot_id: Optional[str] = None,  # ADDED
        retrieval_params: Optional[Dict] = None,  # ADDED
    ) -> tuple[str, Dict]:
        """
        Calculate deterministic hash and return canonical JSON
        Returns: (hash, canonical_json)
        """
        # Build canonical representation with ALL params
        canonical = {
            "system_instructions": cls.normalize_text(system_instructions or ""),
            "user_prompt_template": cls.normalize_text(user_prompt_template),
            "country_set": cls.normalize_countries(country_set),
            "model_id": model_id.strip() if model_id else "",
            "inference_params": cls._deep_sort(
                cls._round_floats(inference_params or {})
            ),
            "tools_spec": cls._deep_sort(tools_spec or []),  # Order preserved
            "response_format": cls._deep_sort(response_format or {}),
            "grounding_profile_id": grounding_profile_id or "",
            "grounding_snapshot_id": grounding_snapshot_id or "",  # ADDED
            "retrieval_params": cls._deep_sort(
                cls._round_floats(retrieval_params or {})
            ),  # ADDED
        }
        
        # Create deterministic JSON string
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA256
        hash_value = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        return hash_value, canonical
```

### Phase 3: Provider-Agnostic Probe (NEW)

```python
# backend/app/services/provider_probe.py
# NEW FILE - Provider-agnostic fingerprint capture

from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

class ProviderProbe:
    """
    Provider-agnostic probe for capturing version fingerprints.
    Does NOT touch ALS or any shared code.
    """
    
    @staticmethod
    async def capture_fingerprint(
        model_id: str,
        config: Dict[str, Any]
    ) -> tuple[str, str, Optional[str]]:
        """
        Run minimal probe to capture provider version.
        Returns: (provider, provider_version_key, raw_fingerprint)
        """
        # Determine provider from model_id
        if model_id.startswith('gpt'):
            provider = 'openai'
            fingerprint = await ProviderProbe._probe_openai(model_id, config)
        elif 'gemini' in model_id.lower():
            provider = 'google'
            fingerprint = await ProviderProbe._probe_gemini(model_id, config)
        elif 'claude' in model_id.lower():
            provider = 'anthropic'
            fingerprint = model_id  # Anthropic uses model ID as version
        else:
            provider = 'unknown'
            fingerprint = model_id
        
        return provider, fingerprint, fingerprint
    
    @staticmethod
    async def _probe_openai(model_id: str, config: Dict) -> str:
        """Probe OpenAI for system_fingerprint"""
        # Direct API call, NOT through shared adapter
        import openai
        client = openai.AsyncOpenAI()
        
        response = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            temperature=config.get('temperature', 0),
            seed=config.get('seed', 42)
        )
        
        return response.system_fingerprint or 'unknown'
    
    @staticmethod
    async def _probe_gemini(model_id: str, config: Dict) -> str:
        """Probe Gemini for modelVersion"""
        # Direct API call, NOT through shared adapter
        import google.generativeai as genai
        
        model = genai.GenerativeModel(model_id)
        response = await model.generate_content_async(
            "test",
            generation_config={'max_output_tokens': 1}
        )
        
        # Try to get modelVersion from response metadata
        if hasattr(response, '_result') and response._result:
            metadata = response._result.metadata
            return metadata.get('modelVersion', model_id)
        
        return model_id
```

### Phase 4: API Updates (CORRECTED)

```python
# Modify backend/app/api/prompt_tracking.py

@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db)
):
    """Create template with dedup by config_hash ONLY"""
    # Get org_id (default for now, multi-tenant ready)
    org_id = request.org_id or "default"
    
    # Calculate config hash with ALL params
    config_hash, canonical = PromptConfigHasher.calculate_config_hash(
        system_instructions=request.system_instructions,
        user_prompt_template=request.user_prompt_template,
        country_set=request.country_set,
        model_id=request.model_id,
        inference_params=request.inference_params.dict() if request.inference_params else {},
        tools_spec=request.tools_spec,
        response_format=request.response_format,
        grounding_profile_id=request.grounding_profile_id,
        grounding_snapshot_id=request.grounding_snapshot_id,  # ADDED
        retrieval_params=request.retrieval_params  # ADDED
    )
    
    # Check for duplicate (org + config_hash)
    existing = db.query(PromptTemplate).filter(
        PromptTemplate.org_id == org_id,
        PromptTemplate.config_hash == config_hash,
        PromptTemplate.deleted_at.is_(None)
    ).first()
    
    if existing:
        # Return 409 Conflict
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEMPLATE_EXISTS",
                "template_id": existing.id,
                "template_name": existing.name,
                "message": "Identical configuration already exists"
            }
        )
    
    # Create new template
    template = PromptTemplate(
        org_id=org_id,
        name=request.name,
        config_hash=config_hash,
        config_canonical_json=json.dumps(canonical),
        # ... other fields
    )
    db.add(template)
    db.commit()
    
    return {"id": template.id, "config_hash": config_hash}

@router.post("/templates/{template_id}/ensure-version")
async def ensure_version(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Capture version using provider-agnostic probe"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Use provider-agnostic probe
    provider, version_key, raw_fingerprint = await ProviderProbe.capture_fingerprint(
        model_id=template.model_id,
        config=json.loads(template.config_canonical_json)
    )
    
    # UPSERT version (org + template + version_key)
    version = db.query(PromptVersion).filter(
        PromptVersion.org_id == template.org_id,
        PromptVersion.template_id == template_id,
        PromptVersion.provider_version_key == version_key
    ).first()
    
    if not version:
        version = PromptVersion(
            org_id=template.org_id,
            template_id=template_id,
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
        "provider": provider,
        "provider_version_key": version_key,
        "captured_at": version.fingerprint_captured_at
    }
```

### Phase 5: Frontend Updates (CORRECTED)

```typescript
// Remove "Create Anyway" button - enforce dedup strictly

const DuplicateWarning: React.FC<{ data: any }> = ({ data }) => {
  if (!data.show) return null;
  
  return (
    <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 mb-4">
      <div className="flex items-center">
        <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-2" />
        <div className="flex-1">
          <h4 className="text-red-800 font-semibold">
            Duplicate Configuration Blocked
          </h4>
          <p className="text-red-700 text-sm mt-1">
            This exact configuration already exists. Duplicates are not allowed.
          </p>
          <p className="text-red-600 text-sm mt-2">
            Existing template: "{data.existingTemplate?.name}" 
            (created {new Date(data.existingTemplate?.created_at).toLocaleDateString()})
          </p>
        </div>
      </div>
      <div className="mt-3">
        <button
          onClick={() => navigateToTemplate(data.existingTemplate.id)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Use Existing Template
        </button>
      </div>
    </div>
  );
};

// Disable submit button when duplicate detected
<button
  type="submit"
  disabled={duplicateWarning.show || isSubmitting}
  className={`px-4 py-2 rounded ${
    duplicateWarning.show 
      ? 'bg-gray-300 cursor-not-allowed' 
      : 'bg-blue-600 hover:bg-blue-700 text-white'
  }`}
>
  {duplicateWarning.show ? 'Duplicate Blocked' : 'Create Template'}
</button>
```

### Phase 6: Testing Protocol (ENHANCED)

```python
# test_prompter_upgrade_v2.py

import asyncio
import concurrent.futures
from datetime import datetime

def test_concurrent_duplicate_creation():
    """Test that concurrent creates of same config result in one row"""
    config = {
        "name_prefix": "Concurrent Test",
        "prompt_text": "Test prompt",
        "countries": ["US", "GB"],
        "model_id": "gpt-4o"
    }
    
    def create_with_name(suffix):
        return create_template(f"{config['name_prefix']} {suffix}", config)
    
    # Try to create 5 templates concurrently with same config
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_with_name, i) for i in range(5)]
        results = [f.result() for f in futures]
    
    # Only one should succeed, others should get 409
    successes = [r for r in results if r.get('id')]
    conflicts = [r for r in results if r.get('error') == 'TEMPLATE_EXISTS']
    
    assert len(successes) == 1, "Exactly one create should succeed"
    assert len(conflicts) == 4, "Four creates should be blocked"
    print("✅ Concurrent dedup working")

def test_sqlite_without_partial_index():
    """Test that app-level dedup works even without DB partial index"""
    # In SQLite dev environment
    template1 = create_template("Test 1")
    
    # Soft delete it
    soft_delete_template(template1['id'])
    
    # Try to create with same config
    template2 = create_template("Test 2", same_config=True)
    
    # Should succeed since first is soft-deleted
    # (App checks deleted_at even if DB doesn't)
    assert template2.get('id'), "Should allow same config after soft delete"
    print("✅ App-level soft-delete dedup working")

def test_version_upsert_idempotent():
    """Test that concurrent version ensures don't create duplicates"""
    template = create_template("Version Test")
    
    async def ensure_concurrently():
        tasks = [
            ensure_version(template['id'])
            for _ in range(5)
        ]
        return await asyncio.gather(*tasks)
    
    versions = asyncio.run(ensure_concurrently())
    
    # All should return same version_id
    version_ids = [v['version_id'] for v in versions]
    assert len(set(version_ids)) == 1, "Should be exactly one version"
    print("✅ Version UPSERT is idempotent")

def test_newline_preservation():
    """Test that prompts with different paragraph structure don't collide"""
    prompt1 = "Line 1\nLine 2\nLine 3"  # Three lines
    prompt2 = "Line 1 Line 2 Line 3"    # One line
    
    hash1 = PromptConfigHasher.normalize_text(prompt1)
    hash2 = PromptConfigHasher.normalize_text(prompt2)
    
    assert hash1 != hash2, "Different paragraph structure should produce different hashes"
    print("✅ Newline preservation working")

# Critical: Test other features still work
def test_als_still_works():
    """CRITICAL: Verify ALS is untouched"""
    countries = ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']
    for country in countries:
        response = requests.post(
            'http://localhost:8000/api/countries/test-with-progress',
            json={'countries': [country]}
        )
        assert response.status_code == 200
        result = response.json()
        assert result['results'][country]['passed'] == True
    print("✅ ALS still working perfectly")

# Run all tests
if __name__ == "__main__":
    test_als_still_works()  # MOST IMPORTANT
    test_concurrent_duplicate_creation()
    test_sqlite_without_partial_index()
    test_version_upsert_idempotent()
    test_newline_preservation()
    print("\n🎉 All tests passed!")
```

---

## KEY CORRECTIONS SUMMARY

1. ✅ **Dedup by config_hash only** (not config + version)
2. ✅ **Multi-tenancy with org_id** everywhere
3. ✅ **Dual DDL** for PostgreSQL and SQLite
4. ✅ **Preserve newlines** in text normalization
5. ✅ **Include ALL hash inputs** (grounding_snapshot_id, retrieval_params)
6. ✅ **DB-level enforcement** with 409 on conflict
7. ✅ **Provider-agnostic probe** (no adapter dependencies)
8. ✅ **Full request/response JSON** storage
9. ✅ **Concurrency tests** added

---

## FINAL REMINDER

**Golden Rule**: "Fix one thing, break nothing else"

The corrections above ensure:
- Proper deduplication semantics
- Multi-tenant readiness
- Database compatibility
- Complete audit trail
- No impact on ALS or other features