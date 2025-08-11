import json
import math

# Test JSON serialization of inf
try:
    json.dumps({"value": float('inf')})
    print("JSON can serialize inf")
except ValueError as e:
    print(f"JSON cannot serialize inf: {e}")

# Test with 999
try:
    json.dumps({"value": 999.0})
    print("JSON can serialize 999.0")
except ValueError as e:
    print(f"JSON cannot serialize 999.0: {e}")