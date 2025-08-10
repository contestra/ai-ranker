# Quick Deployment Guide (Existing Accounts)

Since you already have Fly.io, Upstash, and LangChain accounts set up, here's the streamlined deployment process.

## Prerequisites Checklist

✅ Fly.io account with `flyctl` installed  
✅ Upstash Redis instance (REST URL and Token)  
✅ LangSmith API key  
✅ OpenAI, Google, and/or Anthropic API keys  

## Step 1: Configure Environment

In WSL, navigate to the project:

```bash
cd /mnt/d/OneDrive/CONTESTRA/Microapps/ai-ranker
```

Create and edit the environment file:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Add your existing credentials:

```env
# Database - Leave this commented, Fly will auto-configure
# DATABASE_URL=

# Your existing Upstash Redis credentials
UPSTASH_REDIS_REST_URL=https://your-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token_here

# LLM API Keys
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# Your existing LangSmith credentials
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ai-ranker

# Server settings
HOST=0.0.0.0
PORT=8080
ENVIRONMENT=production
```

## Step 2: Deploy

Run the deployment script:

```bash
chmod +x deploy-existing.sh
./deploy-existing.sh
```

The script will:
1. Check if apps already exist (won't recreate if they do)
2. Ask if you want a new Postgres database
3. Set all secrets from your .env file
4. Deploy both backend and frontend
5. Show you the live URLs

## Step 3: Verify Deployment

Check that everything is running:

```bash
# Check app status
flyctl status --app ai-ranker
flyctl status --app ai-ranker-frontend

# View logs if needed
flyctl logs --app ai-ranker --tail
```

## Step 4: Initialize Data

Add your first brand to track:

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

## URLs

After deployment, your app will be available at:

- **Frontend**: https://ai-ranker-frontend.fly.dev
- **Backend API**: https://ai-ranker.fly.dev/api
- **API Docs**: https://ai-ranker.fly.dev/docs
- **LangSmith Traces**: https://smith.langchain.com/project/ai-ranker

## Troubleshooting

### If deployment fails:

1. **Check logs**: 
   ```bash
   flyctl logs --app ai-ranker
   ```

2. **Verify secrets are set**:
   ```bash
   flyctl secrets list --app ai-ranker
   ```

3. **Restart if needed**:
   ```bash
   flyctl apps restart ai-ranker
   ```

### If you want to use existing Postgres from another app:

Instead of creating a new database, set the DATABASE_URL secret manually:

```bash
# Get DATABASE_URL from your other app
flyctl postgres config --app your-other-db

# Set it for this app
flyctl secrets set DATABASE_URL="postgres://..." --app ai-ranker
```

## Cost Optimization Tips

Since you're already using these services:

1. **Reuse Upstash Redis** - No need for a separate instance
2. **Share Postgres** if your other app's DB is underutilized
3. **Use Fly.io hobby plan** - Both apps can run on the free tier
4. **Monitor LangSmith usage** - Stay within free tier limits

## Next Steps

1. Access the frontend and select/create a brand
2. Run your first experiment
3. Monitor traces in LangSmith
4. Check cache hits in Upstash console