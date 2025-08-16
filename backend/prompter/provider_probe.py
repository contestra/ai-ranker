# backend/prompter/provider_probe.py
"""
Provider probe for extracting version fingerprints from LLM responses.
Integrates with existing LangChain adapter.
"""

import os
import time
import hashlib
from typing import Optional, Tuple
from datetime import datetime, timezone

from app.llm.langchain_adapter import LangChainAdapter, _extract_model_fingerprint


def _hash8(s: str) -> str:
    """Generate 8-character hash for fake fingerprints."""
    return hashlib.sha256(s.encode()).hexdigest()[:8]


async def probe_langchain(
    provider: str,
    model_id: str,
    adapter: Optional[LangChainAdapter] = None
) -> Tuple[Optional[str], datetime]:
    """
    Probe a provider using existing LangChain adapter.
    
    Returns:
        (provider_version_key, captured_at)
    """
    captured_at = datetime.now(timezone.utc)
    
    # Use fake probe in dev mode or when probe is disabled
    if os.getenv("PROMPTER_PROBE_DISABLED", "false").lower() == "true":
        # When probe is disabled, return None (not fake response)
        return None, captured_at
    
    # Use provided adapter or create new one
    if adapter is None:
        adapter = LangChainAdapter()
    
    try:
        # Simple probe prompt
        prompt = "Return only: OK"
        
        if provider == "openai":
            result = await adapter.analyze_with_gpt4(
                prompt=prompt,
                model_name=model_id,
                temperature=0.0
            )
        elif provider == "google" or provider == "gemini":
            result = await adapter.analyze_with_gemini(
                prompt=prompt,
                model_name=model_id,
                temperature=0.0
            )
        elif provider == "anthropic":
            # Use the generic generate method for Anthropic
            result = await adapter.generate(
                vendor="anthropic",
                prompt=prompt,
                temperature=0.0,
                max_tokens=10
            )
        else:
            return None, captured_at
        
        # Extract fingerprint from result
        fingerprint = result.get("system_fingerprint")
        if fingerprint:
            return fingerprint, captured_at
        
        # Fallback to metadata extraction if needed
        if "raw" in result or "metadata" in result:
            metadata = result.get("raw", result.get("metadata", {}))
            fp_info = _extract_model_fingerprint(provider, metadata)
            return fp_info["fingerprint"], captured_at
        
        return None, captured_at
        
    except Exception as e:
        print(f"[WARNING] Provider probe failed for {provider}/{model_id}: {e}")
        return None, captured_at


def _fake_probe_response(provider: str, model_id: str) -> Optional[str]:
    """
    Generate fake provider version key for development.
    Matches the format from prompter_router_min_v3.py
    """
    # Optional sleep for testing
    sleep_ms = int(os.getenv("PROBE_SLEEP_MS", "0"))
    if sleep_ms > 0:
        time.sleep(sleep_ms / 1000.0)
    
    if provider == "openai":
        return f"fp_stub_{_hash8('openai:' + model_id)}"
    elif provider in ["google", "gemini"]:
        return f"{model_id}-stub-001"
    elif provider == "anthropic":
        return f"claude-{_hash8('anthropic:' + model_id)}"
    
    return None


# Alias for backward compatibility
probe = probe_langchain