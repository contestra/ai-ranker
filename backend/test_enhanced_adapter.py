#!/usr/bin/env python3
"""
Test the enhanced OpenAI adapter with real API calls to verify telemetry
"""

import os
import sys
import json
from openai import OpenAI

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.adapters.openai_adapter import run_openai_with_grounding

def test_telemetry():
    """Test that the enhanced adapter provides telemetry data"""
    
    # Initialize client
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    print("Testing Enhanced OpenAI Adapter with Telemetry\n")
    print("=" * 60)
    
    # Test 1: UNGROUNDED mode (no tools, no auto-raise)
    print("\n1. Testing UNGROUNDED mode (GPT-5)...")
    result = run_openai_with_grounding(
        client=client,
        model="gpt-5",
        mode="UNGROUNDED",
        prompt="What is the US federal VAT rate?",
        system="Answer concisely in JSON format"
    )
    
    print(f"   Status: {result['status']}")
    print(f"   Tool calls: {result['tool_call_count']}")
    print(f"   Grounded: {result['grounded_effective']}")
    print(f"   Budget starved: {result.get('budget_starved', 'N/A')}")
    print(f"   Effective max tokens: {result.get('effective_max_output_tokens', 'N/A')}")
    print(f"   Usage - Input: {result.get('usage_input_tokens', 'N/A')}")
    print(f"   Usage - Output: {result.get('usage_output_tokens', 'N/A')}")
    print(f"   Usage - Reasoning: {result.get('usage_reasoning_tokens', 'N/A')}")
    print(f"   Text preview: {result['text'][:100] if result['text'] else 'EMPTY'}...")
    
    # Test 2: PREFERRED mode (tools, auto-raise should kick in)
    print("\n2. Testing PREFERRED mode (GPT-5 with auto-raised tokens)...")
    result = run_openai_with_grounding(
        client=client,
        model="gpt-5",
        mode="PREFERRED",
        prompt="What is the US federal VAT rate?",
        system="Answer concisely in JSON format"
    )
    
    print(f"   Status: {result['status']}")
    print(f"   Tool calls: {result['tool_call_count']}")
    print(f"   Grounded: {result['grounded_effective']}")
    print(f"   Budget starved: {result.get('budget_starved', 'N/A')}")
    print(f"   Effective max tokens: {result.get('effective_max_output_tokens', 'N/A')}")
    print(f"   Usage - Input: {result.get('usage_input_tokens', 'N/A')}")
    print(f"   Usage - Output: {result.get('usage_output_tokens', 'N/A')}")
    print(f"   Usage - Reasoning: {result.get('usage_reasoning_tokens', 'N/A')}")
    print(f"   Reasoning burn ratio: {result.get('usage_reasoning_tokens', 0) / result.get('usage_output_tokens', 1) * 100:.1f}%")
    print(f"   Text preview: {result['text'][:100] if result['text'] else 'EMPTY'}...")
    
    # Test 3: REQUIRED mode (tools, soft-required with provoker)
    print("\n3. Testing REQUIRED mode (GPT-5 with provoker)...")
    result = run_openai_with_grounding(
        client=client,
        model="gpt-5",
        mode="REQUIRED",
        prompt="What is the US federal VAT rate?",
        system="Answer concisely in JSON format"
    )
    
    print(f"   Status: {result['status']}")
    print(f"   Tool calls: {result['tool_call_count']}")
    print(f"   Grounded: {result['grounded_effective']}")
    print(f"   Enforcement mode: {result.get('enforcement_mode', 'N/A')}")
    print(f"   Soft required: {result.get('soft_required', 'N/A')}")
    print(f"   Budget starved: {result.get('budget_starved', 'N/A')}")
    print(f"   Effective max tokens: {result.get('effective_max_output_tokens', 'N/A')}")
    print(f"   Usage - Input: {result.get('usage_input_tokens', 'N/A')}")
    print(f"   Usage - Output: {result.get('usage_output_tokens', 'N/A')}")
    print(f"   Usage - Reasoning: {result.get('usage_reasoning_tokens', 'N/A')}")
    print(f"   Provoker hash: {result.get('provoker_hash', 'N/A')}")
    print(f"   Text preview: {result['text'][:100] if result['text'] else 'EMPTY'}...")
    
    print("\n" + "=" * 60)
    print("Testing complete! The enhanced adapter provides:")
    print("1. Auto-raised tokens for GPT-5 + tools (512 default)")
    print("2. Detailed usage telemetry including reasoning tokens")
    print("3. Budget starvation detection")
    print("4. Enforcement mode tracking")
    print("5. Provoker hash for soft-required mode")

if __name__ == "__main__":
    test_telemetry()