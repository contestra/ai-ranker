# 🤖 AGENT AUTHENTICATION GUIDE - CRITICAL

## 🚨 THE #1 AGENT MISTAKE: Shell Context Confusion

### The Problem

When agents run on Windows, they often make this CRITICAL ERROR:
1. Agent uses Bash tool to check for ADC
2. Bash looks at `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`
3. File doesn't exist there (it's a Linux-style path)
4. Agent reports "ADC missing, need to authenticate"
5. **BUT THE ADC ACTUALLY EXISTS** at `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`

### The Reality on Windows

**Two Different ADC Locations:**
- **Windows/PowerShell path:** `C:\Users\USERNAME\AppData\Roaming\gcloud\application_default_credentials.json`
- **Git Bash/MSYS path:** `/c/Users/USERNAME/.config/gcloud/application_default_credentials.json`

**These are COMPLETELY DIFFERENT locations!**

## ✅ CORRECT Agent Behavior

### Always Check BOTH Locations

```python
# CORRECT - Check both possible locations
import os
from pathlib import Path

def check_adc_exists():
    """Check if ADC exists in either Windows or Linux location"""
    
    # Windows path (PowerShell/CMD)
    windows_adc = Path(r"C:\Users\leedr\AppData\Roaming\gcloud\application_default_credentials.json")
    
    # Linux path (Git Bash/MSYS)
    linux_adc = Path("/c/Users/leedr/.config/gcloud/application_default_credentials.json")
    
    if windows_adc.exists():
        return True, "Windows", str(windows_adc)
    
    if linux_adc.exists():
        return True, "Linux/GitBash", str(linux_adc)
    
    return False, None, None

# Use it
exists, context, path = check_adc_exists()
if exists:
    print(f"✅ ADC EXISTS in {context} context at: {path}")
else:
    print("❌ ADC MISSING - User needs to run: gcloud auth application-default login")
```

## ❌ WRONG Agent Behavior (What NOT to Do)

### Common Mistakes

```bash
# MISTAKE 1: Only checking Linux path
ls ~/.config/gcloud/application_default_credentials.json
# Reports "not found" when file exists at Windows path!

# MISTAKE 2: Using %APPDATA% in bash
ls "%APPDATA%\gcloud\application_default_credentials.json"
# %APPDATA% doesn't expand in bash!

# MISTAKE 3: Not understanding context
echo "ADC not found, creating it..."
gcloud auth application-default login  # FAILS - can't do browser auth!
```

## 🎯 Agent Decision Tree

```
START
  ↓
Check Windows ADC path exists?
  ├─ YES → ADC exists, proceed with auth
  └─ NO → Check Linux ADC path exists?
           ├─ YES → ADC exists (but in wrong location)
           │        Create symlink or copy file
           └─ NO → ADC truly missing
                    STOP - Tell user to run:
                    gcloud auth application-default login
```

## 🔧 Fixing Path Mismatch

If ADC exists in Windows path but agent is running in Bash context:

### Option 1: Set GOOGLE_APPLICATION_CREDENTIALS (BEST - Always Works!)
```bash
# In ANY shell - Point directly to Windows ADC location
export GOOGLE_APPLICATION_CREDENTIALS="/c/Users/leedr/AppData/Roaming/gcloud/application_default_credentials.json"

# This is the MOST RELIABLE solution because:
# - Google libraries check this env var FIRST
# - Bypasses all path searching
# - Works from any shell context
# - No symlinks needed (which often fail on Windows)
```

### Option 2: Create Symlink (Often Fails)
```bash
# In Git Bash - TRY to link to Windows ADC (needs admin/Developer Mode)
mkdir -p /c/Users/leedr/.config/gcloud
ln -sf ../../AppData/Roaming/gcloud/application_default_credentials.json \
       /c/Users/leedr/.config/gcloud/application_default_credentials.json

# WARNING: Often fails with "No such file or directory" on Windows
# Use Option 1 instead if this fails!
```

### Option 3: Copy File (Temporary)
```bash
# Copy from Windows location to Linux location
mkdir -p /c/Users/leedr/.config/gcloud
cp /c/Users/leedr/AppData/Roaming/gcloud/application_default_credentials.json \
   /c/Users/leedr/.config/gcloud/application_default_credentials.json

# WARNING: This is a one-time copy, gets out of sync if ADC refreshed
```

## 📋 Agent Checklist

Before reporting "ADC missing":

- [ ] Checked Windows path: `C:\Users\leedr\AppData\Roaming\gcloud\application_default_credentials.json`
- [ ] Checked Linux path: `/c/Users/leedr/.config/gcloud/application_default_credentials.json`
- [ ] Verified using BOTH Read tool and Bash tool
- [ ] Tried creating symlink if paths mismatch
- [ ] Set GOOGLE_APPLICATION_CREDENTIALS if needed

## 🚨 Critical Rules for Agents

1. **NEVER assume ADC doesn't exist based on one path check**
2. **ALWAYS check both Windows and Linux paths**
3. **NEVER try to run `gcloud auth application-default login` - it needs a browser**
4. **ALWAYS report the exact paths checked when reporting issues**
5. **UNDERSTAND that Bash and PowerShell see different paths**

## Example: Proper ADC Check for Agents

```python
def ensure_adc_accessible():
    """Ensure ADC is accessible from current context"""
    
    windows_adc = r"C:\Users\leedr\AppData\Roaming\gcloud\application_default_credentials.json"
    linux_adc = "/c/Users/leedr/.config/gcloud/application_default_credentials.json"
    
    # Check if Windows ADC exists
    try:
        with open(windows_adc, 'r') as f:
            print(f"✅ ADC found at Windows path: {windows_adc}")
            
            # If in bash context, create symlink
            if os.environ.get('SHELL', '').endswith('bash'):
                os.makedirs('/c/Users/leedr/.config/gcloud', exist_ok=True)
                if not os.path.exists(linux_adc):
                    os.symlink(windows_adc, linux_adc)
                    print(f"✅ Created symlink at: {linux_adc}")
            return True
    except:
        pass
    
    # Check if Linux ADC exists
    try:
        with open(linux_adc, 'r') as f:
            print(f"✅ ADC found at Linux path: {linux_adc}")
            return True
    except:
        pass
    
    print("❌ ADC not found in either location!")
    print("User must run: gcloud auth application-default login")
    return False
```

## Summary

**The Golden Rule for Agents:**
Always check BOTH paths before declaring ADC missing. The file often exists, just in a different location than where you're looking!

**Remember:**
- Windows tools see: `C:\Users\leedr\AppData\Roaming\gcloud\`
- Bash tools see: `/c/Users/leedr/.config/gcloud/`
- These are DIFFERENT directories!