# Prompter Integration Plan
## Merging Production-Ready Modules with Existing Codebase

**Date**: August 14, 2025  
**Status**: Pre-implementation documentation  
**Source**: Production-ready modules from external review

## Overview
This document outlines the step-by-step integration of the provided production modules into our existing ai-ranker codebase, implementing the V3 Prompter upgrade with workspace support and intelligent deduplication.

## Integration Principles
1. **DO NOT MODIFY** ALS or any other working features
2. **PRESERVE** all existing functionality
3. **TEST** after each integration step
4. **ROLLBACK** capability at each stage

## Directory Structure to Create

```
backend/app/services/prompter/
├── __init__.py
├── canonicalize.py        # Hash calculation (drop-in ready)
├── provider_probe.py      # Fingerprint capture (needs adaptation)
├── models.py             # SQLAlchemy models (merge with existing)
└── tests/
    ├── __init__.py
    ├── test_canonicalize.py
    └── test_uniqueness.py
```

## Phase 1: Foundation Setup

### Step 1.1: Create Package Structure
```bash
mkdir -p backend/app/services/prompter/tests
touch backend/app/services/prompter/__init__.py
touch backend/app/services/prompter/tests/__init__.py
```

### Step 1.2: Drop in canonicalize.py
**File**: `backend/app/services/prompter/canonicalize.py`
- Use EXACTLY as provided
- No modifications needed
- Handles all normalization and hashing

### Step 1.3: Adapt provider_probe.py
**File**: `backend/app/services/prompter/provider_probe.py`

Required adaptations:
```python
# Change imports to match our structure
from app.llm.langchain_adapter import LangChainAdapter  # Use existing
from app.config import settings  # Use existing settings

# Add compatibility layer for existing adapter
async def probe_with_existing_adapter(
    model_id: str,
    config: dict
) -> tuple[str, str, Optional[str]]:
    """Bridge to existing LangChainAdapter"""
    adapter = LangChainAdapter()
    
    if model_id.startswith('gpt'):
        # Use existing analyze_with_gpt4
        response = await adapter.analyze_with_gpt4(
            "test", 
            model_name=model_id,
            max_tokens=1
        )
        fingerprint = response.get("system_fingerprint")
        return "openai", fingerprint, fingerprint
    
    elif 'gemini' in model_id.lower():
        # Use existing analyze_with_gemini
        response = await adapter.analyze_with_gemini(
            "test",
            max_tokens=1
        )
        fingerprint = response.get("metadata", {}).get("modelVersion")
        return "google", fingerprint, fingerprint
    
    # Anthropic uses model ID
    return "anthropic", model_id, model_id
```

## Phase 2: Database Integration

### Step 2.1: Backup Current Tables
```sql
-- Create backup before dropping
CREATE TABLE prompt_templates_backup AS SELECT * FROM prompt_templates;
CREATE TABLE prompt_runs_backup AS SELECT * FROM prompt_runs;
CREATE TABLE prompt_results_backup AS SELECT * FROM prompt_results;
```

### Step 2.2: Update Models
**File**: `backend/app/models/prompt_tracking.py`

Add workspace support to existing models:
```python
# Add to existing imports
from app.services.prompter.canonicalize import canonicalize_config

# Update PromptTemplate model
class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    
    id = Column(Integer, primary_key=True)
    org_id = Column(String, default='default')  # NEW
    workspace_id = Column(Integer, ForeignKey('brands.id'))  # NEW - FK to brands
    name = Column(String, nullable=False)
    
    # Existing fields...
    
    config_hash = Column(String(64), nullable=False)  # NEW
    config_canonical_json = Column(Text, nullable=False)  # NEW
    
    # Add relationship
    brand = relationship("Brand", backref="prompt_templates")
    
# Add new PromptVersion model
class PromptVersion(Base):
    __tablename__ = 'prompt_versions'
    
    id = Column(Integer, primary_key=True)
    org_id = Column(String, default='default')
    workspace_id = Column(Integer, ForeignKey('brands.id'))
    template_id = Column(Integer, ForeignKey('prompt_templates.id'))
    
    provider = Column(String(32), nullable=False)
    provider_version_key = Column(Text, nullable=False)
    model_id = Column(String, nullable=False)
    
    fingerprint_captured_at = Column(DateTime)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("PromptTemplate", backref="versions")
    brand = relationship("Brand")

# Update PromptResult model
class PromptResult(Base):
    __tablename__ = 'prompt_results'
    
    # Existing fields...
    
    workspace_id = Column(Integer, ForeignKey('brands.id'))  # NEW
    version_id = Column(Integer, ForeignKey('prompt_versions.id'))  # NEW
    analysis_config = Column(Text)  # NEW - JSON for future alias support
    request = Column(Text)  # NEW - Full request JSON
    response = Column(Text)  # NEW - Full response JSON
```

### Step 2.3: Create Migration Script
**File**: `backend/migrations/upgrade_prompter_v3.py`

```python
import sqlite3
from datetime import datetime

def upgrade():
    """Drop old tables and create new schema with workspace support"""
    conn = sqlite3.connect('ai_ranker.db')
    cursor = conn.cursor()
    
    # Drop old tables (we don't care about data)
    cursor.execute("DROP TABLE IF EXISTS prompt_results")
    cursor.execute("DROP TABLE IF EXISTS prompt_runs")  
    cursor.execute("DROP TABLE IF EXISTS prompt_versions")
    cursor.execute("DROP TABLE IF EXISTS prompt_templates")
    
    # Create new schema
    with open('backend/sql/prompter_v3_schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    conn.commit()
    conn.close()
    print("✅ Prompter tables recreated with workspace support")

if __name__ == "__main__":
    upgrade()
```

## Phase 3: API Integration

### Step 3.1: Update prompt_tracking.py
**File**: `backend/app/api/prompt_tracking.py`

```python
# Add imports
from app.services.prompter.canonicalize import canonicalize_config
from app.services.prompter.provider_probe import probe_with_existing_adapter

# Update create_template endpoint
@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db)
):
    # REQUIRE workspace_id
    if not request.workspace_id:
        raise HTTPException(400, "workspace_id (brand) is required")
    
    # Verify brand exists (READ ONLY)
    brand = db.query(Brand).filter(Brand.id == request.workspace_id).first()
    if not brand:
        raise HTTPException(404, "Brand not found")
    
    # Calculate hash using new canonicalize
    config_hash, canonical = canonicalize_config(
        system_instructions=request.system_instructions,
        user_prompt_template=request.prompt_text,
        country_set=request.selected_countries,
        model_id=request.model_name,
        inference_params={
            "temperature": request.temperature or 0.7,
            "max_tokens": request.max_tokens or 2000
        },
        tools_spec=request.tools_spec,
        response_format=request.response_format,
        grounding_profile_id=request.grounding_profile_id,
        grounding_snapshot_id=request.grounding_snapshot_id,
        retrieval_params=request.retrieval_params
    )
    
    # Check for duplicates WITH workspace scope
    existing = db.query(PromptTemplate).filter(
        PromptTemplate.org_id == request.org_id or 'default',
        PromptTemplate.workspace_id == request.workspace_id,
        PromptTemplate.config_hash == config_hash,
        PromptTemplate.deleted_at.is_(None)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEMPLATE_EXISTS",
                "template_id": existing.id,
                "template_name": existing.template_name,
                "workspace_name": brand.name
            }
        )
    
    # Create with workspace
    template = PromptTemplate(
        org_id=request.org_id or 'default',
        workspace_id=request.workspace_id,
        name=request.template_name,
        config_hash=config_hash,
        config_canonical_json=json.dumps(canonical),
        # ... other fields
    )
    db.add(template)
    db.commit()
    
    return {"id": template.id, "workspace_id": request.workspace_id}

# Add new endpoint for version management
@router.post("/templates/{template_id}/ensure-version")
async def ensure_version(
    template_id: int,
    db: Session = Depends(get_db)
):
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Use adapted probe
    provider, version_key, raw = await probe_with_existing_adapter(
        template.model_name,
        json.loads(template.config_canonical_json)
    )
    
    # Upsert version
    version = db.query(PromptVersion).filter(
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
            model_id=template.model_name,
            fingerprint_captured_at=datetime.utcnow()
        )
        db.add(version)
    else:
        version.last_seen_at = datetime.utcnow()
    
    db.commit()
    return {"version_id": version.id, "provider_version_key": version_key}
```

### Step 3.2: Update Background Runner
**File**: `backend/app/services/background_runner.py`

Add version tracking to execution:
```python
# In execute_prompt method, after getting response
async def execute_prompt(...):
    # ... existing execution code ...
    
    # Extract fingerprint from response
    if vendor == 'openai':
        fingerprint = response.get('system_fingerprint')
    elif vendor == 'google':
        fingerprint = response.get('metadata', {}).get('modelVersion')
    else:
        fingerprint = model_name
    
    # Store with result
    result = PromptResult(
        template_id=template_id,
        workspace_id=template.workspace_id,  # NEW
        version_id=version_id,  # NEW
        provider_version_key=fingerprint,  # NEW
        analysis_config=json.dumps({  # NEW
            "scope": "brand",
            "timestamp": datetime.utcnow().isoformat()
        }),
        request=json.dumps(full_request),  # NEW - full request
        response=json.dumps(full_response),  # NEW - full response
        # ... existing fields
    )
```

## Phase 4: Frontend Integration

### Step 4.1: Add Workspace Selector
**File**: `frontend/src/components/PromptTracking.tsx`

```typescript
// Add brand selector to form
const [brands, setBrands] = useState<Brand[]>([]);
const [selectedWorkspace, setSelectedWorkspace] = useState<string>("");

// Load brands on mount
useEffect(() => {
    fetch('/api/entities/brands')
        .then(res => res.json())
        .then(setBrands);
}, []);

// Add to form JSX
<div className="mb-4">
    <label className="block text-sm font-medium text-gray-700">
        Brand (Required) *
    </label>
    <select 
        value={selectedWorkspace}
        onChange={(e) => setSelectedWorkspace(e.target.value)}
        required
        className="w-full border rounded px-3 py-2"
    >
        <option value="">Select brand...</option>
        {brands.map(brand => (
            <option key={brand.id} value={brand.id}>
                {brand.name}
            </option>
        ))}
    </select>
</div>

// Include in API calls
const createTemplate = async (data: any) => {
    const response = await fetch('/api/prompt-tracking/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...data,
            workspace_id: selectedWorkspace  // Include workspace
        })
    });
    // ... handle response
};
```

## Phase 5: Testing Protocol

### Step 5.1: Unit Tests
**File**: `backend/app/services/prompter/tests/test_canonicalize.py`
- Use provided test as-is
- Verify hash stability

### Step 5.2: Integration Tests
**File**: `backend/tests/test_prompter_integration.py`

```python
def test_workspace_isolation():
    """Verify templates isolated by workspace"""
    # Create two brands
    brand1 = create_brand("AVEA Life")
    brand2 = create_brand("Other Brand")
    
    # Same config, different workspaces
    config = {"prompt_text": "Test", "model_id": "gpt-4o"}
    
    # Should both succeed
    t1 = create_template(workspace_id=brand1.id, **config)
    t2 = create_template(workspace_id=brand2.id, **config)
    
    assert t1['id'] != t2['id']
    print("✅ Workspace isolation working")

def test_als_unchanged():
    """CRITICAL: Verify ALS still works"""
    for country in ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']:
        response = requests.post(
            'http://localhost:8000/api/countries/test-with-progress',
            json={'countries': [country]}
        )
        assert response.status_code == 200
    print("✅ ALS untouched and working")
```

## Rollback Plan

If any issues arise:
```bash
# 1. Restore from backup
sqlite3 ai_ranker.db
> DROP TABLE prompt_templates;
> DROP TABLE prompt_versions;
> DROP TABLE prompt_results;
> CREATE TABLE prompt_templates AS SELECT * FROM prompt_templates_backup;
> CREATE TABLE prompt_results AS SELECT * FROM prompt_results_backup;

# 2. Revert to checkpoint commit
git checkout b3ce61e

# 3. Restart services
```

## Success Criteria
1. ✅ Workspace-scoped deduplication working
2. ✅ Version tracking operational
3. ✅ ALS completely unchanged
4. ✅ All other features working
5. ✅ Frontend shows brand selector
6. ✅ Duplicates blocked within workspace
7. ✅ Same config allowed across workspaces

## Timeline
- Phase 1: 30 minutes (foundation)
- Phase 2: 1 hour (database)
- Phase 3: 2 hours (API integration)
- Phase 4: 1 hour (frontend)
- Phase 5: 1 hour (testing)
- **Total: ~5.5 hours**

## Notes
- This plan integrates the production modules while preserving all existing functionality
- Each phase can be tested independently
- Rollback is possible at any stage
- ALS and other features remain completely untouched