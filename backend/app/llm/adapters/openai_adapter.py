# -*- coding: utf-8 -*-
"""
OpenAI Responses adapter with soft-required fallback for GPT-5.

- REQUIRED on GPT-5 => auto + provoker + fail-closed if no web_search_call
- REQUIRED on other models => tool_choice="required"
- PREFERRED => tool_choice="auto"
- UNGROUNDED => no tools

Now also:
- Auto-raise max_output_tokens when tools are present on GPT-5
- Log reasoning-token burn from usage.output_tokens_details.reasoning_tokens
"""

from __future__ import annotations
from typing import Optional, Literal, Dict, Any, List, Tuple
from openai import OpenAI
import re, time, os, hashlib

GroundingMode = Literal["UNGROUNDED", "PREFERRED", "REQUIRED"]
_GPT5_ALIAS_RE = re.compile(r"^gpt-5", re.I)   # broadened matcher

# NEW: minimal search-first directive for GPT-5 + tools
_SEARCH_FIRST_DIRECTIVE = (
    "Policy for stable facts: When a hosted web_search tool is available, "
    "call web_search BEFORE answering. Keep internal deliberation minimal. "
    "After the tool call, answer concisely (max 2 sentences) and include one official citation."
)

def _is_gpt5(model: str) -> bool:
    return bool(_GPT5_ALIAS_RE.search(model or ""))

def _today_iso() -> str:
    from datetime import date
    return date.today().isoformat()

def _default_provoker() -> str:
    return (f"As of {_today_iso()}, include a citation to an official source "
            f"(e.g., government or standards body) with a working link.")

def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def _build_messages(system: Optional[str], als: Optional[str], prompt: str, provoker: Optional[str]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system.strip()})
    if als:
        msgs.append({"role": "user", "content": als.strip()})
    content = prompt if not provoker else f"{prompt.rstrip()}\n\n{provoker.strip()}"
    msgs.append({"role": "user", "content": content})
    return msgs

def _extract_output(resp: Any) -> List[Any]:
    if hasattr(resp, "output") and isinstance(getattr(resp, "output"), list):
        return resp.output  # SDK object
    if isinstance(resp, dict):
        out = resp.get("output")
        return out if isinstance(out, list) else []
    return []

def _collect_text_and_search_calls(output_items: List[Any]) -> Dict[str, Any]:
    texts: List[str] = []
    search_calls: List[Any] = []
    for o in output_items:
        typ = getattr(o, "type", None) or (isinstance(o, dict) and o.get("type"))
        if typ == "web_search_call":
            status = getattr(o, "status", None) or (isinstance(o, dict) and o.get("status"))
            if status in (None, "ok", "success", "succeeded"):
                search_calls.append(o)
            continue
        if typ == "message":
            content = getattr(o, "content", None) or (isinstance(o, dict) and o.get("content")) or []
            for c in content:
                ctype = getattr(c, "type", None) or (isinstance(c, dict) and c.get("type"))
                if ctype == "output_text":
                    txt = getattr(c, "text", None) or (isinstance(c, dict) and c.get("text"))
                    if txt:
                        texts.append(txt)
    return {"texts": texts, "tool_call_count": len(search_calls)}

# NEW: robust usage extractor (captures reasoning token burn)
def _extract_usage(resp: Any) -> Dict[str, Optional[int]]:
    # tolerate SDK object or dict
    usage = getattr(resp, "usage", None)
    if usage is None and isinstance(resp, dict):
        usage = resp.get("usage", None)

    def _get(obj, *keys):
        if obj is None:
            return None
        # allow attribute or dict access
        for k in keys:
            if hasattr(obj, k):
                obj = getattr(obj, k)
            elif isinstance(obj, dict):
                obj = obj.get(k, None)
            else:
                return None
            if obj is None:
                return None
        return obj

    input_tokens  = _get(usage, "input_tokens")
    output_tokens = _get(usage, "output_tokens")
    total_tokens  = _get(usage, "total_tokens")
    # Reasoning tokens can live under output_tokens_details.reasoning_tokens
    reasoning_tokens = _get(usage, "output_tokens_details", "reasoning_tokens")

    return {
        "usage_input_tokens": input_tokens,
        "usage_output_tokens": output_tokens,
        "usage_total_tokens": total_tokens,
        "usage_reasoning_tokens": reasoning_tokens,
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
    # NEW: caller may override; otherwise we auto-raise for GPT-5 + tools
    max_output_tokens: Optional[int] = None,
    # Optional: keep reasoning low for tool runs (reduce burn)
    reasoning_effort_for_gpt5_tools: Optional[str] = "low",
) -> Dict[str, Any]:

    # ---- Request policy (NO mode downgrades) ----
    tools, tool_choice, soft_required = None, None, False
    enforcement_mode = "none"
    is_gpt5 = _is_gpt5(model)
    wants_tools = mode in ("PREFERRED", "REQUIRED")

    if mode == "UNGROUNDED":
        pass
    elif mode == "PREFERRED":
        tools = [{"type": "web_search"}]
        tool_choice, enforcement_mode = "auto", "none"
    else:  # REQUIRED
        tools = [{"type": "web_search"}]
        if is_gpt5:
            tool_choice, soft_required, enforcement_mode = "auto", True, "soft"
        else:
            tool_choice, enforcement_mode = "required", "hard"

    # ---- Auto-raise output cap for GPT-5 + tools ----
    # env override if you want: OPENAI_GPT5_TOOLS_MAX_OUTPUT_TOKENS=768
    default_cap = int(os.getenv("OPENAI_GPT5_TOOLS_MAX_OUTPUT_TOKENS", "1536"))  # More headroom
    effective_max_tokens = max_output_tokens
    if wants_tools and is_gpt5 and effective_max_tokens is None:
        effective_max_tokens = default_cap

    # CHANGE: don't append a provoker for GPT-5; instead strengthen the SYSTEM
    system_final = (system or "").strip()
    provoker_used = None
    
    if is_gpt5 and wants_tools:
        # Add search-first directive to system message for GPT-5
        system_prefix = _SEARCH_FIRST_DIRECTIVE
        system_final = (system_prefix + ("\n\n" + system_final if system_final else "")).strip()
        # No user-level provoker for GPT-5
    elif soft_required:
        # Non-GPT-5 models still use provoker if soft-required
        provoker_used = (provoker or _default_provoker()).strip()

    msgs = _build_messages(system=system_final, als=als, prompt=prompt, provoker=provoker_used)

    # ---- Call API ----
    def _call() -> Tuple[Any, int]:
        t0 = time.perf_counter()
        kwargs: Dict[str, Any] = dict(
            model=model,
            input=msgs,
            tools=tools,
            tool_choice=tool_choice,
        )
        # GPT-5 DOES NOT support temperature/top_p parameters - they cause 400 errors
        # DO NOT add them for GPT-5 models
        if effective_max_tokens is not None:
            kwargs["max_output_tokens"] = effective_max_tokens
        if is_gpt5 and wants_tools and reasoning_effort_for_gpt5_tools:
            kwargs["reasoning"] = {"effort": reasoning_effort_for_gpt5_tools}
        resp = client.responses.create(**kwargs)
        lat_ms = int((time.perf_counter() - t0) * 1000)
        return resp, lat_ms

    resp, latency_ms = _call()
    output_items = _extract_output(resp)
    usage_stats = _extract_usage(resp)  # NEW
    parsed = _collect_text_and_search_calls(output_items)
    texts, tool_call_count = parsed["texts"], parsed["tool_call_count"]

    had_message = bool(texts)
    budget_starved = (not had_message) and any(
        ((getattr(o, "type", None) or (isinstance(o, dict) and o.get("type"))) == "reasoning")
        for o in output_items
    )

    grounded_effective = tool_call_count > 0
    status, why_not_grounded, error_code = "ok", None, None
    enforcement_passed = True  # Default to true, set to false when enforcement fails

    # ---- Enforce invariants ----
    if mode == "UNGROUNDED" and tool_call_count > 0:
        status, error_code = "failed", "tool_used_in_ungrounded"
        enforcement_passed = False
    elif mode == "REQUIRED" and tool_call_count == 0:
        status = "failed" if strict_fail else "ok"
        error_code = "no_tool_call_in_soft_required" if soft_required else "no_tool_call_in_required"
        why_not_grounded = "tool_forcing_unsupported_on_gpt5" if soft_required else "no_tool_call_in_required"
        enforcement_passed = False
    elif wants_tools and not had_message:
        # No final answer (often a budget starvation symptom)
        status, error_code = "failed", "no_message_output"
        enforcement_passed = False
    
    # Explicit enforcement check
    if mode == "REQUIRED":
        enforcement_passed = tool_call_count > 0
    elif mode == "UNGROUNDED":
        enforcement_passed = tool_call_count == 0

    return {
        "status": status,
        "model": model,
        "requested_mode": mode,
        "enforcement_mode": enforcement_mode,             # "hard" | "soft" | "none"
        "enforcement_passed": enforcement_passed,          # NEW: explicit enforcement check
        "soft_required": soft_required,
        "tool_choice_sent": tool_choice,
        "tool_call_count": tool_call_count,
        "grounded_effective": grounded_effective,
        "why_not_grounded": why_not_grounded,
        "error_code": error_code,
        "latency_ms": latency_ms,
        "provoker_hash": _hash_text(provoker_used) if provoker_used else None,
        # NEW: usage / burn telemetry
        **usage_stats,
        "budget_starved": budget_starved,
        "effective_max_output_tokens": effective_max_tokens,
        "text": "\n\n".join([t for t in texts if t]).strip(),
        "raw": resp,  # redact before long-term storage if needed
    }