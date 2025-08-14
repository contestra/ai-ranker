# FINAL PROMPTER UPGRADE IMPLEMENTATION PROMPT V3
## With Workspace (Multi-Brand) Support & Alias-Ready Architecture

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

## IMPLEMENTATION SPECIFICATION V3

**Role**: Senior Platform Engineer implementing Prompt Deduplication with Multi-Brand Support  
**Principle**: Fix the Prompter feature without breaking ANYTHING else  
**Stack**: FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev), React, TypeScript  
**Current State**: System fully operational, 17+ duplicate prompts need fixing

### OBJECTIVE (V3 - Multi-Brand Ready)
Implement intelligent prompt deduplication that:
1. **Blocks duplicates by config_hash within each brand workspace**
2. Creates new **prompt_version** when provider version key changes
3. **Scopes all templates to workspaces** (brands) for multi-brand support
4. Keeps **aliases OUT of config hash** for future plug-and-play analysis
5. Maintains complete audit trail with analysis_config

### KEY ARCHITECTURE
- **Workspace** = Brand (each brand is a workspace)
- **Templates**: Deduplicated by (org_id, workspace_id, config_hash)
- **Versions**: Hang off templates, one per provider version key
- **Analysis**: Stored in results, not in template hash

---

## TECHNICAL IMPLEMENTATION V3

### Phase 1: Database Schema with Workspace Support

#### SQLite Schema (Development)
```sql
-- Drop old Prompter tables
DROP TABLE IF EXISTS prompt_results CASCADE;
DROP TABLE IF EXISTS prompt_runs CASCADE;
DROP TABLE IF EXISTS prompt_versions CASCADE;
DROP TABLE IF EXISTS prompt_templates CASCADE;

-- Templates with workspace (brand) scoping
CREATE TABLE prompt_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,  -- References brands.id (brand = workspace)
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

-- Unique within org + workspace (brand)
CREATE UNIQUE INDEX ux_templates_org_ws_confighash 
ON prompt_templates (org_id, workspace_id, config_hash);

-- Versions with workspace scoping
CREATE TABLE prompt_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,
  template_id INTEGER REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMP,
  first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (org_id, workspace_id, template_id, provider_version_key)
);

-- Results with workspace and analysis config
CREATE TABLE prompt_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL DEFAULT 'default',
  workspace_id TEXT NOT NULL,
  template_id INTEGER REFERENCES prompt_templates(id),
  version_id INTEGER REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,  -- Raw OpenAI value
  request TEXT NOT NULL,  -- Full request JSON
  response TEXT NOT NULL,  -- Full response JSON
  analysis_config TEXT,  -- NEW: How result was analyzed {"scope":"brand+products","alias_snapshot_id":"..."}
  prompt_hash TEXT,
  brand_name TEXT,
  country TEXT,
  grounding_used BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
CREATE INDEX ix_results_workspace ON prompt_results (workspace_id, created_at DESC);
```

#### PostgreSQL Schema (Production)
```sql
-- Drop old Prompter tables
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
  CONSTRAINT fk_templates_workspace FOREIGN KEY (workspace_id) REFERENCES brands(id)
);

-- Unique within org + workspace (brand), active only
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

-- Results with workspace and analysis config
CREATE TABLE prompt_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  template_id UUID REFERENCES prompt_templates(id),
  version_id UUID REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request JSONB NOT NULL,
  response JSONB NOT NULL,
  analysis_config JSONB,  -- NEW: {"scope":"brand+products","alias_snapshot_id":"..."}
  prompt_hash TEXT,
  brand_name TEXT,
  country TEXT,
  grounding_used BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_results_tpl_time ON prompt_results (template_id, created_at DESC);
CREATE INDEX ix_results_workspace ON prompt_results (workspace_id, created_at DESC);
```

### Phase 2: Config Hash Implementation (UNCHANGED - Aliases Stay OUT)

```python
# backend/app/services/prompt_config_hasher.py
# CRITICAL: workspace_id is NOT in the hash!
# CRITICAL: brand names/aliases are NOT in the hash!

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
        grounding_snapshot_id: Optional[str] = None,
        retrieval_params: Optional[Dict] = None,
        # NOTE: workspace_id NOT here - it's scope, not config
        # NOTE: brand names NOT here - they're analysis, not generation
    ) -> tuple[str, Dict]:
        """
        Calculate deterministic hash for GENERATION config only.
        Returns: (hash, canonical_json)
        """
        canonical = {
            "system_instructions": cls.normalize_text(system_instructions or ""),
            "user_prompt_template": cls.normalize_text(user_prompt_template),
            "country_set": cls.normalize_countries(country_set),
            "model_id": model_id.strip() if model_id else "",
            "inference_params": cls._deep_sort(
                cls._round_floats(inference_params or {})
            ),
            "tools_spec": cls._deep_sort(tools_spec or []),
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

### Phase 3: API Updates with Workspace Support

```python
# Modify backend/app/api/prompt_tracking.py

from typing import Optional

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
    
    # Check for duplicate within org + workspace
    existing = db.query(PromptTemplate).filter(
        PromptTemplate.org_id == org_id,
        PromptTemplate.workspace_id == workspace_id,  # Brand scope
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
                "workspace_id": workspace_id,
                "message": f"Identical configuration already exists in brand {brand.name}"
            }
        )
    
    # Create new template
    template = PromptTemplate(
        org_id=org_id,
        workspace_id=workspace_id,
        name=request.name,
        config_hash=config_hash,
        config_canonical_json=json.dumps(canonical),
        # ... other fields
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
    template_id: int,
    db: Session = Depends(get_db)
):
    """Capture version with workspace scoping"""
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
    
    # UPSERT version (org + workspace + template + version_key)
    version = db.query(PromptVersion).filter(
        PromptVersion.org_id == template.org_id,
        PromptVersion.workspace_id == template.workspace_id,
        PromptVersion.template_id == template_id,
        PromptVersion.provider_version_key == version_key
    ).first()
    
    if not version:
        version = PromptVersion(
            org_id=template.org_id,
            workspace_id=template.workspace_id,
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
        "workspace_id": template.workspace_id,
        "provider": provider,
        "provider_version_key": version_key
    }

@router.post("/templates/{template_id}/run")
async def run_template(
    template_id: int,
    request: RunTemplateRequest,
    db: Session = Depends(get_db)
):
    """Execute template and store result with analysis_config"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Ensure version exists
    version_response = await ensure_version(template_id, db)
    version_id = version_response["version_id"]
    
    # Execute prompt (actual implementation)
    # ... execution code ...
    
    # Prepare analysis config for future alias detection
    analysis_config = {
        "scope": request.analysis_scope or "brand",  # brand | brand+products | sku
        "alias_snapshot_id": None,  # Will be filled when alias system is built
        "entities_checked": [request.brand_name] if request.brand_name else [],
        "matching_rules": "exact",  # Will evolve to fuzzy later
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Store result with workspace and analysis config
    result = PromptResult(
        org_id=template.org_id,
        workspace_id=template.workspace_id,
        template_id=template_id,
        version_id=version_id,
        provider_version_key=version_response["provider_version_key"],
        system_fingerprint=response.get("system_fingerprint"),
        request=json.dumps(full_request),
        response=json.dumps(full_response),
        analysis_config=json.dumps(analysis_config),  # Future alias support
        brand_name=request.brand_name,
        country=request.country,
        grounding_used=request.use_grounding,
        created_at=datetime.utcnow()
    )
    db.add(result)
    db.commit()
    
    return {"result_id": result.id}
```

### Phase 4: Frontend Updates with Workspace Support

```typescript
// Add workspace (brand) selector to template creation

interface TemplateFormData {
  workspace_id: string;  // NEW: Required brand selection
  name: string;
  // ... other fields
}

const TemplateCreationForm: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("");
  const [duplicateWarning, setDuplicateWarning] = useState<any>({});
  
  // Load available brands (workspaces)
  useEffect(() => {
    fetch('/api/entities/brands')
      .then(res => res.json())
      .then(data => setBrands(data));
  }, []);
  
  // Check for duplicates WITH workspace scope
  const checkForDuplicates = useCallback(
    debounce(async (formData: TemplateFormData) => {
      if (!formData.workspace_id) return;  // Can't check without workspace
      
      try {
        const response = await fetch('/api/prompt-tracking/templates/check-duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            workspace_id: formData.workspace_id,  // Include workspace
            system_instructions: formData.systemInstructions,
            user_prompt_template: formData.promptText,
            country_set: formData.selectedCountries,
            model_id: formData.modelName,
            inference_params: {
              temperature: formData.temperature || 0.7,
              max_tokens: formData.maxTokens || 2000
            }
          })
        });
        
        const result = await response.json();
        
        if (result.is_duplicate) {
          setDuplicateWarning({
            show: true,
            existingTemplate: result.existing_template,
            workspace_name: brands.find(b => b.id === formData.workspace_id)?.name,
            message: result.message
          });
        } else {
          setDuplicateWarning({ show: false });
        }
      } catch (error) {
        console.error('Duplicate check failed:', error);
      }
    }, 500),
    [brands]
  );
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Brand/Workspace Selector - REQUIRED */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Brand (Workspace) *
        </label>
        <select
          value={selectedWorkspace}
          onChange={(e) => {
            setSelectedWorkspace(e.target.value);
            // Re-check duplicates when workspace changes
            checkForDuplicates({ ...formData, workspace_id: e.target.value });
          }}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="">Select a brand...</option>
          {brands.map(brand => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
            </option>
          ))}
        </select>
      </div>
      
      {/* Duplicate Warning - Now shows which brand */}
      {duplicateWarning.show && (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 mb-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-2" />
            <div className="flex-1">
              <h4 className="text-red-800 font-semibold">
                Duplicate in {duplicateWarning.workspace_name}
              </h4>
              <p className="text-red-700 text-sm mt-1">
                This exact configuration already exists for this brand.
              </p>
              <p className="text-red-600 text-sm mt-2">
                Existing template: "{duplicateWarning.existingTemplate?.name}"
              </p>
            </div>
          </div>
          <div className="mt-3">
            <button
              type="button"
              onClick={() => navigateToTemplate(duplicateWarning.existingTemplate.id)}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Use Existing Template
            </button>
          </div>
        </div>
      )}
      
      {/* Rest of form fields */}
      {/* ... */}
      
      <button
        type="submit"
        disabled={!selectedWorkspace || duplicateWarning.show || isSubmitting}
        className={`px-4 py-2 rounded ${
          !selectedWorkspace || duplicateWarning.show 
            ? 'bg-gray-300 cursor-not-allowed' 
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        {!selectedWorkspace ? 'Select Brand First' :
         duplicateWarning.show ? 'Duplicate Blocked' : 
         'Create Template'}
      </button>
    </form>
  );
};
```

### Phase 5: Testing with Workspace Support

```python
# test_prompter_upgrade_v3.py

def test_workspace_isolation():
    """Same config in different workspaces should both succeed"""
    # Create two brands (workspaces)
    avea_brand = get_or_create_brand("AVEA Life")
    other_brand = get_or_create_brand("Other Brand")
    
    config = {
        "prompt_text": "List top 10 products",
        "model_id": "gpt-4o",
        "countries": ["US"],
        "temperature": 0.7
    }
    
    # Create in AVEA workspace
    template1 = create_template(
        name="Product List",
        workspace_id=avea_brand.id,
        **config
    )
    assert template1['id'] is not None
    print(f"✅ Created template in AVEA workspace: {template1['id']}")
    
    # Create SAME config in different workspace - should SUCCEED
    template2 = create_template(
        name="Product List",
        workspace_id=other_brand.id,
        **config
    )
    assert template2['id'] is not None
    print(f"✅ Created same template in different workspace: {template2['id']}")
    
    # Try duplicate in SAME workspace - should FAIL
    template3 = create_template(
        name="Product List Copy",
        workspace_id=avea_brand.id,
        **config
    )
    assert template3.get('error') == 'TEMPLATE_EXISTS'
    print("✅ Duplicate blocked within same workspace")

def test_version_isolation_by_workspace():
    """Versions should be isolated by workspace"""
    avea_brand = get_or_create_brand("AVEA Life")
    other_brand = get_or_create_brand("Other Brand")
    
    # Create identical templates in both workspaces
    config = {"prompt_text": "Test", "model_id": "gpt-4o"}
    
    t1 = create_template("Test", workspace_id=avea_brand.id, **config)
    t2 = create_template("Test", workspace_id=other_brand.id, **config)
    
    # Ensure versions for both
    v1 = ensure_version(t1['id'])
    v2 = ensure_version(t2['id'])
    
    # Should have different version IDs (workspace isolated)
    assert v1['version_id'] != v2['version_id']
    assert v1['workspace_id'] == avea_brand.id
    assert v2['workspace_id'] == other_brand.id
    print("✅ Versions properly isolated by workspace")

def test_analysis_config_storage():
    """Verify analysis_config is stored in results"""
    avea_brand = get_or_create_brand("AVEA Life")
    
    template = create_template(
        "Test",
        workspace_id=avea_brand.id,
        prompt_text="Tell me about longevity"
    )
    
    result = run_template(
        template['id'],
        analysis_scope="brand+products",
        brand_name="AVEA Life"
    )
    
    # Fetch result and check analysis_config
    stored_result = get_result(result['result_id'])
    analysis_config = json.loads(stored_result['analysis_config'])
    
    assert analysis_config['scope'] == "brand+products"
    assert "AVEA Life" in analysis_config['entities_checked']
    assert analysis_config['timestamp'] is not None
    print("✅ Analysis config properly stored")

def test_workspace_required():
    """Template creation should fail without workspace_id"""
    try:
        template = create_template(
            name="No Workspace",
            workspace_id=None,  # Missing!
            prompt_text="Test"
        )
        assert False, "Should have failed without workspace_id"
    except Exception as e:
        assert "workspace_id" in str(e).lower()
        print("✅ Workspace_id properly required")

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

def test_brands_table_unchanged():
    """Verify brands table is only referenced, not modified"""
    # Check that brands table structure is unchanged
    # This is a READ-ONLY check
    brands = db.query(Brand).all()
    assert len(brands) > 0
    # Verify columns exist and are unchanged
    first_brand = brands[0]
    assert hasattr(first_brand, 'id')
    assert hasattr(first_brand, 'name')
    print("✅ Brands table remains unchanged (only referenced)")

# Run all tests
if __name__ == "__main__":
    print("=" * 60)
    print("PROMPTER V3 TESTS - With Workspace Support")
    print("=" * 60)
    
    # Test new workspace features
    test_workspace_isolation()
    test_version_isolation_by_workspace()
    test_analysis_config_storage()
    test_workspace_required()
    
    # Test other features unchanged
    test_als_still_works()
    test_brands_table_unchanged()
    
    print("\n🎉 All V3 tests passed! Multi-brand support ready!")
```

---

## KEY CHANGES IN V3

### Added Workspace (Brand) Support
1. ✅ **workspace_id** in all tables (references brands.id)
2. ✅ **Uniqueness scoped** to (org_id, workspace_id, config_hash)
3. ✅ **Brand selector** required in UI
4. ✅ **Workspace isolation** - same config allowed in different brands

### Kept Aliases OUT of Hash
1. ✅ **Config hash unchanged** - only generation config
2. ✅ **analysis_config** field for future alias support
3. ✅ **No brand names** in hash - keeps it pure

### Multi-Brand Benefits
1. ✅ **AVEA Life** gets their workspace
2. ✅ **Other brands** get theirs
3. ✅ **No cross-contamination**
4. ✅ **Future alias system** plugs in cleanly

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Verify brands table has data
- [ ] All tests pass including workspace tests
- [ ] ALS tested with all 8 countries
- [ ] Entity Strength tested
- [ ] UI shows brand selector

### Post-Deployment  
- [ ] Create workspace for each brand
- [ ] Test template creation per brand
- [ ] Verify duplicate blocking per workspace
- [ ] Confirm ALS still works
- [ ] Monitor for any errors

---

## SUCCESS CRITERIA

1. ✅ Duplicates blocked within each brand workspace
2. ✅ Same config allowed across different brands
3. ✅ Model versions tracked and visible
4. ✅ Analysis config ready for future aliases
5. ✅ ALS still works perfectly
6. ✅ No other features affected

---

## FINAL REMINDER

**Golden Rule**: "Fix one thing, break nothing else"

V3 adds multi-brand support cleanly without breaking anything. The workspace concept naturally scopes templates to brands while keeping the architecture ready for future alias detection.