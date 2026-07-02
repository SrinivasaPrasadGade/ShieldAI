import pytest
import os
import json
import importlib
from unittest.mock import patch, MagicMock

# Prevent realtime_server from connecting to Redis at import time
with patch('redis.Redis.from_url'):
    realtime_server = importlib.import_module('realtime_server')
    app = realtime_server.app
    socketio = realtime_server.socketio

@pytest.fixture
def client():
    # Mock redis and firebase so the test doesn't try to connect to real services
    with patch('redis.Redis.from_url'), \
         patch('realtime_server.fetch_recent_alerts', return_value=[]):
        
        # Create a test client for the socketio app
        client = socketio.test_client(app)
        yield client
        client.disconnect()

def test_socketio_connection_and_dashboard_join(client):
    """
    Test that a client can connect, join the law_enforcement room,
    and receive historical alerts.
    """
    assert client.is_connected()
    
    # Emit join event
    client.emit('join_dashboard', {'role': 'law_enforcement'})
    
    # Receive the events
    received = client.get_received()
    
    # Should have 'joined' and potentially 'historical_alerts' (mocked to [])
    event_names = [event['name'] for event in received]
    assert 'joined' in event_names
    
    # Find joined event
    joined_event = next(e for e in received if e['name'] == 'joined')
    assert joined_event['args'][0]['room'] == 'law_enforcement'

def test_socketio_receives_new_alert():
    """
    Test that triggering an alert artificially pushes it to connected clients.
    """
    with patch('redis.Redis.from_url'), \
         patch('realtime_server.fetch_recent_alerts', return_value=[]):
        
        # Connect a client and join room
        client = socketio.test_client(app)
        client.emit('join_dashboard', {'role': 'law_enforcement'})
        
        # Clear previous events
        client.get_received()
        
        # Artificially trigger an alert (as if from redis)
        test_alert = {
            "id": "alert-test-123",
            "severity": "HIGH",
            "message": "Test Alert"
        }
        
        # We can just use the socketio object to emit to the room directly, 
        # mimicking the redis listener's behavior
        socketio.emit("new_alert", test_alert, to="law_enforcement")
        
        # Check if the client received it
        received = client.get_received()
        assert len(received) > 0
        
        event_names = [event['name'] for event in received]
        assert 'new_alert' in event_names
        
        alert_event = next(e for e in received if e['name'] == 'new_alert')
        assert alert_event['args'][0]['id'] == 'alert-test-123'
        assert alert_event['args'][0]['severity'] == 'HIGH'
        
        client.disconnect()

