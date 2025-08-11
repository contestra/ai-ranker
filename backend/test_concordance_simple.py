import json
from pydantic import BaseModel
from typing import Optional
import numpy as np

class TestModel(BaseModel):
    value: float
    
# Test what happens with inf in Pydantic
try:
    m = TestModel(value=float('inf'))
    print(f"Pydantic model created with inf: {m}")
    json_str = m.model_dump_json()
    print(f"JSON: {json_str}")
except Exception as e:
    print(f"Error with inf: {e}")

# Test with 999.0
try:
    m = TestModel(value=999.0)
    print(f"Pydantic model created with 999.0: {m}")
    json_str = m.model_dump_json()
    print(f"JSON: {json_str}")
except Exception as e:
    print(f"Error with 999.0: {e}")