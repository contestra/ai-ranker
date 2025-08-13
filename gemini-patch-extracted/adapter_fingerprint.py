from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FingerprintInfo:
    fingerprint: Optional[str]
    fingerprint_type: Optional[str]
    extras: Dict[str, Any]


def extract_model_fingerprint(provider: str, response_metadata: Optional[Dict[str, Any]]) -> FingerprintInfo:
    """
    Provider-agnostic fingerprint extractor.

    Args:
        provider: "openai" or "gemini" (case-insensitive; other values passthrough None).
        response_metadata: dict-like metadata from the LLM response. For LangChain, this is
            typically available on AIMessage.response_metadata.

    Returns:
        FingerprintInfo with:
          - fingerprint: str | None    -> store into your `system_fingerprint` column
          - fingerprint_type: str | None  -> e.g. 'openai.system_fingerprint' or 'gemini.modelVersion'
          - extras: dict -> additional provider-specific details to merge into your metadata JSON
                           (includes 'gemini_model_version' and 'gemini_response_id' for Gemini).
    """
    md = dict(response_metadata or {})
    p = (provider or "").strip().lower()

    # Default payload for unknown/unsupported providers
    out = FingerprintInfo(
        fingerprint=None,
        fingerprint_type=None,
        extras={},
    )

    if p == "openai":
        # OpenAI provides 'system_fingerprint' when available.
        fp = md.get("system_fingerprint") or md.get("systemFingerprint")
        out.fingerprint = fp
        out.fingerprint_type = "openai.system_fingerprint"

        # Capture top-level id if present (useful parity with Gemini responseId).
        if md.get("id"):
            out.extras["openai_response_id"] = md["id"]

    elif p == "gemini":
        # Gemini exposes modelVersion and responseId in response metadata.
        model_version = (
            md.get("modelVersion")
            or md.get("model_version")
            or md.get("model")       # sometimes includes a fully-qualified name
            or md.get("model_name")
        )
        response_id = md.get("responseId") or md.get("response_id")

        out.fingerprint = model_version
        out.fingerprint_type = "gemini.modelVersion"
        out.extras["gemini_model_version"] = model_version
        if response_id:
            out.extras["gemini_response_id"] = response_id

    return out


def build_run_record(
    *,
    provider: str,
    model_alias: str,
    prompt_text: str,
    completion_text: str,
    response_metadata: Optional[Dict[str, Any]],
    usage_metadata: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    seed: Optional[int] = None,
    existing_metadata_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compose a normalized run record dict ready to insert into your DB.
    - Stores provider-specific fingerprint in a common `system_fingerprint` field.
    - Merges provider-specific extras (e.g., Gemini responseId/modelVersion) into metadata JSON.
    """
    fp = extract_model_fingerprint(provider=provider, response_metadata=response_metadata)
    meta = dict(existing_metadata_json or {})
    if response_metadata:
        meta.update(response_metadata)
    # merge extras last so they're easily discoverable at top-level of the metadata blob
    meta.update(fp.extras)
    if usage_metadata:
        meta["usage"] = usage_metadata

    record = {
        "provider": provider,
        "model": model_alias,
        "prompt": prompt_text,
        "completion": completion_text,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "seed": seed,
        "system_fingerprint": fp.fingerprint,
        "fingerprint_type": fp.fingerprint_type,
        "metadata": meta,
    }
    return record