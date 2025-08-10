from typing import List, Dict, Any, Optional
import openai
from app.llm.base import LLMAdapter
from app.config import settings

class OpenAIAdapter(LLMAdapter):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-5"
        self.embedding_model = "text-embedding-3-small"
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            kwargs["seed"] = seed
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return {
            "text": response.choices[0].message.content,
            "tokens": response.usage.total_tokens,
            "raw": response.model_dump()
        }
    
    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ):
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        if seed is not None:
            kwargs["seed"] = seed
        
        response = await self.client.chat.completions.create(**kwargs)
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def get_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding