"""
Production-grade OpenAI Responses API adapter
Uses SDK with extra_body for missing features instead of raw HTTP
Implements fail-closed semantics for grounding requirements
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI, OpenAI
from .types import RunRequest, RunResult, GroundingMode

logger = logging.getLogger(__name__)

class OpenAIProductionAdapter:
    """
    Production adapter for OpenAI's Responses API
    Uses SDK's extra_body to work around missing text.format parameter
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from environment or parameter"""
        self.client = OpenAI(api_key=api_key)  # Uses OPENAI_API_KEY env var if not provided
        self.async_client = AsyncOpenAI(api_key=api_key)
    
    @staticmethod
    def _extract_usage(response) -> Dict[str, int]:
        """Extract usage statistics from response, handling complex objects"""
        usage = {}
        if hasattr(response, 'usage'):
            usage_obj = response.usage
            if hasattr(usage_obj, '__dict__'):
                for key, value in usage_obj.__dict__.items():
                    # Only include integer values, skip complex objects
                    if isinstance(value, int):
                        usage[key] = value
                    elif hasattr(value, '__dict__'):
                        # Handle nested objects like input_tokens_details
                        for nested_key, nested_value in value.__dict__.items():
                            if isinstance(nested_value, int):
                                usage[f"{key}_{nested_key}"] = nested_value
        return usage
    
    @staticmethod
    def _build_input_messages(
        system_text: str, 
        als_block: str, 
        user_prompt: str
    ) -> List[Dict[str, str]]:
        """Build input messages array for Responses API"""
        messages = []
        
        # Add system message if provided
        if system_text:
            messages.append({"role": "system", "content": system_text})
        elif als_block:
            # Default ALS-aware system prompt
            messages.append({
                "role": "system",
                "content": "Use ambient context to infer locale. Output must match the schema. Do not mention location."
            })
        
        # Add ALS block and user prompt
        combined_user = f"{als_block}\n{user_prompt}".strip() if als_block else user_prompt
        messages.append({"role": "user", "content": combined_user})
        
        return messages
    
    @staticmethod
    def _build_schema_format(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build text.format structure for JSON schema enforcement"""
        return {
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema.get("name", "structured_output"),
                    "schema": schema.get("schema", schema),
                    "strict": schema.get("strict", True)
                }
            }
        }
    
    def run_sync(self, req: RunRequest) -> RunResult:
        """Synchronous run method"""
        start_time = time.time()
        
        # Determine if grounding is needed
        needs_grounding = req.grounding_mode in (GroundingMode.REQUIRED, GroundingMode.PREFERRED)
        
        # Build request parameters
        kwargs = {
            "model": req.model_name,
            "input": self._build_input_messages(req.system_text, req.als_block, req.user_prompt),
            "temperature": 1.0 if 'gpt-5' in req.model_name.lower() else req.temperature,
        }
        
        # Add grounding tools if needed
        if needs_grounding:
            kwargs["tools"] = [{"type": "web_search"}]
            # GPT-5 only supports "auto" with web_search
            kwargs["tool_choice"] = "auto"
        
        # Add seed if provided (only for Chat Completions, not Responses)
        # Responses API doesn't support seed parameter
        # if req.seed is not None:
        #     kwargs["seed"] = req.seed
        
        # Add JSON schema via extra_body (SDK workaround)
        if req.schema:
            kwargs["extra_body"] = self._build_schema_format(req.schema)
        
        try:
            # Make the API call
            logger.info(f"Calling OpenAI Responses API: model={req.model_name}, grounding={needs_grounding}")
            response = self.client.responses.create(**kwargs)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract response data
            output_text = getattr(response, 'output_text', '')
            output_items = getattr(response, 'output', []) or []
            
            # Count tool calls
            tool_call_count = sum(
                1 for item in output_items 
                if getattr(item, 'type', '') == 'web_search_call'
            )
            
            # Check if grounding was effective
            grounded_effective = tool_call_count > 0
            
            # Enforce grounding requirements
            if req.grounding_mode == GroundingMode.REQUIRED and needs_grounding and not grounded_effective:
                raise RuntimeError(
                    f"Grounding REQUIRED but no web search performed. "
                    f"Model: {req.model_name}, Tool calls: {tool_call_count}"
                )
            
            # Parse JSON if schema was provided
            json_obj = None
            json_valid = False
            if req.schema and output_text:
                try:
                    json_obj = json.loads(output_text)
                    json_valid = True
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
                    if req.grounding_mode == GroundingMode.REQUIRED:
                        raise RuntimeError(f"JSON schema enforced but output invalid: {e}")
            
            # Extract citations
            citations = []
            for item in output_items:
                if getattr(item, 'type', '') == 'web_search_call' and hasattr(item, 'citations'):
                    for citation in getattr(item, 'citations', []):
                        citations.append({
                            'url': getattr(citation, 'url', ''),
                            'title': getattr(citation, 'title', ''),
                            'snippet': getattr(citation, 'snippet', '')
                        })
            
            # Build result
            return RunResult(
                run_id=req.run_id,
                provider="openai",
                model_name=req.model_name,
                region=None,
                grounded_effective=grounded_effective,
                tool_call_count=tool_call_count,
                citations=citations,
                json_text=output_text,
                json_obj=json_obj,
                json_valid=json_valid,
                latency_ms=latency_ms,
                error=None,
                system_fingerprint=getattr(response, 'system_fingerprint', None),
                usage=self._extract_usage(response),
                meta={
                    "temperature": kwargs["temperature"],
                    "seed": req.seed,
                    "top_p": req.top_p,
                    "api": "responses"
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            
            # Fail closed for REQUIRED mode
            if req.grounding_mode == GroundingMode.REQUIRED:
                raise
            
            # Return error result for other modes
            return RunResult(
                run_id=req.run_id,
                provider="openai",
                model_name=req.model_name,
                region=None,
                grounded_effective=False,
                tool_call_count=0,
                citations=[],
                json_text="",
                json_obj=None,
                json_valid=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e),
                meta={"api": "responses", "failed": True}
            )
    
    async def run_async(self, req: RunRequest) -> RunResult:
        """Asynchronous run method"""
        start_time = time.time()
        
        # Determine if grounding is needed
        needs_grounding = req.grounding_mode in (GroundingMode.REQUIRED, GroundingMode.PREFERRED)
        
        # Build request parameters
        kwargs = {
            "model": req.model_name,
            "input": self._build_input_messages(req.system_text, req.als_block, req.user_prompt),
            "temperature": 1.0 if 'gpt-5' in req.model_name.lower() else req.temperature,
        }
        
        # Add grounding tools if needed
        if needs_grounding:
            kwargs["tools"] = [{"type": "web_search"}]
            # GPT-5 only supports "auto" with web_search
            kwargs["tool_choice"] = "auto"
        
        # Add seed if provided (only for Chat Completions, not Responses)
        # Responses API doesn't support seed parameter
        # if req.seed is not None:
        #     kwargs["seed"] = req.seed
        
        # Add JSON schema via extra_body (SDK workaround)
        if req.schema:
            kwargs["extra_body"] = self._build_schema_format(req.schema)
        
        try:
            # Make the async API call
            logger.info(f"Calling OpenAI Responses API (async): model={req.model_name}, grounding={needs_grounding}")
            response = await self.async_client.responses.create(**kwargs)
            
            # Rest of the logic is identical to sync version
            latency_ms = int((time.time() - start_time) * 1000)
            
            output_text = getattr(response, 'output_text', '')
            output_items = getattr(response, 'output', []) or []
            
            tool_call_count = sum(
                1 for item in output_items 
                if getattr(item, 'type', '') == 'web_search_call'
            )
            
            grounded_effective = tool_call_count > 0
            
            if req.grounding_mode == GroundingMode.REQUIRED and needs_grounding and not grounded_effective:
                raise RuntimeError(
                    f"Grounding REQUIRED but no web search performed. "
                    f"Model: {req.model_name}, Tool calls: {tool_call_count}"
                )
            
            json_obj = None
            json_valid = False
            if req.schema and output_text:
                try:
                    json_obj = json.loads(output_text)
                    json_valid = True
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
                    if req.grounding_mode == GroundingMode.REQUIRED:
                        raise RuntimeError(f"JSON schema enforced but output invalid: {e}")
            
            citations = []
            for item in output_items:
                if getattr(item, 'type', '') == 'web_search_call' and hasattr(item, 'citations'):
                    for citation in getattr(item, 'citations', []):
                        citations.append({
                            'url': getattr(citation, 'url', ''),
                            'title': getattr(citation, 'title', ''),
                            'snippet': getattr(citation, 'snippet', '')
                        })
            
            return RunResult(
                run_id=req.run_id,
                provider="openai",
                model_name=req.model_name,
                region=None,
                grounded_effective=grounded_effective,
                tool_call_count=tool_call_count,
                citations=citations,
                json_text=output_text,
                json_obj=json_obj,
                json_valid=json_valid,
                latency_ms=latency_ms,
                error=None,
                system_fingerprint=getattr(response, 'system_fingerprint', None),
                usage=self._extract_usage(response),
                meta={
                    "temperature": kwargs["temperature"],
                    "seed": req.seed,
                    "top_p": req.top_p,
                    "api": "responses"
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI async API error: {e}")
            
            if req.grounding_mode == GroundingMode.REQUIRED:
                raise
            
            return RunResult(
                run_id=req.run_id,
                provider="openai",
                model_name=req.model_name,
                region=None,
                grounded_effective=False,
                tool_call_count=0,
                citations=[],
                json_text="",
                json_obj=None,
                json_valid=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e),
                meta={"api": "responses", "failed": True}
            )