# ShieldAI Setup Guide

This project contains the production-ready FastAPI backend, Flask-SocketIO realtime server, and Celery background tasks for the ShieldAI platform.

## Architecture Overview
The system is structured into five decoupled components using Docker or local native execution:
1. **API Server (FastAPI)**: Serves endpoints for scam detection, counterfeit currency checks, and graph database querying.
2. **Realtime Server (Flask-SocketIO)**: Pushes critical/high-severity alerts to the law enforcement dashboard in real time.
3. **Redis Broker**: Acts as the message broker for Celery tasks and provides Pub/Sub channels for realtime event streaming.
4. **Worker (Celery)**: Standalone task worker that handles long-running background tasks (e.g., image/audio analysis, PDF evidence generation, report geocoding).
5. **Vite Frontend**: The React-based administration dashboard and citizen reporting client.

---

## Local Setup Instructions

### 1. Prerequisites
Make sure you have the following installed on your machine:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop)
*   Python 3.10+ (for local native execution or test runner)

### 2. Environment Variables Setup
Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Open `.env` and fill in the required keys:
*   `GEMINI_API_KEY`: Generate a key from Google AI Studio.
*   `FIREBASE_CREDENTIALS_PATH`: Place your Firebase Admin Service Account JSON at `backend/firebase-credentials.json` (do not commit this JSON).
*   `ENABLE_BERT`: If your laptop is memory-constrained, set `ENABLE_BERT=false` to bypass loading the large BERT model locally.

### 3. Spin Up the Services

#### Mode A: Docker Compose (Recommended)
Run Docker Compose in the root folder:
```bash
docker-compose up --build
```
This builds and runs all services in isolated containers.
*   The API server will be available at: **`http://localhost:8000`**
*   The Realtime SocketIO server will be available at: **`http://localhost:5001`**
*   The Vite Frontend will be available at: **`http://localhost:5174`**
*   FastAPI docs will auto-generate at: **`http://localhost:8000/docs`**

#### Mode B: Local Native (Development)
You can also run all services natively on your host machine:
```bash
./start_local.sh
```

---

## Running Integration Tests
To run backend endpoint and task runner tests locally:
1. Initialize a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r backend/requirements.txt
   ```
2. Disable BERT in your `.env` (to prevent test runner timeouts) and run:
   ```bash
   pytest backend/tests/
   ```
