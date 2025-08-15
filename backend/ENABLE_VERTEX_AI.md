# Enable Vertex AI API

The Vertex AI setup is almost complete! You just need to enable the API:

## Option 1: Web Console (Recommended)

1. Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=contestra-ai
2. Click the "ENABLE" button
3. Wait for it to activate (usually takes 1-2 minutes)

## Option 2: Using gcloud CLI in PowerShell

```powershell
# In PowerShell, run:
gcloud services enable aiplatform.googleapis.com --project contestra-ai
```

## Option 3: Direct link to enable multiple APIs at once

Enable these APIs for the contestra-ai project:
- Vertex AI API: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=contestra-ai
- Cloud Resource Manager API (if needed): https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com?project=contestra-ai

## Current Status

✅ Google Cloud Project created: contestra-ai
✅ Billing enabled
✅ Application Default Credentials (ADC) configured
✅ Python packages installed (vertexai, langchain-google-vertexai)
❌ Vertex AI API needs to be enabled

Once you enable the API, run:
```bash
cd backend && python test_vertex_setup.py
```

This should complete successfully and you'll be ready to use Vertex AI for grounding!