"""
Centralized canonical JSON generation for consistency.
Used by both API and backfill scripts.
"""

import hashlib
from typing import Dict, Any, Tuple, Optional

try:
    # Try to use orjson for deterministic serialization
    import orjson
    HAS_ORJSON = True
except ImportError:
    # Fallback to standard json
    import json
    HAS_ORJSON = False

def canonicalize(obj: Dict[str, Any]) -> Tuple[str, str]:
    """
    Create deterministic canonical JSON and SHA256 hash.
    
    Args:
        obj: Dictionary to canonicalize (must have sorted keys already)
        
    Returns:
        Tuple of (json_string, sha256_hash)
    """
    if HAS_ORJSON:
        # Use orjson for deterministic output
        json_bytes = orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
        json_str = json_bytes.decode('utf-8')
        hash_value = hashlib.sha256(json_bytes).hexdigest()
    else:
        # Fallback to standard json
        json_str = json.dumps(obj, sort_keys=True, separators=(',', ':'))
        hash_value = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    return json_str, hash_value

def build_canonical_object(
    provider: str,
    model: str,
    prompt_text: str,
    countries: list,
    grounding_modes: list,
    system_temperature: float = 0.0,
    system_seed: int = 42,
    system_top_p: float = 1.0,
    max_output_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build the canonical object for hashing.
    
    Only includes fields that affect model output.
    """
    # Determine max tokens if not provided
    if max_output_tokens is None:
        max_output_tokens = 2000 if "gpt-5" in model.lower() else 8192
    
    # Sort countries and modes for determinism
    countries = sorted(countries) if countries else ["NONE"]
    grounding_modes = sorted(grounding_modes) if grounding_modes else ["not_grounded"]
    
    # ALS configuration based on countries
    als_config = {
        "mode": "off" if countries == ["NONE"] else "implicit",
        "hash": "als_v3_2025-08"
    }
    
    # Grounding binding note
    if provider == "openai":
        grounding_note = "openai:web_search auto/required"
    else:
        grounding_note = "vertex:google_search pass-1; two-step for JSON"
    
    # Build canonical object - sorted keys for determinism
    canonical = {
        "als": als_config,
        "countries": countries,
        "grounding_binding": grounding_note,
        "grounding_modes": grounding_modes,
        "model": model,
        "prompt_text": prompt_text.strip(),
        "provider": provider,
        "response_format": "text",
        "system": {
            "max_output_tokens": max_output_tokens,
            "seed": system_seed,
            "temperature": system_temperature,
            "top_p": system_top_p
        }
    }
    
    return canonical