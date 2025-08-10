# Deployment Guide

This guide explains how to deploy the AI Rank & Influence Tracker to Fly.io with Upstash Redis and LangChain.

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io
2. **Upstash Account**: Sign up at https://upstash.com
3. **LangChain/LangSmith Account**: Sign up at https://smith.langchain.com
4. **API Keys**: OpenAI, Google, and/or Anthropic

## Setup Steps

### 1. Install Fly CLI

```bash
# macOS/Linux
curl -L https://fly.io/install.sh | sh

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### 2. Authenticate with Fly.io

```bash
flyctl auth login
```

### 3. Set up Upstash Redis

1. Go to https://console.upstash.com
2. Create a new Redis database
3. Copy the REST URL and REST Token from the dashboard

### 4. Configure LangSmith

1. Go to https://smith.langchain.com
2. Create a new project called "ai-ranker"
3. Copy your API key from Settings

### 5. Configure Environment Variables

Create `backend/.env` file:

```env
# Database (will be auto-created by Fly.io)
DATABASE_URL=will_be_set_by_fly

# Upstash Redis
UPSTASH_REDIS_REST_URL=your_upstash_rest_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_rest_token

# LangChain API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ai-ranker
```

### 6. Deploy to Fly.io

#### Option A: Automated Deployment

```bash
# Make the script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

#### Option B: Manual Deployment

**Deploy Backend:**

```bash
cd backend

# Create app
flyctl apps create ai-ranker

# Create Postgres database
flyctl postgres create --name ai-ranker-db --region iad
flyctl postgres attach ai-ranker-db --app ai-ranker

# Set secrets
flyctl secrets set \
  UPSTASH_REDIS_REST_URL="your_url" \
  UPSTASH_REDIS_REST_TOKEN="your_token" \
  OPENAI_API_KEY="your_key" \
  GOOGLE_API_KEY="your_key" \
  ANTHROPIC_API_KEY="your_key" \
  LANGCHAIN_API_KEY="your_key" \
  LANGCHAIN_TRACING_V2="true" \
  LANGCHAIN_PROJECT="ai-ranker" \
  --app ai-ranker

# Deploy
flyctl deploy --app ai-ranker
```

**Deploy Frontend:**

```bash
cd ../frontend

# Create app
flyctl apps create ai-ranker-frontend

# Set environment
flyctl secrets set \
  NEXT_PUBLIC_API_URL="https://ai-ranker.fly.dev/api" \
  --app ai-ranker-frontend

# Deploy
flyctl deploy --app ai-ranker-frontend
```

### 7. Initialize Data

After deployment, add initial brands:

```bash
curl -X POST https://ai-ranker.fly.dev/api/entities/brands \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Brand",
    "domain": "yourdomain.com",
    "aliases": ["Brand Alias"],
    "category": ["your-category"]
  }'
```

## Monitoring

### View Logs

```bash
# Backend logs
flyctl logs --app ai-ranker

# Frontend logs
flyctl logs --app ai-ranker-frontend
```

### View Metrics

```bash
flyctl status --app ai-ranker
flyctl status --app ai-ranker-frontend
```

### LangSmith Tracing

1. Go to https://smith.langchain.com
2. Select your "ai-ranker" project
3. View traces, latency, and token usage

### Upstash Monitoring

1. Go to https://console.upstash.com
2. Select your Redis database
3. View metrics, data browser, and usage

## Scaling

### Increase instances

```bash
flyctl scale count 2 --app ai-ranker
```

### Increase memory

```bash
flyctl scale memory 512 --app ai-ranker
```

### Add regions

```bash
flyctl regions add lhr --app ai-ranker
```

## Troubleshooting

### Database Connection Issues

```bash
# Check database status
flyctl postgres connect -a ai-ranker-db

# Get connection string
flyctl postgres config -a ai-ranker-db
```

### Secret Management

```bash
# List secrets
flyctl secrets list --app ai-ranker

# Update a secret
flyctl secrets set KEY=new_value --app ai-ranker
```

### Restart Application

```bash
flyctl apps restart ai-ranker
flyctl apps restart ai-ranker-frontend
```

## Cost Optimization

### Fly.io
- Free tier: 3 shared VMs, 3GB persistent storage
- Scale to zero when not in use: `flyctl scale count 0`

### Upstash
- Free tier: 10,000 commands/day
- Enable eviction policy for cache optimization

### LangSmith
- Free tier: 5,000 traces/month
- Use sampling for high-volume production

## Security Best Practices

1. **Rotate API Keys Regularly**
   ```bash
   flyctl secrets set OPENAI_API_KEY=new_key --app ai-ranker
   ```

2. **Enable IP Allowlisting** in Upstash console

3. **Use Read Replicas** for scaling read operations

4. **Monitor Usage** via LangSmith to detect anomalies

## URLs After Deployment

- Frontend: https://ai-ranker-frontend.fly.dev
- Backend API: https://ai-ranker.fly.dev/api
- API Documentation: https://ai-ranker.fly.dev/docs
- LangSmith Traces: https://smith.langchain.com/project/ai-ranker