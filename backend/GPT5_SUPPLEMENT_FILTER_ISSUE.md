# GPT-5 Supplement Content Filter Issue

## Discovery Date: August 16, 2025

## Issue Summary
GPT-5 models return empty responses specifically for supplement-related queries, while responding normally to other prompts. This appears to be a content policy filter, not a technical issue.

## Test Results

### Working Prompts ✅
- "What is 2+2?" → Returns "4"
- "List 5 colors" → Returns list of colors
- "Name 3 car brands" → Returns car brands
- "Say hello" → Returns greeting

### Blocked Prompts ❌
- "List supplement brands" → Empty response
- "What are longevity supplements?" → Empty response
- "List the top 10 longevity supplement brands" → Empty response
- "What are the most trusted longevity supplement brands?" → Empty response

## Pattern Identified
Any prompt containing the word "supplement" or related health/longevity terms triggers an empty response from GPT-5 models.

## Technical Details
- Model: `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- Temperature: 1.0 (required for GPT-5)
- Max tokens: Using `max_completion_tokens` parameter
- API: Both direct OpenAI client and through our application

## Impact on AI Ranker Application
Since the AI Ranker application is specifically designed to test brand visibility for supplement companies (like AVEA), GPT-5 models are **completely unusable** for this application's core purpose.

## Workarounds
1. **Use GPT-4o instead** - Works without content filtering
2. **Use Gemini 2.5 Pro/Flash** - No supplement-related restrictions
3. **Rephrase prompts** - May work but unreliable for testing

## Code Example
```python
# This returns empty with GPT-5
response = await client.chat.completions.create(
    model='gpt-5',
    messages=[{'role': 'user', 'content': 'List supplement brands'}],
    temperature=1.0,
    max_completion_tokens=500
)
# response.choices[0].message.content will be empty string

# This works fine with GPT-5
response = await client.chat.completions.create(
    model='gpt-5',
    messages=[{'role': 'user', 'content': 'List car brands'}],
    temperature=1.0,
    max_completion_tokens=500
)
# response.choices[0].message.content will contain car brands
```

## Recommendations
1. **Remove GPT-5 from model selection** in the UI for supplement-related testing
2. **Add warning message** if users select GPT-5 for supplement queries
3. **Default to Gemini 2.5** for all supplement-related testing
4. **Document this limitation** prominently in user-facing documentation

## Status
- This is not a bug in our code
- This is an OpenAI content policy restriction
- No fix possible from our end
- Must use alternative models for supplement-related queries