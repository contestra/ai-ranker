#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_entity_probe_v52.py — Enhanced V52 with improvements

Key improvements over V51:
1. Confidence scoring for classifications (0-100)
2. Simplified pipeline - removed claims_location complexity
3. Structured JSON logging for better observability
4. Retry logic at row level with exponential backoff
5. Full response caching (not just web searches)
6. Incremental update mode (--update-only flag)
7. Optimized token usage with simpler initial prompts
8. Better separation of concerns
9. Export to JSON/CSV formats

IMPORTANT: The OpenAI Responses API requires reasoning parameter to be set to 
'low', 'medium', or 'high'. Setting it to 'none' or omitting it causes empty 
responses. V52 defaults to 'low' for mini model and 'medium' for main model.
"""

import os
import re
import json
import csv
import time
import html
import random
import argparse
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

# Google Sheets (optional)
try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

# OpenAI Responses API
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Gemini (optional)
try:
    import google.generativeai as genai
except Exception:
    genai = None

# -------------- Config & constants --------------

VERSION_TAG = "v52"
DEFAULT_SHEET_SLICE = 1600
DEFAULT_CHUNK_SIZE = 300
MIN_OUTPUT_TOKENS = int(os.getenv("V52_MIN_OUTPUT_TOKENS", "32"))
DEFAULT_WORKERS = int(os.getenv("V52_WORKERS", "1"))
USE_WEB_DEFAULT = os.getenv("V52_USE_WEB", "0").lower() in {"1", "true", "yes"}
LOG_DIR = os.getenv("V52_LOG_DIR", "logs")
EXPORT_DIR = os.getenv("V52_EXPORT_DIR", "exports")

# Models (overridable via env)
GPT_MODEL_FAST = os.getenv("GPT_MODEL_FAST", "gpt-5")
GPT_MODEL_MINI = os.getenv("GPT_MODEL_MINI", "gpt-5-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

# Reasoning knobs
REASONING_EFFORT_MAIN = os.getenv("REASONING_EFFORT_MAIN", os.getenv("REASONING_EFFORT", "medium"))
REASONING_EFFORT_MINI = os.getenv("REASONING_EFFORT_MINI", "low")  # Must be low/medium/high, not none

# Label mapping
LABEL_MAP = {
    "OK_STRONG": "KNOWN_STRONG",
    "OK_WEAK": "KNOWN_WEAK",
    "CLARIFY": "UNKNOWN",
    "HALLUCINATION": "HALLUCINATED",
    "BLOCKED": "EMPTY",
}

# Headers for web probe
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

CACHE_PATH = os.getenv("V52_CACHE_PATH", ".v52_cache.json")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds
RETRY_DELAY_MAX = 32.0  # seconds

# -------------- Structured Logger --------------

class StructuredLogger:
    def __init__(self, log_dir: str = LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"v52_run_{timestamp}.jsonl"
        self.lock = threading.Lock()
        
    def log(self, event_type: str, data: Dict[str, Any]):
        """Log a structured event"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data
        }
        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def log_brand_start(self, brand: str, row: int):
        self.log("brand_start", {"brand": brand, "row": row})
    
    def log_brand_complete(self, brand: str, row: int, label: str, confidence: float, tokens: int):
        self.log("brand_complete", {
            "brand": brand, 
            "row": row, 
            "label": label,
            "confidence": confidence,
            "tokens": tokens
        })
    
    def log_error(self, brand: str, row: int, error: str, retry_count: int):
        self.log("error", {
            "brand": brand,
            "row": row,
            "error": error,
            "retry_count": retry_count
        })
    
    def log_summary(self, stats: Dict[str, Any]):
        self.log("run_summary", stats)

# Global logger instance
logger = StructuredLogger()

# -------------- Utilities --------------

def load_cache() -> Dict[str, Any]:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("cache not a dict")
            # Ensure all cache sections exist
            data.setdefault("web", {})
            data.setdefault("model_responses", {})
            data.setdefault("classifications", {})
            return data
    except Exception:
        return {"web": {}, "model_responses": {}, "classifications": {}}


def save_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def jitter_sleep(base: float, factor: float = 0.4) -> None:
    time.sleep(max(0.05, base + random.uniform(-factor * base, factor * base)))


def exponential_backoff(attempt: int) -> float:
    """Calculate delay with exponential backoff"""
    delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
    return delay + random.uniform(0, delay * 0.1)  # Add jitter


def ensure_env_or_exit():
    missing = []
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if gspread is None or Credentials is None:
        print("WARNING: gspread/google-auth not installed; install to enable Sheets I/O.")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("NOTE: GOOGLE_APPLICATION_CREDENTIALS not set; will attempt gspread default (may fail).")
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")


def make_openai_client() -> OpenAI:
    if OpenAI is None:
        raise SystemExit("openai Python SDK not installed. Try: pip install openai")
    timeout = float(os.getenv("OPENAI_TIMEOUT", "30"))
    return OpenAI(timeout=timeout)


def extract_output_text(resp) -> str:
    """Robustly extract text from Responses API response."""
    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    
    # Fallback walk
    try:
        for block in getattr(resp, "output", []) or []:
            if getattr(block, "type", None) == "message":
                for c in getattr(block, "content", []) or []:
                    if getattr(c, "type", None) == "output_text":
                        t = getattr(c, "text", "")
                        if t:
                            return t
    except Exception:
        pass
    return ""


# -------------- Preflight checks --------------

def run_preflight_checks(sheet_url: Optional[str], no_gemini: bool, require_gemini: bool) -> None:
    """Fail fast with actionable errors when keys/permissions are bad."""
    issues = []
    
    # OpenAI check
    try:
        client = make_openai_client()
        r = client.responses.create(
            model=GPT_MODEL_MINI,
            input="ping",
            max_output_tokens=max(16, MIN_OUTPUT_TOKENS),
            reasoning={"effort": "low"}  # Required for Responses API
        )
        _ = extract_output_text(r)
    except Exception as e:
        msg = str(e)
        low = msg.lower()
        if "api key" in low or "invalid api key" in low or "unauthorized" in low or "401" in low:
            issues.append("OpenAI: Invalid or missing OPENAI_API_KEY.")
        else:
            issues.append(f"OpenAI: {type(e).__name__}: {msg.splitlines()[0]}")
    
    # Google Sheets check
    if sheet_url:
        try:
            if gspread is None:
                issues.append("Google Sheets: gspread/google-auth not installed.")
            else:
                creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                client_email = None
                if creds_path:
                    try:
                        with open(creds_path, "r", encoding="utf-8") as f:
                            j = json.load(f)
                            client_email = j.get("client_email")
                    except Exception:
                        pass
                gc = gspread.service_account(filename=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None))
                sh = gc.open_by_url(sheet_url)
                _ = sh.title
        except FileNotFoundError:
            issues.append("Google Sheets: credentials file not found at GOOGLE_APPLICATION_CREDENTIALS.")
        except Exception as e:
            txt = str(e)
            low = txt.lower()
            if "permission" in low or "not have permission" in low:
                extra = f" Share the sheet with your service account email" + (f" ({client_email})" if client_email else "") + "."
                issues.append("Google Sheets: Permission denied." + extra)
            else:
                issues.append(f"Google Sheets: {type(e).__name__}: {txt.splitlines()[0]}")
    
    # Gemini check
    gemini_status = None
    gemini_issue = None
    if genai is None:
        gemini_status = "NOT INSTALLED"
        gemini_issue = "Install google-generativeai (pip install google-generativeai)."
    else:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY_ALT")
        if not key:
            gemini_status = "MISSING KEY"
            gemini_issue = "GOOGLE_API_KEY not set."
        else:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(GEMINI_MODEL)
                r = model.generate_content("ping")
                _ = getattr(r, "text", "")
                gemini_status = "OK"
            except Exception as e:
                gemini_status = "INVALID"
                gemini_issue = f"{type(e).__name__}: {str(e).splitlines()[0]}"
    
    print(f"[V52] Gemini preflight: {gemini_status or 'UNKNOWN'}" + (f" — {gemini_issue}" if gemini_issue else ""))
    if (not no_gemini or require_gemini) and gemini_status in {"MISSING KEY", "INVALID", "NOT INSTALLED"}:
        issues.append("Gemini: " + (gemini_issue or gemini_status))
    
    if issues:
        print("\n[V52] Preflight failed:")
        for it in issues:
            print(" - " + it)
        raise SystemExit(1)
    else:
        print("[V52] Preflight check: OK")


# -------------- Responses helpers --------------

def responses_json_with_retry(
    model: str,
    system: str,
    user: str,
    schema: Dict[str, Any],
    max_output_tokens: int = 800,
    reasoning_effort: Optional[str] = "low",  # Changed from "none" to "low"
    cache_key: Optional[str] = None,
    cache: Optional[Dict[str, Any]] = None,
    lock: Optional[threading.Lock] = None
) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Responses API with retry logic and caching.
    Returns (dict_or_none, total_tokens).
    """
    # Check cache first
    if cache_key and cache and lock:
        with lock:
            if cache_key in cache.get("model_responses", {}):
                cached_result = cache["model_responses"][cache_key]
                return cached_result.get("data"), cached_result.get("tokens", 0)
    
    last_error = None
    total_tokens = 0
    
    for attempt in range(MAX_RETRIES):
        try:
            client = make_openai_client()
            _min = MIN_OUTPUT_TOKENS
            
            schema_str = json.dumps(schema.get("schema", {}), ensure_ascii=False)
            sys_prompt = ((system + "\n\n") if system else "") + (
                "Return ONLY valid JSON (no markdown, no extra prose). "
                "The JSON MUST match this JSON Schema exactly:\n" + schema_str
            )
            
            kwargs = dict(
                model=model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user}]},
                ],
                max_output_tokens=max(_min, int(max_output_tokens)),
            )
            # Always include reasoning with at least 'low' effort for Responses API
            if reasoning_effort and reasoning_effort.lower() in ["low", "medium", "high"]:
                kwargs["reasoning"] = {"effort": reasoning_effort}
            else:
                kwargs["reasoning"] = {"effort": "low"}  # Default to low if invalid/missing
            
            r = client.responses.create(**kwargs)
            
            tokens = 0
            try:
                u = getattr(r, "usage", None)
                if u and getattr(u, "total_tokens", None) is not None:
                    tokens = int(u.total_tokens or 0)
                    total_tokens += tokens
            except Exception:
                pass
            
            txt = extract_output_text(r).strip()
            if not txt:
                raise ValueError("Empty response from API")
            
            # Try to parse JSON
            result = None
            try:
                result = json.loads(txt)
            except Exception:
                # Try to extract JSON from markdown or other formatting
                txt2 = txt.strip().strip("`").strip()
                i, j = txt2.find("{"), txt2.rfind("}")
                if i != -1 and j != -1:
                    try:
                        result = json.loads(txt2[i:j+1])
                    except Exception:
                        pass
            
            # Cache successful result
            if result and cache_key and cache and lock:
                with lock:
                    if "model_responses" not in cache:
                        cache["model_responses"] = {}
                    cache["model_responses"][cache_key] = {
                        "data": result,
                        "tokens": tokens,
                        "timestamp": datetime.now().isoformat()
                    }
            
            return result, total_tokens
            
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = exponential_backoff(attempt)
                logger.log("retry", {
                    "model": model,
                    "attempt": attempt + 1,
                    "error": str(e),
                    "delay": delay
                })
                time.sleep(delay)
            else:
                logger.log("max_retries_exceeded", {
                    "model": model,
                    "error": str(e)
                })
    
    return None, total_tokens


def responses_text_with_retry(
    model: str,
    prompt: str,
    max_output_tokens: int = None,
    reasoning_effort: Optional[str] = "low"  # Changed from "none" to "low"
) -> Tuple[str, int]:
    """Plain text Responses helper with retry logic."""
    if max_output_tokens is None:
        max_output_tokens = MIN_OUTPUT_TOKENS * 20
    
    last_error = None
    total_tokens = 0
    
    for attempt in range(MAX_RETRIES):
        try:
            client = make_openai_client()
            kwargs = dict(
                model=model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                max_output_tokens=int(max_output_tokens),
            )
            # Always include reasoning with at least 'low' effort for Responses API
            if reasoning_effort and reasoning_effort.lower() in ["low", "medium", "high"]:
                kwargs["reasoning"] = {"effort": reasoning_effort}
            else:
                kwargs["reasoning"] = {"effort": "low"}  # Default to low if invalid/missing
            
            r = client.responses.create(**kwargs)
            txt = extract_output_text(r).strip()
            
            tokens = 0
            try:
                u = getattr(r, "usage", None)
                if u and getattr(u, "total_tokens", None) is not None:
                    tokens = int(u.total_tokens or 0)
                    total_tokens += tokens
            except Exception:
                pass
            
            return txt, total_tokens
            
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = exponential_backoff(attempt)
                time.sleep(delay)
    
    return "", total_tokens


# -------------- Brand Information Extraction --------------

def extract_brand_info(
    brand: str,
    web_snippet: Optional[str] = None,
    cache: Dict[str, Any] = None,
    lock: threading.Lock = None
) -> Tuple[Dict[str, Any], int]:
    """
    Extract structured brand information using GPT-5.
    Returns (info_dict, tokens_used).
    """
    # Build optimized prompt
    prompt_lines = [
        f"Extract facts about {brand}.",
        "Rules: Use 'Unknown' if unsure. Be concise and factual.",
        "Focus on what the company does, not marketing language."
    ]
    if web_snippet and not web_snippet.startswith("[web "):
        prompt_lines.append(f"Context: {web_snippet[:200]}")  # Limit snippet size
    
    prompt = "\n".join(prompt_lines)
    
    schema = {
        "name": "brand_info",
        "schema": {
            "type": "object",
            "properties": {
                "what_it_does": {"type": "string"},
                "founders": {"type": "string"},
                "founded_year": {"type": "string"},
                "hq_city": {"type": "string"},
                "hq_country": {"type": "string"},
                "flagship_products": {"type": "string"},
            },
            "required": ["what_it_does", "founders", "founded_year", "hq_city", "hq_country", "flagship_products"],
            "additionalProperties": False,
        },
    }
    
    cache_key = f"extract_{brand}_{web_snippet[:50] if web_snippet else 'no_web'}"
    
    info, tokens = responses_json_with_retry(
        model=GPT_MODEL_FAST,
        system="Extract company information as JSON.",
        user=prompt,
        schema=schema,
        max_output_tokens=400,  # Reduced from 600
        reasoning_effort=REASONING_EFFORT_MAIN,
        cache_key=cache_key,
        cache=cache,
        lock=lock
    )
    
    if not info:
        # Fallback to defaults
        info = {
            "what_it_does": "Unknown",
            "founders": "Unknown",
            "founded_year": "Unknown",
            "hq_city": "Unknown",
            "hq_country": "Unknown",
            "flagship_products": "Unknown",
        }
    
    return info, tokens


# -------------- Classification with Confidence --------------

def classify_with_confidence(
    text: str,
    cache: Dict[str, Any] = None,
    lock: threading.Lock = None
) -> Tuple[str, float, int]:
    """
    Classify text and return (label, confidence, tokens).
    Confidence is 0-100.
    """
    cache_key = f"classify_{text[:100]}"
    
    # Check cache
    if cache and lock:
        with lock:
            if cache_key in cache.get("classifications", {}):
                cached = cache["classifications"][cache_key]
                return cached["label"], cached["confidence"], 0
    
    # Simple prompt for classification
    prompt = (
        "Classify this company description:\n"
        f"{text[:1000]}\n\n"
        "Return ONE code and confidence (0-100):\n"
        "OK_STRONG (specific, verifiable facts) | "
        "OK_WEAK (generic but plausible) | "
        "CLARIFY (admits unknowns) | "
        "HALLUCINATION (likely false) | "
        "BLOCKED (empty/refusal)\n\n"
        "Format: CODE CONFIDENCE"
    )
    
    result, tokens = responses_text_with_retry(
        model=GPT_MODEL_MINI,
        prompt=prompt,
        max_output_tokens=200,  # Need extra tokens as reasoning uses ~64 tokens
        reasoning_effort=REASONING_EFFORT_MINI
    )
    
    # Parse response
    label = "BLOCKED"
    confidence = 50.0
    
    if result:
        parts = result.upper().split()
        for code in ["OK_STRONG", "OK_WEAK", "CLARIFY", "HALLUCINATION", "BLOCKED"]:
            if code in parts:
                label = code
                # Try to find confidence number
                for part in parts:
                    try:
                        conf = float(part)
                        if 0 <= conf <= 100:
                            confidence = conf
                            break
                    except ValueError:
                        continue
                break
    
    mapped_label = LABEL_MAP.get(label, label)
    
    # Cache result
    if cache and lock:
        with lock:
            if "classifications" not in cache:
                cache["classifications"] = {}
            cache["classifications"][cache_key] = {
                "label": mapped_label,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
    
    return mapped_label, confidence, tokens


# -------------- Web search (optional) --------------

def web_browse(query: str, cache: Dict[str, Any], lock: threading.Lock) -> str:
    key = query.strip().lower()
    with lock:
        cached = cache["web"].get(key)
    if cached is not None:
        return cached
    
    base = 0.6
    last_err = "[web error]"
    for attempt in range(4):
        try:
            resp = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers=HTTP_HEADERS,
                timeout=(3.05, 10),
            )
            resp.raise_for_status()
            text = html.unescape(re.sub(r"<[^>]+>", " ", resp.text))
            text = re.sub(r"\s+", " ", text).strip()
            snippet = text[:300]
            with lock:
                cache["web"][key] = snippet
            return snippet
        except requests.exceptions.RequestException as e:
            last_err = f"[web {type(e).__name__}]"
            jitter_sleep(base * (2 ** attempt))
    return last_err


# -------------- Gemini processing --------------

def gemini_answer(brand: str) -> str:
    """Generate a concise brand blurb from Gemini."""
    if genai is None:
        return "[Gemini not installed]"
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY_ALT")
    if not api_key:
        return "[Gemini missing GOOGLE_API_KEY]"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            f"Tell me about the company {brand}. "
            "Respond in brief bullet points: what it does, founders & founding year, "
            "HQ city & country (if known), flagship products/services."
        )
        time.sleep(1 + random.random() * 0.3)
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", "") or ""
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return text[:1600] if text else "[Gemini empty]"
    except Exception as e:
        return f"[Gemini error: {e}]"


# -------------- Process single brand --------------

def process_brand(
    brand: str,
    no_gemini: bool,
    with_web: bool,
    cache: Dict[str, Any],
    lock: threading.Lock,
    update_only: bool = False,
    existing_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a single brand and return all data.
    If update_only is True, only reclassify existing data.
    """
    tokens_used = 0
    
    if update_only and existing_data:
        # Just reclassify existing answer
        oa_answer = existing_data.get("oa_answer", "")
        oa_label, oa_confidence, tok = classify_with_confidence(oa_answer, cache, lock)
        tokens_used += tok
        
        g_ans = existing_data.get("gemini_answer", "")
        if g_ans and g_ans != "-":
            g_label, g_confidence, tok = classify_with_confidence(g_ans, cache, lock)
            tokens_used += tok
        else:
            g_label, g_confidence = "-", 0.0
        
        return {
            "brand": brand,
            "oa_answer": oa_answer,
            "oa_label": oa_label,
            "oa_confidence": oa_confidence,
            "gemini_answer": g_ans,
            "gemini_label": g_label,
            "gemini_confidence": g_confidence,
            "tokens_used": tokens_used,
            "web_used": False
        }
    
    # Full processing
    web_snippet = ""
    web_used = False
    if with_web:
        web_snippet = web_browse(brand, cache, lock)
        web_used = not web_snippet.startswith("[web ")
    
    # Extract brand info
    info, tok = extract_brand_info(brand, web_snippet if web_used else None, cache, lock)
    tokens_used += tok
    
    # Format answer
    oa_answer = (
        f"What it does: {info.get('what_it_does','Unknown')}. "
        f"Founders: {info.get('founders','Unknown')}. "
        f"Founded: {info.get('founded_year','Unknown')}. "
        f"HQ: {info.get('hq_city','Unknown')}, {info.get('hq_country','Unknown')}. "
        f"Products: {info.get('flagship_products','Unknown')}."
    ).strip()
    
    # Classify OpenAI answer
    oa_label, oa_confidence, tok = classify_with_confidence(oa_answer, cache, lock)
    tokens_used += tok
    
    # Adjust label if mostly unknown but has some substance
    if oa_label in ("UNKNOWN", "EMPTY"):
        what = info.get("what_it_does", "").lower()
        if what and what not in {"unknown", "n/a", "none"}:
            oa_label = "KNOWN_WEAK"
            oa_confidence = min(oa_confidence, 40.0)  # Lower confidence
    
    # Gemini processing
    if no_gemini:
        g_ans = "-"
        g_label = "-"
        g_confidence = 0.0
    else:
        g_ans = gemini_answer(brand)
        if g_ans and not g_ans.startswith("["):
            g_label, g_confidence, tok = classify_with_confidence(g_ans, cache, lock)
            tokens_used += tok
        else:
            g_label = LABEL_MAP.get("BLOCKED", "EMPTY")
            g_confidence = 100.0  # High confidence it's blocked
    
    return {
        "brand": brand,
        "oa_answer": oa_answer,
        "oa_label": oa_label,
        "oa_confidence": oa_confidence,
        "gemini_answer": g_ans,
        "gemini_label": g_label,
        "gemini_confidence": g_confidence,
        "tokens_used": tokens_used,
        "web_used": web_used,
        "info": info  # Include structured data
    }


# -------------- Export functions --------------

def export_to_json(results: List[Dict[str, Any]], filename: str):
    """Export results to JSON file."""
    export_dir = Path(EXPORT_DIR)
    export_dir.mkdir(exist_ok=True)
    filepath = export_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Exported JSON to {filepath}")
    return filepath


def export_to_csv(results: List[Dict[str, Any]], filename: str):
    """Export results to CSV file."""
    export_dir = Path(EXPORT_DIR)
    export_dir.mkdir(exist_ok=True)
    filepath = export_dir / filename
    
    if not results:
        return None
    
    # Flatten nested info dict
    rows = []
    for r in results:
        row = {
            "brand": r["brand"],
            "oa_label": r["oa_label"],
            "oa_confidence": r["oa_confidence"],
            "gemini_label": r.get("gemini_label", "-"),
            "gemini_confidence": r.get("gemini_confidence", 0),
            "what_it_does": r.get("info", {}).get("what_it_does", "Unknown"),
            "founders": r.get("info", {}).get("founders", "Unknown"),
            "founded_year": r.get("info", {}).get("founded_year", "Unknown"),
            "hq_city": r.get("info", {}).get("hq_city", "Unknown"),
            "hq_country": r.get("info", {}).get("hq_country", "Unknown"),
            "flagship_products": r.get("info", {}).get("flagship_products", "Unknown"),
            "tokens_used": r.get("tokens_used", 0),
            "web_used": r.get("web_used", False)
        }
        rows.append(row)
    
    with open(filepath, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Exported CSV to {filepath}")
    return filepath


# -------------- Google Sheets I/O --------------

def open_sheet(sheet_url: str, worksheet: Optional[str] = None):
    if gspread is None:
        raise SystemExit("gspread is required. Install with: pip install gspread google-auth")
    gc = gspread.service_account(filename=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None))
    sh = gc.open_by_url(sheet_url)
    ws = sh.worksheet(worksheet) if worksheet else sh.sheet1
    return ws


def read_sheet_data(sheet_url: str, worksheet: Optional[str] = None):
    ws = open_sheet(sheet_url, worksheet)
    brands = ws.col_values(1)  # Column A
    processed_col = ws.col_values(5)  # Column E: version tag
    labels_col = ws.col_values(6)  # Column F: OA label
    
    # For update mode, also read existing answers
    oa_answers = ws.col_values(2) if len(ws.row_values(1)) >= 2 else []
    gemini_answers = ws.col_values(4) if len(ws.row_values(1)) >= 4 else []
    
    return ws, brands, processed_col, labels_col, oa_answers, gemini_answers


# -------------- Main processing function --------------

def process(
    sheet_url: str,
    worksheet: Optional[str],
    start: int,
    limit: Optional[int],
    only_missing: bool,
    chunk_size: int,
    workers: int,
    no_gemini: bool,
    force: bool,
    with_web: bool,
    update_only: bool,
    export_format: Optional[str]
) -> None:
    ensure_env_or_exit()
    cache = load_cache()
    cache_lock = threading.Lock()
    
    # Read sheet data
    ws, brands, processed_col, labels_col, oa_answers, gemini_answers = read_sheet_data(sheet_url, worksheet)
    
    n_rows = len(brands)
    row_start = max(2, start)
    row_end = n_rows if limit is None else min(n_rows, row_start + max(0, limit) - 1)
    
    updates = []
    results = []  # For export
    total_tokens = 0
    rows_done = 0
    rows_skipped = 0
    
    print(f"[V52] Starting: rows {row_start}..{row_end} (total={n_rows})")
    print(f"[V52] Mode: {'UPDATE_ONLY' if update_only else 'FULL'}, Workers: {workers}, Gemini: {'OFF' if no_gemini else 'ON'}, Web: {'ON' if with_web else 'OFF'}")
    
    # Prepare jobs
    jobs = []
    for idx in range(row_start, row_end + 1):
        brand = (brands[idx - 1] or "").strip() if (idx - 1) < len(brands) else ""
        if not brand:
            rows_skipped += 1
            continue
        
        already = (processed_col[idx - 1] or "").strip() if (idx - 1) < len(processed_col) else ""
        
        # Skip logic
        if not update_only and not force and already == VERSION_TAG:
            rows_skipped += 1
            continue
        
        # Prepare existing data for update mode
        existing_data = None
        if update_only:
            existing_data = {
                "oa_answer": oa_answers[idx - 1] if (idx - 1) < len(oa_answers) else "",
                "gemini_answer": gemini_answers[idx - 1] if (idx - 1) < len(gemini_answers) else ""
            }
        
        jobs.append((idx, brand, existing_data))
    
    # Process jobs
    def process_job(job_data):
        idx, brand, existing_data = job_data
        logger.log_brand_start(brand, idx)
        
        try:
            result = process_brand(
                brand=brand,
                no_gemini=no_gemini,
                with_web=with_web,
                cache=cache,
                lock=cache_lock,
                update_only=update_only,
                existing_data=existing_data
            )
            
            logger.log_brand_complete(
                brand=brand,
                row=idx,
                label=result["oa_label"],
                confidence=result["oa_confidence"],
                tokens=result["tokens_used"]
            )
            
            # Prepare update for sheet
            row_vals = [
                result["oa_answer"][:DEFAULT_SHEET_SLICE],  # B
                "-",  # C (Reserved)
                result["gemini_answer"][:DEFAULT_SHEET_SLICE],  # D
                VERSION_TAG,  # E
                result["oa_label"],  # F
                result["gemini_label"],  # G
                str(result["oa_confidence"]),  # H (confidence instead of HQ gate)
                str(result["gemini_confidence"]),  # I (confidence instead of density)
            ]
            
            update = {"range": f"B{idx}:I{idx}", "values": [row_vals]}
            
            # Add row number for export
            result["row"] = idx
            
            return update, result, result["tokens_used"], None
            
        except Exception as e:
            logger.log_error(brand, idx, str(e), MAX_RETRIES)
            update = {"range": f"E{idx}:F{idx}", "values": [[VERSION_TAG, "ERROR"]]}
            return update, None, 0, str(e)
    
    # Execute with or without workers
    if workers <= 1:
        for job in jobs:
            update, result, tokens, error = process_job(job)
            updates.append(update)
            if result:
                results.append(result)
            total_tokens += tokens
            rows_done += 1
            
            if len(updates) >= chunk_size:
                ws.batch_update(updates, value_input_option="RAW")
                updates.clear()
                save_cache(cache)
            
            if rows_done % 25 == 0:
                print(f"[V52] Processed {rows_done}/{len(jobs)} rows...")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_job = {executor.submit(process_job, job): job for job in jobs}
            
            for future in as_completed(future_to_job):
                update, result, tokens, error = future.result()
                updates.append(update)
                if result:
                    results.append(result)
                total_tokens += tokens
                rows_done += 1
                
                if len(updates) >= chunk_size:
                    ws.batch_update(updates, value_input_option="RAW")
                    updates.clear()
                    save_cache(cache)
                
                if rows_done % 25 == 0:
                    print(f"[V52] Processed {rows_done}/{len(jobs)} rows...")
    
    # Final batch write
    if updates:
        ws.batch_update(updates, value_input_option="RAW")
        save_cache(cache)
    
    # Export if requested
    if export_format and results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if export_format == "json":
            export_to_json(results, f"v52_results_{timestamp}.json")
        elif export_format == "csv":
            export_to_csv(results, f"v52_results_{timestamp}.csv")
        elif export_format == "both":
            export_to_json(results, f"v52_results_{timestamp}.json")
            export_to_csv(results, f"v52_results_{timestamp}.csv")
    
    # Log summary
    summary = {
        "rows_processed": rows_done,
        "rows_skipped": rows_skipped,
        "total_tokens": total_tokens,
        "avg_tokens_per_row": total_tokens / rows_done if rows_done > 0 else 0,
        "update_only": update_only,
        "with_web": with_web
    }
    logger.log_summary(summary)
    
    print("\n=== V52 Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"Log file: {logger.log_file}")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Batch Entity Probe V52 (Enhanced)")
    parser.add_argument("--sheet-url", type=str, default=os.getenv("SHEET_URL"), help="Google Sheet URL")
    parser.add_argument("--worksheet", type=str, default=os.getenv("SHEET_WORKSHEET"), help="Worksheet name")
    parser.add_argument("--start", type=int, default=2, help="Start row (1-based)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of rows to process")
    parser.add_argument("--only-missing", action="store_true", help="Skip rows already tagged")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Batch size for writes")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Worker threads")
    parser.add_argument("--no-gemini", action="store_true", help="Disable Gemini")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip API checks")
    parser.add_argument("--require-gemini", action="store_true", help="Fail if Gemini invalid")
    parser.add_argument("--force", action="store_true", help="Re-run already tagged rows")
    parser.add_argument("--with-web", action="store_true", default=USE_WEB_DEFAULT, help="Enable web search")
    parser.add_argument("--update-only", action="store_true", help="Only reclassify existing answers")
    parser.add_argument("--export", choices=["json", "csv", "both"], help="Export format")
    args = parser.parse_args()
    
    if not args.sheet_url:
        raise SystemExit("Provide --sheet-url or set SHEET_URL env var.")
    
    if not args.skip_preflight:
        run_preflight_checks(args.sheet_url, args.no_gemini, args.require_gemini)
    
    process(
        sheet_url=args.sheet_url,
        worksheet=args.worksheet,
        start=args.start,
        limit=args.limit,
        only_missing=args.only_missing,
        chunk_size=args.chunk_size,
        workers=max(1, args.workers),
        no_gemini=bool(args.no_gemini),
        force=bool(args.force),
        with_web=bool(args.with_web),
        update_only=bool(args.update_only),
        export_format=args.export
    )


if __name__ == "__main__":
    main()