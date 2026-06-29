# ShieldAI Backend Setup Guide

This project contains the production-ready FastAPI backend and Kafka/Celery-based distributed background tasks for the ShieldAI platform.

## Architecture Overview

The backend is structured into four main decoupled components using Docker. ShieldAI uses **Gemini 2.0 Flash as the primary AI engine**, with an optional local Hugging Face zero-shot classifier for redundancy.

1. **API Server (FastAPI)**: Serves endpoints for scam detection, counterfeit checks, and graph database querying. Lightweight, no heavy ML deps.
2. **Realtime Server (Flask-SocketIO)**: Websocket server for pushing live alerts to law enforcement dashboards. Lightweight.
3. **Worker (Celery/Kafka)**: Standalone consumer that handles long-running tasks asynchronously (OpenCV image processing, video analysis, etc.). This image contains the heavy ML libraries (PyTorch, Transformers, OpenCV).
4. **Redis**: Message broker and caching layer.

---

## Local Setup Instructions

### 1. Prerequisites
Make sure you have the following installed on your machine:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop)
*   Python 3.10+ (for running tests/linting locally)

### 2. Environment Variables Setup
Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Open `.env` and fill in the required keys:
*   `GEMINI_API_KEY`: Generate a key from Google AI Studio.
*   `FIREBASE_CREDENTIALS_PATH`: Place your Firebase Admin Service Account JSON at `backend/firebase-credentials.json` (do not commit this JSON).
*   `ENABLE_ZERO_SHOT`: If your laptop is memory-constrained, set this to `false` to bypass loading the Hugging Face BART-MNLI model locally. Gemini will handle all classification.

### 3. Spin Up the Services
Run Docker Compose in the root folder:
```bash
docker-compose up --build
```
This downloads the services, builds the API and Worker containers, sets up shared Docker networking, and starts all servers.
*   The API server will be available at: **`http://localhost:8000`**
*   API Docs (Swagger UI) will auto-generate at: **`http://localhost:8000/docs`**

---

## Running Diagnostics & Tests

ShieldAI includes a built-in diagnostic tool to check if your local environment is configured correctly for ML:

```bash
# Check ML dependencies and API keys
python backend/scripts/check_ml_stack.py
```

### Integration Tests
To run backend endpoint tests locally:
1. Initialize a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.dev.txt
   ```
2. Run the test suite:
   ```bash
   pytest backend/tests/
   ```

### Model Evaluation
To run the automated model evaluation suite against the synthetic dataset:
```bash
# Run using offline mock data
python backend/evaluation/run_model_eval.py --mode mock

# Run using live Gemini API calls
python backend/evaluation/run_model_eval.py --mode live
```
Reports are generated in `backend/evaluation/reports/`.
