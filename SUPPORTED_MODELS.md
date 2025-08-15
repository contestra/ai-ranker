# Officially Supported Models - DO NOT DEVIATE

## Supported Models ONLY

### OpenAI
- **GPT-5** - Primary model with web search via Responses API
- **GPT-5-mini** - Smaller variant 
- **GPT-5-nano** - Smallest variant

**DO NOT USE**: GPT-4o, GPT-4o-mini, or any GPT-3.5 models

### Google/Vertex
- **Gemini 2.5 Pro** - Primary model with GoogleSearch grounding
- **Gemini 2.5 Flash** - Faster variant

**DO NOT USE**: Gemini 1.5 Pro, Gemini 1.5 Flash, or Gemini 2.0 models

## Critical Requirements

1. **GPT-5 Models**:
   - Must use temperature=1.0 (hardcoded requirement)
   - Use Responses API for web search
   - Set `tool_choice="required"` for grounding

2. **Gemini 2.5 Models**:
   - Only 2.5 supports GoogleSearch grounding
   - Use temperature=1.0 for best grounding
   - Returns markdown-wrapped JSON with grounding

## Why These Models Only

- **GPT-5**: Latest OpenAI model with native web search
- **Gemini 2.5 Pro**: Only Gemini version with full grounding support
- Earlier models (GPT-4, Gemini 1.5) lack required grounding capabilities

## Update Required Files

All references to GPT-4o must be changed to GPT-5
All references to Gemini 1.5 or 2.0 must be changed to Gemini 2.5 Pro/Flash