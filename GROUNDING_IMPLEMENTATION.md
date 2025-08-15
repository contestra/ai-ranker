# Grounding Implementation Guide

## Overview
This document describes the proper implementation of grounding (web search) functionality for AI models, specifically focusing on API-level control rather than prompt modification.

## The Problem with Prompt-Based Grounding

### ❌ WRONG: Prompt Modification Approach
```python
# BAD - Modifying the prompt text
if use_grounding:
    prompt = f"Please search the web and answer: {original_prompt}"
else:
    prompt = original_prompt
```

**Issues with this approach:**
- **Contaminates the question** - Adding "please search the web" biases what gets listed
- **Provider-fragile** - Ignored or over-obeyed depending on model updates
- **Poor A/B testing** - Can't compare grounded vs ungrounded with identical prompts
- **Non-deterministic** - Model may or may not actually search based on its interpretation

## The Correct Implementation

### ✅ RIGHT: API-Level Tool Control

#### For Google Gemini (gemini-2.5-pro, gemini-2.5-flash, etc.)

```python
from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
from langchain_google_genai import ChatGoogleGenerativeAI

# Create model
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.1,
    google_api_key=api_key
)

# Enable grounding via API tools
if use_grounding:
    search_tool = GenAITool(google_search={})
    model = model.bind_tools([search_tool])

# Keep prompt naked/unmodified
messages = [
    SystemMessage(content="You may use tools to verify facts. Do not mention tool use, sources, or URLs in the answer."),
    HumanMessage(content=original_prompt)  # UNCHANGED prompt
]

response = await model.ainvoke(messages)
```

#### For OpenAI (GPT-4, GPT-5)

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4", temperature=0.1)

if use_grounding:
    # Define search tool
    tools = [{
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }]
    
    # Bind tools and set tool_choice
    model = model.bind_tools(tools)
    model.tool_choice = "auto"  # Allow model to decide when to use tools
else:
    model.tool_choice = "none"  # Explicitly disable tools
```

#### For Anthropic (Claude)

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-3-5-sonnet", temperature=0.1)

if use_grounding:
    # Include tools in the request
    tools = [
        {
            "name": "web_search",
            "description": "Search the web for current information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    ]
    model = model.bind_tools(tools)
# If not grounding, simply omit tools - Claude won't use them
```

## System Prompts for Grounded Runs

When grounding is enabled, add a minimal system instruction:

```python
grounding_system_prompt = """You may use tools to verify facts. 
Do not mention tool use, sources, or URLs in the answer.
Prefer official/government sources when tools are used."""
```

When ALS (Ambient Location Signals) is also present:

```python
combined_system_prompt = """Use ambient context only to infer locale and set defaults.
You may use tools to verify facts.
Do not mention tool use, sources, URLs, or location inference in the answer."""
```

## Implementation Checklist

### ✅ DO:
- [ ] Create a boolean flag `use_grounding` in your runner
- [ ] Enable/disable tools at the API level based on this flag
- [ ] Keep prompts naked/unmodified regardless of grounding
- [ ] Use system prompts for tool usage guidance
- [ ] Log `grounded` status in run metadata
- [ ] Test both grounded and ungrounded modes with identical prompts

### ❌ DON'T:
- [ ] Add "please search the web" to prompts
- [ ] Modify prompt text based on grounding mode
- [ ] Mix grounded/ungrounded outputs in the same metric
- [ ] Assume grounding works the same across providers

## Required Dependencies

### For Google Gemini:
```bash
pip install google-ai-generativelanguage>=0.6.0
pip install langchain-google-genai>=2.1.0
```

### For OpenAI:
```bash
pip install langchain-openai>=0.1.0
```

### For Anthropic:
```bash
pip install langchain-anthropic>=0.1.0
```

## Testing Grounding

### Test Script Example:
```python
async def test_grounding():
    prompt = "What are the top 3 longevity supplement brands in 2024?"
    
    # Test WITHOUT grounding
    ungrounded_response = await run_prompt(prompt, use_grounding=False)
    
    # Test WITH grounding (same prompt!)
    grounded_response = await run_prompt(prompt, use_grounding=True)
    
    # Compare results
    print(f"Ungrounded: {ungrounded_response[:100]}...")
    print(f"Grounded: {grounded_response[:100]}...")
    
    # Grounded should have more current/specific information
```

## Troubleshooting

### Issue: Empty responses with grounding enabled
**Possible causes:**
1. API quota exceeded for grounding/search tools
2. LangChain version incompatibility
3. Missing tool permissions in API key

**Solution:**
- Check API quotas and limits
- Update LangChain packages
- Verify API key has necessary permissions

### Issue: Model ignores grounding setting
**Cause:** Using prompt modification instead of API tools

**Solution:** Implement proper API-level tool binding as shown above

### Issue: Different results between providers
**Cause:** Each provider implements tools differently

**Solution:** Test and tune system prompts per provider

## Current Status (August 15, 2025)

- ✅ Google Gemini: API-level grounding implemented
- ⚠️ LangChain integration: Intermittent issues with empty responses
- ✅ Direct Google API: Working correctly
- 🔄 OpenAI/Anthropic: Implementation pending

## References

- [Google AI Grounding Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search)
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/agents/tools/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use)