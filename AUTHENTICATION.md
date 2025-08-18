# Contestra AI Ranker — Authentication Guide (Master)

This is the **single source of truth** for authentication in the Contestra AI Ranker platform.
It covers **local development** and **production (Fly.io)** for **Google Vertex AI (Gemini models)**.

Follow this exactly — no shortcuts, no raw OAuth URLs, no service account (SA) key files.

## 🚨 CRITICAL: NO FALLBACK TO DIRECT API

**ABSOLUTE RULE:** If Vertex AI authentication fails, the system MUST fail completely. 
**Falling back to direct Gemini API is a SECURITY BREACH and is FORBIDDEN.**

See [CRITICAL_NO_FALLBACK_ALLOWED.md](./CRITICAL_NO_FALLBACK_ALLOWED.md) for full details.

**Quick Rule:** 
- ✅ Vertex AI working = System operational
- ❌ Fallback to direct API = System DOWN (fix immediately)

## 🚨 CRITICAL: Authentication Context & Shell Issues

### The #1 Problem: Context Mismatch
**THE REAL ISSUE:** Running `gcloud` from Bash/Git Bash/WSL while on Windows causes the ADC file to be written to the wrong location. The browser auth completes in your Windows session, but the ADC file gets written to the home/profile of the process that launched the browser, not where Python checks.

**EVEN WORSE:** Running the backend from Bash after authenticating in PowerShell means the backend can't find the ADC file!
- PowerShell ADC location: `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- Bash looks for ADC at: `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json` (different!)
- **Result**: "Your default credentials were not found" error even when ADC exists

### 🔧 Solutions (Choose One):

**SOLUTION A: Explicitly Set ADC Path (FASTEST FIX - RECOMMENDED)**
Bypass all path confusion by telling Google libraries exactly where the ADC file is:

```powershell
# In PowerShell - Set explicit path to ADC file
$env:GOOGLE_APPLICATION_CREDENTIALS = "$env:APPDATA\gcloud\application_default_credentials.json"

# This works because:
# - Google libraries check GOOGLE_APPLICATION_CREDENTIALS first
# - Bypasses Bash/MSYS search path (~/.config/gcloud) entirely
# - No symlinks needed
# - Works from any shell context
```

**SOLUTION B: Use PowerShell Only**
Use **PowerShell only** on Windows. Do everything in ONE PowerShell window.

**SOLUTION C: Create Symlink for Git Bash (Often Fails)**
```bash
# In Git Bash - TRY to create symlink (often fails without admin/Developer Mode)
mkdir -p ~/.config/gcloud
ln -sf /c/Users/$USER/AppData/Roaming/gcloud/application_default_credentials.json ~/.config/gcloud/application_default_credentials.json

# If ln fails, use SOLUTION A instead (set GOOGLE_APPLICATION_CREDENTIALS)
```

**⚠️ WARNING about Git Bash:**
- Symlinks often fail on Windows without Developer Mode or admin rights
- Even if symlink works, it's fragile and can break
- **SOLUTION A (explicit path) is more reliable**

### The #2 Problem: CLI-Level Impersonation (Sometimes)
**UPDATE:** CLI-level impersonation CAN work but only when:
1. You're in the SAME PowerShell session throughout
2. You've properly granted TokenCreator role
3. You're not in a headless/non-interactive context

**Two Valid Approaches:**

**Option A - CLI Impersonation (OK for interactive dev in PowerShell):**
```powershell
# This CAN work if you stay in the same PowerShell window
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
```

**Option B - Environment Variable (Always safe, required for headless):**
```powershell
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"
```

### Critical Rules:
1. **Windows users:** Use PowerShell ONLY, not Git Bash/WSL/CMD
2. **Same session:** Do login + test + backend start in the SAME window
3. **Backend MUST run in PowerShell:** Never start backend from Git Bash/WSL
4. **Headless/CI:** Must use environment variable approach
5. **Claude Code:** MUST be run from PowerShell or CMD on Windows, NOT Git Bash!

### 🤖 CRITICAL: Claude Code Execution Context

**⚠️ DO NOT RUN CLAUDE CODE FROM GIT BASH!**

When you run Claude Code from Git Bash on Windows:
- Git Bash looks for ADC at: `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
- But Windows/PowerShell creates ADC at: `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- **Result:** Authentication fails even when ADC exists!

**Where to Run Claude Code on Windows:**
✅ **PowerShell** (RECOMMENDED)
✅ **Windows Command Prompt** (cmd.exe)
✅ **Windows Terminal with PowerShell profile**

❌ **NEVER from:**
- Git Bash
- WSL (Windows Subsystem for Linux)
- MinGW
- Cygwin
- Any Unix-like shell on Windows

**Why This Matters:**
Claude Code inherits the shell context it's launched from. If you launch it from Git Bash, all its subprocesses (including Python scripts) will look for ADC in the Git Bash location, not the Windows location.

### ⚠️ NEVER Do This on Windows:
```bash
# ❌ WRONG - Authenticate in PowerShell, run backend in Git Bash
# PowerShell: gcloud auth application-default login
# Git Bash: python -m uvicorn app.main:app  # FAILS - can't find ADC!
```

### ✅ ALWAYS Do This on Windows:
```powershell
# ✅ CORRECT - Everything in same PowerShell window
# PowerShell: gcloud auth application-default login
# PowerShell: python -m uvicorn app.main:app  # Works - finds ADC!

## 🔑 Core Principles

* **No JSON SA keys** — Org policy disables (`iam.disableServiceAccountKeyCreation`)
* **Local development**: Application Default Credentials (ADC) + ENV VAR impersonation (NOT CLI impersonation!)
* **Production (Fly.io)**: Workload Identity Federation (WIF) with OIDC → SA impersonation
* **Primary Service Account**: `vertex-runner@contestra-ai.iam.gserviceaccount.com`
* **Required roles**:
  * `roles/aiplatform.user`
  * `roles/serviceusage.serviceUsageConsumer`
  * `roles/iam.serviceAccountTokenCreator` (for impersonation)

### Authentication Stack
* **OpenAI** → API key (`OPENAI_API_KEY`) in `.env` file
* **Google Vertex AI (Gemini)** → Service account impersonation + WIF (no keys)

## 🖥️ Local Development

### Prerequisites
* `gcloud` CLI installed
* Access to project `contestra-ai`
* **CRITICAL**: Your user MUST have **TokenCreator** permission on the service account

### ⚠️ CRITICAL: Grant TokenCreator Permission FIRST

**This is the #1 missing step that causes "permission denied" errors!**

```powershell
# PowerShell - Grant TokenCreator to your user
$PROJECT = "contestra-ai"
$SA = "vertex-runner@$PROJECT.iam.gserviceaccount.com"
$USER_EMAIL = gcloud config get account  # Or specify: "l@contestra.com"

gcloud iam service-accounts add-iam-policy-binding $SA `
  --role="roles/iam.serviceAccountTokenCreator" `
  --member="user:$USER_EMAIL" `
  --project $PROJECT

# Verify the binding exists
gcloud iam service-accounts get-iam-policy $SA --project $PROJECT `
  --format="table(bindings.role, bindings.members)"

# Test impersonation directly (should succeed if permission granted)
gcloud auth print-access-token --impersonate-service-account=$SA | Out-Null
```

**If the test fails**, you're missing the TokenCreator role. The error will be:
`Error 403: Request had insufficient authentication scopes`
or
`Permission iam.serviceAccounts.getAccessToken denied`

### PowerShell Setup (Windows) - COMPLETE SOLUTION

**⚠️ CRITICAL:** Must use PowerShell, NOT Git Bash/WSL/CMD. Do everything in ONE PowerShell window.

#### The Fastest Fix - Explicit ADC Path Method

```powershell
# 0) Ensure ADC exists (create if missing)
if (-not (Test-Path "$env:APPDATA\gcloud\application_default_credentials.json")) {
    Write-Host "ADC missing, creating..." -ForegroundColor Yellow
    gcloud auth login
    gcloud auth application-default login
}

# 1) Set quota project (REQUIRED)
gcloud auth application-default set-quota-project contestra-ai

# 2) BYPASS PATH CONFUSION - Tell Google libs exactly where ADC is
$env:GOOGLE_APPLICATION_CREDENTIALS = "$env:APPDATA\gcloud\application_default_credentials.json"
Write-Host "Set ADC path explicitly: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Green

# 3) Set impersonation (choose ONE method)
# Method A - CLI config:
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com

# Method B - Environment variable (if CLI method causes issues):
# $env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = "vertex-runner@contestra-ai.iam.gserviceaccount.com"

# 4) Set project and region
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"

# 5) OPTIONAL: Disable fallback to catch auth issues immediately
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"

# 6) Test that everything works
python -c @"
import os, google.auth
from google.auth.transport.requests import Request
from google import genai

creds, proj = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(Request())
print(f'Credential type: {creds.__class__.__name__}')
print(f'ADC path: {os.getenv("GOOGLE_APPLICATION_CREDENTIALS")}')
print(f'Impersonated SA: {getattr(creds, "service_account_email", None)}')

if 'Impersonated' not in creds.__class__.__name__:
    raise SystemExit('Not impersonating service account - aborting.')

client = genai.Client(
    vertexai=True,
    project=proj or os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_REGION', 'europe-west4')
)
r = client.models.generate_content(
    model='publishers/google/models/gemini-2.5-flash',
    contents='ping'
)
print(f'Vertex OK: {bool(r.text or r.candidates)}')
"@

# 7) Start backend FROM THIS SAME WINDOW
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Complete PowerShell Script

Save this as `fix_vertex_powershell.ps1` and run in PowerShell:

```powershell
# Run in PowerShell (as your normal user, not admin):
.\fix_vertex_powershell.ps1

# Or if execution policy blocks it:
powershell -ExecutionPolicy Bypass -File fix_vertex_powershell.ps1
```

#### Manual Step-by-Step in PowerShell (ONE window!)

```powershell
# Step 1: Sanity checks
where gcloud  # Must show Windows path, not WSL
$env:APPDATA  # Should show C:\Users\YourName\AppData\Roaming
whoami        # Your Windows user

# Step 2: Clean and setup
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
gcloud config set project contestra-ai
gcloud auth login  # Browser opens - complete it
gcloud auth application-default login  # Browser opens again - complete it

# Step 3: CRITICAL - Set quota project
gcloud auth application-default set-quota-project contestra-ai
Get-Item "$env:APPDATA\gcloud\application_default_credentials.json"  # MUST exist

# Step 4: Grant permission (one-time)
$userEmail = gcloud config get account
gcloud iam service-accounts add-iam-policy-binding `
  vertex-runner@contestra-ai.iam.gserviceaccount.com `
  --member="user:$userEmail" `
  --role="roles/iam.serviceAccountTokenCreator"

# Step 5: Choose ONE impersonation method
# Option A - CLI (OK for interactive PowerShell):
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com

# Option B - Environment (required for headless):
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"

# Step 6: Set other environment variables
$env:GOOGLE_CLOUD_PROJECT="contestra-ai"
$env:GOOGLE_CLOUD_REGION="europe-west4"

# Step 7: Test (IN SAME WINDOW)
python -c @"
import os, google.auth
from google.auth.transport.requests import Request
from google import genai

creds, proj = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(Request())
print(f'Credential type: {creds.__class__.__name__}')
print(f'Impersonated SA: {getattr(creds, "service_account_email", None)}')

client = genai.Client(vertexai=True, project='contestra-ai', location='europe-west4')
r = client.models.generate_content(model='publishers/google/models/gemini-2.5-flash', contents='ping')
print(f'Vertex OK: {bool(r.text or r.candidates)}')
"@

# Step 8: Start backend (IN SAME WINDOW)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Why Batch Scripts Fail on Windows

Batch scripts (`*.bat`) often fail because:
1. They may spawn new windows, losing environment context
2. Running from Git Bash/WSL causes ADC to be written to wrong location
3. Browser auth completes in Windows session but ADC goes elsewhere
4. Python then checks `%APPDATA%\gcloud` and finds nothing

**SOLUTION:** Always use PowerShell and stay in the same window.

### Manual Step-by-Step Setup (if automated script fails)
echo === Contestra Vertex Auth Fix ===
echo Project: %PROJECT%
echo Region : %REGION%
echo SA     : %SA_EMAIL%
echo.

REM ===== Check gcloud exists =====
where gcloud >nul 2>&1
if errorlevel 1 (
  echo [ERROR] gcloud CLI not found. Install from https://cloud.google.com/sdk
  exit /b 1
)

REM ===== Verify project exists =====
echo [INFO] Verifying that project "%PROJECT%" exists...
gcloud projects describe "%PROJECT%" --format="value(projectNumber)" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] GCP project "%PROJECT%" not found.
  echo.
  echo Try one of these existing projects on your account:
  gcloud projects list --format="table(projectId,name,projectNumber)"
  echo.
  echo Rerun: RUN_THIS_TO_FIX_VERTEX.bat ^<project-id^>
  exit /b 1
)

REM ===== Point gcloud at the project =====
echo [INFO] Setting gcloud core/project ...
gcloud config set project "%PROJECT%" 1>nul

REM ===== Remove brittle CLI impersonation (we use env-var impersonation instead) =====
echo [INFO] Unsetting CLI impersonation (if any) ...
gcloud config unset auth/impersonate_service_account 1>nul

REM ===== Ensure ADC exists; if missing, open browser =====
echo [INFO] Checking Application Default Credentials (ADC) ...
gcloud auth application-default print-access-token 1>nul 2>nul
if errorlevel 1 (
  echo [ACTION] Opening browser for ADC login (one-time) ...
  gcloud auth application-default login
  if errorlevel 1 (
    echo [ERROR] ADC login failed or was cancelled. Please rerun the script after successful login.
    exit /b 1
  )
)

REM ===== Ensure quota project (prevents 403s on some APIs) =====
echo [INFO] Setting quota project to "%PROJECT%" ...
gcloud auth application-default set-quota-project "%PROJECT%" 1>nul

REM ===== Set persistent env vars for SA impersonation and project/region =====
echo [INFO] Setting persistent user env vars ...
setx GOOGLE_IMPERSONATE_SERVICE_ACCOUNT "%SA_EMAIL%" >nul
setx GOOGLE_CLOUD_PROJECT "%PROJECT%" >nul
setx GOOGLE_CLOUD_REGION "%REGION%" >nul

echo [INFO] Also setting them for this session ...
set "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=%SA_EMAIL%"
set "GOOGLE_CLOUD_PROJECT=%PROJECT%"
set "GOOGLE_CLOUD_REGION=%REGION%"

REM ===== Verify token again (non-interactive) =====
echo [INFO] Verifying access token via ADC ...
gcloud auth application-default print-access-token >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Token mint failed. ADC is stale or quota project not set.
  echo        Run these in PowerShell manually and re-run this script:
  echo        gcloud auth application-default login
  echo        gcloud auth application-default set-quota-project %PROJECT%
  exit /b 1
)

echo.
echo ✅ Vertex local auth is configured.
echo    - Project: %PROJECT%
echo    - Region : %REGION%
echo    - SA Imp : %SA_EMAIL%
echo.
echo NOTE: Open a NEW terminal so the persistent env vars take effect.
echo.

endlocal
exit /b 0
```

**Usage:**
- Double-click the .bat file, or
- Run in terminal: `RUN_THIS_TO_FIX_VERTEX.bat`
- With custom project: `RUN_THIS_TO_FIX_VERTEX.bat my-project-id`

**What this script does:**
1. Verifies gcloud is installed
2. **Verifies the project ID actually exists** (common error source!)
3. Removes brittle CLI impersonation
4. Ensures ADC exists (opens browser if needed)
5. Sets persistent environment variables
6. Verifies everything works

**After running:** Open a NEW terminal for the environment variables to take effect.

### Manual Step-by-Step Setup (if automated script fails)

#### 1. Verify Project ID First
```powershell
# List all your projects to find the correct ID
gcloud projects list --format="table(projectId,name,projectNumber)"
```

#### 2. Clean Previous Authentication (if needed)
```powershell
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
```

#### 3. Login with ADC
```powershell
gcloud config set project contestra-ai
gcloud auth application-default login
gcloud auth application-default set-quota-project contestra-ai
```

✅ **The browser page that says "Sign in to the gcloud CLI" is correct.**
❌ **Don't use raw OAuth URLs.**
❌ **Don't append `--impersonate-service-account` to the login command.**

#### 4. Configure Service Account Impersonation

**REQUIRED - Use Environment Variables:**
```powershell
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"
$env:GOOGLE_CLOUD_PROJECT="contestra-ai"
$env:GOOGLE_CLOUD_REGION="europe-west4"
```

**NEVER DO THIS (causes reauthentication loops):**
```powershell
# ❌ DO NOT USE - This breaks everything!
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
```

#### 5. Start the Backend
```bash
cd backend
# Windows - with all required env vars
set PYTHONUTF8=1 && set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=vertex-runner@contestra-ai.iam.gserviceaccount.com && set GOOGLE_CLOUD_PROJECT=contestra-ai && set GOOGLE_CLOUD_REGION=europe-west4 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or if env vars are already set permanently
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verification

#### Check ADC is working:
```bash
gcloud auth application-default print-access-token
```

#### Verify in Python:
```python
import os
import google.auth

creds, project = google.auth.default()
print(f"Project: {project or os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"Impersonating: {os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')}")

# Test Vertex AI client
from google import genai
client = genai.Client(
    vertexai=True, 
    project=project or os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_REGION", "europe-west4")
)
print("GenAI client OK")
```

## 🛡️ Fail-Closed Configuration (RECOMMENDED)

### Prevent Silent Fallback to Direct API

To ensure authentication issues are caught immediately rather than masked by fallback:

```powershell
# Set this environment variable to disable fallback
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"
```

**What this does:**
- Forces the system to fail completely if Vertex AI auth fails
- Prevents masking authentication problems with direct API fallback
- Makes debugging much easier - you know immediately if auth is broken

**Use during:**
- Initial setup and testing
- Debugging authentication issues
- Production (fallback should never happen in production)

## Common Issues and Solutions

### "Permission iam.serviceAccounts.getAccessToken denied" 
- **Cause**: Missing TokenCreator role on the service account (MOST COMMON ISSUE!)
- **Solution**: 
  ```powershell
  $SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
  $USER = gcloud config get account
  
  # Grant the permission
  gcloud iam service-accounts add-iam-policy-binding $SA `
    --role="roles/iam.serviceAccountTokenCreator" `
    --member="user:$USER" `
    --project contestra-ai
  
  # Verify it worked
  gcloud auth print-access-token --impersonate-service-account=$SA
  ```

### "Project does not exist" error
- **Cause**: Wrong project ID or missing TokenCreator permission (impersonation failing)
- **Solution**: 
  1. Verify project: `gcloud projects describe contestra-ai`
  2. Fix TokenCreator permission (see above)

### "Reauthentication is needed"
- **Cause**: ADC token expired or CLI-level impersonation set incorrectly
- **Solution**: 
  ```powershell
  Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
  gcloud auth application-default login
  gcloud auth application-default set-quota-project contestra-ai
  ```

### "ADC not found" or "ADC not set"
- **Cause**: Running gcloud from Git Bash/WSL - ADC written to wrong location
- **Solution**: Use PowerShell ONLY, do everything in one window

### "Permission denied" when calling Vertex AI (after impersonation works)
- **Cause**: Service account lacks Vertex AI permissions
- **Solution**: Grant required roles to the service account:
  ```powershell
  $SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
  
  gcloud projects add-iam-policy-binding contestra-ai `
    --member="serviceAccount:$SA" `
    --role="roles/aiplatform.user"
  
  gcloud projects add-iam-policy-binding contestra-ai `
    --member="serviceAccount:$SA" `
    --role="roles/serviceusage.serviceUsageConsumer"
```

### Code/verification doesn't work
- **Cause**: Trying to paste code from one gcloud session into another
- **Solution**: Use the SAME terminal/command that generated the URL

### Still using user account instead of service account
- **Cause**: Environment variables not set or not picked up
- **Solution**: Restart the backend after setting environment variables

### Environment variables not persisting
- **Cause**: Using `set` instead of `setx` on Windows
- **Solution**: Use the automated script which uses `setx` for persistent variables, then open a NEW terminal

## What NOT to Do

❌ **#1 MISTAKE: Don't use CLI-level impersonation with `gcloud config set auth/impersonate_service_account`**
- **This is the most common error that breaks everything**
- Causes "Reauthentication required" prompts
- Creates "project does not exist" errors
- Breaks in non-interactive/headless environments
- **ALWAYS use environment variable impersonation instead**

❌ **Don't use `--impersonate-service-account` flag with `gcloud auth application-default login`**
- This flag doesn't work as expected
- Use environment variables after creating ADC

❌ **Don't try to complete ADC via raw OAuth URLs**
- Those URLs and codes only work within the gcloud process that generated them

❌ **Don't download service account key JSON files**
- Organization policy blocks this
- Impersonation is more secure

❌ **Don't mix authentication between WSL and Windows**
- Use the same environment for both authentication and running the app

## ☁️ Production (Fly.io) — Workload Identity Federation

### Why WIF
* Keyless, secure, enforced by org policy
* Fly.io provides an OIDC token → GCP exchanges → impersonates SA → calls Vertex

### Setup

**1. Create Workload Identity Pool & Provider**
```bash
gcloud iam workload-identity-pools create flyio-pool --project contestra-ai --location="global"
gcloud iam workload-identity-pools providers create-oidc flyio-oidc \
  --project contestra-ai --location="global" \
  --workload-identity-pool="flyio-pool" \
  --issuer-uri="https://oidc.fly.io" \
  --attribute-mapping="google.subject=assertion.sub,attribute.aud=assertion.aud"
```

**2. Bind SA to Pool**
```bash
gcloud iam service-accounts add-iam-policy-binding vertex-runner@contestra-ai.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/flyio-pool/attribute.aud/https://oidc.fly.io/<org-slug>"
```

**3. External Account JSON (`/app/config/gcp-workload-identity.json`)**
```json
{
  "type": "external_account",
  "audience": "//iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/flyio-pool/providers/flyio-oidc",
  "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
  "token_url": "https://sts.googleapis.com/v1/token",
  "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/vertex-runner@contestra-ai.iam.gserviceaccount.com:generateAccessToken",
  "credential_source": {
    "executable": {
      "command": "/app/bin/flyio_openid_token https://oidc.fly.io/<org-slug>",
      "timeout_millis": 5000
    }
  }
}
```

**4. OIDC Token Helper Script**

Bash version (`/app/bin/flyio_openid_token`):
```bash
#!/usr/bin/env bash
AUDIENCE="$1"
JWT="$(curl -sS -X POST "http://[fdaa::3]:4280/v1/tokens" \
  -H 'Content-Type: application/json' \
  --data "{\"audience\":\"$AUDIENCE\"}" | jq -r '.data.token')"
printf '{"token_type":"urn:ietf:params:oauth:token-type:jwt","token":"%s"}' "$JWT"
```

PowerShell version (`C:\app\bin\flyio_openid_token.ps1`):
```powershell
param([string]$Audience)
$resp = Invoke-RestMethod -Method Post -Uri "http://[fdaa::3]:4280/v1/tokens" `
  -ContentType "application/json" -Body (@{ audience = $Audience } | ConvertTo-Json -Compress)
$jwt = $resp.data.token
$out = @{ token_type = "urn:ietf:params:oauth:token-type:jwt"; token = $jwt } | ConvertTo-Json -Compress
Write-Output $out
```

**5. Runtime Config**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-workload-identity.json
export GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES=1
```

## Authentication Flow Diagram

```
Local Development:
User → gcloud auth application-default login → ADC file created
     → Set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT env var
     → Application uses ADC + impersonation → Vertex AI

Production (Fly.io):
Fly Machine → OIDC token → Workload Identity Pool → Service Account → Vertex AI
```

## File Locations

- **ADC file**: 
  - Windows: `%APPDATA%\gcloud\application_default_credentials.json`
  - Linux/Mac: `~/.config/gcloud/application_default_credentials.json`
- **gcloud config**: `%APPDATA%\gcloud\configurations\config_default` (Windows)

## 🤖 Non-Interactive Authentication (Agents/CI/CD)

### 🚨 CRITICAL FOR AGENTS: Shell Context Awareness

**AGENTS MUST UNDERSTAND THE SHELL CONTEXT THEY'RE RUNNING IN!**

When an agent uses Bash tool on Windows:
- Bash looks for ADC at: `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
- But Windows ADC exists at: `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- **These are DIFFERENT locations!**

**AGENTS MUST:**
1. Check BOTH locations for ADC
2. Use Windows paths when checking from PowerShell context
3. Use Linux paths when checking from Bash context
4. NEVER assume ADC doesn't exist just because one path fails

**Correct Agent Behavior:**
```python
# Check Windows path (for PowerShell/CMD context)
windows_adc = "C:\\Users\\leedr\\AppData\\Roaming\\gcloud\\application_default_credentials.json"

# Check Linux path (for Git Bash/MSYS context)  
linux_adc = "/c/Users/leedr/.config/gcloud/application_default_credentials.json"

# ADC exists if EITHER path has the file!
```

### Key Principle
**Agents and CI environments cannot perform interactive browser authentication.** They must rely on pre-configured ADC created by a human or use environment-based authentication.

### Common Errors to Avoid
- **"cannot prompt during non-interactive execution"** - Agent trying browser auth
- **OAuth timeout** - Agent waiting for code that will never come
- **"Sign in to continue to Google Cloud SDK"** - Browser login in headless context
- **"ADC not found" when checking wrong path** - Shell context mismatch!

### 🤖 AGENT INSTRUCTIONS: How to Check ADC Properly on Windows

**AGENTS: Follow this EXACT process:**

```python
# Step 1: Check Windows path (PowerShell/CMD context)
import os
import pathlib

windows_adc = pathlib.Path(r"C:\Users\leedr\AppData\Roaming\gcloud\application_default_credentials.json")
linux_adc = pathlib.Path("/c/Users/leedr/.config/gcloud/application_default_credentials.json")

adc_exists = False
adc_location = None

# Check Windows path
if windows_adc.exists():
    adc_exists = True
    adc_location = "Windows"
    print(f"ADC found at Windows path: {windows_adc}")

# Check Linux path (Git Bash/MSYS)
if linux_adc.exists():
    adc_exists = True
    adc_location = "Linux/GitBash"
    print(f"ADC found at Linux path: {linux_adc}")

if not adc_exists:
    print("ADC MISSING - User must run: gcloud auth application-default login")
else:
    print(f"ADC EXISTS in {adc_location} context")
```

**NEVER DO THIS (Common Agent Mistake):**
```bash
# WRONG - Only checks one path!
ls ~/.config/gcloud/application_default_credentials.json
# Fails and thinks ADC doesn't exist when it's actually at Windows path!
```

### Correct Non-Interactive Setup

#### 1. Remove CLI-level Impersonation (causes issues in headless)
```bash
gcloud config unset auth/impersonate_service_account || true
```

#### 2. Set Environment Variables for Impersonation
```bash
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"
export GOOGLE_CLOUD_PROJECT="contestra-ai"
export GOOGLE_CLOUD_REGION="europe-west4"
```

#### 3. Verify ADC Exists (Non-Interactive Check)
```bash
gcloud auth application-default print-access-token >/dev/null || echo "ADC missing/expired"
```

If this fails, the **human must create ADC** outside the agent:
```text
(HUMAN ACTION REQUIRED - Run in PowerShell/Terminal)
gcloud config set project contestra-ai
gcloud auth application-default login
gcloud auth application-default set-quota-project contestra-ai
```

#### 4. Start Backend with Environment Variables
```bash
# All env vars in one command (Windows)
set PYTHONUTF8=1 && set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=vertex-runner@contestra-ai.iam.gserviceaccount.com && set GOOGLE_CLOUD_PROJECT=contestra-ai && set GOOGLE_CLOUD_REGION=europe-west4 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 5. Verify Identity (Non-Interactive)
```bash
curl -s http://localhost:8000/__whoami || curl -s http://localhost:8000/api/health
```

### What NOT to Do in Non-Interactive Contexts

❌ **Never run `gcloud auth login` or `gcloud auth application-default login`**
- These require browser interaction

❌ **Never paste OAuth codes or open OAuth URLs**
- The code is tied to the specific gcloud process that generated it

❌ **Never use `--impersonate-service-account` with login commands**
- This flag doesn't work as expected and causes token refresh issues

❌ **Never download service account keys**
- Organization policy blocks this

### Handling Reauthentication in Non-Interactive Contexts

If ADC expires or authentication loops occur:

1. **Print instructions for human** (don't run):
```text
(HUMAN ACTION REQUIRED)
# Windows PowerShell:
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue

# Linux/Mac:
rm ~/.config/gcloud/application_default_credentials.json

# Then recreate ADC:
gcloud auth application-default login
gcloud auth application-default set-quota-project contestra-ai
```

2. **After human completes authentication**, verify:
```bash
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK" || echo "ADC still broken"
```

### Why This Works

- **Environment variable impersonation** (`GOOGLE_IMPERSONATE_SERVICE_ACCOUNT`) works reliably in headless contexts
- **CLI-level impersonation** (`gcloud config set auth/impersonate_service_account`) often breaks token refresh in non-interactive shells
- **ADC creation must be interactive** - requires browser, so human must do it
- **Libraries honor env vars** - Google client libraries respect `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` without any interactive prompts

## 🔍 Debugging

### Who-am-I Endpoint (FastAPI)
Add this to your FastAPI app to check authentication status:

```python
@app.get("/__whoami")
def whoami():
    import google.auth, google.auth.transport.requests as tr
    creds, project = google.auth.default()
    creds.refresh(tr.Request())
    return {
        "project": project,
        "type": creds.__class__.__name__,
        "service_account": getattr(creds, "service_account_email", None)
    }
```

**Interpreting the response:**
- If `type=AuthorizedUser` and `service_account=None` → You're using raw user ADC, not impersonating
- If `service_account=vertex-runner@contestra-ai.iam.gserviceaccount.com` → Impersonation is working correctly

## ✅ DO / DON'T Cheat Sheet

**DO (local):**
* `gcloud auth application-default login`
* `gcloud auth application-default set-quota-project contestra-ai`
* Export `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=vertex-runner@contestra-ai.iam.gserviceaccount.com`

**DO (prod):**
* Use WIF with Fly.io OIDC
* `GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-workload-identity.json`
* `GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES=1`

**DON'T:**
* Add `--impersonate-service-account` to `login` command
* Paste random OAuth URLs into browser expecting them to work
* Generate/download SA keys
* Mix WSL and Windows authentication contexts

## 📌 Summary & TL;DR Rules

### Quick Rules
1. **Local Dev** = ADC + impersonation
2. **Prod (Fly.io)** = Workload Identity Federation (OIDC)
3. **No JSON keys** (org policy blocks them)
4. **Never chase raw OAuth URLs** - The normal browser page is correct
5. **Always confirm with `/__whoami`** to know what identity is active

### Key Points
* **Local dev**: ADC + SA impersonation via env vars, no keys
* **Production**: WIF + OIDC, no keys
* Always confirm identity with `/__whoami` endpoint
* Ignore random OAuth links from confused LLMs
* This doc is the **single source of truth** for authentication

✅ With this, engineers and LLMs have a **single source of truth** for authentication.