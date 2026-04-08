# -------------------- GRADIO UI --------------------
import os

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

        # simple safe allocation
        resource_total = 100
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


# mount
gradio_app = gradio_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/ui")