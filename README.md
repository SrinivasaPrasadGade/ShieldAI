# ShieldAI Backend Setup Guide

This project contains the production-ready FastAPI backend and Kafka-based distributed background tasks for the ShieldAI platform.

## Architecture Overview
The backend is structured into four main decoupled components using Docker:
1. **API Server (FastAPI)**: Serves endpoints for scam detection, counterfeit currency checks, and graph database querying.
2. **Apache Kafka**: Serves as the distributed message queue holding background task messages.
3. **Worker (Python)**: Standalone Kafka consumer that handles long-running tasks asynchronously (e.g. image/audio analysis, data writes).
4. **ZooKeeper**: Manager orchestrator for Kafka.

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
*   `ENABLE_BERT`: If your laptop is memory-constrained (e.g., standard Macbook Air), set `ENABLE_BERT=false` to bypass loading the large BERT model locally.

### 3. Spin Up the Services
Run Docker Compose in the root folder:
```bash
docker-compose up --build
```
This downloads the Kafka services, builds the API and Worker containers, sets up shared Docker networking, and starts all servers.
*   The API server will be available at: **`http://localhost:8000`**
*   API Docs (Swagger UI) will auto-generate at: **`http://localhost:8000/docs`**

---

## Running Integration Tests
If you want to run backend endpoint tests locally:
1. Initialize a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```
2. Disable BERT in your `.env` (to prevent test runner timeouts) and run:
   ```bash
   pytest backend/tests/
   ```
