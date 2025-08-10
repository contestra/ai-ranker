from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np

class LLMAdapter(ABC):
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        grounded: bool = False,
        seed: Optional[int] = None
    ) -> Any:
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass
    
    def normalize(self, vec: List[float]) -> np.ndarray:
        vec_array = np.array(vec)
        mag = np.linalg.norm(vec_array)
        return vec_array / mag if mag > 0 else vec_array
    
    def google_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        return float(np.dot(self.normalize(vec_a), self.normalize(vec_b)))