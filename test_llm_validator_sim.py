#!/usr/bin/env python3
"""
Test what happens when validator provides API credentials.
"""

import os
import sys

# Simulate validator environment
print("=" * 70)
print("SIMULATING VALIDATOR ENVIRONMENT")
print("=" * 70)

# Set mock credentials
os.environ["API_BASE_URL"] = "http://localhost:8000"
os.environ["API_KEY"] = "mock-api-key-from-validator"

print(f"API_BASE_URL: {os.environ.get('API_BASE_URL')}")
print(f"API_KEY: {os.environ.get('API_KEY')}")

print("\n" + "=" * 70)
print("TESTING WARMUP WITH CREDENTIALS")
print("=" * 70)

from inference import warmup_llm

try:
    # This will attempt to connect to the LLM proxy
    result = warmup_llm()
    print(f"Warmup result: {result}")
    if result:
        print("✓ Successfully made API call through LiteLLM proxy!")
    else:
        print("⚠ Warmup returned False (expected if mock API is not running)")
except Exception as e:
    print(f"Error during warmup: {e}")
    print("(This is expected if the mock API is not available)")

print("\nNote: In actual validator environment:")
print("- Validators will inject real API_BASE_URL and API_KEY")
print("- warmup_llm() will make real API calls to their LiteLLM proxy")
print("- Validator will detect these calls in their proxy logs")
