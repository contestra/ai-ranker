from dataclasses import dataclass
from typing import Optional

@dataclass
class ProviderResponse:
    text: str
    token_usage: dict | None
    raw_meta: dict | None
    citations: list[dict] | None
    model_version: str | None
    latency_ms: int | None

class ModelAdapter:
    name: str

    def generate(
        self,
        prompt_text: str,
        language: str,
        geo_country: str,
        grounded_context: Optional[str],
        grounding_mode: str,
        timeout_s: int = 60,
        tracing_ctx: Optional[dict] = None,
        proxy_endpoint: Optional[str] = None,
    ) -> ProviderResponse:
        raise NotImplementedError
