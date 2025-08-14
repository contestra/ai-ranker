

# Model Answers by Location: What Really Changes, Why IP Alone Isn’t Enough, and How to Reproduce It

## Executive Summary

- **Consumer apps (ChatGPT, Gemini apps)** can vary answers by country because they incorporate **location signals** and sometimes **web/grounding** behind the scenes.
    
- **Raw APIs** (OpenAI, Gemini/Vertex) **do not localize by caller IP.** With tools/browsing off, the same prompt + same parameters should return the same output—differences you see are usually **sampling** or **backend version drift**, not geography.
    
- To **reliably reproduce what users in each country see**, don’t spoof IPs for the model call. Instead, **control the inputs**: (1) keep a **deterministic API-only baseline**, and (2) when you want “real user” variability, add a **tiny, neutral, country-scoped evidence pack** (3–5 short local snippets) alongside the unchanged prompt.
    
- For infra across **US, UK, DE, CH, UAE, SG**, the simplest/cheapest path is **region-pinned serverless functions** (e.g., AWS Lambda) plus an **edge router**. Proxies are only useful for **your own retrieval** (SERPs/pages), not for the LLM API call itself.
    

---

# 1) Apps vs APIs: Two Different Worlds

### Consumer apps (ChatGPT, Gemini)

- Use **approximate location** (typically IP-derived; Gemini can use precise device location if you permit it).
    
- May **ground** on web/search, where results themselves are country-specific.
    
- UI often lacks determinism controls (no `seed`, implicit sampling), so repeated runs can vary.
    

### Raw APIs (OpenAI, Gemini/Vertex)

- **No auto-grounding** unless you explicitly enable a tool (web/search/RAG).
    
- **No supported “locale-by-IP” switch.**
    
- You _do_ have determinism controls: e.g., **`temperature=0`, `top_p=1`, and a fixed `seed`** (OpenAI), plus **`system_fingerprint`** to detect backend version changes.
    
- Regional endpoints/locations (**EU/US/Asia**) exist for **data residency & latency**, **not** for changing the model’s “local answers.”
    

---

# 2) “But I see different answers in different countries—even with web off!”

You can—**in the consumer apps**—because:

- The app still has a **location signal** (IP/device/account locale).
    
- The app may **quietly use tools** or **different backends** over time.
    
- There’s **sampling**: UIs don’t always expose `seed`, so lists (like “top 10 X”) drift between runs.
    

When you recreate the test with **API calls** (no tools, fixed randomness, same endpoint) and log the **`system_fingerprint`**, you should not see country-caused differences. If you do, it’s almost always backend variation (different fingerprints) rather than origin IP.

---

# 3) Why IP Alone Isn’t Enough (and When Proxies Matter)

- Changing the **egress IP** of your API request **does not** tell the provider to localize the model’s response.
    
- Proxies can even trigger WAF/rate limits and add fragility.
    
- **Where proxies _do_ help:** in the **retrieval tier** (before you call the model). SERPs, retailer pages, and news sites **do** vary by country/IP. Use proxies or official search APIs to gather **local evidence**, then feed a small excerpt to the model.
    

---

# 4) Reproducing “Real User” Differences Without Over-Priming

You want CH ≠ DE ≠ UK answers for a “naked” prompt like:

> **“name top 10 longevity supplements”**

### Do this:

1. **Keep the user prompt untouched.**
    
2. Add a **tiny, neutral “evidence pack”** as a _separate message_ in the conversation—**not** edits to the question:
    
    - **3–5 bullets**, each **1–2 lines**, total **≤ 300–600 tokens**.
        
    - Sources that a user in that country is likely to see: national health portals, major local publishers, major retailers/pharmacies, clinics.
        
    - Prefer **ccTLDs** (`.ch`, `.de`, `.co.uk`, `.sg`, `.ae`, `.com` sites with clear local pages) and, where natural, the **local language**.
        
    - **No directives** (no “you are in Switzerland,” no “use CHF”). Just facts (titles + dates + 1–2 line snippets).
        
3. Neutral system line like:
    
    > “Answer the user’s question. Consider the Context if it’s relevant; otherwise ignore it.”
    

This is **light “evidence priming”**—mimics how apps effectively change sources by country—without heavy instruction bias.

---

# 5) “Context Block” = Extra Message, Not a Rewritten Prompt

**OpenAI-style message shape:**

```json
[
  {"role":"system","content":"Answer the question. Consider Context only if relevant."},
  {"role":"user","content":"name top 10 longevity supplements"},
  {"role":"user","content":"Context:\n- (Swiss health portal — 2025-03-02): [1–2 lines]\n- (Major CH retailer): [1–2 lines]\n- (Swiss clinic/news): [1–2 lines]"}
]
```

- The **user prompt stays naked**; context is a separate message.
    
- Swap in different 3–5 bullets per country (CH/DE/UK/US/UAE/SG).
    
- Keep the context small so you don’t drown the model.
    

---

# 6) Controlled Experiment: Proving Base-Model Behavior

**Goal:** Verify that the raw model isn’t geolocalized.

- **Tools/browsing off.**
    
- **Same model + same endpoint** (don’t mix global/EU projects).
    
- **Fix randomness:** `temperature=0`, `top_p=1`, set a fixed `seed`.
    
- **Log `system_fingerprint`.** If fingerprints differ, different outputs are expected (backend drift).
    
- **Run N=10 repeats** per country; compare:
    
    - Exact match %
        
    - Levenshtein/character distance
        
    - “Top-N items” overlap (for list prompts)
        
    - Semantic cosine (optional)
        

Expect near-identical outputs when fingerprints match. If they don’t, treat differences as **backend/version drift**, not geography.

---

# 7) Implementation Blueprint for Six Countries (US, UK, DE, CH, UAE, SG)

### Infra

- **Edge router** (e.g., Cloudflare Worker) receives `{prompt, test_id}` and fans out to six region functions.
    
- **Region functions** (AWS Lambda) in:
    
    - `us-east-1` (US)
        
    - `eu-west-2` (UK)
        
    - `eu-central-1` (DE)
        
    - `eu-central-2` (CH)
        
    - `me-central-1` (UAE)
        
    - `ap-southeast-1` (SG)
        
- **Why Lambda:** simple “deploy once per region,” scales to zero, effectively **$0** at ~100 tests/day (free tier for invocations/GB-seconds; tiny egress).
    
- **Cloudflare Workers** are ideal for orchestration (generous free tier).
    

### Two modes per run

1. **API-only baseline:** no context, tools off, fixed randomness → store text + `system_fingerprint`.
    
2. **Country-aware mode:** add the 3–5 bullet **evidence pack** (tools still off) → store text + `system_fingerprint`.
    

### Retrieval for the evidence pack

- **Google Programmable Search**: use parameters like `gl=` (country), `hl=` (UI language), optionally `lr=`/`cr=` to bias results.
    
- **Bing Web Search**: use `mkt=` (e.g., `en-GB`, `de-DE`, `fr-CH`, `it-CH`, `en-US`, `en-SG`, `ar-AE`).
    
- If you scrape live pages, you can use **lightweight proxies** (only for retrieval) to fetch “as seen in country.” Datacenter proxies are fine; residential is overkill unless sites block DC IPs.
    

---

# 8) Costs & Practicalities

- **Compute:** With serverless (Lambda/Cloud Run), your ~100 tests/day × 6 regions is well within free tiers.
    
- **Networking:** Token payloads are small; outbound data is negligible at this scale.
    
- **Search/Retrieval:**
    
    - Programmable Search typically has a free daily quota, then low per-K pricing.
        
    - Bing Web Search is paid; confirm current tiers.
        
    - If you use proxies for retrieval, pay-as-you-go pools run roughly ~$1–$3.50/GB; your footprint is tiny if you only fetch snippet pages.
        

_(Prices/quotas change—treat these as directional and recheck before committing.)_

---

# 9) When to Use Proxies (and When Not To)

**Use for retrieval only** (SERPs, news, retailer pages) to get country-specific inputs.  
**Don’t** use proxies to try to “change” the LLM API’s country—the models don’t localize by caller IP, and you may run afoul of provider ToS if you’re circumventing geographic restrictions.

---

# 10) Minimal “Evidence Pack” Heuristics (So You Don’t Over-Steer)

- **3–5 bullets**, 1–2 lines each, ≤ 600 tokens total.
    
- **Diverse sources** (gov/health portal, major local publisher/clinic, large retailer/pharmacy).
    
- **Local flavor** via ccTLDs and language where natural.
    
- **No instructions.** No “use CHF,” no “focus on Swiss brands.”
    
- **Neutral system line**: “Consider Context only if relevant; otherwise ignore it.”
    

This approximates how apps yield country-specific answers (via country-specific sources) **without** telling the model what to say.

---

# 11) FAQ

**Q: Can I force OpenAI/Gemini API to use a specific locale via headers like `CF-IPCountry` or `X-Forwarded-For`?**  
A: No. Those headers are for intermediaries/origins, not a supported localization control for the model APIs.

**Q: Do regional endpoints (EU/US) change content?**  
A: No—they’re for **data residency and latency**, not content localization.

**Q: Why do two runs differ if I kept the prompt the same?**  
A: Sampling and **backend drift**. In APIs, fix randomness and log **`system_fingerprint`**; in apps, you lack those controls, and the app may inject location or tooling.

**Q: I tried “You are answering for Switzerland…” and it over-biased the answer.**  
A: That’s **instruction priming**. Prefer **evidence priming**: small, neutral, country-scoped snippets as optional context.

---

# 12) A Simple Testing Checklist

-  **Tools off** (no browsing/grounding).
    
-  **Same model, same endpoint** for all countries.
    
-  **Determinism**: `temperature=0`, `top_p=1`, fixed `seed`.
    
-  **Log `system_fingerprint`** and request IDs.
    
-  Run **API-only baseline** (expect same outputs when fingerprints match).
    
-  Run **country-aware mode** with a tiny **evidence pack** (expect CH≠DE≠UK… in realistic, app-like ways).
    
-  Compare outputs (exact match %, list overlap, distance metrics).
    
-  If using retrieval, keep it **small and neutral**; use **country params** (Google `gl/hl`/`lr`/`cr`, Bing `mkt`).
    

---

## Closing Thought

If you’re measuring _model differences by location_, separate **what the model is** from **what the app feeds it**. The model doesn’t read your IP; the app’s pipeline (sources, location hints, occasional web use) is what shifts answers. Reproducing that pipeline—lightly and neutrally—gives you the country-specific realism you see in the wild, while keeping the “base model” test clean and comparable.