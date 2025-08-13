# System Status Monitoring

## Overview
The AI Ranker includes a real-time System Status panel that monitors all critical components and services. Located in the left sidebar of the dashboard, it provides at-a-glance health information with traffic light indicators (green/amber/red) for each component.

## Components Monitored

### 1. API Server (FastAPI Backend)
The main application server handling all API requests.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Response time < 1 second | Full functionality |
| 🟡 **Degraded** | Amber | Response time > 1 second but < 5 seconds | Slower operations |
| 🔴 **Offline** | Red | Not responding or > 5 second timeout | No functionality |

### 2. SQLite Database
Local database storing templates, runs, and results.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Connected, queries < 500ms | Normal operations |
| 🟡 **Degraded** | Amber | Connected, queries > 500ms | Slow data access |
| 🔴 **Offline** | Red | Cannot connect or queries failing | No data access |

### 3. Upstash Redis Cache
Cloud-based cache for task status and temporary data.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Connected, latency < 200ms | Fast caching |
| 🟡 **Degraded** | Amber | Connected, latency > 200ms or write failures | Slower caching |
| 🔴 **Offline** | Red | Cannot connect | No caching (non-critical) |

### 4. GPT-5 (OpenAI API)
OpenAI's latest language model for AI analysis.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Responding with content | Normal AI analysis |
| 🟡 **Degraded** | Amber | Response time > 20s or timeout after 5s | Slow responses |
| 🔴 **Offline** | Red | API errors or authentication failures | No GPT-5 access |

**Known Issues**: 
- GPT-5 typically takes 15-25 seconds to respond (normal behavior)
- Temperature must be set to 1.0 for GPT-5 models
- 30-second timeout implemented to prevent hanging

### 5. Gemini 2.5 Pro (Google API)
Google's Gemini model for AI analysis.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Response time < 2 seconds | Fast AI analysis |
| 🟡 **Degraded** | Amber | Response time > 2s or timeout after 5s | Slower responses |
| 🔴 **Offline** | Red | API errors or authentication failures | No Gemini access |

**Advantages**:
- Much faster than GPT-5 (typically < 1 second)
- More reliable for real-time analysis
- Supports grounding (web search) mode

### 6. Background Runner
Thread-based task executor for avoiding HTTP context issues.

| Status | Indicator | Criteria | Impact |
|--------|-----------|----------|--------|
| 🟢 **Healthy** | Green | Running with < 10 active tasks | Normal processing |
| 🟡 **Degraded** | Amber | 10-50 active tasks (backlog forming) | Delayed processing |
| 🔴 **Offline** | Red | Not available or > 50 active tasks | Processing blocked |

## Overall System Status

The panel shows an aggregate status based on all components:

| Display | Condition | Action Required |
|---------|-----------|-----------------|
| **"All Systems Operational"** | All components green | None |
| **"Partial Degradation"** | One or more amber, no red | Monitor, may experience slowness |
| **"System Issues Detected"** | Any component red | Immediate attention needed |

## Features

### Auto-Refresh
- Status checks every 30 seconds automatically
- Manual refresh available via refresh button
- Last check timestamp displayed

### Visual Indicators
- **Traffic Lights**: Three-dot indicator showing green/amber/red status
- **Status Icons**: Checkmark (✓), Warning (⚠), Error (✗)
- **Response Times**: Displayed for API services in milliseconds
- **Task Counts**: Shows active/completed tasks for background runner

### Performance Metrics
- API response times (ms)
- Database query times (ms)
- Cache latency (ms)
- Model response times (seconds)
- Background task queue depth

## Technical Implementation

### Health Check Endpoint
`GET /api/health` - Comprehensive health check
```json
{
  "status": "healthy",
  "timestamp": "2025-08-13T06:33:24.516634",
  "response_time_ms": 167,
  "database": {...},
  "cache": {...},
  "models": {
    "openai": {...},
    "gemini": {...}
  },
  "background_runner": {...}
}
```

### Simple Health Check
`GET /api/health/simple` - Basic availability check for load balancers
```json
{
  "status": "ok",
  "timestamp": "2025-08-13T06:33:24.516634"
}
```

### Caching Strategy
- Model health checks cached for 5 minutes to avoid API spam
- Database and cache checks performed real-time
- Background runner status checked from in-memory state

## Troubleshooting Guide

### API Server Issues
- **Check**: Backend is running on port 8000
- **Fix**: Restart with `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Database Issues
- **Check**: `ai_ranker.db` file exists and is not corrupted
- **Fix**: Check file permissions, disk space

### Cache Issues (Non-Critical)
- **Check**: Upstash credentials in `.env` file
- **Fix**: Verify `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`
- **Note**: System works without cache, just slower

### GPT-5 Issues
- **Check**: OpenAI API key in `.env`
- **Fix**: Verify `OPENAI_API_KEY` is valid
- **Fallback**: Use Gemini if GPT-5 is down

### Gemini Issues
- **Check**: Google API key in `.env`
- **Fix**: Verify `GOOGLE_API_KEY` is valid
- **Fallback**: Use GPT-5 if Gemini is down

### Background Runner Issues
- **Check**: Thread pool not exhausted
- **Fix**: Restart backend to clear stuck tasks
- **Prevention**: Limit concurrent template runs

## Best Practices

1. **Monitor Regularly**: Check status panel when experiencing issues
2. **Use Fallbacks**: If one AI model is down, switch to the other
3. **Cache is Optional**: Don't panic if Upstash is offline
4. **Response Times Vary**: GPT-5 being slow is normal, not a problem
5. **Restart Fixes Most Issues**: Backend restart clears most problems

## Configuration

### Environment Variables
```bash
# Required for AI models
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Optional for caching
UPSTASH_REDIS_REST_URL=your_upstash_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_token
```

### Timeout Settings
- API Server: 5 seconds
- Database: 1 second
- Cache: 1 second
- GPT-5: 30 seconds
- Gemini: 5 seconds

## Future Enhancements

1. **Historical Metrics**: Track uptime and performance over time
2. **Alerting**: Email/Slack notifications for red status
3. **Auto-Recovery**: Automatic restart attempts for failed services
4. **Detailed Logs**: Click-through to see error details
5. **Custom Thresholds**: User-configurable warning levels
6. **Service Dependencies**: Show which features are affected by each component

## Related Documentation

- [CLAUDE.md](CLAUDE.md) - Main project documentation
- [GPT5_EMPTY_RESPONSE_ISSUE.md](GPT5_EMPTY_RESPONSE_ISSUE.md) - GPT-5 specific issues
- [WINDOWS_ENCODING_FIX.md](WINDOWS_ENCODING_FIX.md) - Character encoding issues
- [ENTITY_DISAMBIGUATION.md](ENTITY_DISAMBIGUATION.md) - Entity detection logic