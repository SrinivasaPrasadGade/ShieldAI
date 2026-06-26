import os
import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Use the same Redis URL that other services use to communicate via SocketIO
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=redis_url,
    async_mode="eventlet"
)

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting realtime server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
