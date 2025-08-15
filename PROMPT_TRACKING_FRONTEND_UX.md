# Prompt Tracking Frontend UX Documentation

## Overview
The Prompt Tracking feature allows users to create **template bundles** that define test configurations. Each template represents a complete run configuration that can fan out to multiple API calls based on selected countries and grounding modes.

## Template = Run Bundle Concept

A template is NOT just prompt text. It's a complete configuration bundle consisting of:
- **Prompt text** (e.g., "What are the best supplements?")
- **Model selection** (e.g., GPT-5, Gemini 2.5 Pro)
- **Countries** (e.g., US, CH, DE - can select multiple)
- **Grounding modes** (e.g., "none", "web" - can select multiple)
- **Prompt type** (e.g., "recognition", "competitive", "custom")

When you click "Run Test", the system creates the Cartesian product:
- 2 countries × 2 grounding modes = 4 separate API calls
- Each combination runs independently

## Deduplication Logic

### What Makes Templates Unique
Templates are deduplicated based on the **entire bundle**, not just prompt text:
```
hash = SHA256(prompt_text + model + sorted(countries) + sorted(modes) + type)
```

### Allowed vs Blocked Scenarios
| Scenario | Result | Reason |
|----------|--------|--------|
| Exact same bundle | ❌ Blocked | Complete duplicate |
| Same prompt, different model | ✅ Allowed | Different test configuration |
| Same prompt, different countries | ✅ Allowed | Different regional test |
| Same prompt, different modes | ✅ Allowed | Different grounding test |

## Copy Template Behavior

### Current Implementation
1. User clicks **Copy** button on existing template
2. Form is populated with all fields from the original
3. Template name gets "(Copy)" appended
4. `isCopyOperation` flag is set internally
5. **No duplicate warning shown** (it's intentional)
6. User can immediately save (creates deliberate duplicate)

### Ideal UX Flow (Future Enhancement)
```mermaid
graph TD
    A[User clicks Copy] --> B[Form populated]
    B --> C{User modifies?}
    C -->|Yes| D[Clear, no warnings]
    C -->|No| E[Clicks Create]
    E --> F[Warning: "You haven't modified the copy"]
    F --> G{User choice}
    G -->|Continue| H[Create duplicate]
    G -->|Cancel| I[Back to editing]
```

## Real-Time Duplicate Checking

### Visual Indicators
The system provides real-time feedback as users type:

| State | Visual | Message |
|-------|--------|---------|
| Checking | 🔄 Gray spinner | "Checking for duplicates..." |
| Unique | ✅ Green checkmark | "Unique prompt" |
| Duplicate | ⚠️ Amber warning | "Duplicate found" |

### Duplicate Warning Panel
When an exact duplicate is detected:
```
┌─────────────────────────────────────────┐
│ ⚠️ This exact configuration exists      │
│                                          │
│ Template: "Brand Recognition Test"      │
│ Model: GPT-5                            │
│                                          │
│ [Run Existing] [View Template]          │
│                                          │
│ 💡 Tip: Change the model or countries   │
│    to create a variation                │
└─────────────────────────────────────────┘
```

### Similar Templates Detection
The system also detects templates with:
- **Same prompt text** but different configuration
- Shows as informational, not blocking
- Helps users understand what variations already exist

## Button States & Actions

### Create Template Button
| Condition | State | Action |
|-----------|-------|--------|
| Unique configuration | ✅ Enabled | Creates new template |
| Exact duplicate | ❌ Disabled | Shows "Duplicate - Use Existing" |
| Copy operation | ✅ Enabled | Allows deliberate duplicate |
| Form incomplete | ❌ Disabled | Missing required fields |

### Action Buttons for Duplicates
- **Run Existing**: Immediately runs the duplicate template
- **View Template**: Scrolls to and highlights the existing template

## Frontend State Management

### Key State Variables
```typescript
interface DuplicateCheck {
  checking: boolean                    // Currently checking with API
  isDuplicate: boolean                 // Exact match found
  existingTemplate?: {                 // Details of duplicate
    id: number
    name: string
    model?: string
  }
  isCopyOperation?: boolean            // Template was copied
  sameTextDiffConfig?: boolean        // Same prompt, different config
  similarTemplates?: Array<{...}>      // Similar but not exact
}
```

### API Integration
Duplicate checking sends the complete bundle:
```typescript
POST /api/prompt-tracking/templates/check-duplicate
{
  brand_name: "AVEA",
  prompt_text: "What are the best supplements?",
  model_name: "gpt-5",
  countries: ["US", "CH"],
  grounding_modes: ["web"],
  prompt_type: "recognition"
}
```

## User Journey Examples

### Creating Original Template
1. User types prompt text
2. Real-time checking shows ✅ "Unique prompt"
3. User selects model, countries, modes
4. Clicks Create → Success

### Accidentally Creating Duplicate
1. User enters same configuration as existing
2. Real-time checking shows ⚠️ "Duplicate found"
3. Create button disabled
4. User can:
   - Click "Run Existing" to test without creating
   - Click "View Template" to see the original
   - Modify configuration to make it unique

### Deliberately Copying Template
1. User clicks Copy on existing template
2. Form populated, no warnings shown
3. User modifies model from GPT-5 to Gemini
4. Now it's unique, saves successfully

### Testing Variations
1. User has template for GPT-5 + US + web
2. Copies template
3. Changes to GPT-5 + US + none (different grounding)
4. Saves successfully (different bundle)
5. Can now compare web vs non-web results

## Implementation Files

- **Frontend Component**: `frontend/src/components/PromptTracking.tsx`
- **Backend API**: `backend/app/api/prompt_tracking.py`
- **Hash Calculation**: `backend/app/services/prompt_hasher.py`

## Design Principles

1. **Templates are configuration bundles**, not just prompts
2. **Prevent accidental duplicates**, allow intentional ones
3. **Provide clear, actionable feedback** when duplicates detected
4. **Make it easy to create variations** for A/B testing
5. **Real-time feedback** reduces user frustration
6. **Copy operations** should be frictionless

## Future Enhancements

1. **Smarter copy warnings**: Warn if saving copied template without changes
2. **Bulk operations**: Copy multiple templates with batch modifications
3. **Template versioning**: Track changes to templates over time
4. **Comparison view**: Side-by-side results from similar templates
5. **Template groups**: Organize related test variations