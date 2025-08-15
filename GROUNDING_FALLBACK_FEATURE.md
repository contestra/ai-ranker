# Grounding Fallback Feature (Future Enhancement)

**Date**: August 15, 2025  
**Status**: Documented for Future Implementation  
**Current State**: System uses Vertex AI exclusively

## Executive Summary

This document describes a potential future feature for implementing intelligent fallback between Vertex AI and Direct Gemini API with grounding support. This feature was initially implemented but removed to maintain simplicity, as Vertex AI is stable and reliable.

## Why This Might Be Needed (Future Scenarios)

1. **Regional Outages**: If Vertex AI experiences regional issues
2. **Quota Limits**: When hitting Vertex quotas during high-volume testing
3. **Cost Optimization**: Direct API might be cheaper for certain workloads
4. **A/B Testing**: Comparing Vertex vs Direct grounding quality
5. **Disaster Recovery**: Business continuity during GCP issues

## Grounding Policy System Design

### Grounding Modes
```python
from enum import Enum

class GroundingMode(str, Enum):
    REQUIRED = "required"   # Must use grounding, fail if unavailable
    PREFERRED = "preferred"  # Try primary, fallback to equivalent
    OFF = "off"             # No grounding needed
```

### Fallback Rules Matrix

| Mode | Primary Path | Fallback Path | Degradation |
|------|-------------|---------------|-------------|
| REQUIRED | Vertex + GoogleSearch() | None - Fail immediately | Never |
| PREFERRED | Vertex + GoogleSearch() | Direct + GoogleSearchRetrieval() | Never to ungrounded |
| OFF | Direct API or Vertex | Other provider | N/A |

### Key Principle: Semantic Equivalence

**NEVER** silently degrade from grounded to ungrounded. Both paths must provide semantically equivalent grounding:
- **Vertex**: Uses `Tool(google_search=GoogleSearch())` - server-side
- **Direct**: Uses `Tool(google_search_retrieval=GoogleSearchRetrieval())` - also server-side

## Complete Implementation (Removed from Production)

### grounding_policy.py (Full Implementation)
```python
"""
Grounding Policy System - Ensures semantic consistency for grounded requests
"""

from enum import Enum
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
import time
import os

class GroundingMode(str, Enum):
    """Grounding policy modes"""
    REQUIRED = "required"   # Must use grounding, fail if unavailable
    PREFERRED = "preferred"  # Try grounding, fallback to equivalent grounded method
    OFF = "off"             # No grounding, use base model only

class GroundingRoute(str, Enum):
    """Route used for grounding"""
    VERTEX = "vertex"
    DIRECT = "direct"
    NONE = "none"

class GroundingEquivalence(str, Enum):
    """Type of grounding used"""
    SERVER = "server"           # Vertex GoogleSearch (server-side)
    RETRIEVAL = "retrieval"     # Direct GoogleSearchRetrieval (server-side) 
    NONE = "none"              # No grounding

class GroundingAdapter:
    """
    Unified grounding adapter that maintains semantic consistency.
    Never silently degrades from grounded to ungrounded.
    """
    
    def __init__(
        self,
        project: str = "contestra-ai",
        location: str = "europe-west4",
        google_api_key: Optional[str] = None
    ):
        # Remove old service account if present (use ADC for Vertex)
        os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
        
        self.project = project
        self.location = location
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        
        # Cache for capability checks
        self.capabilities = {}
        
    async def generate_with_policy(
        self,
        prompt: str,
        grounding_mode: GroundingMode,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.0,
        seed: Optional[int] = None,
        context: Optional[str] = None,
        top_p: float = 1.0,
        allow_degrade: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate content with grounding policy enforcement.
        
        Returns:
            Tuple of (response_dict, metadata_dict)
            
        Raises:
            RuntimeError if grounding requirements cannot be met
        """
        
        start_time = time.time()
        
        # Build content messages
        contents = self._build_contents(prompt, context)
        
        # Route based on grounding mode
        if grounding_mode == GroundingMode.OFF:
            return await self._run_ungrounded(
                contents, model_name, temperature, seed, top_p, start_time
            )
            
        elif grounding_mode == GroundingMode.REQUIRED:
            return await self._run_grounded_required(
                contents, model_name, temperature, seed, top_p, start_time
            )
            
        elif grounding_mode == GroundingMode.PREFERRED:
            return await self._run_grounded_preferred(
                contents, model_name, temperature, seed, top_p, start_time, allow_degrade
            )
        
        else:
            raise ValueError(f"Unknown grounding mode: {grounding_mode}")
    
    async def _run_grounded_preferred(
        self, contents, model_name, temperature, seed, top_p, start_time, allow_degrade
    ) -> Tuple[Dict, Dict]:
        """Run with preferred grounding - try fallback to equivalent method"""
        
        vertex_error = None
        
        # Try Vertex first (preferred path)
        try:
            client = genai.Client(vertexai=True, project=self.project, location=self.location)
            
            tools = [types.Tool(google_search=types.GoogleSearch())]
            
            response = client.models.generate_content(
                model=self._map_model_for_vertex(model_name),
                contents=contents,
                config=self._build_config(temperature, top_p, seed, tools)
            )
            
            return self._format_response(
                response, model_name, temperature, seed, start_time
            ), {
                "route": GroundingRoute.VERTEX,
                "grounded_effective": True,
                "grounding_equivalence": GroundingEquivalence.SERVER,
                "fallback_reason": None
            }
        except Exception as e:
            vertex_error = str(e)
        
        # Try Direct API with grounding (equivalent method)
        if self.google_api_key:
            try:
                # Direct API client - NOT Vertex
                client = genai.Client(api_key=self.google_api_key)
                
                # Direct API uses google_search_retrieval
                tools = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=self._build_config(temperature, top_p, seed, tools)
                )
                
                return self._format_response(
                    response, model_name, temperature, seed, start_time
                ), {
                    "route": GroundingRoute.DIRECT,
                    "grounded_effective": True,
                    "grounding_equivalence": GroundingEquivalence.RETRIEVAL,
                    "fallback_reason": f"Vertex failed: {vertex_error}"
                }
            except Exception as e:
                direct_error = str(e)
                
                # Both grounded methods failed
                if allow_degrade:
                    # Only degrade if explicitly allowed
                    try:
                        return await self._run_ungrounded(
                            contents, model_name, temperature, seed, top_p, start_time
                        )
                    except Exception as e2:
                        raise RuntimeError(
                            f"All methods failed: vertex={vertex_error}, "
                            f"direct_grounded={direct_error}, ungrounded={str(e2)}"
                        )
                else:
                    # Fail closed - don't degrade semantics
                    raise RuntimeError(
                        f"Grounded generation failed: vertex={vertex_error}, "
                        f"direct={direct_error}"
                    )
        else:
            # No API key for Direct fallback
            raise RuntimeError(
                f"Grounded generation failed, no fallback available: {vertex_error}"
            )
    
    async def check_capabilities(self) -> Dict[str, Dict[str, bool]]:
        """
        Check what capabilities are available for preflight health checks.
        Returns a map of route:model to capabilities.
        """
        capabilities = {}
        
        # Check Vertex
        try:
            client = genai.Client(vertexai=True, project=self.project, location=self.location)
            
            # Test ungrounded
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Say OK",
                config=types.GenerateContentConfig(temperature=0, max_output_tokens=10)
            )
            
            if response.text:
                capabilities[f"vertex:{self.location}:gemini-2.0-flash"] = {
                    "ungrounded": True
                }
            
            # Test grounded
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="What year is it?",
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=10,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            if response.text:
                capabilities[f"vertex:{self.location}:gemini-2.0-flash"]["grounded"] = True
                
        except Exception as e:
            print(f"Vertex capability check failed: {e}")
        
        # Check Direct API
        if self.google_api_key:
            try:
                client = genai.Client(api_key=self.google_api_key)
                
                # Test ungrounded
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents="Say OK",
                    config=types.GenerateContentConfig(temperature=0, max_output_tokens=10)
                )
                
                if response.text:
                    capabilities["direct:global:gemini-1.5-flash"] = {
                        "ungrounded": True
                    }
                
                # Test grounded
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents="What year is it?",
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=10,
                        tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                    )
                )
                
                if response.text:
                    capabilities["direct:global:gemini-1.5-flash"]["grounded"] = True
                    
            except Exception as e:
                print(f"Direct API capability check failed: {e}")
        
        self.capabilities = capabilities
        return capabilities
```

## Metadata Tracking for Analytics

When implemented, every response should include:
```python
{
    "grounding_metadata": {
        "route": "vertex|direct",
        "grounded_effective": true|false,
        "grounding_equivalence": "server|retrieval|none",
        "fallback_reason": "string or null",
        "degraded_semantics": false  # MUST be false unless explicitly allowed
    }
}
```

## BigQuery Schema Extensions

For analytics tracking when this feature is implemented:
```sql
ALTER TABLE `contestra-ai.ai_ranker.prompt_results`
ADD COLUMN grounding_route STRING,  -- 'vertex', 'direct', 'none'
ADD COLUMN grounding_effective BOOL,
ADD COLUMN grounding_equivalence STRING,  -- 'server', 'retrieval', 'none'
ADD COLUMN fallback_reason STRING,
ADD COLUMN degraded_semantics BOOL DEFAULT FALSE;
```

## Testing Requirements

If implementing this feature, these tests are mandatory:

### Unit Tests
```python
def test_required_mode_no_fallback():
    """REQUIRED mode should never fallback"""
    # Vertex fails → Should raise error, not try Direct
    
def test_preferred_mode_equivalent_fallback():
    """PREFERRED mode should only fallback to equivalent grounding"""
    # Vertex fails → Try Direct with grounding
    # Both fail → Raise error (no degradation)
    
def test_never_degrade_semantics():
    """Never silently degrade from grounded to ungrounded"""
    # Unless allow_degrade=True explicitly set
```

### Integration Tests
- Test with Vertex down → Direct grounding works
- Test with both down → Clear error message
- Test metadata correctly tracks route used

## Dashboard Metrics

When implemented, track:
- Fallback rate by region/time
- Success rate by route (Vertex vs Direct)
- Performance comparison between routes
- Cost analysis (Vertex vs Direct)

## Decision Matrix for Implementation

### Implement This Feature If:
- [ ] Vertex has >1% downtime in production
- [ ] Cost difference is >20% between providers
- [ ] Need A/B testing of grounding quality
- [ ] Regulatory requirement for multi-provider redundancy
- [ ] Customer SLA requires 99.99% availability

### Keep Current Simple Implementation If:
- [x] Vertex is stable (current state)
- [x] Single provider meets all requirements
- [x] Simplicity is more valuable than redundancy
- [x] Testing shows consistent results

## Current Production Implementation (Simple)

```python
# Current simplified implementation in langchain_adapter.py
async def analyze_with_gemini(self, prompt: str, use_grounding: bool = False, ...):
    """Uses Vertex AI exclusively - no fallback"""
    
    from app.llm.vertex_genai_adapter import VertexGenAIAdapter
    
    vertex_adapter = VertexGenAIAdapter(
        project="contestra-ai",
        location="europe-west4"
    )
    
    result = await vertex_adapter.analyze_with_gemini(
        prompt=prompt,
        use_grounding=use_grounding,
        model_name=model_name,
        temperature=temperature,
        seed=seed,
        context=context,
        top_p=1.0
    )
    
    return result
```

## Recommendation

**Keep the current simple implementation** unless one of the implementation triggers occurs. The added complexity of fallback logic is not justified when:
1. Vertex AI is stable and reliable
2. ADC authentication is working
3. Results are consistent
4. The fallback adds significant code complexity

## Migration Path (If Needed)

1. **Phase 1**: Monitor Vertex stability for 30 days
2. **Phase 2**: If issues detected, implement capability checking
3. **Phase 3**: Add fallback logic with full metadata tracking
4. **Phase 4**: Dashboard for route performance comparison
5. **Phase 5**: Automated route selection based on metrics

## Contact

For questions about potentially implementing this feature, review the complete implementation code above which was tested and working before removal.