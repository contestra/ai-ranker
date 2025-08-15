"""
Vertex GenAI adapter for Gemini models
Production-grade implementation with grounding and structured outputs
Following ChatGPT's reference architecture
"""

import json
import time
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai.types import (
    GenerateContentConfig, Tool, GoogleSearch, Schema, Type, HttpOptions
)
from .types import RunRequest, RunResult, GroundingMode

logger = logging.getLogger(__name__)

class VertexGenAIAdapter:
    """
    Production adapter for Google's Vertex AI Gemini models
    Supports grounding via GoogleSearch and structured JSON outputs
    """
    
    def __init__(self, project: str, location: str):
        """
        Initialize Vertex client
        
        Args:
            project: GCP project ID (e.g., 'contestra-ai')
            location: Vertex region (e.g., 'europe-west4')
        """
        # Enforce correct project
        assert project == "contestra-ai", f"Vertex adapter misconfigured: project={project} != contestra-ai"
        
        self.project = project
        # Use 'global' location for better grounding support per ChatGPT
        self.location = "global" if location == "europe-west4" else location
        # Use API v1 for better grounding support
        self.client = genai.Client(
            http_options=HttpOptions(api_version="v1"),
            vertexai=True, 
            project=project, 
            location=self.location
        )
        logger.info(f"Initialized Vertex adapter: project={project}, location={self.location}, api_version=v1")
    
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
    def _vertex_grounding_signals(resp) -> Dict[str, Any]:
        """Extract grounding signals from Vertex response - updated per ChatGPT guidance"""
        grounded = False
        tc = 0
        citations = []
        queries = []
        chunks = []
        supports = []
        entry_point = None
        
        try:
            # Get grounding metadata from response
            if hasattr(resp, 'candidates') and resp.candidates:
                cand = resp.candidates[0]
                gm = getattr(cand, 'grounding_metadata', None)
                
                if gm:
                    # Extract the correct fields per ChatGPT
                    queries = getattr(gm, 'web_search_queries', []) or []
                    chunks = getattr(gm, 'grounding_chunks', []) or []
                    supports = getattr(gm, 'grounding_supports', []) or []
                    entry_point = getattr(gm, 'search_entry_point', None)
                    
                    # Extract URIs from chunks as citations
                    citations = []
                    for chunk in chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            uri = getattr(chunk.web, 'uri', None)
                            if uri:
                                citations.append(uri)
                    
                    # Grounding is effective if ANY of these are present
                    grounded = bool(queries or chunks or supports or entry_point)
                    tc = len(queries) if queries else (1 if grounded else 0)
                    
                    logger.debug(f"Grounding metadata: queries={len(queries)}, chunks={len(chunks)}, "
                               f"supports={len(supports)}, entry_point={bool(entry_point)}")
        except Exception as e:
            logger.warning(f"Failed to extract grounding signals: {e}")
        
        return {
            "grounded": grounded, 
            "tool_calls": tc, 
            "citations": citations, 
            "queries": queries,
            "chunks": chunks,
            "supports": supports,
            "entry_point": entry_point
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
        
        # Build config kwargs
        cfg_kwargs = dict(
            temperature=req.temperature,
            top_p=req.top_p or 1.0,
        )
        
        # CRITICAL: Cannot use response_schema with GoogleSearch tool
        # Must choose between structured output OR grounding
        if tools and needs_grounding:
            # Grounding mode - no schema allowed
            cfg_kwargs["tools"] = tools
            logger.warning("Vertex limitation: Cannot use JSON schema with GoogleSearch grounding")
        elif req.schema:
            # Structured output mode - no grounding
            cfg_kwargs["response_mime_type"] = "application/json"
            cfg_kwargs["response_schema"] = schema
        
        # Add tools if not grounding (for other tool types)
        if tools and not needs_grounding:
            cfg_kwargs["tools"] = tools
        
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
            
            # Make the API call
            logger.info(f"Calling Vertex API: model={model_name}, grounding={needs_grounding}")
            response = self.client.models.generate_content(
                model=model_name,  # Use publisher path
                contents=contents,
                config=cfg
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Robust JSON extraction
            text = getattr(response, 'text', None)
            if not text:
                # Log response structure for debugging
                logger.warning(f"No text attribute in response. Response type: {type(response)}")
                # Try alternative locations in response structure
                try:
                    candidates = getattr(response, 'candidates', [])
                    if candidates:
                        cand = candidates[0]
                        content = getattr(cand, 'content', None)
                        if content:
                            parts = getattr(content, 'parts', [])
                            for part in parts:
                                if hasattr(part, 'text') and part.text:
                                    text = part.text
                                    break
                except Exception as e:
                    logger.warning(f"Failed to extract text from candidates: {e}")
            
            if not text:
                # Log full response for debugging
                logger.error(f"No text found in response. Response dict: {response.__dict__ if hasattr(response, '__dict__') else 'No dict'}")
                raise RuntimeError("No JSON text in Vertex response")
            
            # Parse JSON (should be valid due to response_schema)
            json_obj = None
            json_valid = False
            
            # Clean up any markdown fences
            text = self._strip_code_fences(text)
            
            try:
                json_obj = json.loads(text)
                json_valid = True
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}. Text was: {text[:200]}")
                # For grounded requests, JSON might not be perfect but grounding might have worked
                if req.schema and not json_valid:
                    logger.warning("JSON schema was requested but output is not valid JSON")
            
            # Extract grounding metadata using helper
            grounding_signals = self._vertex_grounding_signals(response)
            grounded_effective = grounding_signals["grounded"]
            tool_call_count = grounding_signals["tool_calls"]
            citations = grounding_signals["citations"]
            web_queries = grounding_signals["queries"]
            
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
            
            # Build result
            return RunResult(
                run_id=req.run_id,
                provider="vertex",
                model_name=req.model_name,
                region=self.location,
                grounded_effective=grounded_effective,
                tool_call_count=tool_call_count,
                citations=citations,
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
                    "api": "vertex"
                }
            )
            
        except Exception as e:
            logger.error(f"Vertex API error: {e}")
            
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