# Vertex AI Diagnostic Script

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "VERTEX AI DIAGNOSTIC - SYSTEMATIC CHECK" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 0: Check current configuration
Write-Host "STEP 0: CHECKING CURRENT CONFIGURATION" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Gray

Write-Host "Current project:"
gcloud config get-value project

Write-Host "`nActive account:"
gcloud auth list --filter=status:ACTIVE --format="value(account)"

Write-Host "`nChecking ADC..."
try {
    $null = gcloud auth application-default print-access-token 2>$null
    Write-Host "ADC is configured" -ForegroundColor Green
} catch {
    Write-Host "ADC not configured - run: gcloud auth application-default login" -ForegroundColor Red
}

# Step 1: Check IAM roles
Write-Host "`n`nSTEP 1: CHECKING IAM ROLES" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Gray

$email = gcloud auth list --filter=status:ACTIVE --format="value(account)"
Write-Host "Checking roles for: $email"

gcloud projects get-iam-policy contestra-ai --flatten="bindings[].members" `
  --filter="bindings.members:user:$email" `
  --format="table(bindings.role)"

# Step 2: Check API status
Write-Host "`n`nSTEP 2: CHECKING API STATUS" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Gray

$apiEnabled = gcloud services list --enabled --project contestra-ai --format="value(config.name)" | Select-String "aiplatform"
if ($apiEnabled) {
    Write-Host "Vertex AI API is ENABLED" -ForegroundColor Green
} else {
    Write-Host "Vertex AI API is NOT enabled!" -ForegroundColor Red
    Write-Host "Run: gcloud services enable aiplatform.googleapis.com --project contestra-ai"
}

# Step 3: Test REST API access
Write-Host "`n`nSTEP 3: TESTING REST API ACCESS" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Gray

try {
    $TOKEN = gcloud auth application-default print-access-token 2>$null
    $PROJECT = "contestra-ai"
    
    # Test multiple regions
    $regions = @("us-central1", "europe-west4")
    
    foreach ($LOCATION in $regions) {
        Write-Host "`nTesting region: $LOCATION"
        $URL = "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOCATION}/publishers/google/models"
        
        $response = Invoke-WebRequest -Uri $URL -Headers @{"Authorization"="Bearer $TOKEN"} -Method GET -UseBasicParsing -ErrorAction SilentlyContinue
        
        if ($response.StatusCode -eq 200) {
            Write-Host "  SUCCESS! Models available in $LOCATION" -ForegroundColor Green
            $models = ($response.Content | ConvertFrom-Json).models
            Write-Host "  Found $($models.Count) models"
            if ($models.Count -gt 0) {
                Write-Host "  First few models:"
                $models[0..2] | ForEach-Object { Write-Host "    - $($_.name)" }
            }
        } else {
            Write-Host "  Failed with status: $($response.StatusCode)" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "Error testing REST API: $_" -ForegroundColor Red
    Write-Host "This usually means ADC is not configured properly"
}

# Step 4: Python SDK test
Write-Host "`n`nSTEP 4: TESTING PYTHON SDKs" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Gray

# Test traditional Vertex AI SDK
Write-Host "`nTesting traditional Vertex AI SDK..."
$pythonTest1 = @'
import vertexai
from vertexai.generative_models import GenerativeModel
vertexai.init(project="contestra-ai", location="us-central1")
try:
    response = GenerativeModel("gemini-1.5-flash-002").generate_content("Say OK")
    print("SUCCESS: " + response.text[:50])
except Exception as e:
    print("ERROR: " + str(e)[:200])
'@

python -c $pythonTest1

# Test new GenAI client
Write-Host "`nTesting new Google GenAI client..."
$pythonTest2 = @'
from google import genai
client = genai.Client(vertexai=True, project="contestra-ai", location="us-central1")
try:
    response = client.models.generate_content(model="gemini-1.5-flash-002", contents="Say OK")
    print("SUCCESS: " + response.text[:50])
except Exception as e:
    print("ERROR: " + str(e)[:200])
'@

python -c $pythonTest2

Write-Host "`n`n================================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If you see errors above, they indicate what needs fixing:" -ForegroundColor Yellow
Write-Host "- PERMISSION_DENIED: Run the IAM role commands" -ForegroundColor Yellow
Write-Host "- ADC not configured: Run 'gcloud auth application-default login'" -ForegroundColor Yellow
Write-Host "- Wrong project: Run 'gcloud config set project contestra-ai'" -ForegroundColor Yellow
Write-Host ""