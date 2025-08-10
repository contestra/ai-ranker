from typing import List, Dict, Any, Optional
import anthropic
from app.llm.base import LLMAdapter
from app.config import settings

class AnthropicAdapter(LLMAdapter):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return {
            "text": response.content[0].text,
            "tokens": response.usage.input_tokens + response.usage.output_tokens,
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
        async with self.client.messages.stream(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def get_embedding(self, text: str) -> List[float]:
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        dummy_embedding = [float(int(c, 16)) / 15.0 for c in text_hash * 48][:1536]
        return dummy_embedding