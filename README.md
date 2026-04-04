---
title: Crisis Environment
emoji: 🚑
colorFrom: blue
colorTo: red
sdk: docker
sdk_version: "latest"
app_file: app.py
pinned: false
---

# Crisis Intelligence Environment

Deterministic evaluation for AI agents on crisis resource allocation under messy, real-world conditions.

## Results

**Average Score: 0.8742**
- Easy: 0.8553
- Medium: 0.8909
- Hard: 0.8762

## Quick Start

### Setup (One-time)
```bash
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -e .
```

### Run
```bash
# Terminal 1: Start server
python3 -m uvicorn server.app:app --host 0.0.0.0 --port 7860

# Terminal 2: Run inference (heuristic agent by default)
python3 inference.py

# Or test other agents:
python3 inference.py --agent random    # Random baseline (control)
python3 inference.py --agent greedy    # Greedy baseline
python3 inference.py --agent heuristic # Heuristic agent (default)
```

## What It Does

Evaluates agents handling crisis resource allocation with:
- **Messy data**: Text numbers ("sixty"), formatted ("1,100"), roman numerals (III)
- **Missing fields**: Fallback to alternative sources
- **Conflicting signals**: Low severity + huge population = HIGH priority
- **Deterministic scoring**: Reproducible, no randomness

## Scoring Formula

**Final Score = 0.5×Cleaning + 0.2×Priority + 0.3×Allocation**

Components scored in [0, 1] range on:
1. **Cleaning** - Data parsing accuracy
2. **Priority** - Incident classification (high/medium/low)
3. **Allocation** - Resource distribution optimality

## Approach

**Data-Aware Rules** (not linear scoring):
```
if population > 3000:                 → HIGH
if severity >= 4 and population > 200: → HIGH
if severity >= 4:                      → MEDIUM
if population > 500:                   → MEDIUM
else:                                  → LOW
```

**Tier-Based Allocation**:
- 65% to high priority
- 25% to medium priority
- 10% to low priority

## Architecture

```
env/         Core environment
server/      FastAPI backend (6 endpoints)
agents/      Baseline agents
data/        Test datasets (easy/medium/hard - adversarial)
tests/       Test suite (10/10 passing)
inference.py Competition format runner
```

## API

| Endpoint | Method |
|----------|--------|
| `/reset` | POST |
| `/step` | POST |
| `/health` | GET |
| `/ground_truth` | GET |
| `/input` | GET |
| `/state` | GET |

## Docker

```bash
docker build -t crisis-env .
docker run -p 7860:7860 crisis-env
```

Test: `curl http://localhost:7860/health`

## Validation

```bash
bash validate-submission.sh
```

---

**OpenEnv Compatible** | **Production Ready** | **Deterministic**
