import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.citizen_service import get_citizen_service
from tasks.scam_tasks import process_citizen_report_task, geocode_location
from models.database import get_sqlite_connection

def test_scam_tasks_registration():
    """Verify tasks are registered in the Celery app."""
    from celery_app import app
    assert "tasks.scam_tasks.process_citizen_report_task" in app.tasks

def test_geocode_location():
    """Verify geocode_location correctly geocodes cities."""
    res = geocode_location("Mumbai")
    assert res["city"] == "Mumbai"
    assert res["state"] == "Maharashtra"
    assert 18.9 < res["lat"] < 19.2
    assert 72.7 < res["lng"] < 73.0

    # Test case-insensitivity
    res_lower = geocode_location("mumbai")
    assert res_lower["city"] == "Mumbai"

    # Test unknown fallback
    res_fallback = geocode_location("NotACity")
    assert res_fallback["city"] is not None
    assert res_fallback["lat"] != 0.0

@patch("tasks.scam_tasks.process_citizen_report_task.delay")
@patch("models.database.get_firestore_client")
def test_create_report_dispatches_scam_task(mock_get_firestore, mock_delay):
    """Verify that create_report calls process_citizen_report_task.delay."""
    mock_db = MagicMock()
    mock_get_firestore.return_value = mock_db

    citizen_svc = get_citizen_service()
    import asyncio
    res = asyncio.run(citizen_svc.create_report(
        description="Suspicious call claiming to be CBI and locking me under digital arrest.",
        phone_number="+919876543210",
        location="Delhi",
        contact_email="citizen@test.com"
    ))

    assert res["report_id"] is not None
    mock_delay.assert_called_once_with(res["report_id"])

@patch("tasks.scam_tasks.get_scam_detector")
@patch("tasks.scam_tasks.get_firestore_client")
def test_process_citizen_report_task(mock_get_firestore, mock_get_detector):
    """Verify that process_citizen_report_task analyzes text, updates Firestore, and inserts to SQLite."""
    # Mock Firestore
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "description": "CBI drug parcel scam call.",
        "phone_numbers": ["+919876543210"],
        "victim_location": {"city": "Hyderabad"},
        "updates": []
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    mock_get_firestore.return_value = mock_db

    # Mock Scam Detector
    mock_detector = MagicMock()
    mock_detector.analyze_text = AsyncMock()
    mock_detector.analyze_text.return_value = {
        "risk_score": 0.95,
        "risk_label": "CRITICAL",
        "classification": "digital_arrest",
        "scam_type": "Digital Arrest Case",
        "explanation": "CBI impersonation scam.",
        "recommended_action": "Do not pay."
    }
    mock_get_detector.return_value = mock_detector

    # Clear SQLite table just in case
    with get_sqlite_connection() as conn:
        conn.execute("DELETE FROM incidents WHERE report_id = 'test_scam_report_id'")

    try:
        # Run Celery Task
        process_citizen_report_task(report_id="test_scam_report_id")

        # Verify Firestore doc was read & updated
        mock_db.collection.return_value.document.assert_called_with("test_scam_report_id")
        mock_db.collection.return_value.document.return_value.update.assert_called_once()

        # Verify SQLite incident was created
        with get_sqlite_connection() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE report_id = 'test_scam_report_id'").fetchone()
            assert row is not None
            assert row["incident_type"] == "scam_call"
            assert row["severity"] == "CRITICAL"
            assert row["city"] == "Hyderabad"
            assert 17.3 < row["lat"] < 17.5
    finally:
        # Cleanup
        with get_sqlite_connection() as conn:
            conn.execute("DELETE FROM incidents WHERE report_id = 'test_scam_report_id'")
