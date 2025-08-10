from typing import Dict
from app.llm.base import LLMAdapter
from app.llm.openai_adapter import OpenAIAdapter
from app.llm.google_adapter import GoogleAdapter
from app.llm.anthropic_adapter import AnthropicAdapter

_adapters: Dict[str, LLMAdapter] = {}

def get_llm_adapter(vendor: str) -> LLMAdapter:
    if vendor not in _adapters:
        if vendor == "openai":
            _adapters[vendor] = OpenAIAdapter()
        elif vendor == "google":
            _adapters[vendor] = GoogleAdapter()
        elif vendor == "anthropic":
            _adapters[vendor] = AnthropicAdapter()
        else:
            raise ValueError(f"Unknown LLM vendor: {vendor}")
    return _adapters[vendor]