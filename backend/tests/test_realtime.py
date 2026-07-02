"""
Tests for realtime_server.py Socket.IO handlers.

Strategy: Invoke handler functions directly and mock flask_socketio
primitives (emit, join_room). This avoids Flask-SocketIO's test_client
event queue, which is unreliable under async_mode="threading" on
different Python versions and CI environments (the root cause of the
persistent 'joined' not in [] failures).
"""
import pytest
import os
import json
import importlib
from unittest.mock import patch, MagicMock, call

# Prevent realtime_server from connecting to Redis at import time
with patch('redis.Redis.from_url'):
    realtime_server = importlib.import_module('realtime_server')

app = realtime_server.app
socketio_obj = realtime_server.socketio


# ---------------------------------------------------------------------------
# Test 1: Connection + join_dashboard handler
# ---------------------------------------------------------------------------

def test_socketio_connection_and_dashboard_join():
    """
    Test that a client can connect, join the law_enforcement room,
    and receive the 'joined' acknowledgement event.
    """
    # --- Part A: handle_connect accepts connections (no auth token set) ---
    # Use Flask test request context so that `request` is available
    with app.test_request_context('/?token='):
        # Monkey-patch request.sid which Flask-SocketIO normally injects
        from flask import request as flask_request
        flask_request.sid = 'test-sid-001'

        result = realtime_server.handle_connect()
        # None means the connection is accepted
        assert result is None

    # --- Part B: handle_join joins the room and emits 'joined' ---
    with app.test_request_context('/'):
        from flask import request as flask_request
        flask_request.sid = 'test-sid-001'

        with patch('realtime_server.join_room') as mock_join, \
             patch('realtime_server.emit') as mock_emit, \
             patch('realtime_server.fetch_recent_alerts', return_value=[]):

            realtime_server.handle_join({'role': 'law_enforcement'})

            # Client must be added to the law_enforcement room
            mock_join.assert_called_once_with('law_enforcement')

            # Server must emit 'joined' acknowledgement back to the client
            mock_emit.assert_any_call(
                'joined',
                {'room': 'law_enforcement', 'status': 'connected'},
            )

            # Verify the emitted room name is correct
            joined_call = next(
                c for c in mock_emit.call_args_list if c[0][0] == 'joined'
            )
            assert joined_call[0][1]['room'] == 'law_enforcement'


# ---------------------------------------------------------------------------
# Test 2: Alert broadcast via _process_alert_message
# ---------------------------------------------------------------------------

def test_socketio_receives_new_alert():
    """
    Test that triggering a HIGH-severity alert correctly pushes it
    to connected clients in the law_enforcement room.
    """
    test_alert = {
        "id": "alert-test-123",
        "severity": "HIGH",
        "message": "Test Alert",
    }

    # Build the Redis pub/sub message dict that _process_alert_message expects
    redis_message = {"type": "message", "data": json.dumps(test_alert)}

    with patch.object(socketio_obj, 'emit') as mock_emit:
        realtime_server._process_alert_message(redis_message)

        # HIGH severity → new_alert emitted to law_enforcement room
        mock_emit.assert_any_call(
            "new_alert", test_alert, to="law_enforcement"
        )

        # All alerts → alert_feed_update emitted to law_enforcement room
        mock_emit.assert_any_call(
            "alert_feed_update", test_alert, to="law_enforcement"
        )

        # Verify payload integrity
        new_alert_call = next(
            c for c in mock_emit.call_args_list if c[0][0] == "new_alert"
        )
        emitted_data = new_alert_call[0][1]
        assert emitted_data['id'] == 'alert-test-123'
        assert emitted_data['severity'] == 'HIGH'


# ---------------------------------------------------------------------------
# Test 3: Non-message types are silently ignored
# ---------------------------------------------------------------------------

def test_process_alert_ignores_subscribe_messages():
    """Redis subscribe confirmations should not trigger any emission."""
    subscribe_msg = {"type": "subscribe", "data": 1}

    with patch.object(socketio_obj, 'emit') as mock_emit:
        realtime_server._process_alert_message(subscribe_msg)
        mock_emit.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Historical alerts synced on law_enforcement join
# ---------------------------------------------------------------------------

def test_handle_join_sends_historical_alerts():
    """
    Law enforcement clients should receive historical alerts on join.
    """
    mock_alerts = [
        {"id": "hist-1", "severity": "HIGH", "message": "Historical 1"},
        {"id": "hist-2", "severity": "MEDIUM", "message": "Historical 2"},
    ]

    with app.test_request_context('/'):
        from flask import request as flask_request
        flask_request.sid = 'test-sid-002'

        with patch('realtime_server.join_room'), \
             patch('realtime_server.emit') as mock_emit, \
             patch('realtime_server.fetch_recent_alerts', return_value=mock_alerts):

            realtime_server.handle_join({'role': 'law_enforcement'})

            mock_emit.assert_any_call(
                'historical_alerts',
                {'alerts': mock_alerts},
            )


# ---------------------------------------------------------------------------
# Test 5: MEDIUM-severity alert does NOT trigger new_alert
# ---------------------------------------------------------------------------

def test_medium_severity_skips_new_alert():
    """Only CRITICAL/HIGH alerts produce a 'new_alert' event."""
    test_alert = {"id": "med-1", "severity": "MEDIUM", "message": "Low priority"}
    redis_message = {"type": "message", "data": json.dumps(test_alert)}

    with patch.object(socketio_obj, 'emit') as mock_emit:
        realtime_server._process_alert_message(redis_message)

        # alert_feed_update should be emitted
        mock_emit.assert_any_call(
            "alert_feed_update", test_alert, to="law_enforcement"
        )

        # new_alert should NOT be emitted for MEDIUM
        new_alert_calls = [
            c for c in mock_emit.call_args_list if c[0][0] == "new_alert"
        ]
        assert len(new_alert_calls) == 0, \
            f"MEDIUM severity should not trigger new_alert, got: {new_alert_calls}"
