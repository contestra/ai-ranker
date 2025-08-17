"""
Sanity test to verify both import paths return the same class object
"""

# Test that both import paths work and return the same class
from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter as NewImport

# This should trigger a deprecation warning
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    from app.llm.vertex_genai_adapter import VertexGenAIAdapter as OldImport
    
    # Check we got the deprecation warning
    assert len(w) == 1
    assert issubclass(w[0].category, DeprecationWarning)
    assert "deprecated" in str(w[0].message).lower()
    print(f"[PASS] Deprecation warning triggered: {w[0].message}")

# Verify both imports return the exact same class object
assert NewImport is OldImport, "Import paths don't return the same class!"
print("[PASS] Both import paths return the same class object")

# Verify it's the actual adapter class
assert hasattr(NewImport, 'analyze_with_gemini'), "Missing expected method"
print("[PASS] Class has expected methods")

print("\n[SUCCESS] All import sanity checks passed!")
print("   Old path (deprecated): app.llm.vertex_genai_adapter")
print("   New path (use this):  app.llm.adapters.vertex_genai_adapter")