"""
Service layer for LLM execution with proper grounding enforcement.
Uses the new OpenAI adapter with soft-required fallback for GPT-5.
"""

from app.llm.adapters.openai_adapter import run_openai_with_grounding
from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
from openai import OpenAI
from typing import Dict, Any, Optional

_openai = OpenAI()  # uses OPENAI_API_KEY
_vertex = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")

def execute_openai_grounded(
    *, 
    model: str, 
    mode: str, 
    prompt: str, 
    system: Optional[str] = None, 
    als: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wraps the adapter and normalizes the record to your DB schema.
    
    Args:
        model: Model name (e.g., "gpt-5", "gpt-4o")
        mode: "UNGROUNDED"|"PREFERRED"|"REQUIRED"
        prompt: User prompt
        system: Optional system prompt
        als: Optional ALS block
    
    Returns:
        Dict with standardized fields for persistence
    """
    result = run_openai_with_grounding(
        client=_openai,
        model=model,
        mode=mode,          # "UNGROUNDED"|"PREFERRED"|"REQUIRED"
        prompt=prompt,
        system=system,
        als=als,
        provoker=None,      # Uses default provoker for soft-required
        strict_fail=True,   # Fail-closed if REQUIRED yields zero searches
    )

    # Map to persistence schema
    record = {
        "provider": "openai",
        "model_alias": result["model"],
        "requested_mode": result["requested_mode"],
        "tool_choice_sent": result["tool_choice_sent"],
        "tool_call_count": result["tool_call_count"],
        "grounded_effective": result["grounded_effective"],
        "soft_required": result["soft_required"],
        "why_not_grounded": result["why_not_grounded"],
        "status": result["status"],
        "error_code": result["error_code"],
        "answer_text": result["text"],
        # Keep resp in a transient blob if you need to debug; don't store forever
    }
    return record

def execute_vertex_grounded(
    *,
    model: str,
    mode: str,
    prompt: str,
    system: Optional[str] = None,
    als: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute Vertex/Gemini with grounding.
    
    Args:
        model: Model name (e.g., "gemini-2.5-pro")
        mode: "UNGROUNDED"|"PREFERRED"|"REQUIRED"
        prompt: User prompt
        system: Optional system prompt
        als: Optional ALS block
    
    Returns:
        Dict with standardized fields for persistence
    """
    # Build full prompt
    full_prompt = ""
    if system:
        full_prompt += system + "\n\n"
    if als:
        full_prompt += als + "\n\n"
    full_prompt += prompt
    
    # Map mode to use_grounding
    use_grounding = mode in ["PREFERRED", "REQUIRED"]
    
    # Execute with Vertex adapter
    result = _vertex.analyze_with_gemini(
        prompt=full_prompt,
        use_grounding=use_grounding,
        context=None
    )
    
    # Parse result
    grounded_effective = False
    tool_call_count = 0
    why_not_grounded = None
    status = "ok"
    error_code = None
    
    if use_grounding:
        # Check for grounding metadata
        grounding_metadata = result.get("grounding_metadata", {})
        if grounding_metadata:
            # Count search queries
            search_queries = grounding_metadata.get("search_queries", [])
            tool_call_count = len(search_queries)
            grounded_effective = tool_call_count > 0
        
        # Enforce REQUIRED mode
        if mode == "REQUIRED" and not grounded_effective:
            status = "failed"
            why_not_grounded = "no_grounding_metadata"
            error_code = "no_grounding_in_required"
    
    # Map to persistence schema
    record = {
        "provider": "vertex",
        "model_alias": model,
        "requested_mode": mode,
        "tool_choice_sent": "GoogleSearch" if use_grounding else None,
        "tool_call_count": tool_call_count,
        "grounded_effective": grounded_effective,
        "soft_required": False,  # Vertex doesn't need soft-required
        "why_not_grounded": why_not_grounded,
        "status": status,
        "error_code": error_code,
        "answer_text": result.get("response", ""),
    }
    return record