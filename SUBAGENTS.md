# AI Ranker Subagents Architecture

## Overview
This document defines specialized Claude Code subagents for the AI Ranker suite. Each major tool in the platform should have a dedicated agent to ensure focused expertise, parallel development, and consistent implementation patterns.

## Design Principle
**For each major tool added to the suite, consider creating a dedicated subagent** that owns the full stack (backend API, frontend components, tests, and documentation) for that tool.

## Proposed Subagents

### Core Tool Agents (Existing Tools)

#### 1. AI Visibility Agent
- **Owns**: Main dashboard, aggregate scoring across all AI models
- **Responsibilities**: 
  - Aggregate brand strength scores
  - Generate executive summaries
  - Coordinate data from other tools
  - Handle brand profile management

#### 2. Entity Strength Agent
- **Owns**: Brand recognition analysis system
- **Responsibilities**:
  - Classification logic (KNOWN_STRONG/KNOWN_WEAK/UNKNOWN)
  - Entity disambiguation detection
  - Confidence scoring algorithms
  - Warning generation for ambiguous entities
  - Windows encoding fixes for international brands

#### 3. Concordance Agent
- **Owns**: Prompted-list vs embedding comparison tool
- **Responsibilities**:
  - Run parallel ranking methodologies
  - Calculate correlation metrics (Spearman, Kendall Tau)
  - Identify method disagreements
  - Generate insights on ranking divergence
  - Top-K overlap analysis

#### 4. LLM Crawlability Agent
- **Owns**: AI model comprehension analysis
- **Responsibilities**:
  - Measure how well AI models can understand site content
  - Content structure analysis for AI parsing
  - Information architecture assessment
  - AI-readability scoring
  - Recommendations for AI visibility improvements

#### 5. Crawler Monitor Agent
- **Owns**: Crawl status tracking over time
- **Responsibilities**:
  - Schedule periodic crawl checks
  - Track indexing status changes
  - Historical crawlability trends
  - Alert on crawl errors
  - Multi-site portfolio monitoring

#### 6. Weekly Trends Agent
- **Owns**: Historical tracking and trend analysis
- **Responsibilities**:
  - Time-series data management
  - ROI reporting for improvements
  - Trend visualization components
  - Period-over-period comparisons
  - Export functionality for reports

#### 7. Comparison Agent
- **Owns**: Cross-model comparison tool
- **Responsibilities**:
  - Parallel queries to GPT-5, Gemini, Claude
  - Model-specific strength analysis
  - Identify optimization priorities
  - Competitive benchmarking across models
  - Model blind spot detection

#### 8. Bot Analytics Agent
- **Owns**: Platform usage and analytics
- **Responsibilities**:
  - API usage tracking
  - User interaction metrics
  - Cost analysis per tenant
  - Performance monitoring
  - Usage-based billing support

### New Tool Agents (Upcoming Features)

#### 9. Synthetic Prompt Agent
- **Owns**: Automated prompt testing system
- **Responsibilities**:
  - Generate diverse test prompts
  - Schedule management (cron jobs)
  - Parallel model orchestration
  - Result parsing and anomaly detection
  - Alert system for recognition changes
  - A/B testing prompt variations
  - Cost optimization through batching

#### 10. Schema Validator Agent
- **Owns**: Website schema checking tool
- **Responsibilities**:
  - Full-site schema crawling
  - Schema.org validation and scoring (0-100)
  - Type-specific validation rules
  - Competitor schema benchmarking
  - Fix recommendations with JSON-LD snippets
  - Integration with Entity Strength scoring

### Infrastructure Agents

#### 11. Dashboard UX Agent
- **Owns**: Frontend performance and user experience
- **Responsibilities**:
  - React Query caching implementation
  - Virtual scrolling for long lists
  - Debouncing and throttling
  - Loading states for long operations (50-90s waits)
  - Error handling and retry mechanisms
  - Responsive design patterns
  - Component library maintenance
  - Form optimization (React Hook Form)

#### 12. FastAPI Backend Agent
- **Owns**: API architecture, middleware, authentication
- **Responsibilities**:
  - Route optimization and organization
  - Request/response validation (Pydantic)
  - CORS and security middleware
  - Rate limiting implementation
  - API versioning strategy
  - OpenAPI documentation
  - Background task management
  - Error handling patterns

#### 13. Fly.io Deployment Agent
- **Owns**: Deployment pipeline, scaling, monitoring
- **Responsibilities**:
  - fly.toml configuration
  - Multi-region deployment
  - Auto-scaling rules
  - Health checks and restarts
  - Secrets management (API keys, tokens)
  - SSL/TLS certificates
  - Deployment rollbacks
  - Cost optimization
  - Production debugging

#### 14. Postgres Database Agent
- **Owns**: Database schema, migrations, performance
- **Responsibilities**:
  - Schema design and migrations (Alembic)
  - Query optimization
  - Index management
  - Connection pooling
  - Backup strategies
  - Multi-tenant data isolation
  - Time-series data optimization
  - Database monitoring
  - Data retention policies

## Implementation Guidelines

### When to Create a New Agent
Create a dedicated agent when adding a tool that has:
- Complex business logic requiring domain expertise
- Multiple API endpoints and database operations
- Significant frontend components
- Need for autonomous/scheduled operations
- Integration points with other tools

### Agent Responsibilities
Each agent should:
1. Own all code for their tool (backend + frontend)
2. Maintain consistent patterns within their domain
3. Handle tool-specific error cases and edge cases
4. Write comprehensive tests for their tool
5. Document their tool's architecture and usage
6. Optimize performance for their specific use cases

### Agent Communication
Agents don't directly communicate but share data through:
- Common database schemas
- Standardized API contracts
- Event system for cross-tool updates
- Shared type definitions

## Priority Order for Implementation

### Phase 1 (Critical Path)
1. **Synthetic Prompt Agent** - Highest ROI, runs autonomously
2. **Entity Strength Agent** - Core differentiator with disambiguation
3. **Dashboard UX Agent** - Critical for user experience

### Phase 2 (Enhancement)
4. **Schema Validator Agent** - Improves AI visibility
5. **Concordance Agent** - Complex correlation logic
6. **LLM Crawlability Agent** - Actionable insights

### Phase 3 (Scale)
7. **Weekly Trends Agent** - Enterprise reporting needs
8. **Comparison Agent** - Multi-model optimization
9. **Crawler Monitor Agent** - Long-term tracking
10. **AI Visibility Agent** - Orchestration layer
11. **Bot Analytics Agent** - Usage optimization

## Benefits of This Architecture

### Development Speed
- Parallel work on multiple tools without conflicts
- Reduced context switching
- Faster iteration within focused domains
- Autonomous testing and monitoring

### Code Quality
- Deep domain expertise per tool
- Consistent patterns within each tool
- Comprehensive tool-specific testing
- Better error handling for edge cases

### Maintainability
- Clear ownership boundaries
- Isolated tool upgrades
- Easier onboarding per tool
- Reduced coupling between tools

## Agent Usage Triggers

### Automatic Agent Selection
When these keywords or scenarios appear in requests, use the corresponding agent:

#### 1. AI Visibility Agent
**Triggers**: "dashboard", "overall score", "executive summary", "brand profile", "aggregate metrics"
**Example**: "Show me the dashboard for Nike" → Launch AI Visibility Agent

#### 2. Entity Strength Agent  
**Triggers**: "recognition", "disambiguation", "KNOWN_STRONG", "entity confusion", "brand strength", "AVEA"
**Example**: "Why is AVEA showing as KNOWN_WEAK?" → Launch Entity Strength Agent

#### 3. Concordance Agent
**Triggers**: "concordance", "ranking agreement", "prompted vs embedding", "correlation", "method comparison"
**Example**: "Check if the two ranking methods agree" → Launch Concordance Agent

#### 4. LLM Crawlability Agent
**Triggers**: "crawlability", "AI understanding", "content structure", "AI readability"
**Example**: "Can AI models understand my site?" → Launch LLM Crawlability Agent

#### 5. Crawler Monitor Agent
**Triggers**: "crawl status", "indexing", "crawl history", "monitoring"
**Example**: "Track crawl status over time" → Launch Crawler Monitor Agent

#### 6. Weekly Trends Agent
**Triggers**: "trends", "historical", "over time", "ROI", "progress tracking"
**Example**: "Show brand visibility trends this month" → Launch Weekly Trends Agent

#### 7. Comparison Agent
**Triggers**: "compare models", "GPT vs Gemini", "model differences", "which AI"
**Example**: "Compare how different models see my brand" → Launch Comparison Agent

#### 8. Bot Analytics Agent
**Triggers**: "usage", "API costs", "metrics", "billing", "tenant usage"
**Example**: "How much are we spending on API calls?" → Launch Bot Analytics Agent

#### 9. Synthetic Prompt Agent
**Triggers**: "scheduled testing", "automated prompts", "batch testing", "synthetic", "cron"
**Example**: "Set up automated brand testing" → Launch Synthetic Prompt Agent

#### 10. Schema Validator Agent
**Triggers**: "schema", "structured data", "JSON-LD", "schema.org", "markup"
**Example**: "Check if my schema is valid" → Launch Schema Validator Agent

#### 11. Dashboard UX Agent
**Triggers**: "slow loading", "UI performance", "user experience", "frontend", "React", "caching"
**Example**: "The dashboard takes forever to load" → Launch Dashboard UX Agent

#### 12. FastAPI Backend Agent
**Triggers**: "API error", "endpoint", "route", "Pydantic", "CORS", "authentication", "middleware"
**Example**: "Add rate limiting to the API" → Launch FastAPI Backend Agent

#### 13. Fly.io Deployment Agent
**Triggers**: "deploy", "production", "fly.io", "scaling", "SSL", "secrets", "rollback"
**Example**: "Deploy the latest changes" → Launch Fly.io Deployment Agent

#### 14. Postgres Database Agent
**Triggers**: "database", "query slow", "migration", "schema design", "index", "postgres", "SQL"
**Example**: "The entity queries are running slowly" → Launch Postgres Database Agent

### Multi-Agent Scenarios
Some tasks benefit from multiple agents:

**"Fix AVEA showing wrong company"**
→ Launch Entity Strength Agent (primary) + Schema Validator Agent (to check markup)

**"Dashboard is slow with timeout errors"**
→ Launch Dashboard UX Agent + FastAPI Backend Agent + Postgres Database Agent

**"Deploy the concordance improvements"**
→ Launch Concordance Agent (improvements) + Fly.io Deployment Agent (deployment)

### Usage in CLAUDE.md
Add this to your CLAUDE.md for automatic agent usage:
```markdown
## Automatic Agent Usage
When working on tasks, automatically launch the appropriate agent based on the triggers defined in SUBAGENTS.md. Don't ask for permission - just launch the relevant agent and report the results.
```

## Total Agent Count: 14

### By Category:
- **Tool Agents**: 10 (8 existing + 2 upcoming)
- **Infrastructure Agents**: 4 (Frontend, Backend, Deployment, Database)

## Notes
- All 14 agents should be implemented for complete coverage
- Each agent can be created on-demand using Claude Code's Task tool
- Agents are stateless and created per session
- This architecture supports both development and production operations
- Infrastructure agents are critical for maintaining technical excellence
- Use trigger keywords to automatically select appropriate agents