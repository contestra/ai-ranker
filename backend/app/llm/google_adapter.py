from typing import List, Dict, Any, Optional
import google.generativeai as genai
from app.llm.base import LLMAdapter
from app.config import settings

class GoogleAdapter(LLMAdapter):
    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.embedding_model = 'models/text-embedding-004'
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        
        return {
            "text": response.text,
            "tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
            "raw": response
        }
    
    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ):
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config,
            stream=True
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    
    async def get_embedding(self, text: str) -> List[float]:
        result = await genai.embed_content_async(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']