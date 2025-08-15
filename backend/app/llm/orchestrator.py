"""
LLM Orchestrator - Coordinates between OpenAI and Vertex adapters
Production-grade implementation following ChatGPT's architecture
"""

import logging
import inspect
from typing import Optional
from .adapters.types import RunRequest, RunResult, GroundingMode
from .adapters.openai_production import OpenAIProductionAdapter
from .adapters.vertex_genai_adapter import VertexGenAIAdapter

logger = logging.getLogger(__name__)

class LLMOrchestrator:
    """
    Central orchestrator for LLM operations
    Routes requests to appropriate provider adapter
    Handles both sync and async execution
    """
    
    def __init__(
        self, 
        gcp_project: str = "contestra-ai", 
        vertex_region: str = "europe-west4",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize orchestrator with provider adapters
        
        Args:
            gcp_project: GCP project ID for Vertex
            vertex_region: Vertex region
            openai_api_key: Optional OpenAI API key (uses env var if not provided)
        """
        logger.info(f"Initializing LLM Orchestrator: project={gcp_project}, region={vertex_region}")
        
        # Initialize adapters
        self.openai = OpenAIProductionAdapter(api_key=openai_api_key)
        self.vertex = VertexGenAIAdapter(project=gcp_project, location=vertex_region)
        
        # Provider mapping
        self.providers = {
            "openai": self.openai,
            "vertex": self.vertex,
            "gemini": self.vertex,  # Alias for vertex
            "google": self.vertex,  # Another alias
        }
        
        logger.info("LLM Orchestrator initialized successfully")
    
    def run(self, req: RunRequest) -> RunResult:
        """
        Synchronous run method
        Routes to appropriate provider adapter
        
        Args:
            req: RunRequest with all parameters
            
        Returns:
            RunResult from the provider
            
        Raises:
            ValueError: If provider is unknown
            RuntimeError: If grounding requirements not met
        """
        # Validate provider
        provider_key = req.provider.lower()
        if provider_key not in self.providers:
            raise ValueError(
                f"Unknown provider: {req.provider}. "
                f"Available providers: {list(self.providers.keys())}"
            )
        
        # Get adapter
        adapter = self.providers[provider_key]
        
        # Log request
        logger.info(
            f"Processing run request: "
            f"run_id={req.run_id}, "
            f"provider={req.provider}, "
            f"model={req.model_name}, "
            f"grounding_mode={req.grounding_mode}"
        )
        
        try:
            # Execute request
            if hasattr(adapter, 'run_sync'):
                result = adapter.run_sync(req)
            else:
                result = adapter.run(req)
            
            # Log success
            logger.info(
                f"Run completed: "
                f"run_id={req.run_id}, "
                f"grounded_effective={result.grounded_effective}, "
                f"tool_calls={result.tool_call_count}, "
                f"latency_ms={result.latency_ms}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Run failed: "
                f"run_id={req.run_id}, "
                f"error={str(e)}"
            )
            raise
    
    async def run_async(self, req: RunRequest) -> RunResult:
        """
        Asynchronous run method
        Routes to appropriate provider adapter
        
        Args:
            req: RunRequest with all parameters
            
        Returns:
            RunResult from the provider
            
        Raises:
            ValueError: If provider is unknown
            RuntimeError: If grounding requirements not met
        """
        # Validate provider
        provider_key = req.provider.lower()
        if provider_key not in self.providers:
            raise ValueError(
                f"Unknown provider: {req.provider}. "
                f"Available providers: {list(self.providers.keys())}"
            )
        
        # Get adapter
        adapter = self.providers[provider_key]
        
        # Log request
        logger.info(
            f"Processing async run request: "
            f"run_id={req.run_id}, "
            f"provider={req.provider}, "
            f"model={req.model_name}, "
            f"grounding_mode={req.grounding_mode}"
        )
        
        try:
            # Execute request - check if adapter has async method
            if hasattr(adapter, 'run_async'):
                result = await adapter.run_async(req)
            else:
                # Fall back to sync execution in thread pool
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, adapter.run, req)
            
            # Log success
            logger.info(
                f"Async run completed: "
                f"run_id={req.run_id}, "
                f"grounded_effective={result.grounded_effective}, "
                f"tool_calls={result.tool_call_count}, "
                f"latency_ms={result.latency_ms}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Async run failed: "
                f"run_id={req.run_id}, "
                f"error={str(e)}"
            )
            raise
    
    async def __call__(self, req: RunRequest) -> RunResult:
        """
        Make orchestrator callable
        Defaults to async execution
        """
        return await self.run_async(req)
    
    def get_supported_models(self, provider: str) -> list:
        """
        Get list of supported models for a provider
        
        Args:
            provider: Provider name
            
        Returns:
            List of model names
        """
        models = {
            "openai": [
                "gpt-4o",
                "gpt-4o-mini", 
                "gpt-5-chat-latest",
                "gpt-5-mini",
                "gpt-5-nano"
            ],
            "vertex": [
                "publishers/google/models/gemini-2.0-flash-exp",
                "publishers/google/models/gemini-1.5-pro-002", 
                "publishers/google/models/gemini-1.5-flash-002"
            ]
        }
        
        provider_key = provider.lower()
        return models.get(provider_key, [])
    
    def validate_request(self, req: RunRequest) -> bool:
        """
        Validate a run request
        
        Args:
            req: RunRequest to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If request is invalid
        """
        # Check provider
        if req.provider.lower() not in self.providers:
            raise ValueError(f"Unknown provider: {req.provider}")
        
        # Check required fields
        if not req.run_id:
            raise ValueError("run_id is required")
        
        if not req.user_prompt:
            raise ValueError("user_prompt is required")
        
        # Check ALS block length
        if req.als_block and len(req.als_block) > 350:
            raise ValueError(f"ALS block too long: {len(req.als_block)} chars (max 350)")
        
        # Check temperature range
        if not 0 <= req.temperature <= 2:
            raise ValueError(f"Temperature out of range: {req.temperature} (0-2)")
        
        # Check top_p range
        if req.top_p is not None and not 0 <= req.top_p <= 1:
            raise ValueError(f"top_p out of range: {req.top_p} (0-1)")
        
        return True