#!/usr/bin/env python3
"""Quick test that server starts without Gradio errors"""
import subprocess
import time
import requests
import sys

print("Starting server in background...")
proc = subprocess.Popen([sys.executable, "app.py"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       cwd="/Users/arsheelpatel/Desktop/Crisis_Environment")

# Give it 3 seconds to start
time.sleep(3)

try:
    print("Testing if server is running...")
    res = requests.get("http://127.0.0.1:7860/health", timeout=2)
    print(f"✅ Server responded: {res.status_code}")
    if res.status_code == 200:
        print(f"✅ Health check passed: {res.json()}")

    # Clean up
    proc.terminate()
    print("✅ Server startup successful - no immediate errors")

except Exception as e:
    print(f"⚠️ Could not reach server: {e}")
    proc.terminate()
    stdout, stderr = proc.communicate(timeout=2)
    if stdout:
        print("STDOUT:", stdout.decode()[-500:])
    if stderr:
        print("STDERR:", stderr.decode()[-500:])
