from typing import List, Dict, Any, Optional
import asyncio
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import LangChainTracer
from langsmith import Client
from app.config import settings
import numpy as np
import time
import json
import re

# Import Google AI tools for grounding support
try:
    from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
    GOOGLE_GROUNDING_AVAILABLE = True
except ImportError:
    GOOGLE_GROUNDING_AVAILABLE = False
    print("[WARNING] Google AI grounding tools not available - will use prompt-based grounding")

def _extract_model_fingerprint(provider: str, response_metadata: dict) -> dict:
    """
    Extract model fingerprint from provider response metadata.
    
    Returns:
      {
        "fingerprint": str | None,     # stored into system_fingerprint column
        "fingerprint_type": str | None,# e.g., 'openai.system_fingerprint' or 'gemini.modelVersion'
        "extras": dict                 # extra fields to merge into metadata JSON
      }
    """
    md = response_metadata or {}
    out = {"fingerprint": None, "fingerprint_type": None, "extras": {}}

    if provider == "openai":
        fp = md.get("system_fingerprint") or md.get("systemFingerprint")
        out.update({
            "fingerprint": fp,
            "fingerprint_type": "openai.system_fingerprint",
        })

    elif provider == "gemini" or provider == "google":
        # LangChain wrappers may surface either camelCase or snake_case
        # In LangChain, the model_name field contains the model version
        model_version = (
            md.get("modelVersion")
            or md.get("model_version")
            or md.get("model_name")      # LangChain uses model_name for Gemini
            or md.get("model")          # sometimes 'models/gemini-2.5-pro-...' includes version
        )
        response_id = md.get("responseId") or md.get("response_id")

        out.update({
            "fingerprint": model_version,
            "fingerprint_type": "gemini.modelVersion",
            "extras": {
                "gemini_model_version": model_version,
                "gemini_response_id": response_id,
            },
        })

    return out

class LangChainAdapter:
    def __init__(self):
        self.callbacks = []
        if settings.langchain_api_key:
            self.callbacks.append(LangChainTracer(
                project_name=settings.langchain_project,
                client=Client(api_key=settings.langchain_api_key)
            ))
        
        self.models = {
            "openai": ChatOpenAI(
                model="gpt-4o",  # Using GPT-4o as all GPT-5 models return empty responses
                temperature=0.3,  # Lower temperature for more consistent results
                api_key=settings.openai_api_key
            ),
            "google": ChatGoogleGenerativeAI(
                model="gemini-2.5-pro",
                temperature=0.1,
                google_api_key=settings.google_api_key
            ),
            "anthropic": ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.1,
                api_key=settings.anthropic_api_key
            )
        }
        
        self.embeddings = {
            "openai": OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            ),
            "google": GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=settings.google_api_key
            )
        }
    
    async def generate(
        self,
        vendor: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        model = self.models.get(vendor)
        if not model:
            raise ValueError(f"Unknown vendor: {vendor}")
        
        # Don't override temperature for OpenAI models that require specific values
        if vendor != "openai":
            model.temperature = temperature
        
        # Set max_tokens appropriately for each vendor
        if vendor == "google":
            # For Gemini, add seed support via model_kwargs if provided
            if seed is not None:
                if not hasattr(model, 'model_kwargs'):
                    model.model_kwargs = {}
                # Gemini uses generation_config in model_kwargs
                if 'generation_config' not in model.model_kwargs:
                    model.model_kwargs['generation_config'] = {}
                model.model_kwargs['generation_config']['seed'] = seed
        else:
            # GPT-4 and other models use max_tokens
            model.max_tokens = max_tokens
        
        messages = []
        if system_prompt:
            if vendor == "anthropic":
                messages.append(SystemMessage(content=system_prompt))
            else:
                prompt = f"{system_prompt}\n\n{prompt}"
        
        messages.append(HumanMessage(content=prompt))
        
        if grounded and vendor == "openai":
            model.model_kwargs = {"response_format": {"type": "json_object"}}
        
        # Prepare invoke kwargs based on vendor
        invoke_kwargs = {}
        if vendor == "openai" and seed is not None:
            invoke_kwargs["seed"] = seed
        
        response = await model.ainvoke(
            messages,
            config={"callbacks": self.callbacks},
            **invoke_kwargs
        )
        
        # Debug logging for GPT-5 (disabled due to Windows encoding issues)
        # if vendor == "openai":
        #     print(f"DEBUG GPT-5 response type: {type(response)}")
        #     print(f"DEBUG GPT-5 response content: {response.content if hasattr(response, 'content') else 'NO CONTENT ATTR'}")
        #     print(f"DEBUG GPT-5 response metadata: {response.response_metadata if hasattr(response, 'response_metadata') else 'NO METADATA'}")
        
        # Extract model fingerprint based on vendor
        result = {
            "text": response.content if hasattr(response, 'content') else str(response),
            "tokens": response.response_metadata.get("token_usage", {}).get("total_tokens") if hasattr(response, 'response_metadata') else None,
            "raw": response.response_metadata if hasattr(response, 'response_metadata') else {}
        }
        
        # Add fingerprint information
        if hasattr(response, 'response_metadata'):
            fp_info = _extract_model_fingerprint(provider=vendor, response_metadata=response.response_metadata)
            result["system_fingerprint"] = fp_info["fingerprint"]
            result["fingerprint_type"] = fp_info["fingerprint_type"]
            if fp_info["extras"]:
                result["metadata"] = fp_info["extras"]
        
        return result
    
    async def generate_stream(
        self,
        vendor: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ):
        model = self.models.get(vendor)
        if not model:
            raise ValueError(f"Unknown vendor: {vendor}")
        
        # Don't override temperature for OpenAI models that require specific values
        if vendor != "openai":
            model.temperature = temperature
        
        # Only set max_tokens for models that support it
        if vendor != "google":
            model.max_tokens = max_tokens
        
        messages = [HumanMessage(content=prompt)]
        
        async for chunk in model.astream(
            messages,
            config={"callbacks": self.callbacks}
        ):
            if chunk.content:
                yield chunk.content
    
    async def get_embedding(self, vendor: str, text: str) -> List[float]:
        embeddings_model = self.embeddings.get(vendor)
        if not embeddings_model:
            if vendor == "anthropic":
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()
                return [float(int(c, 16)) / 15.0 for c in text_hash * 48][:1536]
            raise ValueError(f"No embeddings available for vendor: {vendor}")
        
        embedding = await embeddings_model.aembed_query(text)
        return embedding
    
    def normalize(self, vec: List[float]) -> np.ndarray:
        vec_array = np.array(vec)
        mag = np.linalg.norm(vec_array)
        return vec_array / mag if mag > 0 else vec_array
    
    def google_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        return float(np.dot(self.normalize(vec_a), self.normalize(vec_b)))
    
    async def analyze_with_gemini(self, prompt: str, use_grounding: bool = False, model_name: str = "gemini-1.5-pro", 
                                  temperature: float = 0.1, seed: int = None, context: str = None, top_p: float = 1.0) -> Dict[str, Any]:
        """Use Gemini via Vertex AI with fallback to direct API for local development
        
        Uses Vertex AI for production (Fly.io with WEF), falls back to direct API for local dev.
        
        Args:
            prompt: The main user prompt (kept naked/unmodified)
            use_grounding: Whether to enable web search via API tools
            model_name: Model variant to use
            temperature: Temperature for randomness
            seed: Seed for reproducibility
            context: Optional context/evidence pack as separate message
            top_p: Top-p for nucleus sampling
        """
        # Try Vertex AI first (works in production with WEF)
        from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
        
        try:
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
                top_p=top_p
            )
            
            print(f"[DEBUG] Vertex succeeded, returning result")
            return result
            
        except Exception as e:
            print(f"[DEBUG] Vertex failed with error: {str(e)}")
            
            # Check if direct API fallback is allowed
            allow_direct = settings.allow_gemini_direct
            
            # NEVER allow direct API for grounded requests
            if use_grounding:
                print(f"[ERROR] Vertex auth failed and grounding requested - cannot use direct API fallback")
                raise Exception(f"Vertex authentication required for grounded requests: {str(e)}")
            
            # Only fall back if explicitly allowed and ungrounded
            if allow_direct and not use_grounding:
                print(f"[WARNING] Vertex auth failed - using DIRECT GEMINI API (ungrounded only, limited features)")
                print(f"[WARNING] This is a diagnostic fallback - set up ADC for proper functionality")
                
                # Use direct Gemini API with API key
                from app.llm.gemini_direct_adapter import GeminiDirectAdapter
                
                try:
                    direct_adapter = GeminiDirectAdapter(api_key=settings.google_api_key)
                    result = await direct_adapter.analyze_with_gemini(
                        prompt=prompt,
                        use_grounding=use_grounding,
                        model_name=model_name,
                        temperature=temperature,
                        seed=seed,
                        context=context
                    )
                    # Mark as fallback for analytics tracking
                    result["transport"] = "gemini_direct"
                    result["api_used"] = "gemini_direct_fallback"
                    result["fallback_reason"] = "vertex_auth_failed"
                    result["warning"] = "Using limited direct API - no grounding parity"
                    print(f"[METRICS] Gemini Direct API fallback used - ungrounded only")
                    return result
                    
                except Exception as fallback_e:
                    # Both failed
                    return {
                        "content": f"[ERROR] Both Vertex and direct API failed: {str(fallback_e)}",
                        "error": "both_apis_failed",
                        "model_version": model_name,
                        "response_time_ms": 0,
                        "vertex_error": str(e),
                        "direct_error": str(fallback_e)
                    }
            else:
                # Non-auth error, don't fallback
                return {
                    "content": f"[ERROR] Vertex AI error: {str(e)}",
                    "error": "vertex_error",
                    "model_version": model_name,
                    "response_time_ms": 0,
                    "message": "Vertex AI error (not auth-related)"
                }
    
    async def analyze_with_gpt4(self, prompt: str, model_name: str = "gpt-4o", 
                                temperature: float = 0.1, seed: int = None, context: str = None,
                                use_grounding: bool = False) -> Dict[str, Any]:
        """Use GPT-5/GPT-4o models with REAL grounding support via tools
        
        Args:
            prompt: The main user prompt (kept naked/unmodified)
            model_name: Model variant to use
            temperature: Temperature for randomness
            seed: Seed for reproducibility
            context: Optional context/evidence pack as separate message
            use_grounding: Enable web search via tools (ACTUALLY WORKS NOW!)
        """
        import time
        start_time = time.time()
        
        # If grounding is requested, use the OpenAI RESPONSES API (the correct one!)
        if use_grounding:
            from app.llm.openai_responses_adapter import OpenAIResponsesAdapter
            responses_adapter = OpenAIResponsesAdapter(api_key=settings.openai_api_key)
            
            # Use the Responses API for REAL grounded requests with web search
            result = await responses_adapter.analyze_with_responses(
                prompt=prompt,
                model_name=model_name,
                use_grounding=True,
                temperature=temperature,
                seed=seed,
                context=context
            )
            
            # Add a note about which API was used
            if result.get('api_used') == 'responses':
                result['grounding_note'] = 'Using OpenAI Responses API with native web search'
            elif result.get('api_used') == 'chat_completions_fallback':
                result['grounding_note'] = 'Responses API unavailable, fell back to Chat Completions (no web search)'
            
            return result
        
        # Original implementation for non-grounded requests
        # Retry logic for empty responses
        max_retries = 3
        retry_delay = 2  # seconds
        
        # Create a new model instance with the requested model name
        # GPT-5 models require temperature=1.0
        actual_temp = 1.0 if 'gpt-5' in model_name.lower() else temperature
        
        # GPT-5 uses max_completion_tokens instead of max_tokens
        if 'gpt-5' in model_name.lower():
            model = ChatOpenAI(
                model=model_name,
                temperature=actual_temp,
                api_key=settings.openai_api_key,
                model_kwargs={"max_completion_tokens": 4000}  # Increased for complex reasoning queries
            )
        else:
            model = ChatOpenAI(
                model=model_name,
                temperature=actual_temp,
                api_key=settings.openai_api_key,
                max_tokens=2000  # Standard parameter for other models
            )
        
        # OpenAI supports seed parameter for reproducibility
        invoke_kwargs = {"seed": seed} if seed is not None else {}
        
        # Build messages array with proper separation
        messages = []
        
        # Only add ALS-specific system prompt when context is provided
        if context:
            # System prompt that allows silent locale adoption while preventing explicit mentions
            # CRITICAL: DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
            
            # OLD PROMPT (commented out for easy rollback):
            # system_prompt = """Answer the user's question directly and naturally.
# You may use any ambient context provided only to infer locale and set defaults (language variants, units, currency, regulatory framing).
# Do not mention, cite, or acknowledge the ambient context or any location inference.
# Do not state or imply country/region/city names unless the user explicitly asks.
# Do not preface with anything about training data or location. Produce the answer only."""
            
            # NEW PROMPT (with country codes ban, JSON handling, balanced localization):
            system_prompt = """Use ambient context only to infer locale and set defaults (language variants, units, currency, regulatory framing, availability). If no ambient context is provided, treat scope as global.
For definitions/explanations/global overviews, treat scope as global.
For lists/rankings/recommendations, only when candidates are equally suitable, choose examples likely to be available or familiar in the inferred locale, and keep a balanced slate.
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not name countries/regions/cities or use country codes unless explicitly asked.
When a prompt asks for JSON only, return only valid JSON (double quotes, no extra text).
Do not preface with statements about training data or location—produce the answer only."""
            messages.append(SystemMessage(content=system_prompt))
            
            # Add context FIRST (before the actual question)
            # This makes it feel more like ambient system state
            messages.append(HumanMessage(content=context))
        
        # User prompt (naked/unmodified)
        messages.append(HumanMessage(content=prompt))
        
        # Add timeout for model calls
        import asyncio
        # GPT-5 needs longer timeout
        timeout_seconds = 60.0 if 'gpt-5' in model_name.lower() else 30.0
        
        # Retry loop for empty responses
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    model.ainvoke(
                        messages,
                        config={"callbacks": self.callbacks},
                        **invoke_kwargs
                    ),
                    timeout=timeout_seconds
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                # Check if response is empty
                content = response.content if hasattr(response, 'content') else str(response)
                # Skip debug printing to avoid encoding issues with Turkish/special characters
                if not content or len(content.strip()) == 0:
                    print(f"[WARNING] {model_name} returned empty response on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Final attempt failed, return error response
                        return {
                            "content": f"[ERROR] {model_name} returned empty response after multiple retries.",
                            "system_fingerprint": None,
                            "model_version": model_name,
                            "temperature": temperature,
                            "seed": seed,
                            "response_time_ms": response_time,
                            "token_count": {},
                            "error": "empty_response",
                            "retry_attempts": max_retries
                        }
                
                # Successful response - extract metadata
                metadata = {}
                if hasattr(response, 'response_metadata'):
                    metadata = response.response_metadata or {}
                
                # Extract fingerprint (system_fingerprint for OpenAI)
                fp_info = _extract_model_fingerprint(provider="openai", response_metadata=metadata)
                
                # Extract finish_reason and safety info
                finish_reason = metadata.get('finish_reason')
                if not finish_reason and 'choices' in metadata:
                    # Try to get from first choice
                    choices = metadata.get('choices', [])
                    if choices and len(choices) > 0:
                        finish_reason = choices[0].get('finish_reason')
                
                result = {
                    "content": content,
                    "system_fingerprint": fp_info["fingerprint"],  # Now stores system_fingerprint for OpenAI
                    "model_version": model_name,
                    "temperature": temperature,
                    "seed": seed,
                    "response_time_ms": response_time,
                    "token_count": {},
                    "metadata": fp_info["extras"] if fp_info["extras"] else {},  # Store any extra metadata
                    "finish_reason": finish_reason,
                    "content_filtered": finish_reason == "content_filter" or (finish_reason == "length" and len(content.strip()) == 0)
                }
                
                # Get token usage if available
                if 'token_usage' in metadata:
                    result["token_count"] = metadata['token_usage']
                elif 'usage' in metadata:
                    result["token_count"] = metadata['usage']
                
                return result
                
            except asyncio.TimeoutError:
                print(f"[WARNING] {model_name} timed out after {timeout_seconds} seconds on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # Final attempt failed
                    return {
                        "content": f"[ERROR] {model_name} timed out after {timeout_seconds} seconds.",
                        "error": f"{model_name} timed out",
                        "model_version": model_name,
                        "response_time_ms": int((time.time() - start_time) * 1000),
                        "token_count": {},
                        "retry_attempts": max_retries
                    }
            except Exception as e:
                print(f"[ERROR] {model_name} API error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # Final attempt failed
                    return {
                        "content": f"[ERROR] {model_name} API error: {str(e)}",
                        "system_fingerprint": None,
                        "model_version": model_name,
                        "temperature": temperature,
                        "seed": seed,
                        "response_time_ms": int((time.time() - start_time) * 1000),
                        "token_count": {},
                        "error": str(e),
                        "retry_attempts": max_retries
                    }
        
        # This should never be reached, but just in case
        return {
            "content": f"[ERROR] Unexpected error with {model_name}",
            "model_version": model_name,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "token_count": {}
        }