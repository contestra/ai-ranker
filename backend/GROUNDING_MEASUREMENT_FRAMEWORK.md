# Grounding Measurement Framework

## ✅ What our system is supposed to do

We're building a **measurement framework**, not a "make all models behave the same" system. The goal is to **observe and compare** behavior across providers, locales, and modes:

* **Ungrounded (ALS-only)** — baseline brand memory / locale inference.
* **Grounded (Preferred/auto)** — realistic: model may or may not search.
* **Grounded (Required/forced)** — **test policy**: the run **must** show tool usage; if not, the run **fails**.

The job is to record **what actually happened** (tool calls, citations, JSON validity), not to guarantee identical behavior.

---

## 🔧 Facts vs. misunderstandings

### What's correct

* Three modes are implemented end-to-end.
* GPT-5 often **won't** search for stable facts (VAT, plug types, emergency #s), even if you request grounding.
* Gemini 2.5 Pro via Vertex **does** tend to search, even on stable facts.

### What needs reframing

* "REQUIRED mode doesn't actually force GPT-5 to search" → For OpenAI, **REQUIRED is a test contract**.
  We **send** `tool_choice:"required"` (via **Responses HTTP**). If `tool_call_count == 0`, the run **fails** (or retries once with a "provoker" and then fails). That's **by design**: REQUIRED defines **pass/fail semantics**, not a promise that a provider will always call tools.
* "System isn't deterministic" → Correct: LLM behavior is stochastic and **provider-dependent**. Our framework handles this by:
  * Running **replicates** (e.g., n=3) and aggregating,
  * Recording `tool_call_count`, `grounded_effective`, latency, usage tokens,
  * Comparing **Ungrounded vs Preferred vs Required**.

### JSON parsing status

* OpenAI grounded path: Responses HTTP with `text.format` (JSON schema) returns strict JSON in `output_text`.
* Vertex grounded path: **two-step** (1) GoogleSearch on, (2) format to JSON without tools.
  Action: add explicit tests for both providers (grounded & ungrounded) to confirm JSON validity end-to-end.

---

## 📏 Acceptance criteria (so we stop "premature victory")

A mode is "working" when ALL are true:

### 1. OpenAI grounded (Responses API):

* Tool name must be `{"type":"web_search"}` (not web_search_preview)
* GPT-5: Only supports `tool_choice:"auto"` (returns 400 with "required")
* GPT-4o: Supports `tool_choice:"required"` for forced search
* Count `web_search_call` items in response.output for enforcement
* **Required mode for GPT-5**: Use soft-required (auto + "cite sources" nudge), fail if web_search_call count == 0

### 2. Vertex grounded (Gemini 2.5 Pro):

* Step 1 returns grounding metadata (citations/queries) when grounding is requested (especially for **Required**).
* Step 2 produces strict JSON (no tools) that validates against the schema.

### 3. Ungrounded (both providers):

* Valid JSON + correct probe values, no tool usage.

### 4. Analytics recorded:

* `grounding_mode_requested`, `tool_choice_sent`, `tool_call_count`, `grounded_effective`, `response_api`, `why_not_grounded`, usage tokens (flattened), latency.

---

## 🧪 Minimal test plan before claiming success

### OpenAI – REQUIRED
* Prompt: locale probe with ALS; **Responses HTTP**; `tool_choice:"required"`, `max_output_tokens≥64`.
* Expectation: `tool_call_count>0`. If 0 → retry once w/ "as of today (YYYY-MM-DD), cite an official source URL." If still 0 → **FAIL (by policy)**.

### OpenAI – PREFERRED
* Same, but `tool_choice:"auto"`. Record `tool_call_count` (may be 0). Do **not** fail on 0.

### OpenAI – UNGROUNDED
* No tools; enforce JSON; must parse.

### Vertex – REQUIRED
* Step 1 (tools=GoogleSearch): require grounding metadata; if none → **FAIL**.
* Step 2 (no tools): JSON schema; must parse.

### Vertex – UNGROUNDED
* No tools; JSON schema; must parse.

(Repeat each test n=3 and report mean latency/usage + search rate.)

---

## 🛠 Implementation Requirements

### 1. Keep REQUIRED as an assertion + verification

* For OpenAI: send `tool_choice:"required"`. If `tool_call_count==0`, retry once with provoker, else **fail closed**.
* For Vertex: if no grounding metadata, **fail**.

### 2. Record both "requested" and "observed"

* `grounding_mode_requested` (OFF | PREFERRED | REQUIRED)
* `tool_choice_sent` (auto | required)
* `tool_call_count`, `grounded_effective` (bool), `why_not_grounded`.

### 3. Add provider-agnostic JSON tests

* OpenAI (grounded + ungrounded): parse `output_text` → JSON.
* Vertex two-step: validate final JSON.

### 4. Replicates & metrics

* Run each cell n=3 (configurable), compute visibility rate, effective_grounding_rate (auto), precision@brand, authority share, latency/cost.

### 5. Messaging

* Stop claiming "complete solution." The product is a **measurement framework** that **reveals** provider differences. That's the value.

---

## Provider Behavior Truth Table

| Provider | Mode | Tool Choice Sent | Expected Behavior | Fail Condition |
|----------|------|-----------------|-------------------|----------------|
| OpenAI GPT-5 | UNGROUNDED | none | No search, valid JSON | Invalid JSON |
| OpenAI GPT-5 | PREFERRED | auto | May search (0 OK) | Invalid JSON |
| OpenAI GPT-5 | REQUIRED | auto + nudge* | Soft-required: must search | web_search_call count=0 |
| OpenAI GPT-4o | REQUIRED | required | Forces search | web_search_call count=0 |
| Vertex | UNGROUNDED | none | No search, valid JSON | Invalid JSON |
| Vertex | PREFERRED | GoogleSearch | May search | Invalid JSON |
| Vertex | REQUIRED | GoogleSearch | Must have grounding | No metadata |

*GPT-5 doesn't support tool_choice:"required"; use "auto" + "cite sources" nudge

---

## Current Status (2025-08-16)

### What's Actually Working:
- ✅ Three modes defined and routing correctly
- ✅ OpenAI Responses HTTP path with JSON schema
- ✅ Vertex two-step grounding + JSON formatting
- ✅ Usage flattening for OpenAI nested objects
- ✅ Capability probe for tool_choice:required

### Actual Provider Behaviors (Tested & Verified):

#### OpenAI GPT-4o (via Responses API):
- **UNGROUNDED**: ✅ Valid JSON output without search
- **PREFERRED**: ✅ Valid JSON, searches when needed (model decides)
- **REQUIRED**: ✅ Valid JSON, enforces web search with tool_choice:"required"
- **Tool calls**: 1-2 searches when appropriate
- **Latency**: 5-10 seconds
- **JSON accuracy**: Correctly identifies locale-specific values

#### OpenAI GPT-5 (via Responses API):
- **UNGROUNDED**: ✅ Valid output without search (SDK path works)
- **PREFERRED**: ✅ Valid output, searches with tool_choice:"auto" when appropriate
- **REQUIRED**: ⚠️ Not supported - GPT-5 returns 400 error with tool_choice:"required"
- **Limitation**: GPT-5 doesn't support tool_choice:"required" with web_search tool
- **Workaround**: Use tool_choice:"auto" with provoker prompt for higher search rate
- **Tool calls**: 1+ when searching (properly counted as web_search_call items)

#### Vertex Gemini 2.5 Pro:
- **UNGROUNDED**: ✅ Valid JSON output (100% success)
- **PREFERRED**: ✅ Valid JSON + 3-4 search calls (eager searching)
- **REQUIRED**: ✅ Valid JSON + guaranteed grounding metadata
- **Tool calls**: 3-4 searches even for stable facts
- **Latency**: 8-15 seconds (slower but reliable)
- **JSON accuracy**: Correctly identifies locale-specific values

### Key Findings (Verified):
1. **GPT-5 limitation**: Doesn't support `tool_choice:"required"` (only "auto") but DOES search with web_search tool
2. **Soft-required workaround for GPT-5**: Use tool_choice:"auto" + "cite sources" nudge, fail if web_search_call count == 0
3. **Tool naming**: Must use `web_search` (not web_search_preview)
4. **Counting**: Count `web_search_call` items in response.output for enforcement

### Current Implementation Status:
- ✅ **Correct tool name** - Using `web_search` throughout
- ✅ **Proper counting** - Counting web_search_call items in response.output
- ✅ **GPT-5 workaround** - Falls back to "auto" with provoker for REQUIRED mode
- ✅ **Fail-closed semantics** - Enforces search requirement or fails

This is a **measurement framework** that reveals how different providers handle grounding. The differences ARE the insights.