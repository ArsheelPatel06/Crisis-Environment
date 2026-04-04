# 🚨 Crisis Intelligence Environment

A production-ready multi-agent simulation environment for disaster response and resource allocation.

---

## 🌐 Live Demo

🔗 https://arsheelpatel06-crisis-environment.hf.space  

### UI Access:
👉 https://arsheelpatel06-crisis-environment.hf.space/ui

---

## 🧠 Problem Statement

Simulate real-world crisis scenarios where multiple incidents occur and limited resources must be allocated efficiently.

The system evaluates:
- Data cleaning  
- Priority assignment  
- Resource allocation  

---

## ⚙️ Features

- 🧪 Multi-difficulty scenarios (easy, medium, hard)  
- 🤖 Multiple agent strategies:
  - Greedy Agent  
  - Heuristic Agent  
  - Random Agent  
- 📊 Evaluation with reward scoring  
- 🔌 REST API for integration  
- 🌐 Interactive UI using Gradio  
- 🐳 Dockerized deployment  

---

## 📁 Project Structure

```bash
Crisis_Environment/
│
├── agents/              # Agent strategies
├── data/                # Scenario datasets
├── env/                 # Core environment logic
├── server/              # FastAPI backend
├── tests/               # API & integration tests
│
├── app.py               # Entry point
├── inference.py         # Agent execution logic
├── openenv.yaml         # OpenEnv configuration
├── Dockerfile           # Deployment configuration
├── requirements.txt     # Dependencies
├── README.md
```

---

## 🚀 Running Locally

### 1. Clone repository

```bash
git clone https://github.com/ArsheelPatel06/Crisis-Environment.git
cd Crisis_Environment
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Mac/Linux
source venv/bin/activate  

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

### 5. Access locally

- API: http://localhost:7860  
- UI: http://localhost:7860/ui  

---

## 📡 API Endpoints

| Endpoint        | Method | Description              |
|----------------|--------|--------------------------|
| `/`            | GET    | Root info                |
| `/health`      | GET    | Health check             |
| `/reset`       | POST   | Start new scenario       |
| `/input`       | GET    | Get current input        |
| `/ground_truth`| GET    | Get correct answer       |
| `/step`        | POST   | Submit prediction        |
| `/state`       | GET    | Environment state        |

---

## 🧪 Example Usage

### Health check

```bash
curl http://localhost:7860/health
```

### Reset environment

```bash
curl -X POST "http://localhost:7860/reset?difficulty=easy"
```

---

## 🖥️ UI Features

- Check API health  
- Reset environment with predefined scenarios  
- View structured JSON responses  
- Interact with backend without writing code  

---

## 🤗 Hugging Face Deployment

This project is deployed using Docker Spaces on Hugging Face.

### Key Details:

- Docker-based deployment  
- FastAPI server running on port 7860  
- Gradio UI mounted at `/ui`  

### Steps followed:

1. Created Hugging Face Space (Docker)  
2. Added project files  
3. Configured Dockerfile  
4. Exposed FastAPI app  
5. Mounted Gradio UI  

---

## 👥 Contributors

- Arsheel Patel  
- Sufyan Khan  
- Saif Salmani  

---

## 🧠 Notes

- API is stateful (one active episode at a time)  
- Designed for extensibility (add new agents easily)  
- Backend and UI communicate via REST APIs  
- Suitable for simulation, evaluation, and experimentation  

---

## 🏁 Submission

This repository is part of a hackathon submission demonstrating:

- Backend system design (FastAPI)  
- API engineering  
- Docker-based deployment  
- Full-stack integration (API + UI)  
- Real-time simulation environment  

---

## 📜 License

MIT License
