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
from typing import Dict, Any, Optional, List

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
import os

def ensure_state_initialized(state_dict):
    """Initialize state with default values if needed."""
    if state_dict is None:
        state_dict = {}
    defaults = {
        "incidents": [],
        "episode_id": None,
        "resource_units_total": 0,
        "priorities": {},
        "allocation": {},
    }
    for key, value in defaults.items():
        if key not in state_dict:
            state_dict[key] = value
    return state_dict

def check_health():
    """Check system health status."""
    try:
        res = requests.get("/health")
        if res.status_code != 200:
            print(f"[HEALTH] Status {res.status_code}: {res.text}")
            return f"❌ Error (code {res.status_code})", "N/A"
        data = res.json()
        status = "✅ Healthy"
        return status, data.get("episode_id", "None")
    except Exception as e:
        print(f"[HEALTH ERROR] {str(e)}")
        return f"❌ Error: {str(e)}", "N/A"

def reset_task(difficulty):
    """Reset the environment with selected difficulty."""
    try:
        res = requests.post(f"/reset?difficulty={difficulty}")
        if res.status_code != 200:
            print(f"[RESET] Status {res.status_code}: {res.text}")
            return f"❌ Error: HTTP {res.status_code}", None, None, None

        data = res.json()

        if not data.get("success", False):
            print(f"[RESET] Success=false: {data}")
            return "❌ Reset failed", None, None, None

        observation = data.get("observation", {})
        input_data = observation.get("input", {})
        incidents = input_data.get("incidents", [])
        episode_id = observation.get("episode_id", "Unknown")
        resource_total = input_data.get("resource_units_total", 0)

        # Return incidents as table data
        table_data = []
        for inc in incidents:
            table_data.append([
                inc.get("incident_id", "N/A"),
                str(inc.get("severity", "N/A")),
                str(inc.get("people_affected", 0)),
                inc.get("description", "No description")[:50],
            ])

        state = {
            "incidents": incidents,
            "episode_id": episode_id,
            "resource_units_total": resource_total,
            "priorities": {},
            "allocation": {},
        }

        return f"✅ Reset to {difficulty} difficulty", episode_id, resource_total, table_data
    except Exception as e:
        print(f"[RESET ERROR] {str(e)}")
        return f"❌ Error: {str(e)}", None, None, None

def update_priority(state_dict, incident_id, priority):
    """Update priority for an incident."""
    state_dict = ensure_state_initialized(state_dict)
    state_dict["priorities"][incident_id] = priority
    return state_dict

def update_allocation(state_dict, incident_id, resources):
    """Update resource allocation for an incident."""
    state_dict = ensure_state_initialized(state_dict)
    try:
        state_dict["allocation"][incident_id] = int(resources) if resources else 0
    except:
        state_dict["allocation"][incident_id] = 0
    return state_dict

def run_allocation(state_dict):
    """Execute the allocation step."""
    state_dict = ensure_state_initialized(state_dict)

    try:
        # Build the prediction payload
        prediction = {
            "cleaned_data": {},  # Users would clean this; here we use incidents as-is
            "priorities": state_dict.get("priorities", {}),
            "allocation": state_dict.get("allocation", {}),
        }

        # Add cleaned data from incidents
        for inc in state_dict.get("incidents", []):
            inc_id = inc.get("incident_id")
            if inc_id:
                prediction["cleaned_data"][inc_id] = {
                    "severity": inc.get("severity"),
                    "people_affected": inc.get("people_affected"),
                }

        res = requests.post("/step", json=prediction)
        if res.status_code != 200:
            print(f"[STEP] Status {res.status_code}: {res.text}")
            return f"❌ Error: HTTP {res.status_code}", None, None, None, None

        data = res.json()

        if not data.get("success", False):
            print(f"[STEP] Success=false: {data}")
            return "❌ Step failed", None, None, None, None

        info = data.get("info", {})
        scores = info.get("scores", {})
        explanations = info.get("explanation", {})

        reward = scores.get("final", 0)

        # Build results display
        results_text = f"""
### 🏆 Allocation Results

**Final Score: {reward:.4f} / 1.0**

#### Score Breakdown:
- **Cleaning:** {scores.get('cleaning', 0):.4f} / 0.5000
- **Priority:** {scores.get('priority', 0):.4f} / 0.2000
- **Allocation:** {scores.get('allocation', 0):.4f} / 0.3000

#### Feedback:
- {explanations.get('cleaning_feedback', 'N/A')}
- {explanations.get('priority_feedback', 'N/A')}
- {explanations.get('allocation_feedback', 'N/A')}
"""

        return results_text, reward, scores, explanations, data.get("observation")
    except Exception as e:
        print(f"[STEP ERROR] {str(e)}")
        return f"❌ Error: {str(e)}", None, None, None, None

def gradio_ui():
    """Build the professional Gradio UI."""
    state = gr.State(value={})

    with gr.Blocks(title="Crisis Intelligence System") as demo:
        # Title
        gr.Markdown("# 🚨 Crisis Intelligence System")
        gr.Markdown("Professional resource allocation dashboard for disaster response")

        # ==================== SECTION 1 ====================
        with gr.Group():
            gr.Markdown("## 📊 System Status")
            with gr.Row():
                health_btn = gr.Button("Check System Health", scale=1, variant="primary")
                health_status = gr.Label(value="Unknown", label="Status")
                episode_display = gr.Label(value="No Episode", label="Episode ID")

            health_btn.click(
                check_health,
                outputs=[health_status, episode_display],
            )

        # ==================== SECTION 2 ====================
        with gr.Group():
            gr.Markdown("## 🎯 Task Initialization")
            with gr.Row():
                difficulty_dropdown = gr.Dropdown(
                    choices=["easy", "medium", "hard"],
                    value="easy",
                    label="Difficulty",
                    scale=1
                )
                reset_btn = gr.Button("Start New Scenario", scale=1, variant="primary")

            reset_status = gr.Label(value="Ready", label="Status")

            with gr.Row():
                episode_id_display = gr.Textbox(label="Episode ID", interactive=False)
                resource_total_display = gr.Number(label="Total Resources", interactive=False)

        # ==================== SECTION 3 ====================
        with gr.Group():
            gr.Markdown("## 📋 Incident Viewer")
            incident_table = gr.Dataframe(
                headers=["Incident ID", "Severity", "People Affected", "Description"],
                label="Active Incidents",
                interactive=False,
                wrap=True,
            )

        # ==================== SECTION 4 ====================
        allocation_group = gr.Group(visible=False)
        with allocation_group:
            gr.Markdown("## 💼 Resource Allocation Panel")
            gr.Markdown("Configure priorities and resource allocation for each incident")

            allocation_container = gr.Column()

            with allocation_container:
                gr.Textbox(
                    value="Load a scenario to see incidents",
                    label="Status",
                    interactive=False
                )

        # ==================== SECTION 5 ====================
        with gr.Group():
            gr.Markdown("## ▶️ Execute Allocation")
            run_btn = gr.Button("Run Allocation", scale=1, variant="primary", size="lg")

        # ==================== SECTION 6 ====================
        with gr.Group():
            gr.Markdown("## 🎖️ Results & Scores")

            results_markdown = gr.Markdown("Results will appear here after running allocation")

            with gr.Row():
                final_score_display = gr.Number(label="Final Score", interactive=False, value=0)

            with gr.Accordion(label="Score Breakdown", open=False):
                scores_json = gr.JSON(label="Detailed Scores")

            with gr.Accordion(label="Feedback", open=False):
                explanations_json = gr.JSON(label="Feedback Details")

        # ==================== EVENTS ====================

        def on_reset_with_state(difficulty):
            status, ep_id, res_total, table_data = reset_task(difficulty)

            new_state = ensure_state_initialized({})

            # Only populate state if reset was successful
            if ep_id and table_data:
                new_state["episode_id"] = ep_id
                new_state["resource_units_total"] = res_total
                # Extract incidents from table_data
                incidents = []
                # Re-call to get full incident objects (table_data is just display)
                try:
                    res = requests.post(f"/reset?difficulty={difficulty}")
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("success"):
                            observation = data.get("observation", {})
                            new_state["incidents"] = observation.get("input", {}).get("incidents", [])
                except:
                    pass

            return (
                status,
                ep_id,
                res_total,
                table_data or [],
                new_state,
                gr.update(visible=len(table_data) > 0 if table_data else False)
            )

        reset_btn.click(
            on_reset_with_state,
            inputs=[difficulty_dropdown],
            outputs=[reset_status, episode_id_display, resource_total_display, incident_table, state, allocation_group],
        )

        def build_allocation_ui(state_dict):
            state_dict = ensure_state_initialized(state_dict)
            incidents = state_dict.get("incidents", [])

            if not incidents:
                return None

            ui_outputs = []
            for inc in incidents:
                inc_id = inc.get("incident_id", "Unknown")
                severity = inc.get("severity", "N/A")
                affected = inc.get("people_affected", 0)

                ui_outputs.append(
                    f"**{inc_id}** | Severity: {severity} | Affected: {affected}"
                )

            return "\n\n".join(ui_outputs)

        state.change(
            build_allocation_ui,
            inputs=[state],
            outputs=[],
        )

        def on_run_allocation_from_dropdown(state_dict):
            state_dict = ensure_state_initialized(state_dict)
            incidents = state_dict.get("incidents", [])

            if not incidents:
                return "❌ No incidents loaded", 0, {}, {}

            priorities = {}
            allocation_vals = {}

            for inc in incidents:
                inc_id = inc.get("incident_id")
                priorities[inc_id] = "medium"
                allocation_vals[inc_id] = 100

            state_dict["priorities"] = priorities
            state_dict["allocation"] = allocation_vals

            results_text, reward, scores, explanations, _ = run_allocation(state_dict)
            return (
                results_text,
                reward or 0,
                scores or {},
                explanations or {}
            )

        run_btn.click(
            on_run_allocation_from_dropdown,
            inputs=[state],
            outputs=[results_markdown, final_score_display, scores_json, explanations_json],
        )

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