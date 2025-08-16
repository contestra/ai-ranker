"""
Direct Gemini API adapter using the new Google GenAI client
This provides grounding via the direct API (not Vertex)
"""

from typing import Dict, Any, Optional, List
import time
import os
from google import genai
from google.genai import types

class GeminiDirectAdapter:
    """Adapter for Google GenAI client with direct API backend"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Google GenAI client with API key"""
        if not api_key:
            # Try to get from environment
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                # Try to get from .env file
                try:
                    with open(".env") as f:
                        for line in f:
                            if line.startswith("GOOGLE_API_KEY="):
                                api_key = line.split("=", 1)[1].strip()
                                break
                except:
                    pass
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or .env file")
        
        self.client = genai.Client(api_key=api_key)
    
    async def analyze_with_gemini(
        self,
        prompt: str,
        use_grounding: bool = False,
        model_name: str = "gemini-1.5-pro",
        temperature: float = 0.0,
        seed: int = 42,
        context: str = None,
        top_p: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generate content using direct Gemini API with optional grounding.
        
        Args:
            prompt: The main user prompt (kept naked/unmodified)
            use_grounding: Whether to enable Google Search grounding
            model_name: Model variant to use (e.g., gemini-1.5-pro, gemini-1.5-flash)
            temperature: Temperature for randomness (0.0 for deterministic)
            seed: Seed for reproducibility
            context: Optional ALS context as separate message
            top_p: Top-p sampling parameter
            
        Returns:
            Dict with content, metadata, and timing information
        """
        start_time = time.time()
        
        try:
            # Build conversation messages for ALS support
            messages = []
            
            if context:
                # System instruction for ALS handling
                system_prompt = """Use ambient context only to infer locale and set defaults (language variants, units, currency, regulatory framing, availability).
If no ambient context is provided, treat scope as global.
For definitions/explanations/global overviews, treat scope as global.
For lists/rankings/recommendations, only when candidates are equally suitable, choose examples likely to be available or familiar in the inferred locale, and keep a balanced slate.
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not name countries/regions/cities or use country codes unless explicitly asked.
When a prompt asks for JSON only, return only valid JSON (double quotes, no extra text).
Do not preface with statements about training data or location—produce the answer only."""
                
                # Add system instruction
                messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text=system_prompt)]
                ))
                messages.append(types.Content(
                    role="model",
                    parts=[types.Part(text="Understood.")]
                ))
                
                # Add ALS context
                messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text=context)]
                ))
                messages.append(types.Content(
                    role="model",
                    parts=[types.Part(text="Noted.")]
                ))
            
            # Add the naked user prompt
            messages.append(types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            ))
            
            # Configure generation parameters
            config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                candidate_count=1
            )
            
            # Add seed if provided (for reproducibility)
            if seed is not None:
                config.seed = seed
            
            # Add grounding tool if requested
            # IMPORTANT: Direct API uses google_search_retrieval, not google_search
            if use_grounding:
                config.tools = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                config.tool_config = types.ToolConfig()
            
            # Generate response (server-side tool execution happens automatically)
            response = self.client.models.generate_content(
                model=model_name,  # Direct API doesn't need "models/" prefix
                contents=messages if messages else prompt,  # Use messages for multi-turn, prompt for single
                config=config
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Extract metadata
            result = {
                "content": response.text if hasattr(response, 'text') else str(response),
                "model_version": model_name,
                "temperature": temperature,
                "seed": seed,
                "response_time_ms": response_time,
                "grounded": use_grounding,
                "token_count": {}
            }
            
            # Try to extract grounding metadata if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Get grounding metadata if it exists
                if hasattr(candidate, 'grounding_metadata'):
                    grounding_meta = candidate.grounding_metadata
                    if hasattr(grounding_meta, 'search_entry_point'):
                        result["grounding_metadata"] = {
                            "search_performed": True,
                            "entry_point": str(grounding_meta.search_entry_point)
                        }
                    if hasattr(grounding_meta, 'retrieval_metadata'):
                        result["system_fingerprint"] = str(grounding_meta.retrieval_metadata)
                
                # Get token usage if available
                if hasattr(candidate, 'token_count') and candidate.token_count:
                    tc = candidate.token_count
                    result["token_count"] = {
                        "prompt_tokens": tc.prompt_token_count if hasattr(tc, 'prompt_token_count') else 0,
                        "completion_tokens": tc.candidates_token_count if hasattr(tc, 'candidates_token_count') else 0,
                        "total_tokens": tc.total_token_count if hasattr(tc, 'total_token_count') else 0
                    }
                
                # Get finish reason
                if hasattr(candidate, 'finish_reason'):
                    result["finish_reason"] = str(candidate.finish_reason)
            
            # Get model version from response if available
            if hasattr(response, 'model_version'):
                result["system_fingerprint"] = response.model_version
            
            return result
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            
            error_msg = str(e)
            
            # Check for specific error types
            if "google_search is not supported" in error_msg:
                error_msg = "Grounding configuration error: use google_search_retrieval for direct API"
            elif "404" in error_msg:
                error_msg = f"Model not found: {model_name}"
            elif "403" in error_msg:
                error_msg = "Permission denied - check API key permissions"
            
            return {
                "error": error_msg,
                "content": f"[ERROR] {error_msg}",
                "model_version": model_name,
                "temperature": temperature,
                "seed": seed,
                "response_time_ms": response_time,
                "grounded": use_grounding,
                "token_count": {}
            }