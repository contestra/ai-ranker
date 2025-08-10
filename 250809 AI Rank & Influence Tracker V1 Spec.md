Got it — here’s a **full, detailed, end-to-end project specification** that another LLM or engineering team could directly follow to build the **AI Rank & Influence Tracker** exactly as we’ve developed it.

---

# **Project Specification: AI Rank & Influence Tracker (Google-Aligned)**

## **1. Project Overview**

The **AI Rank & Influence Tracker** is a measurement and optimization platform for monitoring and improving brand visibility in Large Language Models (LLMs) like GPT-5, Gemini, and Claude.

The system will:

1. **Measure** brand visibility via prompt-based probing (B→E and E→B), grounded and ungrounded modes.
    
2. **Analyze** LLM behavior to identify conditions, pivot words, and contexts that trigger brand mentions.
    
3. **Map** brand association networks to show brand ↔ concept ↔ competitor relationships.
    
4. **Track** trends over time and produce a **single representation score** for executive reporting.
    
5. **Provide** actionable insights for increasing brand recall in LLMs via PR, content, structured data, and training data injection.
    
6. **Align** embedding similarity scoring with **Google/Gemini’s dot product on normalized vectors** method.
    

---

## **2. Core Concepts**

- **B→E (Brand-to-Entities):** Prompts that elicit concepts/products/competitors associated with a brand.
    
- **E→B (Entities-to-Brand):** Prompts that elicit brands associated with a concept/category.
    
- **Grounded Mode:** Model uses external data retrieval.
    
- **Ungrounded Mode:** Model answers from internal weights only.
    
- **Naked Brand Token Recall:** Brand appears without hints/context.
    
- **Google-Aligned Embedding Similarity:** Dot product between normalized vectors (equivalent to cosine similarity for unit-length vectors).
    

---

## **3. Functional Requirements**

### **3.1 Prompt Experimentation**

- Maintain a **prompt taxonomy** covering:
    
    - Intent types: informational, comparison, recommendation, transactional.
        
    - Syntax variations: question, statement, scenario.
        
    - Specificity levels: broad vs niche category prompts.
        
- Execute prompts in:
    
    - **Ungrounded** mode.
        
    - **Grounded** mode.
        
- Run multiple repetitions per prompt (configurable N) with fixed random seeds.
    
- Control generation parameters (temperature=0 or 0.1, top_p fixed).
    

### **3.2 LLM Integration**

- **Providers:**
    
    - OpenAI (GPT-5 + embeddings)
        
    - Google (Gemini + embeddings)
        
    - Anthropic (Claude + embeddings)
        
- **Embedding Alignment:**
    
    - Normalize all vectors.
        
    - Score similarity using dot product:
        
        ```python
        def normalize(vec):
            mag = np.linalg.norm(vec)
            return vec / mag if mag > 0 else vec
        
        def google_similarity(vec_a, vec_b):
            return float(np.dot(normalize(vec_a), normalize(vec_b)))
        ```
        

### **3.3 Entity Extraction & Normalization**

- Extract entities from completions using:
    
    - spaCy transformer NER
        
    - Brand dictionary
        
    - Regex fallback patterns
        
- Canonicalize variants (e.g., “Avea”, “Avea Life AG” → canonical ID)
    
- Collision handling:
    
    - Blocklist unrelated entities with same name.
        
    - Require ≥2 signals (name + domain, name + product line).
        
- Store canonical entity IDs in DB.
    

### **3.4 Scoring**

- **Mention Rate:** % completions with brand present.
    
- **Avg Rank:** Mean list position of brand when mentioned.
    
- **Weighted Score:** mention_rate × rank_weight(avg_rank).
    
- **Confidence Intervals:** Wilson CI for mention_rate; bootstrapped CI for scores.
    
- **Stability:** Coefficient of variation across repetitions.
    

### **3.5 Completion Threshold Analysis**

- Generate completions token-by-token.
    
- Detect index where brand first appears.
    
- Store preceding 40-token context window.
    
- Cluster thresholds by linguistic patterns (n-grams, POS tags).
    

### **3.6 Semantic Pivot Testing**

- Replace pivot terms at threshold positions with:
    
    - Synonyms
        
    - Category qualifiers
        
    - Value props (e.g., “patented”, “clinically-tested”)
        
- Measure Δ mention probability and Δ avg rank.
    
- Record statistically significant pivots (p<0.05).
    

### **3.7 Association Network Mapping**

- From all prompts, extract all entities and canonicalize.
    
- Build a weighted co-occurrence graph:
    
    - Nodes = brands/concepts.
        
    - Edges = frequency × rank-weight strength.
        
- Provide time-slider visualization to track evolution.
    

### **3.8 Grounded vs Ungrounded Gap Analysis**

- Compare representation in grounded vs ungrounded mode.
    
- Gap >10%:
    
    - Ungrounded weak → fix entity grounding (Wikidata, Wikipedia, schema).
        
    - Grounded weak → fix content/PR/SEO footprint.
        

### **3.9 Dashboard & Reporting**

- Display:
    
    - **Representation Score** (overall weighted score)
        
    - Naked Brand Token Recall %
        
    - Grounded gap report
        
    - Association network graph
        
    - Top concepts associated with brand
        
    - Competitive overlap maps
        
    - Pivot term impact chart
        
    - Trends over time
        
- Export:
    
    - CSV/JSON for raw scores and mention data.
        
    - PDF/HTML executive summaries.
        

---

## **4. Data Model (Postgres)**

**Tables:**

- `brands(id, name, domain, wikidata_qid, aliases[], category[])`
    
- `concepts(id, text, topic, intent, locale)`
    
- `models(id, vendor, name, version, mode)`
    
- `experiments(id, title, created_at)`
    
- `runs(id, experiment_id, model_id, locale, started_at, seed, temperature, grounded bool)`
    
- `prompts(id, run_id, type, template_id, input_text, variant_id)`
    
- `completions(id, prompt_id, raw_json, text, tokens, created_at)`
    
- `entities(id, label, canonical_id, type)`
    
- `mentions(id, completion_id, entity_id, start_idx, rank_pos, sentiment, confidence)`
    
- `metrics(id, run_id, brand_id, concept_id, mention_rate, avg_rank, weighted_score, ci_low, ci_high)`
    
- `thresholds(id, prompt_id, token_idx_first_mention, preceding_window, pattern_hash)`
    
- `pivots(id, threshold_id, term, variant, delta_prob, significance)`
    

---

## **5. Technical Stack**

- **Backend:** Python (FastAPI)
    
- **DB:** Postgres + Timescale (trends) + pgvector (optional)
    
- **NER:** spaCy `en_core_web_trf` + brand dictionaries
    
- **Frontend:** Next.js + ECharts/Cytoscape.js
    
- **Infra:** Docker Compose, optional Celery/Redis for async jobs
    

---

## **6. Implementation Phases**

**Phase 1:**

- DB schema + LLM adapters + prompt runner.
    

**Phase 2:**

- NER + entity normalization + scoring.
    

**Phase 3:**

- Threshold & pivot testing modules.
    

**Phase 4:**

- Association network builder.
    

**Phase 5:**

- Dashboard & API endpoints.
    

**Phase 6:**

- Grounded/ungrounded gap reporting + alerts.
    

---

## **7. Deliverables**

- API with endpoints for scores, pivots, networks.
    
- Dashboard with:
    
    - Representation Score
        
    - Trends
        
    - Networks
        
    - Pivot reports
        
    - Grounded gap
        
- Data exports.
    
- Operator runbook.
    
- Playbook of recommended influence actions.
    

---

## **8. Influence Action Playbook**

- **Ungrounded fixes:** Wikipedia/Wikidata/schema updates, consistent naming.
    
- **Grounded fixes:** PR, category-specific articles, backlinks from authority sources.
    
- **Training data seeding:** Publish factual, association-rich datasets to Hugging Face/Kaggle.
    
- **RAG visibility:** Ensure brand content is retrievable by Perplexity, Bing, etc.
    

---

## **9. Ethics & Guardrails**

- Transparency about measurement and influence goals.
    
- Only factually accurate brand–concept associations.
    
- Avoid manipulative or adversarial prompts.
    

---

## **10. Success Criteria**

- Accurate, reproducible brand visibility measurement.
    
- Executives can understand results via a single score + narrative.
    
- Action recommendations lead to measurable visibility gains in quarterly reports.
    

---

I can now also prepare a **prompt-pack definition** that the LLM could use to auto-generate all B→E and E→B queries for a given brand and concept list.

Do you want me to prepare that prompt pack spec next?