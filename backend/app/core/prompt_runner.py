from typing import List, Dict, Any, Optional
import asyncio
import hashlib
from sqlalchemy.orm import Session
from app.llm.langchain_adapter import LangChainAdapter
from app.models import Run, Prompt, Completion, Model
from app.cache.upstash_cache import cache

class PromptRunner:
    def __init__(self, db: Session):
        self.db = db
        self.adapter = LangChainAdapter()
    
    async def run_experiment(
        self,
        experiment_id: int,
        model_vendor: str,
        model_name: str,
        prompts: List[str],
        repetitions: int = 3,
        temperature: float = 0.1,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Run:
        model = self.db.query(Model).filter(
            Model.vendor == model_vendor,
            Model.name == model_name
        ).first()
        
        if not model:
            model = Model(
                vendor=model_vendor,
                name=model_name,
                mode="grounded" if grounded else "ungrounded"
            )
            self.db.add(model)
            self.db.commit()
        
        run = Run(
            experiment_id=experiment_id,
            model_id=model.id,
            temperature=temperature,
            grounded=grounded,
            seed=seed
        )
        self.db.add(run)
        self.db.commit()
        
        for prompt_text in prompts:
            for rep in range(repetitions):
                cache_key = f"prompt:{hashlib.md5(f'{prompt_text}:{model_vendor}:{temperature}:{grounded}:{seed+rep if seed else rep}'.encode()).hexdigest()}"
                
                cached_response = await cache.get(cache_key)
                if cached_response:
                    response = cached_response
                else:
                    response = await self.adapter.generate(
                        vendor=model_vendor,
                        prompt=prompt_text,
                        temperature=temperature,
                        grounded=grounded,
                        seed=seed + rep if seed else None
                    )
                    await cache.set(cache_key, response, ttl=86400)
                
                prompt = Prompt(
                    run_id=run.id,
                    type="B2E" if "associated with" in prompt_text else "E2B",
                    input_text=prompt_text,
                    variant_id=rep
                )
                self.db.add(prompt)
                self.db.flush()
                
                completion = Completion(
                    prompt_id=prompt.id,
                    text=response["text"],
                    tokens=response.get("tokens"),
                    raw_json=response.get("raw")
                )
                self.db.add(completion)
        
        self.db.commit()
        return run
    
    async def generate_with_threshold(
        self,
        prompt_text: str,
        model_vendor: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        tokens = []
        full_text = ""
        
        async for token in self.adapter.generate_stream(
            vendor=model_vendor,
            prompt=prompt_text,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            tokens.append(token)
            full_text += token
        
        return {
            "tokens": tokens,
            "full_text": full_text
        }