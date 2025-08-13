# Fingerprint Patch (OpenAI + Gemini)

This mini-drop adds **provider-agnostic fingerprinting** for your LangChain adapter.

- **OpenAI (ChatGPT-5/GPT):** store `system_fingerprint`
- **Gemini 2.5 Pro:** store `modelVersion` (as the fingerprint) and also capture `responseId`
- Store `seed` and full generation params for best-effort reproducibility

## Files
- `adapter_fingerprint.py` – utilities to extract a normalized fingerprint and build a DB-ready record
- `tests/test_adapter_fingerprint.py` – pytest unit tests

## How to use in your adapter

```python
from adapter_fingerprint import build_run_record

# ... after you get ai_msg from LangChain (regardless of provider)
response_metadata = dict(getattr(ai_msg, "response_metadata", {}) or {})
usage_metadata = getattr(ai_msg, "usage_metadata", None) or {}

record = build_run_record(
    provider=provider_name,               # "openai" | "gemini"
    model_alias=model_name,               # e.g. "gpt-5" or "gemini-2.5-pro"
    prompt_text=prompt_text,
    completion_text=ai_msg.content,
    response_metadata=response_metadata,
    usage_metadata=usage_metadata,
    temperature=temperature,
    top_p=top_p,
    max_tokens=max_tokens,
    seed=seed,                            # make sure you pass it into both providers
    existing_metadata_json={},            # start with your current metadata blob if needed
)

# Insert `record` into your DB as usual. You can keep your existing `system_fingerprint` column.
```

### Passing a seed
- **OpenAI:** set `seed` on the model or call (LangChain supports this).
- **Gemini:** on Vertex AI, pass `generation_config={"seed": seed}`; the plain Gemini Dev API may ignore `seed` but logging it is still useful.

### No schema change required
- We reuse your `system_fingerprint` column:
  - OpenAI → `system_fingerprint` (native)
  - Gemini → `modelVersion` (stored in `system_fingerprint`)
- `responseId` and `modelVersion` are also copied into the `metadata` JSON for transparency (`gemini_response_id`, `gemini_model_version`).

If you later want stronger typing, add a `fingerprint_type` column (we already include this key in the dict).

## Run tests
```
pytest -q
```

MIT License.