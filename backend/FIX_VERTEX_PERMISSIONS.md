# Fix Vertex AI Permissions

## Status
✅ **Vertex AI API is ENABLED** (confirmed by dashboard showing 2 requests)  
❌ **IAM permissions missing** (403 Permission denied errors)

## Quick Fix - Add IAM Role

### Option 1: Via Console (Easiest)
1. Go to: https://console.cloud.google.com/iam-admin/iam?project=contestra-ai
2. Find your email in the list (should have "Owner" role already)
3. Click the pencil icon to edit
4. Click "ADD ANOTHER ROLE"
5. Search for and add: **Vertex AI User** (roles/aiplatform.user)
6. Click "SAVE"
7. Wait 1-2 minutes for permissions to propagate

### Option 2: Via PowerShell (if gcloud is installed)
```powershell
# Get your email
$email = gcloud config get-value account

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding contestra-ai `
  --member="user:$email" `
  --role="roles/aiplatform.user"
```

### Option 3: Direct Link to Add Role
https://console.cloud.google.com/iam-admin/iam?project=contestra-ai

Add these roles to your user:
- **Vertex AI User** (roles/aiplatform.user) - Required for using models
- **Vertex AI Viewer** (roles/aiplatform.viewer) - Optional, for viewing resources

## What This Fixes
The 403 errors show that:
- ✅ Your ADC credentials are working
- ✅ The API is enabled and receiving requests
- ❌ Your user lacks the `aiplatform.endpoints.predict` permission

Adding the "Vertex AI User" role grants all necessary permissions including:
- `aiplatform.endpoints.predict` - To call models
- `aiplatform.locations.get` - To access regions
- `aiplatform.models.get` - To access model metadata

## Test After Adding Role
```bash
cd backend && python test_vertex_simple.py
```

You should see "SUCCESS!" instead of permission errors.

## Alternative: Use Direct Gemini API
If you don't want to set up Vertex permissions, the system already falls back to the direct Gemini API which is working fine. Vertex is only needed for server-side grounding.