# DEPRECATED SHIM – do not add logic here.
# Keep imports stable for older code (Templates tab, old orchestrator, etc.)
import warnings

warnings.warn(
    "Importing from app.llm.vertex_genai_adapter is deprecated. "
    "Please use: from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter",
    DeprecationWarning,
    stacklevel=2
)

from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter

__all__ = ["VertexGenAIAdapter"]