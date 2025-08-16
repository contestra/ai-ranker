"""
Production-grade OpenAI Responses API adapter
Uses SDK with extra_body for missing features instead of raw HTTP
Implements fail-closed semantics for grounding requirements
"""

import json
import time
import logging
import os
import httpx
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI, OpenAI
from .types import RunRequest, RunResult, GroundingMode

logger = logging.getLogger(__name__)

# Constants for Responses API (centralized to avoid drift)
RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT = 512  # Increased from 96 to prevent token starvation
RESPONSES_MAX_OUTPUT_TOKENS_MIN = 16       # API minimum
RESPONSES_TEMPERATURE_DEFAULT = 0           # Deterministic for testing
RESPONSES_TEMPERATURE_GPT5 = 1.0           # GPT-5 requirement
RESPONSES_MAX_OUTPUT_TOKENS_GPT5_GROUNDED = 1024  # Higher budget for GPT-5 with tools

class OpenAIProductionAdapter:
    """
    Production adapter for OpenAI's Responses API
    Uses SDK's extra_body to work around missing text.format parameter
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from environment or parameter"""
        self.client = OpenAI(api_key=api_key)  # Uses OPENAI_API_KEY env var if not provided
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        # Capability flags (will be set by probe)
        self.supports_required_toolchoice = None  # Will probe on first use
    
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
    
    async def _probe_required_toolchoice(self, model_name: str = "gpt-4o") -> bool:
        """
        Probe if model supports tool_choice:"required" with web_search
        One-time check, cached for session
        Note: GPT-5 does NOT support required, but GPT-4o does
        """
        if self.supports_required_toolchoice is not None:
            return self.supports_required_toolchoice
        
        # GPT-5 models don't support tool_choice:"required" with web_search
        if 'gpt-5' in model_name.lower():
            self.supports_required_toolchoice = False
            logger.info(f"GPT-5 detected, tool_choice:required not supported")
            return False
        
        url = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Minimal probe request
        probe_body = {
            "model": model_name,
            "input": [
                {"role": "user", "content": [{"type": "input_text", "text": "What is today's date?"}]}
            ],
            "tools": [{"type": "web_search"}],
            "tool_choice": "required",  # Test if required is supported
            "temperature": RESPONSES_TEMPERATURE_GPT5 if 'gpt-5' in model_name.lower() else RESPONSES_TEMPERATURE_DEFAULT,
            "max_output_tokens": RESPONSES_MAX_OUTPUT_TOKENS_MIN  # Use minimum for probe
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=probe_body)
                # If we get 200 or even 429 (rate limit), it means syntax is valid
                self.supports_required_toolchoice = response.status_code in (200, 429)
                logger.info(f"Capability probe: tool_choice:required {'supported' if self.supports_required_toolchoice else 'not supported'} (status {response.status_code})")
                print(f"[PROBE] tool_choice:required support = {self.supports_required_toolchoice} (status {response.status_code})", flush=True)
                if response.status_code == 400:
                    error_detail = response.text[:500]
                    print(f"[PROBE] 400 error: {error_detail}", flush=True)
        except Exception as e:
            logger.warning(f"Capability probe failed: {e}")
            self.supports_required_toolchoice = False
        
        return self.supports_required_toolchoice
    
    @staticmethod
    def _flatten_usage_openai(usage_raw) -> Dict[str, int]:
        """
        Flattens OpenAI Responses 'usage' into flat ints.
        - Leaves input_tokens/output_tokens as-is if present.
        - Flattens *_details into *_details_<key>=int.
        - Computes total_tokens if missing (input + output only).
        """
        out: Dict[str, int] = {}

        def walk(prefix: str, val):
            if isinstance(val, (int, float)):
                out[prefix] = int(val)
            elif isinstance(val, dict):
                for k, v in val.items():
                    walk(f"{prefix}_{k}" if prefix else k, v)

        if isinstance(usage_raw, dict):
            for k, v in usage_raw.items():
                walk(k, v)

        # Prefer provider's rollup if present; otherwise compute a minimal one
        if "total_tokens" not in out:
            total = out.get("input_tokens", 0) + out.get("output_tokens", 0)
            out["total_tokens"] = total

        return out
    
    @staticmethod
    def _build_input_messages(
        system_text: str, 
        als_block: str, 
        user_prompt: str,
        use_typed_parts: bool = False
    ) -> List[Dict[str, Any]]:
        """Build input messages array for Responses API"""
        messages = []
        
        # For HTTP Responses API, content must be typed parts
        if use_typed_parts:
            # Add system message if provided
            if system_text:
                messages.append({
                    "role": "system", 
                    "content": [{"type": "input_text", "text": system_text}]
                })
            elif als_block:
                messages.append({
                    "role": "system",
                    "content": [{"type": "input_text", "text": "Use ambient context to infer locale. Output must match the schema. Do not mention location."}]
                })
            
            # Add ALS block and user prompt
            combined_user = f"{als_block}\n\n{user_prompt}".strip() if als_block else user_prompt
            messages.append({
                "role": "user", 
                "content": [{"type": "input_text", "text": combined_user}]
            })
        else:
            # SDK format - plain strings
            if system_text:
                messages.append({"role": "system", "content": system_text})
            elif als_block:
                messages.append({
                    "role": "system",
                    "content": "Use ambient context to infer locale. Output must match the schema. Do not mention location."
                })
            
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
    
    async def _http_grounded_with_schema(
        self, 
        req: RunRequest
    ) -> RunResult:
        """
        Direct HTTP call to Responses API for grounded + schema requests
        Uses tool_choice:"required" to force web searches
        """
        print(f"[DEBUG] Entered _http_grounded_with_schema", flush=True)
        start_time = time.time()
        
        url = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Probe capability if needed for REQUIRED mode
        if req.grounding_mode == GroundingMode.REQUIRED:
            supports_required = await self._probe_required_toolchoice(req.model_name)
            if supports_required:
                tool_choice = "required"
                print(f"[INFO] Using tool_choice='required' (probe confirmed support)", flush=True)
            else:
                tool_choice = "auto"
                print(f"[INFO] Using tool_choice='auto' (required not supported, will enforce after)", flush=True)
        else:
            tool_choice = "auto"
        
        # Determine token budget based on model and mode
        is_gpt5 = 'gpt-5' in req.model_name.lower()
        needs_grounding = req.grounding_mode in [GroundingMode.PREFERRED, GroundingMode.REQUIRED]
        
        if is_gpt5 and needs_grounding:
            max_output_tokens = RESPONSES_MAX_OUTPUT_TOKENS_GPT5_GROUNDED  # 1024 tokens
            print(f"[INFO] Using increased token budget for GPT-5 with grounding: {max_output_tokens} tokens", flush=True)
        else:
            max_output_tokens = RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT  # 512 tokens
        
        body = {
            "model": req.model_name,
            "input": self._build_input_messages(req.system_text, req.als_block, req.user_prompt, use_typed_parts=True),
            "tools": [{"type": "web_search"}],
            "tool_choice": tool_choice,
            "temperature": RESPONSES_TEMPERATURE_GPT5 if is_gpt5 else (req.temperature if req.temperature is not None else RESPONSES_TEMPERATURE_DEFAULT),
            "max_output_tokens": max_output_tokens
        }
        
        # Add reasoning config for GPT-5 with tools to reduce token consumption
        if is_gpt5 and needs_grounding:
            body["reasoning"] = {"effort": "low"}
            print(f"[INFO] Added reasoning effort='low' for GPT-5 with tools", flush=True)
        
        # Add JSON schema if provided
        if req.schema:
            # Extract the actual schema
            schema_def = req.schema.get("schema", req.schema)
            
            # Ensure it's a valid JSON Schema object
            if "type" not in schema_def:
                schema_def["type"] = "object"
            if "additionalProperties" not in schema_def:
                schema_def["additionalProperties"] = False
            
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "LocaleProbe",  # name at FORMAT level (not nested under json_schema)
                    "schema": schema_def,   # the JSON Schema object
                    "strict": req.schema.get("strict", True)
                }
            }
        
        try:
            logger.info(f"HTTP Responses API call: model={req.model_name}, tool_choice={tool_choice}, mode={req.grounding_mode}")
            print(f"[DEBUG] Making HTTP request with tool_choice={tool_choice}, grounding_mode={req.grounding_mode}", flush=True)
            
            # Make async HTTP request
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.post(url, headers=headers, json=body)
                print(f"[DEBUG] HTTP response status: {response.status_code}", flush=True)
                if response.status_code != 200:
                    error_detail = response.text[:2000]
                    logger.error(f"HTTP {response.status_code}: {error_detail}")
                    print(f"[ERROR] HTTP {response.status_code}: {error_detail}", flush=True)
                    print(f"[REQUEST BODY] {json.dumps(body)[:1000]}", flush=True)
                    raise httpx.HTTPStatusError(f"HTTP {response.status_code}: {error_detail}", request=response.request, response=response)
                data = response.json()
                print(f"[DEBUG] Response data keys: {list(data.keys())}", flush=True)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Parse response - extract text from the message in output items
            output_items = data.get("output", []) or []
            output_text = ""
            
            # Find the message item which contains the actual response
            for item in output_items:
                if item.get("type") == "message":
                    # The message item should have content
                    content = item.get("content")
                    if isinstance(content, str):
                        output_text = content
                    elif isinstance(content, list) and len(content) > 0:
                        # If content is a list, extract text from first item
                        first_content = content[0]
                        if isinstance(first_content, dict):
                            output_text = first_content.get("text", "")
                        elif isinstance(first_content, str):
                            output_text = first_content
                    break
            
            # Fallback to checking output_text field if not found
            if not output_text:
                output_text = data.get("output_text", "")
            
            print(f"[DEBUG] Output text: {output_text[:500] if output_text else 'EMPTY'}", flush=True)
            print(f"[DEBUG] Output items count: {len(output_items)}", flush=True)
            if output_items:
                print(f"[DEBUG] First few items: {json.dumps(output_items[:2], default=str)[:1000]}", flush=True)
            
            # Check for token starvation (reasoning but no message) in GPT-5
            has_reasoning = any(item.get("type") == "reasoning" for item in output_items)
            has_message = any(item.get("type") == "message" for item in output_items)
            
            if is_gpt5 and has_reasoning and not has_message and max_output_tokens < 2048:
                # Token starvation detected, retry with double the tokens
                logger.warning(f"Token starvation detected (reasoning but no message), retrying with {max_output_tokens * 2} tokens")
                print(f"[WARNING] Token starvation detected, retrying with {max_output_tokens * 2} tokens", flush=True)
                
                retry_body = body.copy()
                retry_body["max_output_tokens"] = max_output_tokens * 2
                
                # Make second attempt with same mode/tools
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    retry_response = await client.post(url, headers=headers, json=retry_body)
                    if retry_response.status_code == 200:
                        data = retry_response.json()
                        output_items = data.get("output", []) or []
                        
                        # Re-extract output text
                        output_text = ""
                        for item in output_items:
                            if item.get("type") == "message":
                                content = item.get("content")
                                if isinstance(content, str):
                                    output_text = content
                                elif isinstance(content, list) and len(content) > 0:
                                    first_content = content[0]
                                    if isinstance(first_content, dict):
                                        output_text = first_content.get("text", "")
                                    elif isinstance(first_content, str):
                                        output_text = first_content
                                break
                        
                        if not output_text:
                            output_text = data.get("output_text", "")
                        
                        print(f"[DEBUG] After retry - Output text: {output_text[:500] if output_text else 'STILL EMPTY'}", flush=True)
                        print(f"[DEBUG] After retry - Output items count: {len(output_items)}", flush=True)
            
            # Count tool calls
            tool_call_count = sum(
                1 for item in output_items 
                if (item.get("type") or "").startswith("web_search")
            )
            
            grounded_effective = tool_call_count > 0
            
            logger.info(f"HTTP response: tool_calls={tool_call_count}, grounded={grounded_effective}, mode={req.grounding_mode}")
            
            # Enforce REQUIRED mode - must have at least one web search
            if req.grounding_mode == GroundingMode.REQUIRED and not grounded_effective:
                # Only retry with provoker if we had to use "auto" (required not supported)
                if tool_choice == "auto" and not self.supports_required_toolchoice:
                    print(f"[INFO] No search with auto, retrying with provoker prompt", flush=True)
                    
                    # Add provoker to user prompt
                    import time as time_module
                    provoker = f"\n\nProvide information as of today ({time_module.strftime('%Y-%m-%d')}), citing an official source URL."
                    provoker_prompt = req.user_prompt + provoker
                    
                    # Retry with provoker
                    retry_body = body.copy()
                    retry_body["input"] = self._build_input_messages(
                        req.system_text, req.als_block, provoker_prompt, use_typed_parts=True
                    )
                    
                    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                        retry_response = await client.post(url, headers=headers, json=retry_body)
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            retry_items = retry_data.get("output", []) or []
                            retry_tool_calls = sum(
                                1 for item in retry_items 
                                if (item.get("type") or "").startswith("web_search")
                            )
                            
                            if retry_tool_calls > 0:
                                # Success with provoker!
                                print(f"[INFO] Provoker triggered {retry_tool_calls} searches", flush=True)
                                data = retry_data  # Use retry response
                                output_items = retry_items
                                tool_call_count = retry_tool_calls
                                grounded_effective = True
                                
                                # Re-extract output text
                                output_text = ""
                                for item in output_items:
                                    if item.get("type") == "message":
                                        content = item.get("content")
                                        if isinstance(content, str):
                                            output_text = content
                                        elif isinstance(content, list) and len(content) > 0:
                                            first_content = content[0]
                                            if isinstance(first_content, dict):
                                                output_text = first_content.get("text", "")
                                            elif isinstance(first_content, str):
                                                output_text = first_content
                                        break
                                
                                # Re-extract usage
                                usage_raw = retry_data.get('usage', {}) or {}
                                flat_usage = self._flatten_usage_openai(usage_raw)
                
                # Still no search after retry? Fail
                if not grounded_effective:
                    raise RuntimeError(
                        f"Grounding REQUIRED but no web search performed. "
                        f"Model: {req.model_name}, Tool calls: {tool_call_count}, "
                        f"Tried: tool_choice={tool_choice}" + 
                        (" with provoker" if tool_choice == "auto" else "")
                    )
            
            # Parse JSON if expected
            json_obj = None
            json_valid = False
            if req.schema and output_text:
                try:
                    json_obj = json.loads(output_text)
                    json_valid = True
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
            
            # Extract citations
            citations = []
            for item in output_items:
                if (item.get("type") or "").startswith("web_search"):
                    # Try to extract citations if present
                    if "citations" in item:
                        for citation in item.get("citations", []):
                            citations.append({
                                'url': citation.get('url', ''),
                                'title': citation.get('title', ''),
                                'snippet': citation.get('snippet', '')
                            })
            
            # Extract and flatten usage with the robust flattener
            usage_raw = data.get('usage', {}) or {}
            flat_usage = self._flatten_usage_openai(usage_raw)
            print(f"[DEBUG] Raw usage data: {usage_raw}", flush=True)  # Debug
            print(f"[DEBUG] Flattened usage: {flat_usage}", flush=True)  # Debug
            
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
                system_fingerprint=data.get('system_fingerprint'),
                usage=flat_usage,
                meta={
                    "temperature": body["temperature"],
                    "seed": req.seed,
                    "top_p": req.top_p,
                    "api": "responses_http",
                    "tool_choice": tool_choice,
                    "grounding_mode": req.grounding_mode.value
                }
            )
            
        except Exception as e:
            logger.error(f"HTTP Responses API error: {str(e)[:500]}")
            print(f"[ERROR] Exception type: {type(e).__name__}", flush=True)
            print(f"[ERROR] Exception details: {str(e)[:1000]}", flush=True)
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()[:2000]}", flush=True)
            
            # Fail closed for REQUIRED mode
            if req.grounding_mode == GroundingMode.REQUIRED:
                raise
            
            # Try to extract usage from partial data if available
            usage_raw = {}
            try:
                if 'data' in locals():
                    usage_raw = data.get('usage', {}) or {}
            except:
                pass
            flat_usage = self._flatten_usage_openai(usage_raw)
            
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
                usage=flat_usage,
                meta={"api": "responses_http", "failed": True}
            )
    
    def run(self, req: RunRequest) -> RunResult:
        """Alias for run_sync for compatibility"""
        return self.run_sync(req)
    
    def run_sync(self, req: RunRequest) -> RunResult:
        """Synchronous run method - now uses the new adapter with soft-required logic"""
        from .openai_adapter import run_openai_with_grounding
        
        # Map GroundingMode enum to string
        mode_map = {
            GroundingMode.OFF: "UNGROUNDED",
            GroundingMode.PREFERRED: "PREFERRED", 
            GroundingMode.REQUIRED: "REQUIRED"
        }
        mode = mode_map.get(req.grounding_mode, "UNGROUNDED")
        
        # Use the new adapter
        result = run_openai_with_grounding(
            client=self.client,
            model=req.model_name,
            mode=mode,
            prompt=req.user_prompt,
            system=req.system_text,
            als=req.als_block,
            strict_fail=True
        )
        
        # Map back to RunResult
        return RunResult(
            run_id=req.run_id,
            provider="openai",
            model_name=req.model_name,
            region=None,
            grounded_effective=result["grounded_effective"],
            tool_call_count=result["tool_call_count"],
            citations=[],  # Would need to extract from raw response
            json_text=result["text"],
            json_obj=None,  # Would need JSON parsing
            json_valid=False,  # Would need validation
            latency_ms=0,  # Would need timing
            error=result.get("error_code"),
            system_fingerprint=None,
            usage={},
            meta={
                "soft_required": result["soft_required"],
                "tool_choice_sent": result["tool_choice_sent"],
                "why_not_grounded": result["why_not_grounded"],
                "status": result["status"]
            }
        )
    
    def run_sync_legacy(self, req: RunRequest) -> RunResult:
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
        # CRITICAL: GPT-5 cannot use JSON schema AND web_search together
        # If grounding is needed, skip the schema enforcement
        if req.schema and not needs_grounding:
            kwargs["extra_body"] = self._build_schema_format(req.schema)
        elif req.schema and needs_grounding:
            logger.warning("GPT-5 limitation: Cannot use JSON schema with web_search grounding")
        
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
                usage=self._extract_usage(response),  # SDK response uses old extractor
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
        
        # Use HTTP path for grounded requests to force tool usage
        if needs_grounding:
            logger.info(f"Using HTTP path for grounded request: model={req.model_name}")
            print(f"[DEBUG] needs_grounding={needs_grounding}, model={req.model_name}, has_schema={bool(req.schema)}", flush=True)
            print(f"[DEBUG] Calling HTTP grounded method for {req.model_name}", flush=True)  # Debug
            return await self._http_grounded_with_schema(req)
        
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
        # CRITICAL: GPT-5 cannot use JSON schema AND web_search together
        # If grounding is needed, skip the schema enforcement
        if req.schema and not needs_grounding:
            kwargs["extra_body"] = self._build_schema_format(req.schema)
        elif req.schema and needs_grounding:
            logger.warning("GPT-5 limitation: Cannot use JSON schema with web_search grounding")
        
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
                usage=self._extract_usage(response),  # SDK response uses old extractor
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