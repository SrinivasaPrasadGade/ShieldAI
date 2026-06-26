#!/bin/bash

echo "🚀 Starting ShieldAI Local Environment (Native Mode)..."
echo "Press Ctrl+C to shut down all services gracefully."

# Ensure all background processes in this script are killed on exit
trap "echo '🛑 Shutting down services...'; kill 0" SIGINT SIGTERM EXIT

echo "▶️ Starting Redis..."
redis-server &

# Wait a moment for Redis to initialize
sleep 2

echo "▶️ Starting FastAPI Server..."
source .venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

echo "▶️ Starting Realtime SocketIO Server..."
python realtime_server.py &

echo "▶️ Starting Celery Worker..."
celery -A celery_app worker --loglevel=info &

echo "▶️ Starting Vite Frontend..."
cd ../frontend
npm run dev &

# Wait for all background jobs to finish
wait
