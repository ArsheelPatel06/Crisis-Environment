"""
Crisis Intelligence Environment - FastAPI Server

Production-grade REST API with OpenEnv-compatible endpoints.

Usage:
    python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
"""

import sys
from pathlib import Path

# Add parent directory to path for imports

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uuid
from typing import Dict, Any, Optional

from env import CrisisEnv

# Global environment instance (single environment per server)
env: Optional[CrisisEnv] = None


# Create FastAPI app
@app.get("/")
async def root():
    return {
        "message": "Crisis Intelligence API is running 🚀",
        "endpoints": [
            "/health",
            "/reset?difficulty=easy",
            "/step",
            "/state"
        ]
    }

app = FastAPI(
    title="Crisis Intelligence Environment API",
    description="Multi-agent resource allocation for disaster response",
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    """Initialize environment on server startup."""
    global env
    env = CrisisEnv()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "episode_id": env.episode_id if env else None}


@app.post("/reset")
async def reset(difficulty: str = Query("easy", pattern="^(easy|medium|hard)$")):
    """
    Reset environment and load a new task.

    Query Parameters:
    - difficulty: "easy", "medium", or "hard"

    Returns:
    {
        "success": true,
        "observation": {
            "episode_id": str,
            "difficulty": str,
            "input": { task input data },
            "metadata": { dataset info }
        }
    }
    """
    try:
        observation = env.reset(difficulty=difficulty)
        return {
            "success": True,
            "observation": observation,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/input")
async def get_input():
    """Get raw input data for current episode."""
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    return {
        "success": True,
        "episode_id": env.episode_id,
        "input": env.get_input(),
    }


@app.get("/ground_truth")
async def get_ground_truth():
    """Get ground truth for current episode (answer key)."""
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    gt = env.get_ground_truth()
    return {
        "success": True,
        "episode_id": env.episode_id,
        "ground_truth": gt,
    }


@app.post("/step")
async def step(prediction: Dict[str, Any]):
    """
    Execute one step: evaluate prediction against ground truth.

    Request body:
    {
        "cleaned_data": { incident_id → {severity, people_affected} },
        "priorities": { incident_id → "high"|"medium"|"low" },
        "allocation": { incident_id → resource_count }
    }

    Returns:
    {
        "success": true,
        "observation": { same as reset },
        "reward": float in [0, 1],
        "done": true,
        "info": {
            "scores": { cleaning, priority, allocation, final },
            "explanation": { cleaning_feedback, priority_feedback, allocation_feedback }
        }
    }
    """
    try:
        observation, reward, done, info = env.step(prediction)

        return {
            "success": True,
            "observation": observation,
            "reward": reward,
            "done": done,
            "info": info,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def get_state():
    """Get current environment state."""
    return {
        "episode_id": env.episode_id if env else None,
        "step_count": env.step_count if env else None,
        "done": env.done if env else None,
    }


def main():
    """Main entry point for the server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()

import gradio as gr
from fastapi.middleware.wsgi import WSGIMiddleware

def gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# 🚨 Crisis Intelligence System")

        output = gr.JSON()

        def check_health():
            return {"status": "API running"}

        def reset_easy():
            return {"call": "/reset?difficulty=easy"}

        gr.Button("Check Health").click(check_health, outputs=output)
        gr.Button("Reset Easy Task").click(reset_easy, outputs=output)

    return demo

gradio_app = gradio_ui()

app.mount("/ui", gr.mount_gradio_app(app, gradio_app, path="/ui"))
