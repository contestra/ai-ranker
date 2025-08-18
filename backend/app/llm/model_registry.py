"""
Model Registry - Single Source of Truth for Model Routing
Prevents misrouting and ensures correct adapter selection
"""

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ModelInfo:
    provider: str              # "openai" | "vertex"
    canonical_id: str          # e.g., "publishers/google/models/gemini-2.5-pro"
    grounding_capable: bool    # supports web tools
    response_api: str          # "sdk_chat" | "responses_http" | "vertex_genai"

# Canonical registry - NEVER route by ad-hoc string checks
REGISTRY = {
    # OpenAI models
    "gpt-5": ModelInfo("openai", "gpt-5", True, "responses_http"),
    "gpt-5-mini": ModelInfo("openai", "gpt-5-mini", True, "responses_http"),
    "gpt-5-nano": ModelInfo("openai", "gpt-5-nano", True, "responses_http"),
    "gpt-4o": ModelInfo("openai", "gpt-4o", False, "sdk_chat"),
    "gpt-4o-mini": ModelInfo("openai", "gpt-4o-mini", False, "sdk_chat"),
    
    # Vertex Gemini models
    "gemini-2.5-pro": ModelInfo("vertex", "gemini-2.5-pro", True, "vertex_genai"),
    "gemini-2.5-flash": ModelInfo("vertex", "gemini-2.5-flash", True, "vertex_genai"),
    "gemini-2.0-flash": ModelInfo("vertex", "gemini-2.0-flash", True, "vertex_genai"),  # We verified it supports grounding
    "gemini-1.5-pro": ModelInfo("vertex", "gemini-1.5-pro", False, "vertex_genai"),
    "gemini-1.5-flash": ModelInfo("vertex", "gemini-1.5-flash", False, "vertex_genai"),
}

# Common aliases and variations
ALIASES = {
    "gemini 2.5 pro": "gemini-2.5-pro",
    "gemini2.5pro": "gemini-2.5-pro",
    "gemini-25-pro": "gemini-2.5-pro",
    "gemini_2_5_pro": "gemini-2.5-pro",
    "gemini 2.5 flash": "gemini-2.5-flash",
    "gemini2.5flash": "gemini-2.5-flash",
    "gemini-25-flash": "gemini-2.5-flash",
    "gemini_2_5_flash": "gemini-2.5-flash",
    "gemini 2.0 flash": "gemini-2.0-flash",
    "gemini2.0flash": "gemini-2.0-flash",
    "gemini-20-flash": "gemini-2.0-flash",
    "gemini_2_0_flash": "gemini-2.0-flash",
    "gpt5": "gpt-5",
    "gpt-5-latest": "gpt-5",
    "gpt5mini": "gpt-5-mini",
    "gpt5nano": "gpt-5-nano",
    "gpt4o": "gpt-4o",
    "gpt-4-o": "gpt-4o",
    "gpt4omini": "gpt-4o-mini",
}

def resolve_model(name: str) -> ModelInfo:
    """
    Resolve a model name to its canonical ModelInfo
    Raises ValueError if model is unknown
    """
    if not name:
        raise ValueError("Model name cannot be empty")
    
    # Normalize the name
    n = name.strip().lower().replace("_", "-").replace("—", "-")
    
    # Check aliases first
    if n in ALIASES:
        n = ALIASES[n]
    
    # Look up in registry
    if n not in REGISTRY:
        raise ValueError(f"Unknown model: {name}. Available models: {list(REGISTRY.keys())}")
    
    return REGISTRY[n]

def is_vertex_model(name: str) -> bool:
    """Quick check if a model should be routed to Vertex"""
    try:
        mi = resolve_model(name)
        return mi.provider == "vertex"
    except ValueError:
        return False

def is_openai_model(name: str) -> bool:
    """Quick check if a model should be routed to OpenAI"""
    try:
        mi = resolve_model(name)
        return mi.provider == "openai"
    except ValueError:
        return False

def supports_grounding(name: str) -> bool:
    """Check if a model supports grounding/web search"""
    try:
        mi = resolve_model(name)
        return mi.grounding_capable
    except ValueError:
        return False