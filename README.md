# AI Ranker - BEEB Implementation (Dejan.ai Clone)

A comprehensive implementation of Dejan.ai's Brand-Entity Embedding Benchmark (BEEB) methodology for tracking brand visibility and entity associations across AI models.

## Overview

AI Ranker analyzes how AI models perceive and rank brands using pure embedding space analysis and chat-based recommendations. It implements the complete BEEB methodology with time-series tracking and multi-vendor support.

## Key Features

### 1. Pure BEEB Implementation
- **B→E Analysis**: Discovers which entities AI models associate with your brand
- **E→B Analysis**: Tracks which brands AI models recommend for your tracked phrases
- **Vendor-Specific Embeddings**: Separate analysis for OpenAI and Google embedding spaces
- **Dot Product Similarity**: Google-aligned normalized vector calculations

### 2. Time-Series Tracking
- **Weekly Snapshots**: Historical ranking data with 1-10 inverted scale (1 is best)
- **Interactive Line Graphs**: Visualize ranking trends over time
- **Variance Analysis**: Track volatility and consistency
- **Frequency Metrics**: Count mentions across queries

### 3. Entity Confusion Detection
- **Brand Disambiguation**: Identifies semantic confusion (e.g., AVEA Life vs AVEA Telecom)
- **Confusion Tracking**: Measures how disambiguation changes across vendors
- **Weak Entity Detection**: Identifies brands with poor semantic associations

### 4. Multi-Vendor Support
- **OpenAI**: GPT models and text-embedding-3
- **Google**: Gemini models and text-embedding
- **Vendor Comparison**: Cross-vendor analysis capabilities
- **Anthropic**: Planned integration

## Architecture

### Backend (FastAPI + Python)
```
backend/
├── app/
│   ├── api/
│   │   ├── pure_beeb.py          # Pure embedding analysis
│   │   ├── weekly_tracking.py    # Time-series data management
│   │   ├── real_analysis.py      # Chat-based analysis
│   │   └── vendor_beeb.py        # Vendor-specific BEEB
│   ├── llm/
│   │   └── langchain_adapter.py  # LLM integration
│   └── main.py                   # FastAPI application
```

### Frontend (Next.js + React + TypeScript)
```
frontend/
├── src/
│   ├── components/
│   │   ├── AIVisibility.tsx           # Aggregated BEEB view
│   │   ├── ModelComparison.tsx        # Vendor-specific tabs
│   │   ├── RankingTimeSeriesChart.tsx # Time-series graphs
│   │   ├── Settings.tsx               # Configuration & triggers
│   │   └── ...
│   └── app/
│       └── page.tsx                   # Main application
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key
- Google Cloud API key (optional)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env:
# OPENAI_API_KEY=your_key
# GOOGLE_API_KEY=your_key (optional)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Access the application at `http://localhost:3002`

## Usage Guide

### 1. Initial Configuration
1. Enter your brand name (e.g., "AVEA Life")
2. Navigate to Settings tab
3. Add tracked phrases:
   - "best longevity supplements"
   - "Swiss NAD booster"
   - "anti-aging solutions"

### 2. Run Analysis

#### Vector Analysis (BEEB)
- Pure embedding space analysis
- Runs for all configured vendors
- Updates weekly tracking data
- Stores vendor-specific results

#### AI Analysis
- Chat-based brand recommendations
- Identifies brand mentions
- Tracks competitive landscape

### 3. View Results

#### AI Visibility Tab
- **Top 20 Entities**: Aggregated entity associations
- **Top 20 Brands**: Aggregated brand recommendations
- **Bar Charts**: Visual representation of association strength

#### OpenAI/Google Tabs
- **Your Brand Section**: Time-series graph of entity rankings
- **Your Phrases Section**: Time-series graphs for each tracked phrase
- **Weekly View Toggle**: Granular analysis options
- **Legend Details**: Frequency and variance indicators

## API Documentation

### Core Endpoints

#### Embedding Analysis
```
POST /api/vendor-beeb
  - Multi-vendor BEEB analysis
  - Returns vendor-specific entity/brand associations

POST /api/pure-beeb
  - Single vendor analysis
  - Optional vendor parameter

GET /api/weekly-tracking/{brand_name}/{vendor}
  - Retrieve historical tracking data
  - Returns time-series data points

POST /api/weekly-tracking/update
  - Update tracking with new rankings
  - Accumulates historical data
```

#### Chat Analysis
```
POST /api/real-analysis
  - Multi-vendor chat completions
  - Brand extraction and ranking

POST /api/simple-analysis
  - Basic brand mention detection
```

## BEEB Methodology

### Core Concepts

#### B→E (Brand to Entity)
Measures what concepts AI models associate with your brand in embedding space.
- Example: "AVEA Life" → ["longevity", "supplements", "AVEA", "telecommunications"]
- Reveals brand confusion and weak associations

#### E→B (Entity to Brand)
Tracks which brands AI recommends for specific search queries.
- Example: "best longevity supplements" → ["Life Extension", "Thorne", "AVEA Life"]
- Shows competitive positioning

### Ranking System
- **Scale**: 1-10 (inverted - 1 is best)
- **Frequency**: Number of mentions
- **Variance**: Ranking volatility
- **Weight**: Combined score

### Analysis Modes
- **Ungrounded**: Pure model knowledge from training data
- **Grounded** (planned): Enhanced with web search results

## Case Study: AVEA Brand Confusion

The system correctly identifies that "AVEA Life" (longevity supplements) is confused with "AVEA" (defunct Turkish telecom) in embedding spaces:

- OpenAI embeddings: 83.26% similarity with "AVEA" entity
- Telecom entities appearing in top associations
- Demonstrates weak brand entity definition

This confusion indicates need for:
1. Stronger brand content creation
2. Wikipedia/Wikidata updates
3. Consistent brand messaging

## Development Roadmap

### Completed ✅
- Pure BEEB with vendor-specific embeddings
- Weekly time-series tracking
- Interactive line graphs
- Variance and frequency metrics
- Entity confusion detection
- Multi-vendor support

### In Progress 🚧
- Canonical entity resolution
- Project management system
- Language/location settings

### Planned 📋
- Grounded mode with web search
- Anthropic Claude integration
- Export functionality
- Automated weekly analysis
- Competitive benchmarking
- Tracked domains
- Brand disambiguation tools

## Configuration

### Environment Variables
```env
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...

# Optional
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
```

### Settings Options
- **Canonical Entities**: Standardize entity names
- **Weekly Aggregation**: Time-based grouping
- **Model Selection**: Choose specific AI models
- **Language Settings**: Multi-language support (planned)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Based on Dejan.ai's BEEB methodology
- Implements brand visibility analysis for AI systems
- Uses LangChain for LLM orchestration
- Chart.js for data visualization

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact: support@contestra.com