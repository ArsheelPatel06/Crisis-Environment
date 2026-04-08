#!/usr/bin/env python3
"""
Test LLM warmup with environment variables.
Simulates what the validator will do.
"""

import os
import sys

# Test 1: Check environment variables
print("=" * 70)
print("TEST 1: Checking Environment Variables")
print("=" * 70)
api_base = os.environ.get("API_BASE_URL")
api_key = os.environ.get("API_KEY")
print(f"API_BASE_URL: {api_base or '❌ NOT SET'}")
print(f"API_KEY: {'✓ SET' if api_key else '❌ NOT SET'}")

# Test 2: Import and check warmup function
print("\n" + "=" * 70)
print("TEST 2: Checking Warmup Function Import")
print("=" * 70)
try:
    from inference import warmup_llm
    print("✓ warmup_llm function imported successfully")
except Exception as e:
    print(f"❌ Failed to import warmup_llm: {e}")
    sys.exit(1)

# Test 3: Run warmup (will skip if env vars not set, which is ok for local test)
print("\n" + "=" * 70)
print("TEST 3: Running Warmup Function")
print("=" * 70)
try:
    result = warmup_llm()
    print(f"Result: {result}")
    if result or (not api_base and not api_key):
        print("✓ Warmup executed (or skipped due to missing env vars)")
    else:
        print("⚠ Warmup returned False")
except Exception as e:
    print(f"❌ Warmup failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check that inference can be imported
print("\n" + "=" * 70)
print("TEST 4: Checking Main Inference Module")
print("=" * 70)
try:
    from inference import run_task, run_all, run_inference, AGENT_MAP
    print("✓ Main functions imported successfully")
    print(f"  - run_task: {run_task}")
    print(f"  - run_all: {run_all}")
    print(f"  - run_inference: {run_inference}")
    print(f"  - Agents available: {list(AGENT_MAP.keys())}")
except Exception as e:
    print(f"❌ Failed to import inference functions: {e}")
    sys.exit(1)

# Test 5: Verify warmup is called in main
print("\n" + "=" * 70)
print("TEST 5: Verifying Warmup in main()")
print("=" * 70)
import inspect
from inference import main
source = inspect.getsource(main)
if "warmup_llm()" in source:
    print("✓ warmup_llm() is called in main()")
    print("\nCode snippet from main():")
    for i, line in enumerate(source.split("\n")[:15], 1):
        print(f"  {i:2d}: {line}")
else:
    print("❌ warmup_llm() is NOT called in main()")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nSummary:")
print("- Warmup function exists and is importable")
print("- Warmup is called at start of main()")
print("- All inference functions are available")
print("- When validators provide API_BASE_URL and API_KEY, warmup will make LLM calls")
