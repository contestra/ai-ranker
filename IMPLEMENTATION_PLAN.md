# AI Rank & Influence Tracker - Implementation Plan

## Based on Dejan.ai Research & airank.dejan.ai Reference Implementation

This implementation plan incorporates advanced methodologies from:
- [Strategic Brand Positioning in LLMs](https://dejan.ai/blog/strategic-brand-positioning-in-llms-a-methodological-framework-for-prompt-engineering-and-model-behavior-analysis/)
- [Beyond Rank Tracking: Association Networks](https://dejan.ai/blog/beyond-rank-tracking-analyzing-brand-perceptions-through-language-model-association-networks/)
- [Vector Embedding Optimization](https://dejan.ai/blog/vector-embedding-optimization/)
- [Cosine Similarity vs Dot Product](https://dejan.ai/blog/cosine-similarity-or-dot-product/)

## 🎯 Priority 1: BEEB System (Brand-Entity Embedding Benchmark)

### Overview
Implement comprehensive bidirectional testing to measure brand strength in LLMs through two-way association analysis.

### Features to Implement

#### 1.1 Tracked Phrases System
```python
class TrackedPhrase(Base):
    __tablename__ = "tracked_phrases"
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    phrase = Column(String, nullable=False)  # e.g., "collagen activator"
    category = Column(String)  # e.g., "product", "benefit", "technology"
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
```

**UI Requirements:**
- Settings page with tracked phrases input (one per line)
- Examples shown: "collagen activator", "Swiss NAD booster", "best longevity supplements"
- Checkbox for "Use Canonical Entities" to group variations

#### 1.2 E→B Testing (Entity to Brand)
**"Can they find you?"** - Start from categories, find brands

```python
def generate_e2b_prompts(tracked_phrases: List[str]) -> List[str]:
    templates = [
        "List the top 10 {phrase} brands",
        "What are the best {phrase} companies?",
        "Recommend {phrase} products",
        "Who are the leading {phrase} providers?",
        "Name the most popular {phrase} solutions"
    ]
    return [t.format(phrase=p) for p in tracked_phrases for t in templates]
```

#### 1.3 B→E Testing (Brand to Entities)
**"What do they know about you?"** - Start from brand, find associations

```python
def generate_b2e_prompts(brand_name: str, aliases: List[str]) -> List[str]:
    templates = [
        "What is {brand} known for?",
        "List 10 things associated with {brand}",
        "What products does {brand} offer?",
        "Describe {brand}'s main features",
        "What makes {brand} unique?"
    ]
    prompts = []
    for name in [brand_name] + aliases:
        prompts.extend([t.format(brand=name) for t in templates])
    return prompts
```

### Dashboard Views (from airank.dejan.ai screenshots)

#### Top 20 Entities View
Shows entities AI associates with your brand:
- Table columns: Entity, Frequency, Avg Position, Weighted Score
- Bar chart visualization of weighted scores
- Color-coded by association strength

#### Top 20 Brands View
Shows brands that appear for your tracked phrases:
- Competitor analysis with rankings
- Your brand highlighted in results
- Weighted score calculation

## 🎯 Priority 2: Weekly Trend Tracking

### Implementation
Based on the Google/OpenAI tab screenshots showing time-series data:

```python
class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    tracked_phrase_id = Column(Integer, ForeignKey("tracked_phrases.id"))
    week_starting = Column(Date, nullable=False)
    
    # For E→B (tracked phrases)
    rank_position = Column(Integer)  # Position when brand appears
    frequency = Column(Integer)  # Times appeared this week
    
    # For B→E (brand associations)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    entity_frequency = Column(Integer)
    entity_rank = Column(Float)
```

### Visualization Requirements
From screenshots, implement line charts showing:
- X-axis: Week Starting (Jul 13, Jul 16, Jul 19, etc.)
- Y-axis: Rank Position (1-10)
- Multiple colored lines for different brands/entities
- Frequency shown in parentheses in legend
- Toggle for "Weekly View" checkbox

## 🎯 Priority 3: Association Network Visualization

### Cytoscape.js Integration

```javascript
// Frontend component for network visualization
const AssociationNetwork = ({ brandId }) => {
  const cytoscapeConfig = {
    elements: {
      nodes: [
        { data: { id: 'brand', label: 'AVEA', type: 'brand', weight: 100 } },
        { data: { id: 'comp1', label: 'Garden of Life', type: 'competitor', weight: 80 } },
        { data: { id: 'cat1', label: 'Collagen', type: 'category', weight: 60 } },
      ],
      edges: [
        { data: { source: 'brand', target: 'cat1', weight: 0.85 } },
        { data: { source: 'comp1', target: 'cat1', weight: 0.75 } },
      ]
    },
    style: [
      {
        selector: 'node[type="brand"]',
        style: { 'background-color': '#0066cc', 'label': 'data(label)' }
      },
      {
        selector: 'node[type="competitor"]',
        style: { 'background-color': '#cc0000', 'label': 'data(label)' }
      },
      {
        selector: 'node[type="category"]',
        style: { 'background-color': '#00cc66', 'label': 'data(label)' }
      }
    ],
    layout: { name: 'cose-bilkent' }  // Force-directed layout
  };
};
```

### Backend API Endpoint
```python
@router.get("/api/networks/associations/{brand_id}")
def get_association_network(
    brand_id: int,
    depth: int = 2,
    min_weight: float = 0.3,
    db: Session = Depends(get_db)
):
    # Build co-occurrence graph from mentions
    nodes = []
    edges = []
    
    # Get all entities mentioned with the brand
    co_mentions = db.query(
        Entity.id, Entity.label, func.count().label('frequency')
    ).join(Mention).join(Completion).join(Prompt).join(Run).filter(
        Run.brand_id == brand_id
    ).group_by(Entity.id, Entity.label).all()
    
    for entity in co_mentions:
        nodes.append({
            'id': f'entity_{entity.id}',
            'label': entity.label,
            'type': determine_entity_type(entity.label),
            'weight': entity.frequency
        })
        
        # Calculate edge weight using cosine similarity
        if entity.frequency > min_threshold:
            edges.append({
                'source': f'brand_{brand_id}',
                'target': f'entity_{entity.id}',
                'weight': calculate_similarity(brand_id, entity.id)
            })
    
    return {'nodes': nodes, 'edges': edges}
```

## 🎯 Priority 4: Threshold & Pivot Analysis

### Threshold Discovery System

```python
class ThresholdAnalyzer:
    def find_trigger_combinations(self, base_prompt: str, brand_name: str):
        """
        Incrementally add modifiers to find what triggers brand mention
        """
        modifiers = [
            'Swiss', 'vegan', 'collagen', 'longevity', 'NAD', 
            'supplements', 'anti-aging', 'cellular', 'health'
        ]
        
        results = []
        for r in range(1, len(modifiers) + 1):
            for combo in itertools.combinations(modifiers, r):
                test_prompt = f"{base_prompt} {' '.join(combo)}"
                response = self.test_prompt(test_prompt)
                
                if brand_name.lower() in response.lower():
                    results.append({
                        'prompt': test_prompt,
                        'modifiers': combo,
                        'triggered': True,
                        'position': response.lower().index(brand_name.lower())
                    })
        
        return results
```

### Pivot Word Discovery

```python
class PivotAnalyzer:
    def test_synonyms(self, working_prompt: str, brand_name: str):
        """
        Replace each word with synonyms to find critical triggers
        """
        synonyms = {
            'Swiss': ['European', 'Alpine', 'Switzerland-based'],
            'longevity': ['anti-aging', 'life extension', 'healthspan'],
            'supplements': ['nutraceuticals', 'vitamins', 'nutrition'],
            'best': ['top', 'leading', 'premium', 'highest-quality']
        }
        
        words = working_prompt.split()
        pivot_impact = []
        
        for i, word in enumerate(words):
            if word.lower() in synonyms:
                for synonym in synonyms[word.lower()]:
                    test_prompt = ' '.join(words[:i] + [synonym] + words[i+1:])
                    response = self.test_prompt(test_prompt)
                    
                    maintains_brand = brand_name.lower() in response.lower()
                    pivot_impact.append({
                        'original': word,
                        'replacement': synonym,
                        'maintains_brand': maintains_brand,
                        'impact': 'critical' if not maintains_brand else 'neutral'
                    })
        
        return pivot_impact
```

## 🎯 Priority 5: Enhanced UI Features

### 5.1 Multi-Tab Interface (from screenshots)
```typescript
// Frontend tabs component
const BrandAnalysisTabs = () => {
  const tabs = [
    { id: 'ai-visibility', label: 'AI Visibility', icon: '👁️' },
    { id: 'openai', label: 'Open AI', icon: '🤖' },
    { id: 'google', label: 'Google', icon: '🔍' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];
  
  return (
    <TabGroup>
      {tabs.map(tab => (
        <Tab key={tab.id}>
          {tab.icon} {tab.label}
        </Tab>
      ))}
    </TabGroup>
  );
};
```

### 5.2 Settings Page Features
Based on the settings screenshot:
- Project Language selector
- Project Location (Global, USA, UK, etc.)
- Tracked Domains management
- Bulk domain import
- Tracked Phrases management
- Canonical entities toggle

### 5.3 Top Associations Bar Charts
Implement horizontal bar charts showing:
- Entity associations (left side)
- Brand associations (right side)
- Weighted scores with gradient colors
- Values from 0 to 0.5 scale

## 🎯 Priority 6: Advanced Metrics

### 6.1 Weighted Score Calculation
```python
def calculate_weighted_score(
    frequency: int,
    avg_position: float,
    total_mentions: int,
    max_position: int = 10
) -> float:
    """
    Calculate weighted score as shown in airank.dejan.ai
    """
    # Normalize frequency
    freq_score = frequency / total_mentions if total_mentions > 0 else 0
    
    # Position weight (inverse - better position = higher weight)
    pos_weight = max(0, 1 - (avg_position - 1) / max_position)
    
    # Combined weighted score
    return freq_score * pos_weight * 100  # Scale to 0-100
```

### 6.2 Canonical Entity Resolution
```python
class CanonicalEntityResolver:
    def __init__(self):
        self.canonical_mappings = {
            'avea': ['AVEA', 'Avea Life', 'Avea AG', 'avea-life'],
            'garden_of_life': ['Garden of Life', 'GoL', 'Garden Of Life'],
            'vital_proteins': ['Vital Proteins', 'VitalProteins', 'Vital']
        }
    
    def resolve(self, entity_text: str) -> str:
        """
        Map entity variations to canonical form
        """
        normalized = entity_text.lower().strip()
        
        for canonical, variations in self.canonical_mappings.items():
            if any(v.lower() == normalized for v in variations):
                return canonical
        
        return entity_text
```

## 📊 Database Schema Updates

### New Tables Required

```sql
-- Tracked phrases for E→B testing
CREATE TABLE tracked_phrases (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brands(id),
    phrase VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Weekly metrics for trend tracking
CREATE TABLE weekly_metrics (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brands(id),
    tracked_phrase_id INTEGER REFERENCES tracked_phrases(id),
    entity_id INTEGER REFERENCES entities(id),
    week_starting DATE NOT NULL,
    rank_position INTEGER,
    frequency INTEGER,
    weighted_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Threshold analysis results
CREATE TABLE threshold_results (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brands(id),
    base_prompt TEXT,
    modifiers TEXT[],
    triggers_mention BOOLEAN,
    token_position INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pivot word analysis
CREATE TABLE pivot_analysis (
    id SERIAL PRIMARY KEY,
    threshold_id INTEGER REFERENCES threshold_results(id),
    original_word VARCHAR(100),
    replacement_word VARCHAR(100),
    maintains_mention BOOLEAN,
    impact_level VARCHAR(20), -- 'critical', 'moderate', 'neutral'
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🚀 Implementation Timeline

### Week 1-2: BEEB System Foundation
- [ ] Implement tracked phrases management
- [ ] Create E→B prompt generation
- [ ] Build B→E prompt system
- [ ] Add canonical entity resolution

### Week 3-4: Visualization & Trends
- [ ] Integrate Cytoscape.js for network graphs
- [ ] Implement weekly trend tracking
- [ ] Create line chart components
- [ ] Add bar chart visualizations

### Week 5-6: Advanced Analysis
- [ ] Build threshold discovery system
- [ ] Implement pivot word analysis
- [ ] Create optimization matrices
- [ ] Add power word rankings

### Week 7-8: UI Polish & Testing
- [ ] Implement multi-tab interface
- [ ] Complete settings page
- [ ] Add bulk import features
- [ ] Comprehensive testing

## 📈 Success Metrics

### Technical KPIs
- Response time < 500ms for network visualization
- Support for 100+ tracked phrases per brand
- Weekly trend data retention for 52 weeks
- Threshold analysis completion < 5 minutes

### Business KPIs
- Identify 10+ power words per brand
- Track 20+ competitor brands
- 95% accuracy in canonical entity resolution
- Discover 5+ critical pivot words per category

## 🔧 Technical Requirements

### Frontend Dependencies
```json
{
  "cytoscape": "^3.28.0",
  "cytoscape-cose-bilkent": "^4.1.0",
  "recharts": "^2.13.3",
  "date-fns": "^3.0.0",
  "@tanstack/react-table": "^8.11.0"
}
```

### Backend Dependencies
```python
# Add to requirements.txt
networkx==3.2.1  # For graph analysis
scikit-learn==1.4.0  # For clustering
nltk==3.8.1  # For synonym generation
wordnet==0.1.0  # For semantic analysis
```

## 🎯 Next Steps

1. **Review with stakeholders** to prioritize features
2. **Set up development branches** for each major feature
3. **Create detailed API specifications** for new endpoints
4. **Design mockups** based on airank.dejan.ai UI
5. **Establish testing framework** for new components

## 📸 Key Insights from airank.dejan.ai Screenshots

### Critical Features Observed

1. **Weekly Trend Tracking is Essential**
   - 8-week rolling windows for all metrics
   - Frequency shown in parentheses (e.g., "Garden of Life (freq: 4)")
   - Dramatic rank changes visible (Elysium Health: rank 9→1)

2. **Dual Table Layout for Comparisons**
   - Top 20 Entities (B→E): What AI associates with your brand
   - Top 20 Brands (E→B): Which brands appear for your phrases
   - Both include: Frequency, Avg Position, Weighted Score

3. **Brand Confusion Detection**
   - AVEA associated with telecommunications instead of health
   - Shows need for entity disambiguation and grounding

4. **Competitive Landscape Visualization**
   - Bar charts with gradient coloring (0-0.5 scale)
   - Clear market leader identification
   - Gap analysis opportunities

5. **Tracked Phrases Management**
   - Critical phrases: "collagen activator", "Swiss NAD booster"
   - Bulk import functionality
   - One phrase per line interface

### Implementation Must-Haves from Screenshots

- **Multi-tab navigation**: AI Visibility | OpenAI | Google | Settings
- **Weekly View toggle**: Checkbox for time-series display
- **Variance tracking**: Shows result stability (e.g., "20 var.")
- **Domain tracking**: Monitor brand domains (www.avea-life.com)
- **Canonical entities checkbox**: Group brand variations

## 📚 References

- [airank.dejan.ai](https://airank.dejan.ai) - Reference implementation
- [Screenshot Analysis](./SCREENSHOT_ANALYSIS.md) - Detailed UI/UX breakdown
- [Dejan.ai Blog](https://dejan.ai/blog/) - Methodology documentation
- [LangChain Docs](https://python.langchain.com/) - LLM orchestration
- [Cytoscape.js](https://js.cytoscape.org/) - Network visualization

---

*This implementation plan incorporates best practices from Dejan.ai's research on brand positioning in LLMs and provides a roadmap for building a comprehensive AI rank tracking system.*