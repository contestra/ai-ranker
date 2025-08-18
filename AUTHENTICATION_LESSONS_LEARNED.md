# Authentication Lessons Learned - CRITICAL

## 🚨 The #1 CRITICAL Mistake: Shell Context Mismatch (WINDOWS)

### ❌ Backend Running in Different Shell Than Auth = ALWAYS BROKEN

**THIS IS THE MOST COMMON FAILURE MODE:** When you authenticate in PowerShell but run the backend from Git Bash/WSL, the backend CANNOT find the ADC file!

**What happens (EXACT SCENARIO FROM TODAY):**
1. You run `gcloud auth application-default login` in PowerShell
2. ADC file is created at `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
3. You start backend from Git Bash: `python -m uvicorn app.main:app`
4. Git Bash looks for ADC at `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
5. **RESULT:** "Your default credentials were not found" - EVEN THOUGH ADC EXISTS!
6. System falls back to direct API (SECURITY BREACH!)

**THE FIX:** 
```powershell
# EVERYTHING in the SAME PowerShell window:
# 1. Authenticate
gcloud auth application-default login

# 2. Set environment variables
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"

# 3. Start backend FROM SAME WINDOW
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**CRITICAL RULE FOR WINDOWS:**
- **PowerShell ADC location:** `%APPDATA%\gcloud\application_default_credentials.json`
- **Git Bash looks for ADC at:** `~/.config/gcloud/application_default_credentials.json`
- **These are DIFFERENT locations!**
- **Backend MUST run from same shell type as authentication!**

## The #2 Mistake: Missing TokenCreator Permission

### ❌ Not Granting TokenCreator Role = BROKEN

**THE ROOT CAUSE OF PERMISSION ERRORS:** The user account (e.g., l@contestra.com) MUST have `roles/iam.serviceAccountTokenCreator` permission on the service account to impersonate it.

**Error you'll see:**
```
Error 403: Permission iam.serviceAccounts.getAccessToken denied
```

**SOLUTION:**
```powershell
$SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
$USER = gcloud config get account

gcloud iam service-accounts add-iam-policy-binding $SA `
  --role="roles/iam.serviceAccountTokenCreator" `
  --member="user:$USER" `
  --project contestra-ai

# Verify:
gcloud auth print-access-token --impersonate-service-account=$SA
```

## The #3 Mistake: Using Git Bash/WSL on Windows

### ❌ Using Git Bash/WSL/CMD Instead of PowerShell = BROKEN

**THE ROOT CAUSE:** Running `gcloud` from Bash/Git Bash/WSL while on Windows causes the ADC file to be written to the wrong location. The browser auth completes in your Windows session, but the ADC file gets written to the home/profile of the process that launched the browser, not where Python checks (`%APPDATA%\gcloud`).

**What happens:**
1. You run `gcloud auth application-default login` from Git Bash
2. Browser opens and you authenticate
3. ADC file gets written to Git Bash's home directory
4. Python checks `%APPDATA%\gcloud\application_default_credentials.json` and finds nothing
5. "ADC not set" error occurs repeatedly

**SOLUTION:** Use PowerShell ONLY on Windows. Do everything in ONE PowerShell window.

## The #2 Mistake: CLI-Level Impersonation (Sometimes)

### UPDATE: CLI-Level Impersonation Can Work (With Caveats)

**CLI impersonation CAN work when:**
1. You're in PowerShell (not Git Bash/WSL)
2. You stay in the SAME session for everything
3. You've granted TokenCreator role properly
4. You're not in a headless/non-interactive context

```powershell
# This CAN work in interactive PowerShell:
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
```

**But it BREAKS when:**
1. Running in Git Bash/WSL (context mismatch)
2. Running in headless/CI environments
3. Switching between terminals
4. Missing TokenCreator role
5. Scripts that spawn new windows

### ✅ Environment Variable Impersonation = CORRECT

**ALWAYS DO THIS:**
```bash
# Linux/Mac:
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="vertex-runner@contestra-ai.iam.gserviceaccount.com"

# Windows:
set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=vertex-runner@contestra-ai.iam.gserviceaccount.com

# Windows (persistent):
setx GOOGLE_IMPERSONATE_SERVICE_ACCOUNT "vertex-runner@contestra-ai.iam.gserviceaccount.com"
```

**Why this works:**
- Google client libraries respect this env var
- No reauthentication prompts
- Works in headless/non-interactive contexts
- Token refresh works properly
- No authentication loops

## Common Script Errors to Avoid

### ❌ Missing Critical Steps:
```powershell
# WRONG - Missing TokenCreator grant
gcloud auth application-default login
gcloud config set auth/impersonate_service_account vertex-runner@...  # FAILS!
```

### ✅ Correct Order (PowerShell):
```powershell
# 1. Ensure correct user is active
gcloud config set account l@contestra.com
gcloud auth login  # If needed

# 2. GRANT TokenCreator (CRITICAL!)
$SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding $SA `
  --role="roles/iam.serviceAccountTokenCreator" `
  --member="user:$(gcloud config get account)" `
  --project contestra-ai

# 3. Verify permission works
gcloud auth print-access-token --impersonate-service-account=$SA

# 4. Set up ADC
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
gcloud auth application-default login
gcloud auth application-default set-quota-project contestra-ai

# 5. Choose impersonation method
# Option A - CLI (OK for PowerShell):
gcloud config set auth/impersonate_service_account $SA

# Option B - Environment (always safe):
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=$SA
```

## Symptoms and Solutions

### Symptom: "Reauthentication required. Please enter your password:"
**Cause:** CLI-level impersonation is set
**Solution:** Run `gcloud config unset auth/impersonate_service_account`

### Symptom: "You do not appear to have access to project [contestra-ai] or it does not exist"
**Cause:** CLI-level impersonation blocking project access
**Solution:** Remove CLI impersonation, use env vars instead

### Symptom: "cannot prompt during non-interactive execution"
**Cause:** Script trying to use CLI impersonation in headless context
**Solution:** Use environment variable impersonation only

### Symptom: OAuth URL appears with "Enter verification code"
**Cause:** Trying to paste OAuth code from different session
**Solution:** Use the same terminal that generated the URL

## The Golden Rules for Windows

1. **ALWAYS use PowerShell, NEVER Git Bash/WSL/CMD:**
   ```powershell
   # Use PowerShell for all gcloud commands on Windows
   ```

2. **Stay in the SAME PowerShell window:**
   - Login + setup + test + backend start all in one window
   - Don't switch terminals mid-process

3. **Verify gcloud is Windows version:**
   ```powershell
   where gcloud  # Should NOT show WSL path
   ```

4. **Check ADC file location after auth:**
   ```powershell
   Get-Item "$env:APPDATA\gcloud\application_default_credentials.json"
   ```

5. **For headless/CI, use environment variables:**
   ```powershell
   $env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="..."
   ```

6. **For interactive PowerShell, CLI impersonation is OK:**
   ```powershell
   gcloud config set auth/impersonate_service_account vertex-runner@...
   ```

## Working Scripts

### `fix_vertex_powershell.ps1` (RECOMMENDED)
- Runs in PowerShell to avoid context mismatch
- Verifies Windows gcloud (not WSL)
- Checks ADC file location
- Tests in same session
- Supports both CLI and env var impersonation

### Scripts with Issues:
- `RUN_THIS_TO_FIX_VERTEX.bat` - Batch scripts can spawn new windows, losing context
- `FIX_VERTEX_NOW.bat` - Sets CLI impersonation before ADC
- Any script run from Git Bash/WSL - Context mismatch issue

## For Agents and CI/CD

**Non-interactive contexts CANNOT:**
- Run `gcloud auth login`
- Run `gcloud auth application-default login`
- Handle interactive prompts

**Non-interactive contexts MUST:**
- Rely on pre-created ADC (human creates it)
- Use environment variable impersonation
- Never use CLI-level impersonation
- Verify with `gcloud auth application-default print-access-token`

## 🤖 Claude Code Execution Context (CRITICAL)

### ❌ Running Claude Code from Git Bash = BROKEN

**DO NOT RUN CLAUDE CODE FROM GIT BASH ON WINDOWS!**

When Claude Code is launched from Git Bash:
- All its subprocesses inherit Git Bash's environment
- Python scripts look for ADC at `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
- But ADC exists at `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- Result: Authentication fails even when ADC is properly configured!

**Where to Run Claude Code:**
- ✅ PowerShell (RECOMMENDED)
- ✅ Windows Command Prompt (cmd.exe)
- ✅ Windows Terminal with PowerShell profile
- ❌ NOT Git Bash
- ❌ NOT WSL
- ❌ NOT MinGW/Cygwin

### 🔧 Workaround if You Must Use Git Bash

If you absolutely must use Git Bash (not recommended), create a symlink:

```bash
# In Git Bash - Create symlink to Windows ADC location
mkdir -p ~/.config/gcloud
ln -sf /c/Users/$USER/AppData/Roaming/gcloud/application_default_credentials.json ~/.config/gcloud/application_default_credentials.json

# Verify it works
ls -la ~/.config/gcloud/application_default_credentials.json
```

**But remember:**
- This is a workaround, not a proper solution
- You still need to authenticate in PowerShell first
- The symlink may break if paths change
- PowerShell is the correct approach

## 🔍 Critical Diagnostic: How to Check if Shell Mismatch is Happening

### The Tell-Tale Signs:
1. **ADC file exists in PowerShell:**
   ```powershell
   Test-Path "$env:APPDATA\gcloud\application_default_credentials.json"  # Returns True
   ```

2. **But backend says ADC not found:**
   ```
   google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found
   ```

3. **Health endpoint shows fallback:**
   ```json
   {
     "vertex_genai_adapter": "WARNING: Using fallback to Direct API"
   }
   ```

### How to Verify Which Shell Backend is Running In:
```powershell
# In PowerShell, check running processes:
Get-Process python | Select-Object Id, ProcessName, Path

# Look for the terminal that started it:
# If you see "bash_22" or similar in the process tree = PROBLEM!
```

### The Fix Checklist:
- [ ] Stop backend running in Git Bash (Ctrl+C)
- [ ] Open PowerShell (Windows key, type "PowerShell")
- [ ] Run `DIAGNOSE_AND_FIX_VERTEX.ps1` from PowerShell
- [ ] Start backend from SAME PowerShell window
- [ ] Never switch shells mid-process

## Summary

**Golden Rule for Windows:** Everything (auth + backend) in the SAME PowerShell window
**Never:** Authenticate in PowerShell, run backend in Git Bash
**Always:** Use environment variables for impersonation
**Result:** No more "ADC not found" when file clearly exists!