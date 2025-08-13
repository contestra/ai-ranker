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
        if vendor != "google":
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
        
        response = await model.ainvoke(
            messages,
            config={"callbacks": self.callbacks}
        )
        
        # Debug logging for GPT-5 (disabled due to Windows encoding issues)
        # if vendor == "openai":
        #     print(f"DEBUG GPT-5 response type: {type(response)}")
        #     print(f"DEBUG GPT-5 response content: {response.content if hasattr(response, 'content') else 'NO CONTENT ATTR'}")
        #     print(f"DEBUG GPT-5 response metadata: {response.response_metadata if hasattr(response, 'response_metadata') else 'NO METADATA'}")
        
        return {
            "text": response.content if hasattr(response, 'content') else str(response),
            "tokens": response.response_metadata.get("token_usage", {}).get("total_tokens") if hasattr(response, 'response_metadata') else None,
            "raw": response.response_metadata if hasattr(response, 'response_metadata') else {}
        }
    
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
                                  temperature: float = 0.1, seed: int = None, context: str = None) -> Dict[str, Any]:
        """Use Gemini with optional grounding (web search) and return metadata
        
        Args:
            prompt: The main user prompt (kept naked/unmodified)
            use_grounding: Whether to enable web search
            model_name: Model variant to use
            temperature: Temperature for randomness
            seed: Seed for reproducibility
            context: Optional context/evidence pack as separate message
        """
        import time
        start_time = time.time()
        
        # Retry logic for empty responses
        max_retries = 3
        retry_delay = 2  # seconds
        
        # Create a new model instance with the requested model name
        # This allows us to use different Gemini models dynamically
        model = ChatGoogleGenerativeAI(
            model=model_name,  # Use the requested model (gemini-2.5-pro, gemini-2.0-flash-exp, etc.)
            temperature=temperature,
            google_api_key=settings.google_api_key
        )
        
        # Build messages array with proper separation
        messages = []
        
        # Only add ALS-specific system prompt when context is provided
        if context:
            # System prompt that allows silent locale adoption while preventing explicit mentions
            # This is critical for Ambient Blocks to work correctly
            system_prompt = """Answer the user's question directly and naturally.
You may use any ambient context provided only to infer locale and set defaults (language variants, units, currency, regulatory framing).
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not state or imply country/region/city names unless the user explicitly asks.
Do not preface with anything about training data or location. Produce the answer only."""
            
            messages.append(SystemMessage(content=system_prompt))
            # Add context FIRST (before the actual question)
            # This makes it feel more like ambient system state
            messages.append(HumanMessage(content=context))
        
        if use_grounding:
            # Add instruction for Gemini to use its grounding capability
            grounded_prompt = f"""Please search the web and provide an accurate, up-to-date answer to the following question:

{prompt}

Use recent information from reliable sources."""
            messages.append(HumanMessage(content=grounded_prompt))
        else:
            # Keep prompt naked
            messages.append(HumanMessage(content=prompt))
        
        # DEBUG LOGGING - Show exactly what's being sent (disabled to avoid interference)
        # print("\n" + "="*80)
        # print("EXACT MESSAGES BEING SENT TO GEMINI:")
        # print("="*80)
        # for i, msg in enumerate(messages, 1):
        #     print(f"\nMessage {i} (Type: {type(msg).__name__}):")
        #     print("-"*40)
        #     # Show repr to see any hidden characters
        #     print(repr(msg.content))
        #     # Also check for any metadata
        #     if hasattr(msg, 'additional_kwargs'):
        #         print(f"Additional kwargs: {msg.additional_kwargs}")
        #     if hasattr(msg, '__dict__'):
        #         # Check for any hidden attributes
        #         for key, val in msg.__dict__.items():
        #             if key not in ['content', 'type'] and val:
        #                 print(f"Hidden attr {key}: {val}")
        #     print("-"*40)
        # print("\nModel settings:")
        # print(f"- Model: {model_name}")
        # print(f"- Temperature: {temperature}")
        # print(f"- Seed: {seed}")
        # print(f"- Use grounding: {use_grounding}")
        # print("="*80 + "\n")
        
        # Retry loop for empty responses
        for attempt in range(max_retries):
            try:
                response = await model.ainvoke(
                    messages,
                    config={"callbacks": self.callbacks}
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                # Check if response is empty
                content = response.content if hasattr(response, 'content') else str(response)
                if not content or len(content.strip()) == 0:
                    print(f"[WARNING] Gemini returned empty response on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Final attempt failed, return error response
                        return {
                            "content": "[ERROR] Gemini returned empty response after multiple retries.",
                            "system_fingerprint": None,
                            "model_version": model_name,
                            "temperature": temperature,
                            "seed": seed,
                            "response_time_ms": response_time,
                            "token_count": {},
                            "error": "empty_response",
                            "retry_attempts": max_retries
                        }
                
                # Successful response
                result = {
                    "content": content,
                    "system_fingerprint": None,  # Gemini doesn't provide this
                    "model_version": model_name,
                    "temperature": temperature,
                    "seed": seed,
                    "response_time_ms": response_time,
                    "token_count": {}
                }
                break  # Success, exit retry loop
                
            except Exception as e:
                print(f"[ERROR] Gemini API error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # Final attempt failed
                    return {
                        "content": f"[ERROR] Gemini API error: {str(e)}",
                        "system_fingerprint": None,
                        "model_version": model_name,
                        "temperature": temperature,
                        "seed": seed,
                        "response_time_ms": int((time.time() - start_time) * 1000),
                        "token_count": {},
                        "error": str(e),
                        "retry_attempts": max_retries
                    }
        
        # Try to get token usage if available
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if 'token_usage' in metadata:
                result["token_count"] = metadata['token_usage']
        
        return result
    
    async def analyze_with_gpt4(self, prompt: str, model_name: str = "gpt-4o", 
                                temperature: float = 0.1, seed: int = None, context: str = None) -> Dict[str, Any]:
        """Use GPT-5/GPT-4o models (note: GPT-5 models currently return empty responses) and return metadata
        
        Args:
            prompt: The main user prompt (kept naked/unmodified)
            model_name: Model variant to use
            temperature: Temperature for randomness
            seed: Seed for reproducibility
            context: Optional context/evidence pack as separate message
        """
        import time
        start_time = time.time()
        
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
                model_kwargs={"max_completion_tokens": 2000}  # GPT-5 specific parameter
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
            system_prompt = """Answer the user's question directly and naturally.
You may use any ambient context provided only to infer locale and set defaults (language variants, units, currency, regulatory framing).
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not state or imply country/region/city names unless the user explicitly asks.
Do not preface with anything about training data or location. Produce the answer only."""
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
                
                # Successful response
                result = {
                    "content": content,
                    "system_fingerprint": None,
                    "model_version": model_name,
                    "temperature": temperature,
                    "seed": seed,
                    "response_time_ms": response_time,
                    "token_count": {}
                }
                
                # OpenAI provides system_fingerprint and token usage
                if hasattr(response, 'response_metadata'):
                    metadata = response.response_metadata
                    if 'system_fingerprint' in metadata:
                        result["system_fingerprint"] = metadata['system_fingerprint']
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