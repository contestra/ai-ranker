# -*- coding: utf-8 -*-
"""
OpenAI Responses adapter with soft-required fallback for GPT-5.

- REQUIRED on GPT-5 => auto + provoker + fail-closed if no web_search_call
- REQUIRED on other models => tool_choice="required"
- PREFERRED => tool_choice="auto"
- UNGROUNDED => no tools

Returns a dict you can persist directly to Postgres/BigQuery.
"""

from __future__ import annotations
from typing import Optional, Literal, Dict, Any, List
from openai import OpenAI
import re
import time
import hashlib
import os
from datetime import date

GroundingMode = Literal["UNGROUNDED", "PREFERRED", "REQUIRED"]
ErrorCode = Literal[
    "no_tool_call_in_required",
    "no_tool_call_in_soft_required", 
    "force_tools_unsupported",
    "api_error_4xx",
    "api_error_5xx",
    "timeout"
]

# Broader regex to catch gpt-5, gpt-5o, gpt-5.1, gpt-5-mini, etc.
_GPT5_ALIAS_RE = re.compile(r"^gpt-5", re.I)

def _is_gpt5(model: str) -> bool:
    return bool(_GPT5_ALIAS_RE.search(model or ""))

def _build_messages(system: Optional[str], als: Optional[str], prompt: str, provoker: Optional[str]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system.strip()})
    if als:
        msgs.append({"role": "user", "content": als.strip()})
    # append a gentle "provoker" line when provided (for soft-required on GPT-5)
    content = prompt if not provoker else f"{prompt.rstrip()}\n\n{provoker.strip()}"
    msgs.append({"role": "user", "content": content})
    return msgs

def _today_iso() -> str:
    return date.today().isoformat()

def _default_provoker() -> str:
    # short, neutral; nudges search without over-constraining
    # Can be overridden via OPENAI_PROVOKER env var
    custom = os.environ.get("OPENAI_PROVOKER")
    if custom:
        return custom.strip()
    return (
        f"As of {_today_iso()}, include a citation to an official source "
        f"(e.g., government or standards body) with a working link."
    )

def _hash_provoker(provoker: str) -> str:
    """Hash the provoker for telemetry"""
    return hashlib.sha256(provoker.encode()).hexdigest()[:8]

def _extract_output(resp: Any) -> List[Any]:
    """
    Robustly extract 'output' list from the Responses API result, tolerating SDK/dict shapes.
    """
    if hasattr(resp, "output") and isinstance(getattr(resp, "output"), list):
        return resp.output  # type: ignore[attr-defined]
    if isinstance(resp, dict):
        out = resp.get("output")
        return out if isinstance(out, list) else []
    return []

def _collect_text_and_search_calls(output_items: List[Any]) -> Dict[str, Any]:
    texts: List[str] = []
    search_calls: List[Any] = []
    citations: List[Dict[str, Any]] = []

    for o in output_items:
        typ = getattr(o, "type", None) or (isinstance(o, dict) and o.get("type"))
        
        # Only count successful web search calls
        if typ == "web_search_call":
            status = getattr(o, "status", None) or (isinstance(o, dict) and o.get("status"))
            if status in (None, "ok", "success", "succeeded"):
                search_calls.append(o)
            continue
            
        if typ == "message":
            content = getattr(o, "content", None) or (isinstance(o, dict) and o.get("content")) or []
            # content is a list of blocks; pick output_text blocks
            for c in content:
                ctype = getattr(c, "type", None) or (isinstance(c, dict) and c.get("type"))
                if ctype == "output_text":
                    txt = getattr(c, "text", None) or (isinstance(c, dict) and c.get("text"))
                    if txt:
                        texts.append(txt)
                elif ctype in ("citation", "link", "web_reference"):
                    citations.append(c)

    return {
        "texts": texts,
        "tool_call_count": len(search_calls),
        "citations": citations,
    }

def run_openai_with_grounding(
    client: OpenAI,
    *,
    model: str,
    mode: GroundingMode,
    prompt: str,
    system: Optional[str] = None,
    als: Optional[str] = None,
    provoker: Optional[str] = None,
    strict_fail: bool = True,
    seed: int = 42,
    temperature: float = 0.0,
    top_p: float = 1.0,
) -> Dict[str, Any]:
    """
    Executes an OpenAI Responses call with grounding behavior per mode and model.

    Returns:
        dict with fields:
          - status: "ok"|"failed"
          - model, requested_mode, model_used
          - soft_required: bool
          - tool_choice_sent: "required"|"auto"|None
          - tool_call_count: int
          - grounded_effective: bool
          - why_not_grounded: Optional[str]
          - error_code: Optional[ErrorCode]
          - text: str
          - latency_ms: int
          - system_fingerprint: Optional[str]
          - citations_count: int
          - enforcement_mode: "hard"|"soft"|"none"
          - enforcement_passed: bool
          - meta: Dict with additional telemetry
          - raw: Any (original response; redact before permanent storage if needed)
    """
    soft_required = False
    tools = None
    tool_choice = None
    tool_choice_sent = None
    enforcement_mode = "none"
    enforcement_passed = True

    # Decide tool policy
    if mode == "UNGROUNDED":
        # No tools at all
        pass
    elif mode == "PREFERRED":
        tools = [{"type": "web_search"}]
        tool_choice = "auto"
    else:  # REQUIRED
        tools = [{"type": "web_search"}]
        if _is_gpt5(model):
            # GPT-5: cannot force; fall back to soft-required
            tool_choice = "auto"
            soft_required = True
            enforcement_mode = "soft"
        else:
            tool_choice = "required"
            enforcement_mode = "hard"

    tool_choice_sent = tool_choice
    final_provoker = None
    provoker_hash = None
    if soft_required:
        final_provoker = provoker.strip() if provoker else _default_provoker()
        provoker_hash = _hash_provoker(final_provoker)

    # Build request
    msgs = _build_messages(system=system, als=als, prompt=prompt, provoker=final_provoker)
    
    # Start timing
    t0 = time.perf_counter()
    
    try:
        # Use temperature=1.0 for GPT-5 models (requirement)
        actual_temp = 1.0 if _is_gpt5(model) else temperature
        
        resp = client.responses.create(
            model=model,
            input=msgs,
            tools=tools,
            tool_choice=tool_choice,
            seed=seed,
            temperature=actual_temp,
            top_p=top_p,
        )
        
        # Calculate latency
        latency_ms = int((time.perf_counter() - t0) * 1000)
        
        # Extract metadata
        system_fingerprint = getattr(resp, "system_fingerprint", None) or (isinstance(resp, dict) and resp.get("system_fingerprint"))
        model_used = getattr(resp, "model", None) or (isinstance(resp, dict) and resp.get("model")) or model
        
        output_items = _extract_output(resp)
        parsed = _collect_text_and_search_calls(output_items)
        texts: List[str] = parsed["texts"]
        tool_call_count: int = parsed["tool_call_count"]
        citations = parsed["citations"]
        citations_count = len(citations)
        
        # Grounding outcomes
        grounded_effective = tool_call_count > 0
        status = "ok"
        why_not_grounded = None
        error_code = None
        
        if mode == "REQUIRED":
            if tool_call_count == 0:
                enforcement_passed = False
                if soft_required:
                    # GPT-5 "soft required": still enforce fail-closed if we didn't observe a search
                    status = "failed" if strict_fail else "ok"
                    why_not_grounded = "tool_forcing_unsupported_on_gpt5"
                    error_code = "no_tool_call_in_soft_required"
                else:
                    # Non-GPT-5: strict required; if no tool call, mark failed
                    status = "failed"
                    why_not_grounded = "no_tool_call_in_required"
                    error_code = "no_tool_call_in_required"
        
        # Final text fallback (rare)
        if not texts:
            fallback = getattr(resp, "output_text", None) or (isinstance(resp, dict) and resp.get("output_text"))
            if fallback:
                texts.append(fallback)
        
    except Exception as e:
        # Error handling
        latency_ms = int((time.perf_counter() - t0) * 1000)
        
        # Classify error
        error_msg = str(e)
        if "400" in error_msg or "Bad Request" in error_msg:
            error_code = "api_error_4xx"
        elif "500" in error_msg or "503" in error_msg:
            error_code = "api_error_5xx"
        elif "timeout" in error_msg.lower():
            error_code = "timeout"
        else:
            error_code = "api_error_4xx"
        
        return {
            "status": "failed",
            "model": model,
            "model_used": model,
            "requested_mode": mode,
            "soft_required": soft_required,
            "tool_choice_sent": tool_choice_sent,
            "tool_call_count": 0,
            "grounded_effective": False,
            "why_not_grounded": error_msg[:200],
            "error_code": error_code,
            "text": "",
            "latency_ms": latency_ms,
            "system_fingerprint": None,
            "citations_count": 0,
            "enforcement_mode": enforcement_mode,
            "enforcement_passed": False,
            "meta": {
                "seed": seed,
                "temperature": temperature,
                "top_p": top_p,
                "error": error_msg,
            },
            "raw": None,
        }

    return {
        "status": status,
        "model": model,
        "model_used": model_used,
        "requested_mode": mode,
        "soft_required": soft_required,
        "tool_choice_sent": tool_choice_sent,
        "tool_call_count": tool_call_count,
        "grounded_effective": grounded_effective,
        "why_not_grounded": why_not_grounded,
        "error_code": error_code,
        "text": "\n\n".join([t for t in texts if t]).strip(),
        "latency_ms": latency_ms,
        "system_fingerprint": system_fingerprint,
        "citations_count": citations_count,
        "enforcement_mode": enforcement_mode,
        "enforcement_passed": enforcement_passed,
        "meta": {
            "seed": seed,
            "temperature": actual_temp,
            "top_p": top_p,
            "provoker_hash": provoker_hash,
        },
        "raw": resp,  # consider redacting before persistence
    }