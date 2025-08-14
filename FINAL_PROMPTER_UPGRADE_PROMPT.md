# FINAL PROMPTER UPGRADE IMPLEMENTATION PROMPT

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

## IMPLEMENTATION SPECIFICATION

**Role**: Senior Platform Engineer implementing Prompt Deduplication System  
**Principle**: Fix the Prompter feature without breaking ANYTHING else  
**Stack**: FastAPI, SQLAlchemy, PostgreSQL/SQLite, React, TypeScript  
**Current State**: System fully operational, 17+ duplicate prompts need fixing

### OBJECTIVE
Implement intelligent prompt deduplication that:
1. Blocks exact duplicates (same config + same model version)
2. Allows re-testing only when model version changes
3. Makes model versions visible throughout UI
4. Maintains complete audit trail

### SCOPE BOUNDARIES

#### ✅ WILL MODIFY (Prompter Feature Only)
**Backend Files**:
- `backend/app/api/prompt_tracking.py`
- `backend/app/api/prompt_tracking_background.py` 
- `backend/app/api/prompt_integrity.py`
- `backend/app/models/prompt_tracking.py`
- `backend/app/services/prompt_hasher.py`

**Frontend Files**:
- `frontend/src/components/PromptTracking.tsx`
- Related Prompter-specific components only

**Database Tables** (Can DROP and recreate):
- `prompt_templates`
- `prompt_runs`
- `prompt_results`
- `prompt_versions` (new table)

#### 🚫 WILL NOT MODIFY (Preserve Completely)
- Any file in `backend/app/services/als/`
- Any ALS-related code in langchain_adapter.py
- Tables: brands, entity_mentions, countries
- Any Entity Strength files
- Any Brand Tracking files

---

## TECHNICAL IMPLEMENTATION

### Phase 1: Database Schema (Clean Slate)

```python
# STEP 1: Backup current data (even though user doesn't care)
# This is for safety during development
backup_prompt_data = """
SELECT * INTO prompt_templates_backup FROM prompt_templates;
SELECT * INTO prompt_runs_backup FROM prompt_runs;
SELECT * INTO prompt_results_backup FROM prompt_results;
"""

# STEP 2: Drop ONLY Prompter tables
drop_prompter_tables = """
DROP TABLE IF EXISTS prompt_results CASCADE;
DROP TABLE IF EXISTS prompt_runs CASCADE;
DROP TABLE IF EXISTS prompt_templates CASCADE;
DROP TABLE IF EXISTS prompt_versions CASCADE;
"""

# STEP 3: Create new schema with proper constraints
create_new_schema = """
-- Templates (no fingerprint here)
CREATE TABLE prompt_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,  -- SQLite syntax
  name TEXT NOT NULL,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,  -- JSON array as text for SQLite
  model_id TEXT NOT NULL,
  inference_params TEXT NOT NULL,  -- JSON as text
  tools_spec TEXT,  -- JSON as text
  response_format TEXT,  -- JSON as text
  grounding_profile_id TEXT,
  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);

-- Unique constraint for active templates only
CREATE UNIQUE INDEX ux_templates_confighash 
ON prompt_templates (config_hash) 
WHERE deleted_at IS NULL;

-- Versions table
CREATE TABLE prompt_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMP,
  first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (template_id, provider_version_key)
);

-- Results with version tracking
CREATE TABLE prompt_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER REFERENCES prompt_templates(id),
  version_id INTEGER REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,
  prompt_hash TEXT,
  prompt_text TEXT NOT NULL,
  model_response TEXT NOT NULL,
  brand_name TEXT,
  country TEXT,
  grounding_used BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
```

### Phase 2: Config Hash Implementation

```python
# backend/app/services/prompt_config_hasher.py
# NEW FILE - Don't modify existing prompt_hasher.py

import hashlib
import json
from typing import Dict, Any, List

class PromptConfigHasher:
    """
    Deterministic hashing for prompt configurations.
    This is SEPARATE from prompt_hasher.py to avoid breaking existing code.
    """
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for consistent hashing"""
        if not text:
            return ""
        # Trim, collapse spaces, normalize line endings
        text = text.strip()
        text = " ".join(text.split())
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text
    
    @staticmethod
    def normalize_countries(countries: List[str]) -> List[str]:
        """Normalize country codes"""
        if not countries:
            return []
        # Uppercase, sort, map UK->GB
        normalized = []
        for country in countries:
            country = country.upper().strip()
            if country == 'UK':
                country = 'GB'
            normalized.append(country)
        return sorted(normalized)
    
    @staticmethod
    def normalize_inference_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize inference parameters"""
        if not params:
            return {}
        normalized = {}
        for key in sorted(params.keys()):
            value = params[key]
            # Round floats to 4 decimal places
            if isinstance(value, float):
                value = round(value, 4)
            normalized[key] = value
        return normalized
    
    @classmethod
    def calculate_config_hash(cls, 
                             system_instructions: str,
                             user_prompt_template: str,
                             country_set: List[str],
                             model_id: str,
                             inference_params: Dict[str, Any],
                             tools_spec: List[Dict] = None,
                             response_format: Dict = None,
                             grounding_profile_id: str = None) -> tuple[str, Dict]:
        """
        Calculate deterministic hash and return canonical JSON
        Returns: (hash, canonical_json)
        """
        # Build canonical representation
        canonical = {
            "system_instructions": cls.normalize_text(system_instructions),
            "user_prompt_template": cls.normalize_text(user_prompt_template),
            "country_set": cls.normalize_countries(country_set),
            "model_id": model_id.strip() if model_id else "",
            "inference_params": cls.normalize_inference_params(inference_params),
            "tools_spec": tools_spec or [],  # Preserve order!
            "response_format": response_format or {},
            "grounding_profile_id": grounding_profile_id or ""
        }
        
        # Create deterministic JSON string
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA256
        hash_value = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        return hash_value, canonical
```

### Phase 3: API Updates

```python
# Modify backend/app/api/prompt_tracking.py
# ADD these endpoints, don't remove existing ones

@router.post("/templates/check-duplicate")
async def check_duplicate(
    request: CheckDuplicateRequest,
    db: Session = Depends(get_db)
):
    """Check if a prompt configuration already exists"""
    # Calculate config hash
    config_hash, canonical = PromptConfigHasher.calculate_config_hash(
        system_instructions=request.system_instructions,
        user_prompt_template=request.user_prompt_template,
        country_set=request.country_set,
        model_id=request.model_id,
        inference_params=request.inference_params.dict() if request.inference_params else {}
    )
    
    # Check for exact match
    existing = db.query(PromptTemplate).filter(
        PromptTemplate.config_hash == config_hash,
        PromptTemplate.deleted_at.is_(None)
    ).first()
    
    if existing:
        return {
            "is_duplicate": True,
            "existing_template": {
                "id": existing.id,
                "name": existing.name,
                "created_at": existing.created_at
            },
            "message": "This exact configuration already exists"
        }
    
    return {"is_duplicate": False}

@router.post("/templates/{template_id}/ensure-version")
async def ensure_version(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Capture or update version for a template"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Run 1-token probe to get fingerprint
    adapter = LangChainAdapter()
    
    # CRITICAL: Only call the probe, don't modify any ALS code
    if template.model_id.startswith("gpt"):
        # OpenAI - fingerprint in response
        response = await adapter.analyze_with_gpt4(
            "test",
            model_name=template.model_id,
            max_tokens=1
        )
        fingerprint = response.get("system_fingerprint")
        provider = "openai"
    elif "gemini" in template.model_id:
        # Gemini - modelVersion in response
        response = await adapter.analyze_with_gemini(
            "test",
            max_tokens=1
        )
        fingerprint = response.get("metadata", {}).get("modelVersion")
        provider = "google"
    else:
        # Anthropic - use model ID
        fingerprint = template.model_id
        provider = "anthropic"
    
    if not fingerprint:
        return {"error": "Could not capture fingerprint"}
    
    # Upsert version
    version = db.query(PromptVersion).filter(
        PromptVersion.template_id == template_id,
        PromptVersion.provider_version_key == fingerprint
    ).first()
    
    if not version:
        version = PromptVersion(
            template_id=template_id,
            provider=provider,
            provider_version_key=fingerprint,
            model_id=template.model_id,
            fingerprint_captured_at=datetime.utcnow()
        )
        db.add(version)
    else:
        version.last_seen_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "version_id": version.id,
        "provider_version_key": fingerprint,
        "captured_at": version.fingerprint_captured_at
    }
```

### Phase 4: Frontend Updates

```typescript
// Modify frontend/src/components/PromptTracking.tsx
// ADD duplicate detection, don't break existing functionality

// Add debounced duplicate checking
const checkForDuplicates = useCallback(
  debounce(async (formData: TemplateFormData) => {
    try {
      const response = await fetch('/api/prompt-tracking/templates/check-duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
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
          message: result.message
        });
      } else {
        setDuplicateWarning({ show: false });
      }
    } catch (error) {
      console.error('Duplicate check failed:', error);
    }
  }, 500),
  []
);

// Add visual warning component
const DuplicateWarning: React.FC<{ data: any }> = ({ data }) => {
  if (!data.show) return null;
  
  return (
    <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 mb-4">
      <div className="flex items-center">
        <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-2" />
        <div className="flex-1">
          <h4 className="text-red-800 font-semibold">Duplicate Configuration Detected</h4>
          <p className="text-red-700 text-sm mt-1">{data.message}</p>
          <p className="text-red-600 text-sm mt-2">
            Existing template: "{data.existingTemplate?.name}" 
            (created {new Date(data.existingTemplate?.created_at).toLocaleDateString()})
          </p>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => navigateToTemplate(data.existingTemplate.id)}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Use Existing Template
        </button>
        <button
          onClick={() => setDuplicateWarning({ show: false })}
          className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
        >
          Create Anyway (Not Recommended)
        </button>
      </div>
    </div>
  );
};

// Add fingerprint badge to template list
const FingerprintBadge: React.FC<{ version: any }> = ({ version }) => {
  if (!version) return null;
  
  const shortFingerprint = version.provider_version_key?.substring(0, 8) || 'unknown';
  
  return (
    <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
      <CpuChipIcon className="h-3 w-3 mr-1" />
      {shortFingerprint}...
    </span>
  );
};
```

### Phase 5: Testing Protocol

```python
# test_prompter_upgrade.py
# Run these tests to verify nothing is broken

def test_als_still_works():
    """CRITICAL: Verify ALS is untouched"""
    # Test all 8 countries
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

def test_entity_strength_still_works():
    """Verify Entity Strength is untouched"""
    response = requests.post(
        'http://localhost:8000/api/brand-entity-strength',
        json={
            'brand_name': 'AVEA',
            'domain': 'avea-life.com',
            'vendor': 'google'
        }
    )
    assert response.status_code == 200
    print("✅ Entity Strength still working")

def test_duplicate_detection():
    """Test new duplicate detection"""
    # Create first template
    template1 = create_template("Test 1")
    
    # Try to create duplicate
    template2 = create_template("Test 2", same_config=True)
    assert template2['error'] == 'duplicate_detected'
    print("✅ Duplicate detection working")

def test_version_tracking():
    """Test version management"""
    template = create_template("Version Test")
    
    # Ensure version
    version = ensure_version(template['id'])
    assert version['provider_version_key'] is not None
    print("✅ Version tracking working")

# Run all tests
if __name__ == "__main__":
    test_als_still_works()  # MOST IMPORTANT
    test_entity_strength_still_works()
    test_duplicate_detection()
    test_version_tracking()
    print("\n🎉 All tests passed! Other features remain intact.")
```

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All tests pass
- [ ] ALS tested with all 8 countries
- [ ] Entity Strength tested
- [ ] No changes to als/ directory
- [ ] No changes to ALS system prompts
- [ ] Backup created (even if not needed)

### Post-Deployment
- [ ] Verify ALS still works
- [ ] Check Entity Strength
- [ ] Test duplicate detection
- [ ] Confirm version tracking
- [ ] Monitor for any errors

---

## ROLLBACK PLAN

If ANYTHING breaks:
```bash
git checkout b3ce61e  # Checkpoint commit
# Restore database from backup
# Restart services
```

---

## SUCCESS CRITERIA

1. ✅ Duplicate prompts blocked
2. ✅ Model versions visible
3. ✅ Re-testing allowed when model changes
4. ✅ ALS still works perfectly
5. ✅ Entity Strength unchanged
6. ✅ No other features affected

---

## FINAL REMINDER

**Golden Rule**: "Fix one thing, break nothing else"

The Prompter feature needs fixing, but the rest of the system is working perfectly. Your job is to fix the Prompter WITHOUT touching anything else. If you're unsure about a change affecting other features, STOP and ask.

Remember: This is a production system. The user depends on all features working correctly.