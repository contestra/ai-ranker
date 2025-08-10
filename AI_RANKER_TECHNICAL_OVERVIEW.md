# AI Rank & Influence Tracker - Technical Documentation

## Executive Summary
AI Rank & Influence Tracker is an analytical tool that measures and tracks how Large Language Models (LLMs) perceive and associate brands with various concepts, entities, and competitors. This system helps businesses understand their "AI visibility" - essentially their SEO for AI-generated responses.

## System Architecture

### Core Concept: BEEB (Brand Entity Embedding Benchmark)
The system uses a novel approach to measure brand associations:
1. Query LLMs about a brand
2. Extract entities from responses using NLP
3. Calculate embedding similarities between brand and entities
4. Rank associations by relevance scores

## Technical Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Cache**: Redis (production)
- **LLM Integration**: LangChain
- **NLP**: spaCy for entity extraction
- **Deployment**: Fly.io

### Frontend
- **Framework**: Next.js 14 (React)
- **Styling**: Tailwind CSS
- **Charts**: Chart.js, Recharts
- **State**: React hooks + localStorage
- **Deployment**: Fly.io

## Core Functionality

### 1. Entity Extraction & Association Analysis

```python
# Simplified flow
async def analyze_brand(brand_name: str, vendor: str):
    # Step 1: Query LLM
    prompt = f"List the top 10 things you associate with {brand_name}"
    response = await llm.generate(prompt)
    
    # Step 2: Extract entities using NLP
    entities = extract_entities_from_text(response)
    
    # Step 3: Calculate embeddings
    brand_embedding = await get_embedding(brand_name)
    entity_embeddings = [await get_embedding(e) for e in entities]
    
    # Step 4: Calculate similarities
    similarities = [cosine_similarity(brand_embedding, e) for e in entity_embeddings]
    
    return ranked_associations
```

### 2. Tracked Phrase Analysis
Users can define key business phrases and discover which brands AI models associate with them:
- Input: "diagnostic infrastructure platform"
- Output: Ranked list of brands LLMs associate with this phrase

### 3. Multi-Vendor Comparison
Compare results across different LLM providers:
- **OpenAI**: GPT-4/GPT-5 with text-embedding-3-small
- **Google**: Gemini 1.5 Flash/Pro
- **Anthropic**: Claude (prepared, embeddings not available)

## Key Algorithms

### Entity Extraction Pipeline
```python
def extract_entities_from_text(text: str) -> Set[str]:
    entities = set()
    
    # SpaCy NER for standard entities
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT", "PERSON", "GPE", "LOC"]:
            entities.add(ent.text)
    
    # Noun phrase extraction
    for chunk in doc.noun_chunks:
        if len(chunk.text.split()) > 1:
            entities.add(chunk.text)
    
    # Pattern matching for domain-specific terms
    patterns = [
        r'\b\w+\s+(?:service|solution|platform|system)s?\b',
        r'\b(?:mobile|cloud|data|internet)\s+\w+',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.update(matches)
    
    return normalize_entities(entities)
```

### Similarity Scoring
```python
def calculate_similarity(brand_vec: np.array, entity_vec: np.array) -> dict:
    # Normalize vectors
    brand_norm = brand_vec / np.linalg.norm(brand_vec)
    entity_norm = entity_vec / np.linalg.norm(entity_vec)
    
    # Cosine similarity
    similarity = float(np.dot(brand_norm, entity_norm))
    
    # Convert to position score (1-10 scale)
    avg_position = 1 + (1 - similarity) * 9
    
    return {
        "similarity": similarity,
        "avg_position": avg_position,
        "weighted_score": similarity  # Can be adjusted with frequency
    }
```

## API Endpoints

### Backend API Structure
```
/api/entity-beeb (POST)
  - Inputs: brand_name, tracked_phrases[], vendor
  - Returns: extracted_entities[], entity_associations[], brand_associations[]

/api/brands/{brand_id}/tracked-phrases (GET/POST)
  - Manage tracked phrases for brand analysis

/api/dashboard/overview/{brand_id} (GET)
  - Aggregated analytics for brand visibility

/api/weekly-tracking/{brand}/{vendor} (GET)
  - Historical tracking data
```

## Data Models

### Core Entities
```python
class Brand:
    id: int
    name: str
    domain: str
    aliases: List[str]
    category: List[str]

class TrackedPhrase:
    id: int
    brand_id: int
    phrase: str
    is_active: bool

class EntityAssociation:
    entity: str
    similarity: float
    frequency: int
    avg_position: float
    weighted_score: float
```

## Frontend Components

### Key React Components
```
Settings.tsx
  - Brand configuration
  - Tracked phrase management
  - Analysis trigger

AIVisibility.tsx
  - Entity association display
  - Brand ranking visualization
  - Real-time results

ModelComparison.tsx
  - Vendor-specific results
  - Comparative analysis
```

## Performance Optimizations

1. **Caching Strategy**
   - Redis for API responses (15-minute TTL)
   - localStorage for frontend state
   - Embedding cache to avoid recomputation

2. **API Rate Limiting**
   - Google: 50 requests/day (free tier)
   - OpenAI: Managed via API key limits
   - Retry logic with exponential backoff

3. **Query Optimization**
   - Limited to 2 tracked phrases per analysis
   - Top 15 entities for embedding calculation
   - Batch processing where possible

## Deployment Configuration

### Docker Compose (Development)
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_ranker
  
  redis:
    image: redis:7-alpine
  
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://...
      REDIS_URL: redis://...
  
  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api
```

### Production (Fly.io)
```toml
# fly.toml
app = "ai-ranker-backend"

[env]
  PORT = "8000"

[[services]]
  http_checks = []
  internal_port = 8000
  protocol = "tcp"
```

## Use Cases & Applications

### 1. Brand Monitoring
Track how AI models understand and represent your brand compared to competitors.

### 2. AI SEO Optimization
Optimize content and messaging for better representation in AI responses.

### 3. Competitive Intelligence
Discover which competitors appear for your key business phrases.

### 4. Market Positioning
Understand gaps between AI perception and actual brand positioning.

## Example Analysis Results

### Brand: "Hurdle" (B2B Diagnostic Platform)
```json
{
  "extracted_entities": [
    "diagnostic infrastructure",
    "biomarker discovery platform",
    "healthcare providers",
    "clinical research"
  ],
  "entity_associations": [
    {"entity": "diagnostic infrastructure", "similarity": 0.612},
    {"entity": "healthcare technology", "similarity": 0.534},
    {"entity": "precision medicine", "similarity": 0.478}
  ],
  "brand_associations": [
    {"brand": "LabCorp", "phrase": "diagnostic infrastructure platform"},
    {"brand": "Quest Diagnostics", "phrase": "clinical diagnostics API"}
  ]
}
```

## Known Limitations & Mitigations

1. **API Rate Limits**
   - Issue: Google free tier limited to 50 requests/day
   - Solution: Disable tracked phrase processing for Google

2. **Response Time**
   - Issue: OpenAI queries take 10-30 seconds
   - Solution: Progress indicators, background processing

3. **Embedding Availability**
   - Issue: Anthropic doesn't provide embedding API
   - Solution: Focus on OpenAI and Google implementations

## Future Enhancements

1. **Historical Tracking**
   - Weekly snapshots of brand visibility
   - Trend analysis over time

2. **Advanced Analytics**
   - Sentiment analysis of associations
   - Competitor gap analysis
   - Category-specific benchmarks

3. **Enterprise Features**
   - Multi-user support
   - API access for integration
   - Custom LLM deployment options

## Contributing
This system demonstrates a novel approach to measuring AI visibility. Key areas for contribution:
- Additional LLM vendor adapters
- Enhanced entity extraction algorithms
- Industry-specific analysis templates
- Performance optimizations

## License
Proprietary - Contestra

## Contact
For questions about implementation or deployment, refer to the deployment guides in the repository.

---

*This document provides a technical overview of the AI Rank & Influence Tracker system. For setup instructions, see README.md. For deployment details, see DEPLOYMENT.md.*