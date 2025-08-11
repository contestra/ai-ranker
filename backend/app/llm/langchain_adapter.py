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
                model="gpt-5",  # GPT-5 - the only model now
                temperature=1.0,  # GPT-5 only supports default temperature
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
        
        # Only set max_tokens for models that support it
        if vendor != "google":
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
        
        return {
            "text": response.content,
            "tokens": response.response_metadata.get("token_usage", {}).get("total_tokens"),
            "raw": response.response_metadata
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