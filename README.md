---
title: Crisis Environment
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: gradio
sdk_version: "3.50.2"
python_version: "3.10"
app_file: app.py
pinned: false
---

# Crisis Intelligence Environment (CIE)

A multi-step OpenEnv reinforcement learning environment where AI agents must operate on unreliable disaster data — cleaning corrupted inputs, assigning priorities, and allocating limited emergency resources under constrained conditions.

## Why This Environment Exists

Real-world disaster response systems receive data from dozens of sources simultaneously — field reports, sensors, human inputs. This data is routinely incomplete, inconsistent, delayed, or incorrect. Existing RL benchmarks assume clean inputs. CIE does not.

CIE trains and evaluates agents on the full pipeline: data forensics → triage → resource allocation. This directly models how AI systems must operate in high-stakes, data-imperfect environments.

---
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Status](https://img.shields.io/badge/status-live-brightgreen)

## Live Environment
https://arsheelpatel06-crisis-environment.hf.space

Health check:
```bash
curl https://arsheelpatel06-crisis-environment.hf.space/health
```
## UI Usage

Access the live interface:
https://arsheelpatel06-crisis-environment.hf.space/ui

Steps:
1. Click "Check Health"
2. Select difficulty and start a scenario
3. View incidents
4. Assign priorities and allocate resources
5. Run step to receive reward and feedback

---
## Quick Start

```bash
git clone https://github.com/ArsheelPatel06/Crisis-Environment.git
cd Crisis-Environment
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860

## Episode Protocol (3-Step)

Each episode runs exactly 3 steps. The agent receives corrupted incident data and must work through three phases sequentially:
POST /reset?difficulty=easy|medium|hard   → raw corrupted observation
POST /step  {"cleaned_data": {...}}        → Phase 1 reward (max 0.5)
POST /step  {"priorities": {...}}          → Phase 2 reward (max 0.2)
POST /step  {"allocation": {...}}          → Phase 3 reward (max 0.3), done=True
Total max reward = 1.0

---

## Action Space

**Phase 1 — Data Cleaning:**
```json
{
  "cleaned_data": {
    "INC-001": {"incident_id": "INC-001", "severity": 5, "people_affected": 800},
    "INC-002": {"incident_id": "INC-002", "severity": 3, "people_affected": 120}
  }
}
```

**Phase 2 — Priority Assignment:**
```json
{
  "priorities": {
    "INC-001": "high",
    "INC-002": "medium",
    "INC-003": "low"
  }
}
```

**Phase 3 — Resource Allocation:**
```json
{
  "allocation": {
    "INC-001": 25,
    "INC-002": 15,
    "INC-003": 10
  }
}
```

---

## Observation Space
```json
{
  "episode_id": "string",
  "difficulty": "easy|medium|hard",
  "phase": 1,
  "input": {
    "resource_units_total": 50,
    "incidents": [
      {
        "incident_id": "INC-001",
        "severity": "CRITICAL",
        "people_affected": "800"
      }
    ]
  },
  "step_count": 0,
  "max_steps": 3,
  "cumulative_reward": 0.0
}
```

Incident data contains deliberate corruptions:
- Severity as string ("HIGH", "III", "CRITICAL"), roman numeral, numeric, or missing
- People affected as string ("1,100"), word ("sixty"), null, or with formatting
- Conflicting signals (low severity, massive population)
- Missing or null incident IDs

---

## Reward Function
Final Score = Cleaning(0.5) + Priority(0.2) + Allocation(0.3)

**Cleaning (0–0.5):** Proportional to correct field parsing across all incidents. Penalizes wrong types, missing incidents, incorrect values.

**Priority (0–0.2):** Exact match of urgency labels against ground truth. Each correct label contributes proportionally.

**Allocation (0–0.3):** Measures deviation from optimal resource distribution. Perfect match = 0.3. Partial credit for near-optimal allocations.

Rewards are non-sparse — every phase produces a signal regardless of overall episode outcome.

---

## Tasks

### Easy
- 3 incidents
- Single corruption type per field
- Clear severity signals
- Straightforward priority ordering
- Simple budget allocation

### Medium
- 6 incidents
- Multiple corruption types simultaneously
- Conflicting signals (e.g., low severity label but high population)
- Moderate resource constraints requiring trade-offs

### Hard
- 8 incidents
- Ambiguous and misleading data (roman numerals, missing IDs, empty severity)
- Edge cases: extreme severity with zero population, massive population with missing severity
- Strict resource constraints across many competing incidents

---

## Baseline Scores

| Agent | Easy | Medium | Hard | Avg |
|-------|------|--------|------|-----|
| Random | ~0.30 | ~0.25 | ~0.28 | ~0.28 |
| Greedy | 0.71 | 0.44 | 0.50 | 0.55 |
| Heuristic | 0.78 | 0.72 | 0.79 | 0.76 |

Random baseline shows meaningful variance confirming graders are not static. Heuristic outperforms greedy across all difficulties confirming difficulty progression is real.

---

## Project Structure
crisis-intelligence-env/
├── env/
│   ├── env.py          # CrisisEnv: reset(), step(), state()
│   ├── grader.py       # Deterministic scoring engine
│   └── tasks.py        # Task loader
├── server/
│   └── app.py          # FastAPI server
├── agents/
│   ├── heuristic_agent.py
│   ├── greedy_agent.py
│   └── random_agent.py
├── data/
│   ├── easy.json
│   ├── medium.json
│   └── hard.json
├── tests/
│   ├── test_api.py
│   └── test_integration.py
├── client.py           # Python client
├── inference.py        # Baseline inference script
├── openenv.yaml        # OpenEnv spec
├── Dockerfile
└── requirements.txt

---

## Setup and Usage
```bash
git clone https://github.com/ArsheelPatel06/Crisis-Environment.git
cd Crisis-Environment
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Run baseline agents:
```bash
python3 inference.py --agent heuristic
python3 inference.py --agent random
python3 inference.py --agent greedy
```

Docker:
```bash
docker build -t crisis-intelligence-env .
docker run -p 7860:7860 crisis-intelligence-env
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/reset` | POST | Start new episode |
| `/step` | POST | Submit phase action |
| `/state` | GET | Current episode state |
| `/docs` | GET | Swagger UI |

---

## OpenEnv Compliance
```bash
openenv validate  # passes
```

- Typed Pydantic models via FastAPI
- step() / reset() / state() endpoints
- openenv.yaml with full metadata
- Dockerized deployment
- Deterministic graders with scores in [0.0, 1.0]

---

## Why This Is Challenging

- Multi-step decision making (not single action RL)
- Noisy and inconsistent inputs
- Conflicting signals across features
- Hard resource constraints
- Partial credit scoring instead of binary rewards

## License
MIT License
