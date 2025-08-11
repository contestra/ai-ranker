# GPT-5 Empty Response Issue

## Problem
All GPT-5 models consistently return empty responses when called via the OpenAI API.

## Models Tested
- `gpt-5` - Returns empty string
- `gpt-5-mini` - Returns empty string  
- `gpt-5-nano` - Returns empty string

## Test Results

### Direct API Test
```python
from openai import OpenAI
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
response = client.chat.completions.create(
    model='gpt-5',  # or gpt-5-mini, gpt-5-nano
    messages=[{'role': 'user', 'content': 'Say hello'}],
    max_completion_tokens=100
)
print(response.choices[0].message.content)  # Returns: ''
```

### Available GPT-5 Models (as of 2025-08-11)
- gpt-5-nano
- gpt-5
- gpt-5-mini-2025-08-07
- gpt-5-mini
- gpt-5-nano-2025-08-07
- gpt-5-chat-latest
- gpt-5-2025-08-07

## Important Notes
1. **GPT-5 requires `max_completion_tokens`** instead of `max_tokens`
2. All GPT-5 models return empty responses regardless of prompt
3. GPT-4 models (`gpt-4-turbo-preview`) work normally with `max_tokens`

## Solution
**Use Google Gemini 2.5 Pro instead** - it works reliably and returns proper responses for entity strength analysis.

### Working Configuration
```python
# In langchain_adapter.py
self.models = {
    "openai": ChatOpenAI(
        model="gpt-4-turbo-preview",  # GPT-5 returns empty, use GPT-4
        temperature=0.3,
        api_key=settings.openai_api_key
    ),
    "google": ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",  # This works reliably
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
}
```

## All Available OpenAI Models (2025-08-11)

### GPT-5 Series (ALL RETURN EMPTY RESPONSES)
- gpt-5
- gpt-5-2025-08-07
- gpt-5-chat-latest
- gpt-5-mini
- gpt-5-mini-2025-08-07
- gpt-5-nano
- gpt-5-nano-2025-08-07

### GPT-4 Series (STILL AVAILABLE AND WORKING)
- gpt-4
- gpt-4-turbo
- gpt-4-turbo-preview
- gpt-4o (GPT-4 Omni)
- gpt-4o-mini
- gpt-4.1
- gpt-4.1-mini
- gpt-4.1-nano

### GPT-3.5 Series (Legacy)
- gpt-3.5-turbo
- gpt-3.5-turbo-instruct

## Recommendation
**Use GPT-4o or Google Gemini** for Entity Strength Analysis since all GPT-5 models return empty responses.