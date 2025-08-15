# AI Ranker - Complete AI Visibility & Influence Platform

[![GitHub](https://img.shields.io/badge/GitHub-contestra%2Fai--ranker-blue)](https://github.com/contestra/ai-ranker)
[![Production](https://img.shields.io/badge/Production-ai--ranker.fly.dev-green)](https://ai-ranker.fly.dev)

A comprehensive suite for tracking and optimizing brand visibility across AI systems including ChatGPT, Perplexity, Claude, and other LLMs. Features bot traffic monitoring, crawlability analysis, and brand association tracking.

**Repository:** https://github.com/contestra/ai-ranker

## 🚀 Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend  
cd frontend
npm install
npm run dev
```

Access at `http://localhost:3001`

## 🛠️ Core Features

### 1. **AI Crawler Monitor** 
Real-time tracking of AI bot traffic on your website
- Detects ChatGPT, Perplexity, Claude, and other AI bots
- WordPress plugin for easy integration
- Spoof detection and verification
- Traffic analytics and reporting

### 2. **Brand Association Analysis**
Track how AI models perceive your brand
- Prompted-list methodology with rank aggregation
- Multi-model support (OpenAI, Google, Anthropic)
- Grounded vs ungrounded comparison
- Weekly tracking and trends

### 3. **LLM Crawlability Checker**
Ensure AI can access your content
- Robots.txt analysis for AI bots
- CDN/WAF detection
- JavaScript dependency testing
- Generates optimized configurations

### 4. **Entity Strength Dashboard**
Measure brand recognition strength

### 5. **Prompt Tracking System** (NEW)
Systematic testing of AI responses across countries
- Base Model testing for control baseline
- Multi-country comparison (US, UK, DE, CH, UAE, SG)
- Grounded vs ungrounded mode testing
- Template management and analytics
- Evidence pack support (coming soon)
- Classification: KNOWN_STRONG, KNOWN_WEAK, UNKNOWN
- Confidence scoring
- Competitive comparison
- Actionable recommendations

## 📊 Architecture

```
Frontend (Next.js 14 + TypeScript)
    ↓
Backend API (FastAPI + Python)
    ↓
PostgreSQL + Redis Cache
    ↓
LLM Providers (OpenAI, Google, Anthropic)
```

## 🔧 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- API Keys: OpenAI, Google Cloud (optional), Anthropic (optional)

### Environment Setup

```bash
# Backend .env
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key  # Optional
ANTHROPIC_API_KEY=your_key  # Optional
DATABASE_URL=postgresql://user:pass@localhost/airanker
UPSTASH_REDIS_URL=your_redis_url  # Optional
```

### Database Setup

```bash
cd backend
python create_tables.py
```

## 🎯 WordPress Plugin

Install the AI Crawler Monitor plugin to track bot traffic:

1. Download from `wordpress-plugin/ai-crawler-monitor/`
2. Upload to WordPress `/wp-content/plugins/`
3. Activate and configure (pre-set for Contestra cloud)

## 📈 API Endpoints

### Bot Analytics
```
POST /api/crawler/v2/ingest/generic  # Receive bot events
GET  /api/crawler/v2/monitor/stats/{domain}  # Get statistics
GET  /api/crawler/v2/monitor/events/{domain}  # Get events
WS   /api/crawler/v2/ws/monitor/{domain}  # Real-time updates
```

### Brand Analysis
```
POST /api/contestra/v2/analyze  # Run analysis
GET  /api/weekly-tracking/{brand}  # Get historical data
POST /api/llm-crawlability/check  # Check crawlability
```

## 🚀 Deployment

### Production (Fly.io)
```bash
# Deploy backend
cd backend
flyctl deploy

# Deploy frontend
cd frontend
flyctl deploy
```

### Local Development
```bash
# Run both services
npm run dev  # In frontend/
uvicorn app.main:app --reload  # In backend/
```

## 📊 Multi-Tenant Architecture

- Domain-based data isolation
- Brand → Domain → Events hierarchy
- Automatic domain validation
- WordPress plugin support

## 🔒 Security

- API keys in environment variables
- PostgreSQL with SSL
- No PII in prompts
- Rate limiting implemented

## 📝 Documentation

- [CLAUDE.md](CLAUDE.md) - **IMPORTANT: Latest updates and critical implementation details**
- [Grounding Implementation](GROUNDING_IMPLEMENTATION.md) - Proper API-level grounding vs prompt modification
- [Project Overview](PROJECT_OVERVIEW.md) - Detailed architecture and methodology
- [Multi-Tenant Architecture](MULTI_TENANT_ARCHITECTURE.md) - Domain isolation design
- [WordPress Plugin](wordpress-plugin/README.md) - Installation and configuration
- [System Integrity Rules](SYSTEM_INTEGRITY_RULES.md) - Critical components that must not be modified

## 🤝 Contributing

1. Fork the repository at https://github.com/contestra/ai-ranker
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new features
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Submit pull request

## 📄 License

Copyright Contestra - All rights reserved

## 🙏 Acknowledgments

Built with:
- FastAPI & LangChain
- Next.js & React
- PostgreSQL & Redis
- OpenAI, Google Gemini, Anthropic Claude

---

*For support: support@contestra.com*