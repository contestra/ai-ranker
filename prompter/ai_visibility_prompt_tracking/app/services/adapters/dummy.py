from time import sleep
from .base import ModelAdapter, ProviderResponse

class DummyAdapter(ModelAdapter):
    name = "dummy"
    def generate(self, prompt_text, language, geo_country, grounded_context, grounding_mode, timeout_s=60, tracing_ctx=None, proxy_endpoint=None):
        sleep(0.1)
        body = [
            "[DUMMY ADAPTER]",
            f"lang={language} geo={geo_country} grounded={grounding_mode}",
            f"context_len={len(grounded_context) if grounded_context else 0}",
            "",
            "This is a stubbed answer."
        ]
        return ProviderResponse(
            text="\n".join(body),
            token_usage={"input": 0, "output": 20},
            raw_meta={"adapter": "dummy"},
            citations=None,
            model_version="dummy-0.1",
            latency_ms=100,
        )
