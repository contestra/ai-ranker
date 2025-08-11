# Deploying AI Ranker to Fly.io

## Complete Product Overview

AI Ranker is a comprehensive AI visibility tracking platform that includes:

1. **Contestra V2 Analysis** - Prompted-list methodology for brand visibility
2. **Entity Extraction** - BEEB vector embeddings analysis
3. **Concordance Analysis** - Compare different ranking methods
4. **LLM Crawlability Checker** - Test if AI bots can access your site
5. **Weekly Tracking** - Historical data storage and trends
6. **Brand Entity Strength** - Entity association scoring
7. **AI Crawler Monitor** - Real-time bot traffic tracking (NEW)

## Prerequisites

1. **Fly.io Account** - Sign up at https://fly.io
2. **Fly CLI** - Install from https://fly.io/docs/hands-on/install-flyctl/
3. **PostgreSQL Database** - Fly Postgres or external (Supabase, Neon, etc.)
4. **API Keys Required**:
   - OpenAI API Key (required)
   - Google API Key (for Gemini grounded mode)
   - Anthropic API Key (optional, for Claude)
   - LangSmith API Key (optional, for tracing)

## Deployment Steps

### 1. Prepare Your Backend

```bash
cd ai-ranker/backend

# Ensure you have these files:
# - Dockerfile (already exists)
# - fly.toml (already exists)
# - requirements.txt (already exists)
# - .env (create from .env.example)
```

### 2. Create Fly App (First Time Only)

```bash
# Login to Fly
fly auth login

# Launch the app (use existing fly.toml)
fly launch --name ai-ranker-contestra --region iad --no-deploy

# Or if app already exists
fly apps create ai-ranker-contestra --region iad
```

### 3. Set Up PostgreSQL Database

Option A: **Use Fly Postgres** (Recommended for simplicity)
```bash
# Create Postgres cluster
fly postgres create --name ai-ranker-db --region iad

# Attach to your app (this sets DATABASE_URL automatically)
fly postgres attach ai-ranker-db --app ai-ranker-contestra
```

Option B: **Use External Database** (Supabase, Neon, etc.)
```bash
# Set DATABASE_URL manually
fly secrets set DATABASE_URL="postgresql://user:pass@host:5432/dbname" --app ai-ranker-contestra
```

### 4. Set Environment Variables

```bash
# Required API Keys
fly secrets set \
  OPENAI_API_KEY="sk-..." \
  GOOGLE_API_KEY="AIza..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  --app ai-ranker-contestra

# Optional: LangSmith Tracing
fly secrets set \
  LANGCHAIN_API_KEY="ls__..." \
  LANGCHAIN_TRACING_V2="true" \
  LANGCHAIN_PROJECT="ai-ranker" \
  --app ai-ranker-contestra

# Optional: Upstash Redis Cache
fly secrets set \
  UPSTASH_REDIS_REST_URL="https://..." \
  UPSTASH_REDIS_REST_TOKEN="..." \
  --app ai-ranker-contestra
```

### 5. Deploy to Fly

```bash
# Deploy the application
fly deploy --app ai-ranker-contestra

# Check deployment status
fly status --app ai-ranker-contestra

# View logs
fly logs --app ai-ranker-contestra
```

### 6. Verify Deployment

```bash
# Get your app URL
fly info --app ai-ranker-contestra

# Your app will be available at:
# https://ai-ranker-contestra.fly.dev

# Test the API
curl https://ai-ranker-contestra.fly.dev/
# Should return: {"message":"AI Rank & Influence Tracker API","version":"1.0.0"}

# Test crawler monitor endpoint
curl https://ai-ranker-contestra.fly.dev/api/crawler/monitor/stats
```

## WordPress Plugin Configuration

After deployment, configure WordPress plugins to use your Fly.io endpoint:

```
API Endpoint: https://ai-ranker-contestra.fly.dev/api/crawler/ingest/generic
```

## API Endpoints Available

Once deployed, all these endpoints are available:

### Core Analysis
- `/api/contestra-v2` - Prompted-list analysis
- `/api/entity-extraction-beeb` - Vector embeddings
- `/api/concordance` - Method comparison
- `/api/weekly-tracking` - Historical data

### Crawler Monitor
- `/api/crawler/ingest/generic` - Receive bot data from WordPress
- `/api/crawler/monitor/stats` - View statistics
- `/api/crawler/ws/monitor` - WebSocket for real-time updates

### LLM Crawlability
- `/api/llm-crawlability/check` - Test site accessibility
- `/api/llm-crawlability/advanced` - Advanced checks

### Brand Management
- `/api/brands` - Brand CRUD operations
- `/api/tracked-phrases` - Manage tracked phrases

## Scaling Considerations

### Current Configuration (fly.toml)
- **Memory**: 1GB (sufficient for most usage)
- **CPU**: 1 shared CPU
- **Auto-scaling**: Stops when idle, starts on request
- **Min machines**: 0 (to save costs)

### For Production Traffic
```toml
# Edit fly.toml for always-on production:
[http_service]
  min_machines_running = 1  # Keep at least 1 running
  auto_stop_machines = 'off'  # Never stop

[[vm]]
  memory = '2gb'  # More memory for heavy analysis
  cpus = 2  # More CPU for parallel processing
```

### Scale Up Command
```bash
# Scale to multiple regions
fly scale count 2 --region iad,lhr --app ai-ranker-contestra

# Increase resources
fly scale vm shared-cpu-2x --memory 2048 --app ai-ranker-contestra
```

## Database Migrations

If you need to run database migrations:

```bash
# SSH into your app
fly ssh console --app ai-ranker-contestra

# Run migrations
cd /app
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
```

## Monitoring & Debugging

```bash
# View real-time logs
fly logs --app ai-ranker-contestra

# SSH into container
fly ssh console --app ai-ranker-contestra

# Check app status
fly status --app ai-ranker-contestra

# View secrets (names only)
fly secrets list --app ai-ranker-contestra
```

## Frontend Deployment

The frontend should be deployed separately (Vercel, Netlify, or another Fly app):

1. Update frontend API URL:
```javascript
// In frontend code, update all API calls to:
const API_URL = 'https://ai-ranker-contestra.fly.dev'
```

2. Deploy frontend to your preferred platform

## Cost Estimation

With Fly.io free tier:
- **3 shared VMs** (enough for this app)
- **160GB outbound transfer**
- **Postgres**: 256MB RAM, 1GB storage

Estimated monthly cost: **$0-5** for light usage

## Troubleshooting

### Database Connection Issues
```bash
# Check DATABASE_URL
fly ssh console --app ai-ranker-contestra
echo $DATABASE_URL

# Test connection
fly postgres connect --app ai-ranker-db
```

### Memory Issues
```bash
# If app crashes with memory errors
fly scale memory 2048 --app ai-ranker-contestra
```

### API Key Issues
```bash
# Verify secrets are set
fly secrets list --app ai-ranker-contestra

# Re-set a secret
fly secrets set OPENAI_API_KEY="new-key" --app ai-ranker-contestra
```

## Security Notes

1. **API Keys**: Never commit `.env` files to git
2. **Database**: Use connection pooling for production
3. **CORS**: Configure allowed origins in production
4. **Rate Limiting**: Consider adding rate limits for public endpoints

## Support

For deployment issues:
- Fly.io Community: https://community.fly.io
- Fly.io Docs: https://fly.io/docs
- AI Ranker Issues: https://github.com/contestra/ai-ranker/issues