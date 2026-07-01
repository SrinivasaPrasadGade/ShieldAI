# backend/realtime_server.py
import os
import sys
import json
import time
import threading
import logging
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import redis

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("shield_ai.realtime")

# Add current directory to path to allow importing backend services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode="threading")
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

logger.info(f"Connecting to Redis at: {redis_url}")

@socketio.on('connect')
def handle_connect(auth=None):
    token = request.args.get('token', '')
    expected = os.environ.get('REALTIME_AUTH_TOKEN', '')
    if expected and token != expected:
        logger.warning(f"Unauthorized connection attempt from client: {request.sid}")
        return False  # Reject connection
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_dashboard')
def handle_join(data):
    role = data.get("role", "citizen")
    join_room(role)
    logger.info(f"Client {request.sid} joined room: {role}")
    emit("joined", {"room": role, "status": "connected"})

    # Dashboard State Sync: Send recent alerts to Law Enforcement on join to avoid blank state
    if role == "law_enforcement":
        alerts = fetch_recent_alerts()
        if alerts:
            logger.info(f"Syncing {len(alerts)} historical alerts to client {request.sid}")
            emit("historical_alerts", {"alerts": alerts})

def fetch_recent_alerts():
    """Helper to fetch recent alerts from Firestore synchronously"""
    try:
        import asyncio
        from services.alert_service import get_alert_service
        alert_svc = get_alert_service()
        
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(alert_svc.get_alerts(limit=15))
        loop.close()
        return res.get("alerts", [])
    except Exception as e:
        logger.error(f"Error fetching historical alerts: {e}")
        return []

def listen_for_alerts_with_retry():
    """Self-healing background thread to listen to Redis pub/sub for new alerts"""
    backoff = 1.0
    while True:
        try:
            logger.info("Attempting to connect to Redis pub/sub...")
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe("new_alerts")
            logger.info("Successfully subscribed to Redis channel: new_alerts")
            backoff = 1.0  # Reset backoff on success
            
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        alert = json.loads(message["data"])
                        severity = alert.get("severity", "MEDIUM")
                        logger.info(f"New alert received from Redis pub/sub: {alert.get('id')} ({severity})")
                        
                        # Critical and High alerts go specifically to law enforcement room
                        if severity in ["CRITICAL", "HIGH"]:
                            socketio.emit("new_alert", alert, to="law_enforcement")
                        
                        # All alerts go to the general feed
                        socketio.emit("alert_feed_update", alert, to="law_enforcement")
                    except Exception as parse_err:
                        logger.error(f"Error parsing alert message: {parse_err}")
                        
        except (redis.ConnectionError, redis.TimeoutError) as conn_err:
            logger.warning(f"Redis connection error: {conn_err}. Reconnecting in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)  # Exponential backoff capped at 60s
        except Exception as general_err:
            logger.error(f"Unexpected error in Redis listener: {general_err}. Reconnecting in 5s...")
            time.sleep(5)

# Start the Redis listener thread
threading.Thread(target=listen_for_alerts_with_retry, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Starting realtime server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
