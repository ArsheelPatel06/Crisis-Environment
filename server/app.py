"""
Crisis Intelligence Environment - FastAPI Server

Production-grade REST API with OpenEnv-compatible endpoints.

Usage:
    python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any, Optional

import requests
import gradio as gr

from env import CrisisEnv

# Global environment instance
env: Optional[CrisisEnv] = None

# Create FastAPI app
app = FastAPI(
    title="Crisis Intelligence Environment API",
    description="Multi-agent resource allocation for disaster response",
    version="1.0.0",
)

# -------------------- STARTUP --------------------
@app.on_event("startup")
async def startup():
    global env
    env = CrisisEnv()
    print("✓ CrisisEnv initialized (ready to reset)")


# -------------------- ROOT --------------------
@app.get("/")
async def root():
    return {
        "message": "Crisis Intelligence API is running 🚀",
        "endpoints": [
            "/health",
            "/reset?difficulty=easy",
            "/step",
            "/state",
            "/ui"
        ]
    }


# -------------------- HEALTH --------------------
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "episode_id": env.episode_id if env else None
    }


# -------------------- RESET --------------------
@app.post("/reset")
async def reset(difficulty: str = Query("easy", pattern="^(easy|medium|hard)$")):
    try:
        observation = env.reset(difficulty=difficulty)
        return {
            "success": True,
            "observation": observation,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------- INPUT --------------------
@app.get("/input")
async def get_input():
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    return {
        "success": True,
        "episode_id": env.episode_id,
        "input": env.get_input(),
    }


# -------------------- GROUND TRUTH --------------------
@app.get("/ground_truth")
async def get_ground_truth():
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    return {
        "success": True,
        "episode_id": env.episode_id,
        "ground_truth": env.get_ground_truth(),
    }


# -------------------- STEP --------------------
@app.post("/step")
async def step(prediction: Dict[str, Any]):
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


# -------------------- STATE --------------------
@app.get("/state")
async def get_state():
    return {
        "episode_id": env.episode_id if env else None,
        "step_count": env.step_count if env else None,
        "done": env.done if env else None,
    }


# -------------------- GRADIO UI --------------------
import requests

BASE_URL = "https://arsheelpatel06-crisis-environment.hf.space"

def gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# 🚨 Crisis Intelligence System")

        output = gr.JSON()

        def check_health():
            res = requests.get(f"{BASE_URL}/health")
            return res.json()

        def reset_easy():
            res = requests.post(f"{BASE_URL}/reset?difficulty=easy")
            return res.json()

        gr.Button("Check Health").click(check_health, outputs=output)
        gr.Button("Reset Easy Task").click(reset_easy, outputs=output)

    return demo


# Create and mount Gradio app properly
gradio_app = gradio_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/ui")


# -------------------- MAIN --------------------
def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()