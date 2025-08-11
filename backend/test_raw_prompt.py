"""
Test to see EXACTLY what prompt is sent to GPT-5 for AVEA
"""
import asyncio
from app.api.brand_entity_strength import create_probe_prompt

# Test what prompt is generated
system_prompt, user_prompt = create_probe_prompt("AVEA", industry_hint=None)

print("="*60)
print("SYSTEM PROMPT:")
print("="*60)
print(system_prompt)
print("\n" + "="*60)
print("USER PROMPT:")
print("="*60)
print(user_prompt)
print("="*60)

# Also test with industry hint to see the difference
system_prompt2, user_prompt2 = create_probe_prompt("AVEA", industry_hint="health/wellness")
print("\nWITH INDUSTRY HINT (NOT USED IN ACTUAL CODE):")
print("="*60)
print(user_prompt2[:200] + "...")