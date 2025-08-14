
# services/provider_probe.py
# Stubbed provider probe for local/dev. Returns deterministic provider_version_key values
# without calling external AI providers. Replace with real adapters in production.
from __future__ import annotations

import os
import hashlib
import datetime as dt
from typing import Any, Dict, Optional, Tuple

# Optional latency simulation (ms)
_SLEEP_MS = int(os.getenv("PROBE_SLEEP_MS", "0"))

def _hash8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

def _sleep():
    if _SLEEP_MS > 0:
        import time
        time.sleep(_SLEEP_MS / 1000.0)

def probe_provider_version(*, provider: str, model_id: str,
                           system_instructions: Optional[str] = None,
                           inference_params: Optional[Dict[str, Any]] = None
                           ) -> Tuple[str, dt.datetime]:
    """Return (provider_version_key, captured_at) for a given provider/model.

    This is a **stub** implementation for dev/test:
      - openai: returns a fake system_fingerprint-like key ("fp_stub_<hash8>")
      - google (Gemini): returns a fake modelVersion ("<model_id>-stub-001")
      - anthropic: returns the model_id (matches our V7 rule)
      - azure-openai: returns "fp_stub_azure_<hash8>"
      - unknown: returns "unknown"

    Set PROBE_SLEEP_MS to simulate latency in milliseconds.
    """
    _sleep()
    p = (provider or "").lower()
    captured_at = dt.datetime.utcnow()

    if p == "openai":
        key = f"fp_stub_{_hash8('openai:' + model_id)}"
        return key, captured_at

    if p == "google":  # Gemini
        # mimic a modelVersion string
        key = f"{model_id}-stub-001"
        return key, captured_at

    if p == "anthropic":
        # Spec: use model id directly
        return model_id, captured_at

    if p == "azure-openai":
        key = f"fp_stub_azure_{_hash8('azure:' + model_id)}"
        return key, captured_at

    # Fallback
    return "unknown", captured_at
