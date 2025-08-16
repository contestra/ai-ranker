# DEPRECATED SHIM – do not add logic here.
# Keep imports stable for older code (Templates tab, old orchestrator, etc.)
from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter

__all__ = ["VertexGenAIAdapter"]