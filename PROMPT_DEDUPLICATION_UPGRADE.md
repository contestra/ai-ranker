# Prompt Deduplication & Fingerprinting Upgrade Specification

## Problem Statement
The current prompt template system allows unlimited duplicate prompts with different names, resulting in:
- **17 copies** of identical prompts with names like "Copy (Copy) (Copy)"
- Wasted storage and confused users
- No visibility into model fingerprints/versions
- Inability to track prompt performance across model updates
- No aggregation of results for identical prompts

## Solution Overview
Implement intelligent prompt deduplication that:
1. Prevents exact duplicates (same prompt + model + fingerprint)
2. Allows valid duplicates when model version changes
3. Shows model fingerprints to users
4. Links related prompts as versions of each other

## Database Schema Changes

### 1. Add Unique Constraint
```sql
-- Prevent exact duplicates
ALTER TABLE prompt_templates 
ADD CONSTRAINT unique_prompt_model_fingerprint 
UNIQUE (prompt_hash, model_name, system_fingerprint);
```

### 2. Add Prompt Versioning Table
```sql
CREATE TABLE prompt_versions (
    id INTEGER PRIMARY KEY,
    prompt_hash VARCHAR(64) NOT NULL,
    version_number INTEGER NOT NULL,
    template_id INTEGER REFERENCES prompt_templates(id),
    model_name VARCHAR(100),
    system_fingerprint VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_count INTEGER DEFAULT 0,
    avg_mention_rate FLOAT,
    notes TEXT,
    UNIQUE(prompt_hash, model_name, system_fingerprint)
);
```

### 3. Add Fingerprint Tracking to Templates
```sql
ALTER TABLE prompt_templates ADD COLUMN system_fingerprint VARCHAR(255);
ALTER TABLE prompt_templates ADD COLUMN fingerprint_captured_at TIMESTAMP;
ALTER TABLE prompt_templates ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE;
ALTER TABLE prompt_templates ADD COLUMN original_template_id INTEGER REFERENCES prompt_templates(id);
```

## Backend API Changes

### 1. Template Creation Endpoint
**POST /api/prompt-tracking/templates**

#### New Logic:
```python
async def create_template(template: PromptTemplate):
    # Calculate prompt hash
    prompt_hash = calculate_prompt_hash(template.prompt_text)
    
    # Get current model fingerprint
    fingerprint = await get_current_model_fingerprint(template.model_name)
    
    # Check for duplicates
    existing = find_existing_template(
        prompt_hash=prompt_hash,
        model_name=template.model_name,
        system_fingerprint=fingerprint
    )
    
    if existing:
        return {
            "error": "duplicate_detected",
            "existing_template": {
                "id": existing.id,
                "name": existing.template_name,
                "created_at": existing.created_at,
                "run_count": existing.run_count
            },
            "message": "This exact prompt already exists for this model version"
        }
    
    # Check for similar prompts (same hash, different model/fingerprint)
    similar = find_similar_templates(prompt_hash=prompt_hash)
    
    # Create new template with fingerprint
    template.system_fingerprint = fingerprint
    template.fingerprint_captured_at = datetime.now()
    
    if similar:
        # Link as new version
        template.original_template_id = similar[0].id
        version_number = len(similar) + 1
    
    # Save template...
```

### 2. New Endpoint: Check Current Model Fingerprint
**GET /api/prompt-tracking/model-fingerprint/{model_name}**

Returns:
```json
{
    "model_name": "gpt-4o",
    "current_fingerprint": "fp_07871e2ad8",
    "fingerprint_type": "openai.system_fingerprint",
    "last_changed": "2025-08-10T14:30:00Z",
    "previous_fingerprint": "fp_abc123def",
    "model_version": "gpt-4-0613"
}
```

### 3. New Endpoint: Find Duplicate Templates
**GET /api/prompt-tracking/check-duplicate**

Query params:
- `prompt_text`: The prompt to check
- `model_name`: Target model

Returns:
```json
{
    "exact_duplicate": {
        "exists": true,
        "template_id": 27,
        "template_name": "Top 10 longevity companies",
        "model_fingerprint": "fp_07871e2ad8"
    },
    "similar_prompts": [
        {
            "template_id": 4,
            "template_name": "Top 10",
            "model_name": "gpt-4o",
            "model_fingerprint": "fp_previous123",
            "created_at": "2025-08-01",
            "is_outdated": true
        }
    ],
    "recommendation": "use_existing"
}
```

## Frontend UI Changes

### 1. Template Creation Form Enhancement

#### A. Real-time Duplicate Detection
```typescript
// As user types prompt, debounce and check for duplicates
const checkDuplicate = debounce(async (promptText: string) => {
    const response = await fetch('/api/prompt-tracking/check-duplicate', {
        method: 'POST',
        body: JSON.stringify({ prompt_text: promptText, model_name: selectedModel })
    });
    
    if (response.exact_duplicate.exists) {
        showWarning({
            type: 'exact_duplicate',
            message: `This exact prompt already exists as "${response.exact_duplicate.template_name}"`,
            actions: [
                { label: 'Use Existing', action: () => navigateToTemplate(response.exact_duplicate.template_id) },
                { label: 'View Details', action: () => showTemplateDetails(response.exact_duplicate) }
            ]
        });
    } else if (response.similar_prompts.length > 0) {
        showInfo({
            type: 'similar_found',
            message: `${response.similar_prompts.length} similar prompts found with different model versions`,
            details: response.similar_prompts
        });
    }
}, 500);
```

#### B. Visual Duplicate Warning Component
```jsx
<DuplicateWarning 
    type="exact"
    existingTemplate={{
        name: "Top 10 longevity companies",
        created: "2 days ago",
        runs: 15,
        modelFingerprint: "fp_07871e2ad8"
    }}
    currentFingerprint="fp_07871e2ad8"
>
    <Alert variant="error">
        <AlertTitle>Exact Duplicate Detected</AlertTitle>
        <AlertDescription>
            This prompt already exists with the same model version.
            Creating it again will be rejected by the system.
        </AlertDescription>
        <AlertActions>
            <Button onClick={useExisting}>Use Existing Template</Button>
            <Button variant="ghost" onClick={viewDetails}>View Details</Button>
        </AlertActions>
    </Alert>
</DuplicateWarning>
```

### 2. Template List View Enhancements

#### A. Show Model Fingerprint
```jsx
<TemplateCard>
    <TemplateHeader>
        <Title>{template.name}</Title>
        <ModelBadge>
            {template.model_name}
            <Tooltip content={`Fingerprint: ${template.system_fingerprint}`}>
                <FingerprintIcon size={12} />
            </Tooltip>
        </ModelBadge>
    </TemplateHeader>
    
    {template.is_duplicate && (
        <DuplicateBadge>
            Duplicate of #{template.original_template_id}
        </DuplicateBadge>
    )}
    
    {template.has_newer_version && (
        <UpdateAvailable>
            Newer model version available (fp_new123)
            <Button size="sm" onClick={createNewVersion}>Test with New Model</Button>
        </UpdateAvailable>
    )}
</TemplateCard>
```

#### B. Group Duplicate Templates
```jsx
<TemplateGroup>
    <GroupHeader>
        "List top 10 longevity companies" (3 versions)
        <ExpandIcon />
    </GroupHeader>
    
    <GroupContent>
        <VersionTimeline>
            <Version active>
                <VersionDate>Aug 13, 2025</VersionDate>
                <ModelInfo>GPT-4 (fp_current)</ModelInfo>
                <Stats>15 runs, 80% mention rate</Stats>
            </Version>
            
            <Version>
                <VersionDate>Aug 1, 2025</VersionDate>
                <ModelInfo>GPT-4 (fp_previous)</ModelInfo>
                <Stats>23 runs, 75% mention rate</Stats>
            </Version>
            
            <Version>
                <VersionDate>Jul 15, 2025</VersionDate>
                <ModelInfo>GPT-4 (fp_older)</ModelInfo>
                <Stats>8 runs, 70% mention rate</Stats>
            </Version>
        </VersionTimeline>
    </GroupContent>
</TemplateGroup>
```

### 3. New "Prompt Library" View

A dedicated view showing unique prompts with their version history:

```jsx
<PromptLibrary>
    <SearchBar placeholder="Search prompts..." />
    
    <FilterBar>
        <Filter>Model: All</Filter>
        <Filter>Status: Active</Filter>
        <Toggle>Show Duplicates</Toggle>
    </FilterBar>
    
    <PromptGrid>
        {uniquePrompts.map(prompt => (
            <PromptCard key={prompt.hash}>
                <PromptText>{prompt.text}</PromptText>
                <VersionCount>{prompt.versions.length} versions</VersionCount>
                <ModelList>
                    {prompt.models.map(model => (
                        <ModelChip key={model}>
                            {model} ({prompt.versionsByModel[model].length})
                        </ModelChip>
                    ))}
                </ModelList>
                <Actions>
                    <Button onClick={() => testWithCurrentModel(prompt)}>
                        Test with Latest Model
                    </Button>
                    <Button variant="ghost" onClick={() => viewHistory(prompt)}>
                        View History
                    </Button>
                </Actions>
            </PromptCard>
        ))}
    </PromptGrid>
</PromptLibrary>
```

### 4. Model Fingerprint Status Widget

Add to the main dashboard:

```jsx
<ModelStatus>
    <Title>Model Versions</Title>
    <ModelList>
        <ModelItem>
            <ModelName>GPT-4o</ModelName>
            <Fingerprint>fp_07871e2ad8</Fingerprint>
            <LastChanged>3 days ago</LastChanged>
            {hasNewFingerprint && (
                <Badge variant="new">New Version Available</Badge>
            )}
        </ModelItem>
        
        <ModelItem>
            <ModelName>Gemini 2.5 Pro</ModelName>
            <Fingerprint>gemini-2.5-pro</Fingerprint>
            <LastChanged>Stable</LastChanged>
        </ModelItem>
    </ModelList>
</ModelStatus>
```

## Migration Plan

### Phase 1: Add Fingerprint Visibility
1. Start capturing and displaying model fingerprints
2. Add fingerprint to template creation
3. Show in UI but don't enforce uniqueness yet

### Phase 2: Soft Duplicate Prevention
1. Warn users about duplicates but allow creation
2. Track which templates are duplicates
3. Gather metrics on duplicate creation patterns

### Phase 3: Hard Duplicate Prevention
1. Block exact duplicates (same prompt + model + fingerprint)
2. Provide clear UI for using existing templates
3. Implement prompt versioning system

### Phase 4: Cleanup Existing Duplicates
1. Identify all duplicate groups
2. Mark canonical version for each group
3. Offer bulk merge tool for admins
4. Preserve all historical data but link duplicates

## Success Metrics

1. **Duplicate Reduction**: Reduce duplicate templates by 80%
2. **User Clarity**: 100% of templates show model fingerprint
3. **Version Tracking**: Track prompt performance across model updates
4. **Storage Efficiency**: Reduce template count from 41 to ~15 unique prompts
5. **User Satisfaction**: Reduce "which template should I use?" confusion

## Example User Flow

### Creating a New Template:
1. User enters prompt: "List top 10 longevity companies"
2. System checks for duplicates → finds exact match
3. Shows warning: "This exact prompt exists as 'Top 10' (created 2 days ago)"
4. User clicks "Use Existing"
5. Redirected to existing template
6. Can run tests immediately

### Model Version Changed:
1. User opens existing template "Top 10"
2. System detects new model fingerprint available
3. Shows banner: "GPT-4 has been updated (fp_new). Test with new version?"
4. User clicks "Create New Version"
5. System creates linked version with new fingerprint
6. Both versions visible in history

## Implementation Priority

1. **Critical**: Add fingerprint tracking and display
2. **High**: Implement duplicate detection API
3. **High**: Add duplicate warnings in UI
4. **Medium**: Build prompt library view
5. **Medium**: Implement versioning system
6. **Low**: Cleanup existing duplicates

This upgrade will transform the prompt system from a chaotic collection of duplicates into an organized, version-controlled library with full model fingerprint awareness.