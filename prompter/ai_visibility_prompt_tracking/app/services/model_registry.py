from typing import Dict
from uuid import UUID
from .adapters.base import ModelAdapter

class ModelRegistry:
    def __init__(self):
        self._by_id: Dict[UUID, ModelAdapter] = {}

    def register(self, model_id: UUID, adapter: ModelAdapter):
        self._by_id[model_id] = adapter

    def get(self, model_id: UUID) -> ModelAdapter:
        return self._by_id[model_id]
