"""
Vertex GenAI adapter for Gemini models
Production-grade implementation with grounding and structured outputs
Following ChatGPT's reference architecture
"""

import os
import json
import time
import logging
import re
from typing import Dict, Any, Optional, List
import google.auth
from google import genai
from google.genai.types import (
    GenerateContentConfig, Tool, GoogleSearch, Schema, Type, HttpOptions
)
from .types import RunRequest, RunResult, GroundingMode

# Add LangSmith tracing
try:
    from langsmith.run_trees import RunTree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)

# URL regex for citation normalization
URL_RE = re.compile(r'https?://\S+')

def _gget(obj: Any, names: List[str], default=None):
    """Get attr or key from obj trying several name variants (attr or dict)."""
    if obj is None:
        return default
    for n in names:
        # dict-style
        if isinstance(obj, dict) and n in obj:
            return obj[n]
        # attr-style (Vertex SDK objects)
        if hasattr(obj, n):
            try:
                return getattr(obj, n)
            except Exception:
                pass
    return default

class VertexGenAIAdapter:
    """
    Production adapter for Google's Vertex AI Gemini models
    Supports grounding via GoogleSearch and structured JSON outputs
    """
    
    def __init__(self, project: Optional[str] = None, location: Optional[str] = None):
        """
        Initialize Vertex client
        
        Args:
            project: GCP project ID (defaults to VERTEX_PROJECT env or 'contestra-ai')
            location: Vertex region (defaults to VERTEX_LOCATION env or 'europe-west4')
        """
        # Use environment variables with sensible defaults
        self.project = project or os.getenv("VERTEX_PROJECT", "contestra-ai")
        self.location = location or os.getenv("VERTEX_LOCATION", "europe-west4")
        
        # Check ADC project matches configured project
        try:
            _, adc_project = google.auth.default()
            if adc_project and adc_project != self.project:
                logger.warning(f"ADC project {adc_project} != configured project {self.project}")
        except Exception as e:
            logger.debug(f"Could not check ADC project: {e}")
        
        # Initialize client with v1 API for better grounding support
        self.client = genai.Client(
            http_options=HttpOptions(api_version="v1"),
            vertexai=True, 
            project=self.project, 
            location=self.location
        )
        logger.info(f"Initialized Vertex adapter: project={self.project}, location={self.location}, api_version=v1")
    
    @staticmethod
    def _strip_code_fences(s: str) -> str:
        """Remove markdown code fences and preamble if present"""
        if not s: 
            return s
        
        import re
        # Check if there's a code fence anywhere in the text
        if "```" in s:
            # Extract JSON from markdown code block
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', s, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no fences, return cleaned text
        return s.strip()
    
    
    @staticmethod
    def extract_text(resp) -> str:
        """
        Robustly extract text from Vertex response
        Handles various response structures across SDK versions
        """
        # Try candidates[].content.parts[].text
        try:
            if hasattr(resp, 'candidates') and resp.candidates:
                parts = resp.candidates[0].content.parts
                return "".join(getattr(p, "text", "") or "" for p in parts).strip()
        except Exception:
            pass

        # Try plain text field
        try:
            if hasattr(resp, 'text'):
                return resp.text.strip()
        except Exception:
            pass

        # Try json_text for structured responses
        try:
            if hasattr(resp, 'json_text'):
                return resp.json_text.strip()
        except Exception:
            pass

        # Last resort - stringify
        return str(resp)
    
    @staticmethod
    def extract_grounding_metadata(resp) -> dict:
        """
        Extract grounding metadata from response
        Handles various attribute names across SDK versions
        """
        # Primary path
        try:
            if hasattr(resp, 'candidates') and resp.candidates:
                gm = getattr(resp.candidates[0], 'grounding_metadata', None)
                if gm:
                    return gm
        except Exception:
            pass

        # Try alternate attribute names
        for name in ("groundingMetadata", "grounding_meta", "grounding"):
            try:
                if hasattr(resp, 'candidates') and resp.candidates:
                    gm = getattr(resp.candidates[0], name, None)
                    if gm:
                        return gm
            except Exception:
                pass
        
        return {}
    
    @staticmethod
    def _citations_from_chunks(chunks) -> List[Dict[str, Any]]:
        """Build citations exclusively from grounding chunks (dedup by URI)"""
        seen = set()
        cites = []
        for ch in (chunks or []):
            # attr → dict fallbacks
            web = getattr(ch, "web", None) if hasattr(ch, "web") else None
            uri = getattr(web, "uri", None) if web else None
            title = getattr(web, "title", None) if web and hasattr(web, "title") else None
            
            if not uri and isinstance(ch, dict):
                uri = (_gget(ch, ["uri", "sourceUrl"]) or 
                       _gget(_gget(ch, ["web", "source"], {}), ["uri"]))
                title = title or _gget(_gget(ch, ["web", "source"], {}), ["title"])
            
            if uri and uri not in seen:
                seen.add(uri)
                cites.append({
                    "uri": uri, 
                    "title": title or "No title", 
                    "source": "web_search"
                })
        return cites
    
    @staticmethod
    def _assert_vertex_shape(signals: Dict[str, Any]) -> None:
        """Assert that grounding signals have the correct shape - blocks string leak regressions"""
        assert isinstance(signals["citations"], list), f"citations must be list, got {type(signals['citations'])}"
        assert all(isinstance(c, dict) for c in signals["citations"]), "All citations must be dicts"
        assert isinstance(signals["grounded"], bool), f"grounded must be bool, got {type(signals['grounded'])}"
        assert isinstance(signals["tool_calls"], int), f"tool_calls must be int, got {type(signals['tool_calls'])}"
    
    @classmethod
    def _vertex_grounding_signals(cls, resp) -> Dict[str, Any]:
        """
        Extract grounding signals from Vertex response (handles camelCase/snake_case).
        Builds citations EXCLUSIVELY from grounding_chunks, never from gm.citations.
        Returns:
          {
            "grounded": bool,
            "tool_calls": int,
            "citations": list[dict],  # Built from chunks only
            "queries": list[str],
            "grounding_sources": list[dict],  # Same as citations
          }
        """
        grounded = False
        tool_calls = 0
        citations: List[Dict[str, Any]] = []
        queries: List[str] = []
        
        try:
            # Get candidate and grounding metadata
            cand = resp.candidates[0] if getattr(resp, "candidates", None) else None
            gm = _gget(cand, ["grounding_metadata", "groundingMetadata"], default=None)
            
            if gm:
                # Get queries (handles both camelCase and snake_case)
                queries = _gget(gm, ["web_search_queries", "webSearchQueries"], default=[]) or []
                
                # Get chunks (handles both camelCase and snake_case)
                chunks = _gget(gm, ["grounding_chunks", "groundingChunks"], default=[]) or []
                
                # Build citations EXCLUSIVELY from chunks - single source of truth
                citations = cls._citations_from_chunks(chunks)
                
                # Log what we found for debugging
                logger.debug(f"Vertex grounding: queries={len(queries)}, chunks={len(chunks)}, "
                           f"citations={len(citations)}")
                
                # Evidence of grounding: chunks OR queries
                grounded = bool(citations or queries)
                
                # Tool count: prefer queries count, else 1 if grounded
                tool_calls = len(queries) if queries else (1 if grounded else 0)
            else:
                logger.debug("No grounding_metadata found in Vertex response")
            
        except Exception as e:
            # Never raise here; return safe defaults and let caller decide
            logger.warning(f"Failed to extract grounding signals: {e}")
        
        # Return normalized data - citations are guaranteed to be list[dict]
        return {
            "grounded": grounded,
            "tool_calls": tool_calls,
            "citations": citations,  # list[dict] built from chunks only
            "queries": queries,
            "grounding_sources": citations,  # Keep same reference for compatibility
        }
    
    @staticmethod
    def _assert_grounding_capable(model_name: str):
        """Ensure model supports grounding"""
        # Accept both short and full publisher paths
        if "/" in model_name:
            short_name = model_name.split("/")[-1]
        else:
            short_name = model_name
            
        allowed = {
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",  # Testing if this model supports grounding
        }
        if short_name not in allowed:
            raise RuntimeError(
                f"Model '{model_name}' not configured for GoogleSearch grounding. "
                "Use gemini-2.5-pro or gemini-2.5-flash."
            )
    
    @staticmethod
    def _to_schema(schema_dict: Dict[str, Any]) -> Schema:
        """
        Convert JSON schema to Vertex Schema object
        
        Args:
            schema_dict: JSON schema dictionary
            
        Returns:
            Vertex Schema object
        """
        # Handle both wrapped and unwrapped schemas
        schema_def = schema_dict.get("schema", schema_dict)
        properties = schema_def.get("properties", {})
        required = schema_def.get("required", [])
        
        # Build Vertex schema dynamically based on input
        vertex_props = {}
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "string")
            if prop_type == "string":
                vertex_props[prop_name] = Schema(type=Type.STRING)
            elif prop_type == "array":
                items_type = prop_def.get("items", {}).get("type", "string")
                if items_type == "string":
                    vertex_props[prop_name] = Schema(type=Type.ARRAY, items=Schema(type=Type.STRING))
            elif prop_type == "number":
                vertex_props[prop_name] = Schema(type=Type.NUMBER)
            elif prop_type == "boolean":
                vertex_props[prop_name] = Schema(type=Type.BOOLEAN)
            else:
                # Default to string for unknown types
                vertex_props[prop_name] = Schema(type=Type.STRING)
        
        return Schema(
            type=Type.OBJECT,
            properties=vertex_props,
            required=required
        )
    
    def run(self, req: RunRequest) -> RunResult:
        """
        Execute a run request against Vertex Gemini
        
        Args:
            req: RunRequest with all parameters
            
        Returns:
            RunResult with response data
            
        Raises:
            RuntimeError: If grounding is REQUIRED but not achieved
        """
        start_time = time.time()
        
        # Set up LangSmith tracing if available
        parent_run = None
        if LANGSMITH_AVAILABLE and os.getenv("LANGCHAIN_TRACING_V2") == "true":
            try:
                parent_run = RunTree(
                    name="vertex.grounded_run" if req.grounding_mode != GroundingMode.OFF else "vertex.ungrounded_run",
                    run_type="chain",
                    project_name=os.getenv("LANGCHAIN_PROJECT", "ai-ranker"),
                    inputs={
                        "model": req.model_name,
                        "grounding_mode": req.grounding_mode.value,
                        "prompt": req.user_prompt[:500] if req.user_prompt else "",
                        "has_schema": bool(req.schema),
                        "has_als": bool(req.als_block),
                    },
                    metadata={
                        "provider": "vertex",
                        "temperature": req.temperature,
                        "top_p": req.top_p,
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to create LangSmith run tree: {e}")
                parent_run = None
        
        # Determine if grounding is needed
        needs_grounding = req.grounding_mode in (GroundingMode.REQUIRED, GroundingMode.PREFERRED)
        
        # Check model capability if grounding is needed
        if needs_grounding:
            self._assert_grounding_capable(req.model_name)
        
        # Build tools list - using global location helps trigger search
        if needs_grounding:
            # GoogleSearch tool for web grounding
            # Note: DynamicRetrievalConfig not supported via google_search field in Vertex API
            tools = [Tool(google_search=GoogleSearch())]
        else:
            tools = None
        
        # Convert schema
        schema = self._to_schema(req.schema or {})
        
        # Build config kwargs based on ChatGPT's recommendations
        cfg_kwargs = dict(
            temperature=req.temperature,
            top_p=req.top_p or 1.0,
        )
        
        # CRITICAL FIX per ChatGPT: Separate grounding and schema modes completely
        # Rule: If grounding ON → no response_schema and use text/plain
        #       If schema required → turn tools OFF
        if needs_grounding:
            # Grounding mode - NO schema allowed, use plain text
            cfg_kwargs["tools"] = tools
            cfg_kwargs["response_mime_type"] = "text/plain"  # Force plain text
            # DO NOT set response_schema when grounding is enabled
            if req.schema:
                logger.warning("Vertex limitation: Cannot use JSON schema with GoogleSearch grounding - using plain text")
        elif req.schema:
            # Structured output mode - NO grounding/tools allowed
            cfg_kwargs["response_mime_type"] = "application/json"
            cfg_kwargs["response_schema"] = schema
            # Explicitly no tools when using schema
            cfg_kwargs["tools"] = None
        
        # Add seed if provided
        if req.seed is not None:
            cfg_kwargs["seed"] = req.seed
        
        # Create config
        cfg = GenerateContentConfig(**cfg_kwargs)
        
        # Combine ALS block and user prompt
        contents = f"{req.als_block}\n{req.user_prompt}".strip() if req.als_block else req.user_prompt
        
        # If grounding with schema, add JSON instruction to prompt
        if needs_grounding and req.schema:
            contents += "\n\nReturn your response as valid JSON matching the requested format."
        
        # Add system instruction if provided
        if req.system_text:
            # Vertex uses system instruction separately (if supported by model)
            # For now, prepend to contents
            contents = f"{req.system_text}\n\n{contents}"
        
        try:
            # Convert model name to publisher path if needed
            model_name = req.model_name
            if not model_name.startswith("publishers/"):
                model_name = f"publishers/google/models/{model_name}"
            
            # Make the API call with LangSmith tracing
            logger.info(f"Calling Vertex API: model={model_name}, grounding={needs_grounding}")
            
            # Create child run for the actual API call
            api_run = None
            if parent_run:
                try:
                    api_run = parent_run.create_child(
                        name="vertex.generate_content",
                        run_type="llm",
                        inputs={
                            "model": model_name,
                            "messages": [{"role": "user", "content": req.user_prompt[:500] if req.user_prompt else ""}],
                            "has_tools": bool(tools),
                            "has_schema": bool(req.schema and not needs_grounding),
                        },
                        metadata={
                            "grounding_enabled": needs_grounding,
                            "response_mime_type": cfg_kwargs.get("response_mime_type", "text/plain"),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to create child run: {e}")
            
            response = self.client.models.generate_content(
                model=model_name,  # Use publisher path
                contents=contents,
                config=cfg
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Use robust text extraction helper
            text = self.extract_text(response)
            
            if not text:
                # Log response for debugging (sample 10% to avoid bloat per ChatGPT)
                import random
                if random.random() < 0.1:
                    logger.error(f"No text found in response. Response dict: {response.__dict__ if hasattr(response, '__dict__') else 'No dict'}")
                raise RuntimeError("No text in Vertex response")
            
            # Parse JSON (only if not grounding mode)
            json_obj = None
            json_valid = False
            
            # If we used grounding, expect plain text not JSON
            if needs_grounding:
                # Grounding mode returns plain text, not JSON
                json_obj = {"response": text}  # Wrap in simple object
                json_valid = False  # Mark as not valid JSON since it's plain text
                logger.debug("Grounding mode: returned plain text, not JSON")
            else:
                # Clean up any markdown fences
                text = self._strip_code_fences(text)
                
                try:
                    json_obj = json.loads(text)
                    json_valid = True
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}. Text was: {text[:200]}")
                    # For structured requests without grounding, this is an error
                    if req.schema:
                        logger.error("JSON schema was requested but output is not valid JSON")
            
            # Extract grounding metadata using helper - single source of truth
            grounding_signals = self._vertex_grounding_signals(response)
            
            # Assert shape to block any string leak regressions
            self._assert_vertex_shape(grounding_signals)
            
            # Use returned values VERBATIM - DO NOT re-normalize or re-process
            grounded_effective = grounding_signals["grounded"]
            tool_call_count = grounding_signals["tool_calls"]
            citations = grounding_signals["citations"]  # Already guaranteed list[dict]
            web_queries = grounding_signals["queries"]
            grounding_sources = grounding_signals.get("grounding_sources", [])
            
            # Optional: Early validation to catch any issues
            if citations:
                for i, c in enumerate(citations):
                    if not isinstance(c, dict):
                        raise TypeError(f"citations[{i}] not dict: {type(c).__name__} -> {c!r}")
                logger.debug(f"Citations validated: {len(citations)} dicts")
            
            # Log grounding status for debugging
            if needs_grounding:
                logger.info(f"Grounding status: effective={grounded_effective}, tool_calls={tool_call_count}, "
                           f"citations={len(citations)}, queries={len(web_queries)}")
            
            # Enforce grounding requirements
            if req.grounding_mode == GroundingMode.REQUIRED and needs_grounding and not grounded_effective:
                raise RuntimeError(
                    f"Grounding REQUIRED but no grounding metadata found. "
                    f"Model: {req.model_name}, Response has grounding: {grounded_effective}"
                )
            
            # Extract model metadata
            model_version = None
            response_id = None
            try:
                if hasattr(response, 'metadata'):
                    metadata = response.metadata
                    model_version = getattr(metadata, 'model_version', None)
                    response_id = getattr(metadata, 'response_id', None)
            except Exception:
                pass
            
            # Build result with citations from grounding_signals (already list[dict])
            result = RunResult(
                run_id=req.run_id,
                provider="vertex",
                model_name=req.model_name,
                region=self.location,
                grounded_effective=grounded_effective,
                tool_call_count=tool_call_count,
                citations=citations,  # Use citations directly from signals
                json_text=text,
                json_obj=json_obj,
                json_valid=json_valid,
                latency_ms=latency_ms,
                error=None,
                system_fingerprint=model_version,
                usage={},  # Vertex doesn't expose token usage in same way
                meta={
                    "temperature": req.temperature,
                    "seed": req.seed,
                    "top_p": req.top_p,
                    "response_id": response_id,
                    "api": "vertex",
                    "grounding_mode": req.grounding_mode.value,
                    "queries_count": len(web_queries),
                    "citations_count": len(citations),
                    "schema_applied": bool(req.schema and not needs_grounding),
                    "tools_enabled": bool(needs_grounding)
                }
            )
            
            # End LangSmith runs with outputs
            if api_run:
                try:
                    api_run.end(outputs={
                        "text": text[:1000] if text else "",  # Truncate for display
                        "grounded": grounded_effective,
                        "citations_count": len(citations),
                        "tool_calls": tool_call_count,
                    })
                except Exception as e:
                    logger.debug(f"Failed to end child run: {e}")
            
            if parent_run:
                try:
                    parent_run.end(outputs={
                        "grounded_effective": grounded_effective,
                        "citations": len(citations),
                        "web_queries": len(web_queries) if web_queries else 0,
                        "json_valid": json_valid,
                        "response_preview": text[:200] if text else "",
                    })
                    parent_run.post()  # Ensure it's sent to LangSmith
                except Exception as e:
                    logger.debug(f"Failed to end parent run: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Vertex API error: {e}")
            
            # End LangSmith runs with error
            if api_run:
                try:
                    api_run.end(error=str(e))
                except:
                    pass
            
            if parent_run:
                try:
                    parent_run.end(error=str(e))
                    parent_run.post()
                except:
                    pass
            
            # Re-raise authentication errors so fallback can work
            if "Reauthentication is needed" in str(e) or "ADC" in str(e) or "auth" in str(e).lower():
                raise  # Let the caller handle auth failures
            
            # Fail closed for REQUIRED mode
            if req.grounding_mode == GroundingMode.REQUIRED:
                raise
            
            # Return error result for other modes
            return RunResult(
                run_id=req.run_id,
                provider="vertex",
                model_name=req.model_name,
                region=self.location,
                grounded_effective=False,
                tool_call_count=0,
                citations=[],
                json_text="",
                json_obj=None,
                json_valid=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e),
                meta={"api": "vertex", "failed": True}
            )
    
    async def run_async(self, req: RunRequest) -> RunResult:
        """
        Async version - Vertex SDK doesn't have async support yet
        Falls back to sync execution
        """
        # Vertex genai SDK doesn't support async yet
        # Run synchronously in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, req)
    
    async def analyze_with_gemini(
        self,
        prompt: str,
        use_grounding: bool = False,
        model_name: str = "gemini-2.5-pro",
        temperature: float = 0.0,
        seed: int = 42,
        context: str = None,
        top_p: float = 1.0
    ) -> Dict[str, Any]:
        """
        Compatibility method for old interface used by Templates tab
        Converts old-style call to new RunRequest format
        """
        import uuid
        
        # Create a RunRequest from old-style parameters
        req = RunRequest(
            run_id=str(uuid.uuid4()),
            client_id="legacy_templates",
            provider="vertex",
            model_name=model_name,
            grounding_mode=GroundingMode.REQUIRED if use_grounding else GroundingMode.OFF,
            system_text="",
            als_block=context or "",
            user_prompt=prompt,
            temperature=temperature,
            seed=seed,
            top_p=top_p
        )
        
        # Run and convert result
        result = await self.run_async(req)
        
        # Convert RunResult back to old format
        # Use json_text for text content, or json_obj if structured
        content = result.json_text if result.json_text else str(result.json_obj or "")
        
        # Build proper grounding metadata with citations
        grounding_metadata = None
        if result.grounded_effective:
            grounding_metadata = {
                "grounded": True,
                "citations": result.citations,  # Include the actual citations!
                "web_search_queries": result.meta.get("queries", []) if hasattr(result, "meta") else [],
                "tool_call_count": result.tool_call_count
            }
        
        return {
            "content": content,
            "model_version": result.system_fingerprint,  # Use system_fingerprint for model version
            "grounded": result.grounded_effective,
            "grounding_metadata": grounding_metadata,
            "temperature": temperature,
            "seed": seed,
            "response_time_ms": result.latency_ms,
            "token_count": result.usage or {},  # Use usage instead of token_count
            "system_fingerprint": result.system_fingerprint
        }
