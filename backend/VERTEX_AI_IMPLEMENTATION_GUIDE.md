# Vertex AI Implementation Guide for AI Ranker

## Two SDK Options

### Option 1: Traditional Vertex AI SDK (Stable)
```python
import vertexai
from vertexai.generative_models import GenerativeModel, Tool
vertexai.init(project="contestra-ai", location="europe-west4")

# Ungrounded
model = GenerativeModel("gemini-1.5-flash-002")
response = model.generate_content("List top longevity supplements")

# Grounded with Google Search
from vertexai.generative_models import grounding
google_search_tool = Tool.from_google_search_retrieval(
    grounding.GoogleSearchRetrieval()
)
model_grounded = GenerativeModel(
    "gemini-1.5-flash-002",
    tools=[google_search_tool]
)
response = model_grounded.generate_content("List top longevity supplements in 2024")
```

### Option 2: New Google GenAI Client (Simpler)
```python
from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")

# Ungrounded
response = client.models.generate_content(
    model="gemini-1.5-flash-002",
    contents="List top longevity supplements"
)

# Grounded with Google Search
response = client.models.generate_content(
    model="gemini-1.5-flash-002",
    contents="List top longevity supplements in 2024",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
```

## Implementation for AI Ranker

### 1. Install Dependencies
```bash
pip install google-cloud-aiplatform google-genai langchain-google-vertexai -q
```

### 2. Update langchain_adapter.py for Vertex AI

```python
async def analyze_with_vertex_gemini(
    self, 
    prompt: str, 
    use_grounding: bool = False,
    model_name: str = "gemini-1.5-flash-002",
    temperature: float = 0.0,
    seed: int = 42,
    context: str = None  # ALS block
) -> Dict[str, Any]:
    """
    Use Vertex AI Gemini with server-side grounding.
    
    Args:
        prompt: Naked user prompt (unmodified)
        use_grounding: Enable Google Search tool
        context: ALS ambient block (separate message)
    """
    from google import genai
    from google.genai import types
    
    # Initialize client (uses ADC)
    client = genai.Client(
        vertexai=True, 
        project="contestra-ai", 
        location="europe-west4"
    )
    
    # Build messages with ALS context
    messages = []
    
    # System prompt for ALS handling
    if context:
        system_prompt = """Use ambient context only to infer locale and set defaults (language variants, units, currency, regulatory framing, availability). 
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not name countries/regions/cities or use country codes unless explicitly asked.
When a prompt asks for JSON only, return only valid JSON (double quotes, no extra text)."""
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=system_prompt)]
        ))
        messages.append(types.Content(
            role="model", 
            parts=[types.Part(text="Understood.")]
        ))
        # Add ALS block
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=context)]
        ))
        messages.append(types.Content(
            role="model",
            parts=[types.Part(text="Noted.")]
        ))
    
    # Add naked prompt
    messages.append(types.Content(
        role="user",
        parts=[types.Part(text=prompt)]
    ))
    
    # Configure generation
    config = types.GenerateContentConfig(
        temperature=temperature,
        top_p=1.0,
        candidate_count=1,
        seed=seed
    )
    
    # Add grounding if requested
    if use_grounding:
        config.tools = [types.Tool(google_search=types.GoogleSearch())]
    
    # Generate response
    import time
    start_time = time.time()
    
    try:
        response = await client.models.generate_content_async(
            model=f"models/{model_name}",
            contents=messages,
            config=config
        )
        
        return {
            "content": response.text,
            "system_fingerprint": response.candidates[0].grounding_metadata.retrieval_metadata if use_grounding else None,
            "model_version": model_name,
            "temperature": temperature,
            "seed": seed,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "grounded": use_grounding
        }
    except Exception as e:
        return {
            "content": f"[ERROR] Vertex AI error: {str(e)}",
            "error": str(e),
            "response_time_ms": int((time.time() - start_time) * 1000)
        }
```

## IAM Setup (for Production)

### Create Service Account
```powershell
# In PowerShell with gcloud installed
gcloud iam service-accounts create vertex-runner `
  --display-name "Vertex AI Runner" `
  --project contestra-ai

# Grant necessary roles
gcloud projects add-iam-policy-binding contestra-ai `
  --member="serviceAccount:vertex-runner@contestra-ai.iam.gserviceaccount.com" `
  --role="roles/aiplatform.user"

# For BigQuery analytics (future)
gcloud projects add-iam-policy-binding contestra-ai `
  --member="serviceAccount:vertex-runner@contestra-ai.iam.gserviceaccount.com" `
  --role="roles/bigquery.dataEditor"
```

### Download Service Account Key (for production deployment)
```powershell
gcloud iam service-accounts keys create vertex-key.json `
  --iam-account=vertex-runner@contestra-ai.iam.gserviceaccount.com
```

## Quick Smoke Tests

### Test 1: Basic Vertex AI
```python
import vertexai
from vertexai.generative_models import GenerativeModel
vertexai.init(project="contestra-ai", location="europe-west4")
resp = GenerativeModel("gemini-1.5-flash-002").generate_content("Say OK")
print("Vertex says:", resp.text)
```

### Test 2: New GenAI Client
```python
from google import genai
client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
print(client.models.generate_content(model="gemini-1.5-flash-002", contents="Say OK").text)
```

### Test 3: With Grounding
```python
from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
response = client.models.generate_content(
    model="gemini-1.5-flash-002",
    contents="What is the current weather in Tokyo?",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
print("Grounded response:", response.text)
```

## Key Architecture Points

1. **No prompt modification**: Never add "search the web" to prompts
2. **Server-side grounding**: Vertex executes tools automatically
3. **ALS stays separate**: Context as separate message, prompt stays naked
4. **Fixed params**: temperature=0, top_p=1, seed=42 for reproducibility
5. **Europe region**: Using europe-west4 for data residency

## Migration Path

1. Enable Vertex AI API in console
2. Test with smoke tests above
3. Update langchain_adapter.py with vertex method
4. Route grounded calls through Vertex
5. Keep ungrounded calls on direct Gemini API (or move all to Vertex)

## Advantages of Vertex AI

- **Server-side tool execution**: No manual tool loops
- **Built-in grounding**: Google Search works out of the box
- **Better reliability**: Google handles retries and fallbacks
- **Data residency**: Can specify region (europe-west4)
- **Future extensibility**: Easy to add enterprise search, datastores

## Cost Considerations

- Vertex AI pricing is similar to direct API
- Grounding adds minimal cost (~$0.0001 per grounded query)
- Free tier: $300 credits for new GCP accounts
- Monitor usage in Cloud Console