#!/usr/bin/env python3
"""
Crisis Intelligence Environment - Production Entry Point

Runs the FastAPI server for crisis resource allocation benchmarking.
"""

import uvicorn
from server.app import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info",
    )
