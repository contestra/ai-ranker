# backend/prompter/utils_prompting.py
"""
Canonicalization utilities for prompt deduplication.
"""

import hashlib
import json
from typing import Any, Optional

from sqlalchemy.orm import Session


def canonicalize(raw_config: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a minimal, sorted dictionary for hashing.
    Strips whitespace, normalizes keys, removes null values.
    """
    def _clean(obj):
        if isinstance(obj, dict):
            return {
                k.strip().lower(): _clean(v)
                for k, v in sorted(obj.items())
                if v is not None and k.strip()
            }
        elif isinstance(obj, list):
            return [_clean(item) for item in obj]
        elif isinstance(obj, str):
            return obj.strip()
        else:
            return obj
    
    return _clean(raw_config)


def calc_config_hash(config: dict[str, Any]) -> str:
    """
    Generate SHA256 hash of canonicalized config.
    Returns hex digest for database storage.
    """
    canonical = canonicalize(config)
    config_str = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(config_str.encode('utf-8')).hexdigest()


def is_sqlite(db: Session) -> bool:
    """
    Legacy function - always returns False as SQLite is no longer supported.
    Kept for backward compatibility during transition.
    """
    return False


def infer_provider(model_id: str) -> Optional[str]:
    """
    Infer provider from model ID patterns.
    
    Returns:
        'openai', 'google', 'anthropic', or None
    """
    model_lower = model_id.lower()
    
    # OpenAI patterns
    if any(p in model_lower for p in [
        'gpt-3', 'gpt-4', 'gpt-5', 
        'o1', 'o3', 'o4', 'omni',
        'davinci', 'curie', 'babbage', 'ada',
        'text-embedding', 'whisper', 'dall-e'
    ]):
        return 'openai'
    
    # Google/Gemini patterns
    if any(p in model_lower for p in [
        'gemini', 'bison', 'gecko', 'palm'
    ]):
        return 'google'
    
    # Anthropic patterns
    if any(p in model_lower for p in [
        'claude', 'anthropic'
    ]):
        return 'anthropic'
    
    return None