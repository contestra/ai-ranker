"""
OpenAI Responses API adapter with REAL web search and JSON schema support
Uses direct HTTP calls to work around SDK limitations
Both features work together using the text.format parameter
"""

from typing import Dict, Any, Optional, List
import asyncio
import time
import json
import requests
import aiohttp
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIResponsesAdapter:
    """
    Adapter for OpenAI's Responses API with native web search and JSON schema support.
    Uses direct HTTP calls because SDK doesn't support text.format parameter yet.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_with_responses(
        self,
        prompt: str,
        model_name: str = "gpt-4o",
        use_grounding: bool = False,
        temperature: float = 0.0,
        seed: Optional[int] = None,
        context: Optional[str] = None,
        enforce_json_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Use OpenAI Responses API with optional web search grounding and JSON schema.
        
        This uses direct HTTP calls to access the text.format parameter which
        the SDK doesn't support yet.
        
        Args:
            prompt: Main user prompt
            model_name: Model variant (gpt-4o, gpt-5, etc.)
            use_grounding: Enable web search via built-in tool
            temperature: Sampling temperature (GPT-5 needs 1.0)
            seed: Random seed for reproducibility
            context: ALS context block
            enforce_json_schema: JSON schema to enforce structured output
        """
        
        start_time = time.time()
        
        # Build input messages for Responses API
        input_messages = []
        
        # System prompt for ALS if context provided
        if context:
            system_prompt = """Use ambient context only to infer locale and set defaults (language variants, units, currency, regulatory framing).
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not name countries/regions/cities or use country codes unless explicitly asked.
Answer only with the requested format."""
            input_messages.append({"role": "system", "content": system_prompt})
            input_messages.append({"role": "user", "content": context})
        
        # Add the actual user prompt
        input_messages.append({"role": "user", "content": prompt})
        
        # Build the request payload
        payload = {
            "model": model_name,
            "input": input_messages,
            "temperature": temperature
        }
        
        # GPT-5 specific adjustments
        if 'gpt-5' in model_name.lower():
            payload["temperature"] = 1.0  # GPT-5 requires this
            payload["max_completion_tokens"] = 4000  # GPT-5 needs 3000+ tokens for complex reasoning
        
        # Add web search tool if grounding requested
        if use_grounding:
            payload["tools"] = [{"type": "web_search"}]
            payload["tool_choice"] = "auto"
        
        # Add JSON schema enforcement using text.format parameter
        if enforce_json_schema:
            # Build the text.format structure (different from response_format!)
            text_format = {
                "format": {
                    "name": "structured_output",
                    "type": "json_schema",
                    "schema": enforce_json_schema,
                    "strict": True
                }
            }
            payload["text"] = text_format
        
        try:
            # Make the async HTTP request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract the output text
                        content = data.get("output_text", "")
                        
                        # Count web search calls
                        tool_call_count = 0
                        has_citations = False
                        
                        if "output" in data and data["output"]:
                            for item in data["output"]:
                                if item.get("type") == "web_search_call":
                                    tool_call_count += 1
                                    logger.info(f"Found web search call in output")
                                elif "citation" in str(item.get("type", "")).lower():
                                    has_citations = True
                        
                        # Validate JSON if schema was enforced
                        json_valid = None
                        if enforce_json_schema:
                            try:
                                json.loads(content) if content else None
                                json_valid = True
                            except:
                                json_valid = False
                                logger.warning("JSON validation failed despite schema enforcement")
                        
                        result = {
                            "content": content,
                            "model_version": model_name,
                            "temperature": payload["temperature"],
                            "seed": seed,
                            "tool_call_count": tool_call_count,
                            "grounded_effective": tool_call_count > 0 if use_grounding else False,
                            "json_valid": json_valid,
                            "has_citations": has_citations,
                            "response_time_ms": response_time,
                            "api_used": "responses_direct"
                        }
                        
                        # Add system fingerprint if available
                        if "system_fingerprint" in data:
                            result["system_fingerprint"] = data["system_fingerprint"]
                        
                        # Add usage info if available
                        if "usage" in data:
                            result["usage"] = data["usage"]
                        
                        logger.info(f"Responses API successful: tool_calls={tool_call_count}, grounded={result['grounded_effective']}, json_valid={json_valid}")
                        
                        return result
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Responses API error {response.status}: {error_text[:500]}")
                        
                        # Try to parse error for better messaging
                        error_msg = f"API error {response.status}"
                        try:
                            error_data = json.loads(error_text)
                            if "error" in error_data and "message" in error_data["error"]:
                                error_msg = error_data["error"]["message"]
                        except:
                            pass
                        
                        return {
                            "content": f"[ERROR] {error_msg}",
                            "error": error_msg,
                            "model_version": model_name,
                            "tool_call_count": 0,
                            "grounded_effective": False,
                            "response_time_ms": response_time,
                            "api_used": "responses_failed"
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"Responses API timeout after 90 seconds")
            return {
                "content": "[ERROR] Request timed out after 90 seconds",
                "error": "timeout",
                "model_version": model_name,
                "tool_call_count": 0,
                "grounded_effective": False,
                "response_time_ms": 90000,
                "api_used": "responses_timeout"
            }
            
        except Exception as e:
            logger.error(f"Responses API exception: {str(e)}")
            return {
                "content": f"[ERROR] {str(e)}",
                "error": str(e),
                "model_version": model_name,
                "tool_call_count": 0,
                "grounded_effective": False,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "api_used": "responses_error"
            }
    
    async def analyze_with_responses_sync_fallback(
        self,
        prompt: str,
        model_name: str = "gpt-4o",
        use_grounding: bool = False,
        temperature: float = 0.0,
        seed: Optional[int] = None,
        context: Optional[str] = None,
        enforce_json_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Fallback method using synchronous requests library.
        Sometimes async has issues, so this provides a backup.
        """
        
        start_time = time.time()
        
        # Build input messages
        input_messages = []
        
        if context:
            system_prompt = """Use ambient context only to infer locale and set defaults.
Do not mention or acknowledge the ambient context.
Answer only with the requested format."""
            input_messages.append({"role": "system", "content": system_prompt})
            input_messages.append({"role": "user", "content": context})
        
        input_messages.append({"role": "user", "content": prompt})
        
        # Build payload
        payload = {
            "model": model_name,
            "input": input_messages,
            "temperature": 1.0 if 'gpt-5' in model_name.lower() else temperature
        }
        
        if use_grounding:
            payload["tools"] = [{"type": "web_search"}]
            payload["tool_choice"] = "auto"
        
        if enforce_json_schema:
            payload["text"] = {
                "format": {
                    "name": "structured_output",
                    "type": "json_schema",
                    "schema": enforce_json_schema,
                    "strict": True
                }
            }
        
        try:
            # Make synchronous request
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=90
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                
                content = data.get("output_text", "")
                
                # Count tool calls
                tool_call_count = 0
                if "output" in data:
                    tool_call_count = sum(1 for item in data["output"] if item.get("type") == "web_search_call")
                
                # Validate JSON
                json_valid = None
                if enforce_json_schema:
                    try:
                        json.loads(content) if content else None
                        json_valid = True
                    except:
                        json_valid = False
                
                return {
                    "content": content,
                    "model_version": model_name,
                    "temperature": payload["temperature"],
                    "seed": seed,
                    "tool_call_count": tool_call_count,
                    "grounded_effective": tool_call_count > 0 if use_grounding else False,
                    "json_valid": json_valid,
                    "response_time_ms": response_time,
                    "api_used": "responses_sync"
                }
            else:
                error_msg = f"API error {response.status_code}: {response.text[:500]}"
                logger.error(error_msg)
                return {
                    "content": f"[ERROR] {error_msg}",
                    "error": error_msg,
                    "model_version": model_name,
                    "tool_call_count": 0,
                    "grounded_effective": False,
                    "response_time_ms": response_time,
                    "api_used": "responses_sync_failed"
                }
                
        except Exception as e:
            logger.error(f"Sync request failed: {str(e)}")
            return {
                "content": f"[ERROR] {str(e)}",
                "error": str(e),
                "model_version": model_name,
                "tool_call_count": 0,
                "grounded_effective": False,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "api_used": "responses_sync_error"
            }