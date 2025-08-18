"""
Grounding mode enforcement and normalization service.
Ensures canonical grounding modes are properly enforced throughout the application.
"""
from typing import Optional, Tuple
from enum import Enum

class CanonicalGroundingMode(Enum):
    """Canonical grounding modes used throughout the system."""
    NOT_GROUNDED = "not_grounded"
    PREFERRED = "preferred"
    ENFORCED = "enforced"

def normalize_grounding_mode(mode: Optional[str]) -> str:
    """
    Normalize any grounding mode value to canonical format.
    
    Args:
        mode: Raw grounding mode value from frontend/API
        
    Returns:
        Canonical grounding mode value
    """
    if not mode:
        return CanonicalGroundingMode.NOT_GROUNDED.value
    
    mode_lower = str(mode).strip().lower()
    
    # Map legacy/variant values to canonical
    legacy_map = {
        # Not grounded variants
        "off": CanonicalGroundingMode.NOT_GROUNDED.value,
        "none": CanonicalGroundingMode.NOT_GROUNDED.value,
        "ungrounded": CanonicalGroundingMode.NOT_GROUNDED.value,
        "model knowledge only": CanonicalGroundingMode.NOT_GROUNDED.value,
        "model_only": CanonicalGroundingMode.NOT_GROUNDED.value,
        "not_grounded": CanonicalGroundingMode.NOT_GROUNDED.value,
        
        # Preferred variants
        "web": CanonicalGroundingMode.PREFERRED.value,
        "grounded": CanonicalGroundingMode.PREFERRED.value,
        "grounded (web search)": CanonicalGroundingMode.PREFERRED.value,
        "web_search": CanonicalGroundingMode.PREFERRED.value,
        "auto": CanonicalGroundingMode.PREFERRED.value,
        "preferred": CanonicalGroundingMode.PREFERRED.value,
        
        # Enforced variants
        "required": CanonicalGroundingMode.ENFORCED.value,
        "enforced": CanonicalGroundingMode.ENFORCED.value,
        "grounded (required)": CanonicalGroundingMode.ENFORCED.value,
        "mandatory": CanonicalGroundingMode.ENFORCED.value
    }
    
    return legacy_map.get(mode_lower, CanonicalGroundingMode.NOT_GROUNDED.value)

def should_use_grounding(mode: str) -> bool:
    """
    Determine if grounding should be used based on canonical mode.
    
    Args:
        mode: Canonical grounding mode
        
    Returns:
        True if grounding should be attempted
    """
    canonical = normalize_grounding_mode(mode)
    return canonical in [
        CanonicalGroundingMode.PREFERRED.value,
        CanonicalGroundingMode.ENFORCED.value
    ]

def is_grounding_enforced(mode: str) -> bool:
    """
    Determine if grounding is mandatory (must fail if not available).
    
    Args:
        mode: Canonical grounding mode
        
    Returns:
        True if grounding is mandatory
    """
    canonical = normalize_grounding_mode(mode)
    return canonical == CanonicalGroundingMode.ENFORCED.value

def validate_grounding_result(
    mode: str,
    grounded_effective: bool,
    provider: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate if grounding result meets requirements.
    
    Args:
        mode: Canonical grounding mode
        grounded_effective: Whether grounding actually occurred
        provider: Model provider (openai/vertex)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    canonical = normalize_grounding_mode(mode)
    
    # Not grounded mode - grounding should not occur
    if canonical == CanonicalGroundingMode.NOT_GROUNDED.value:
        if grounded_effective:
            return False, "Grounding occurred when it should not have"
        return True, None
    
    # Preferred mode - grounding is optional
    if canonical == CanonicalGroundingMode.PREFERRED.value:
        # For Vertex/Gemini, model decides automatically
        if provider == "vertex":
            return True, None  # Always valid for Vertex in preferred mode
        # For OpenAI, we attempt but don't require
        return True, None
    
    # Enforced mode - grounding must occur
    if canonical == CanonicalGroundingMode.ENFORCED.value:
        # Note: Vertex doesn't support true enforcement (model always decides)
        if provider == "vertex":
            if not grounded_effective:
                return False, "Vertex model chose not to use grounding (app-level enforcement failed)"
            return True, None
        
        # OpenAI should enforce grounding
        if not grounded_effective:
            return False, "Grounding was required but did not occur"
        return True, None
    
    return True, None

def get_display_label(mode: str, provider: str) -> str:
    """
    Get user-friendly display label for grounding mode.
    
    Args:
        mode: Canonical grounding mode
        provider: Model provider (openai/vertex)
        
    Returns:
        Display label string
    """
    canonical = normalize_grounding_mode(mode)
    
    if canonical == CanonicalGroundingMode.NOT_GROUNDED.value:
        return "No Grounding"
    
    if canonical == CanonicalGroundingMode.PREFERRED.value:
        if provider == "vertex":
            return "Web Search (Model Decides)"
        return "Web Search (Auto)"
    
    if canonical == CanonicalGroundingMode.ENFORCED.value:
        if provider == "vertex":
            return "Web Search (App-Enforced)"
        return "Web Search (Required)"
    
    return mode  # Fallback to raw value