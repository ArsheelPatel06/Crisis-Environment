"""
Crisis Intelligence Environment - FastAPI Server with Gradio UI
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import requests
from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any, Optional
import gradio as gr

from env import CrisisEnv

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="Crisis Intelligence Environment API",
    description="Multi-agent resource allocation for disaster response",
    version="1.0.0",
)

# Global environment instance
env: Optional[CrisisEnv] = None

@app.on_event("startup")
async def startup():
    global env
    env = CrisisEnv()
    print("✓ CrisisEnv initialized")

@app.get("/")
async def root():
    return {
        "message": "Crisis Intelligence API is running",
        "endpoints": ["/health", "/reset", "/step", "/state", "/input", "/ui"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "episode_id": env.episode_id if env else None
    }

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

@app.get("/input")
async def get_input():
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    return {
        "success": True,
        "episode_id": env.episode_id,
        "input": env.get_input(),
    }

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

@app.get("/state")
async def get_state():
    return {
        "episode_id": env.episode_id if env else None,
        "step_count": env.step_count if env else None,
        "done": env.done if env else None,
    }

@app.get("/ground_truth")
async def get_ground_truth():
    if not env or not env.episode_id:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    return {"success": True, "ground_truth": env.get_ground_truth()}

# ==================== GRADIO UI ====================

BASE_URL = "http://127.0.0.1:7860"

def check_health():
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=5)
        if res.status_code != 200:
            return f"❌ Error ({res.status_code})", "N/A"
        data = res.json()
        return "✅ Healthy", data.get("episode_id", "None")
    except Exception as e:
        return f"❌ {str(e)}", "N/A"

def reset_task(difficulty):
    try:
        res = requests.post(f"{BASE_URL}/reset", params={"difficulty": difficulty}, timeout=10)
        if res.status_code != 200:
            return f"❌ HTTP {res.status_code}", "", 0, [], "[]"
        data = res.json()
        if not data.get("success"):
            return "❌ Reset failed", "", 0, [], "[]"

        observation = data["observation"]
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        episode_id = observation.get("episode_id", "")
        resource_total = input_data.get("resource_units_total", 0)

        table_data = [
            [
                inc.get("incident_id", "N/A"),
                str(inc.get("severity", "N/A")),
                str(inc.get("people_affected", 0)),
                inc.get("description", "")[:50],
            ]
            for inc in incidents
        ]

        return (
            f"✅ Reset ({difficulty})",
            episode_id,
            resource_total,
            table_data,
            json.dumps(incidents),
        )
    except Exception as e:
        return f"❌ {str(e)}", "", 0, [], "[]"

def run_allocation(incidents_json):
    try:
        incidents = json.loads(incidents_json) if incidents_json else []
        if not incidents:
            return "❌ No incidents loaded", 0, {}, {}

        # Simple safe allocation
        resource_total = state_dict.get("resource_units_total", 50)
        per = max(1, resource_total // max(1, len(incidents)))

        prediction = {
            "cleaned_data": {
                inc.get("incident_id", "UNK"): {
                    "severity": inc.get("severity", 3),
                    "people_affected": inc.get("people_affected", 0),
                }
                for inc in incidents
            },
            "priorities": {
                inc.get("incident_id", "UNK"): "medium"
                for inc in incidents
            },
            "allocation": {
                inc.get("incident_id", "UNK"): per
                for inc in incidents
            },
        }

        res = requests.post(f"{BASE_URL}/step", json=prediction, timeout=10)
        if res.status_code != 200:
            return f"❌ HTTP {res.status_code}", 0, {}, {}

        data = res.json()
        if not data.get("success"):
            return "❌ Step failed", 0, {}, {}

        info = data.get("info", {})
        scores = info.get("scores", {})
        reward = scores.get("final", 0)

        return (
            f"✅ Score: {reward:.4f}",
            reward,
            scores,
            info.get("explanation", {}),
        )
    except Exception as e:
        return f"❌ {str(e)}", 0, {}, {}

def gradio_ui():
    with gr.Blocks(title="Crisis Intelligence System") as demo:
        incidents_storage = gr.Textbox(visible=False, value="[]")

        gr.Markdown("# 🚨 Crisis Intelligence System")

        # -------- HEALTH --------
        with gr.Row():
            health_btn = gr.Button("Check Health")
            health_status = gr.Textbox("Unknown", label="Status")
            episode_display = gr.Textbox("None", label="Episode")

        health_btn.click(check_health, outputs=[health_status, episode_display])

        # -------- RESET --------
        difficulty = gr.Dropdown(["easy", "medium", "hard"], value="easy")
        reset_btn = gr.Button("Start")

        reset_status = gr.Textbox("Ready")
        episode_id = gr.Textbox()
        resources = gr.Number()

        incident_table = gr.Dataframe(
            headers=["ID", "Severity", "People", "Desc"],
            interactive=False,
        )

        reset_btn.click(
            reset_task,
            inputs=[difficulty],
            outputs=[reset_status, episode_id, resources, incident_table, incidents_storage],
        )

        # -------- RUN --------
        run_btn = gr.Button("Run Allocation")

        result = gr.Markdown()
        score = gr.Number()
        scores_json = gr.JSON()
        explanation = gr.JSON()

        run_btn.click(
            run_allocation,
            inputs=[incidents_storage],
            outputs=[result, score, scores_json, explanation],
        )

    return demo

# Create and mount Gradio app
gradio_app = gradio_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/ui")

# ==================== MAIN ====================

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
