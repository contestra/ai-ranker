# conftest.py - Test configuration for Windows Unicode support
import sys
import os

# Fix Windows Unicode output issues
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Set UTF-8 encoding for all tests
os.environ["PYTHONUTF8"] = "1"