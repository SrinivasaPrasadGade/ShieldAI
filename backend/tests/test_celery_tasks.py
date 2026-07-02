import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.currency_analyzer import get_currency_analyzer
from services.graph_service import get_graph_service
from tasks.currency_tasks import verify_currency_task
from tasks.graph_tasks import generate_evidence_task

def test_celery_tasks_registration():
    """Verify tasks are registered in the Celery app."""
    from celery_app import app
    assert "tasks.currency_tasks.verify_currency_task" in app.tasks
    assert "tasks.graph_tasks.generate_evidence_task" in app.tasks

@patch("tasks.currency_tasks.verify_currency_task.delay")
@patch("services.currency_analyzer.get_storage_service")
def test_currency_verification_dispatches_celery(mock_get_storage, mock_delay):
    """Verify that start_verification uploads image and dispatches Celery task."""
    mock_storage = MagicMock()
    mock_storage.upload_file.return_value = "https://mock-url.com/scan.jpg"
    mock_get_storage.return_value = mock_storage

    analyzer = get_currency_analyzer()
    import asyncio
    task_id = asyncio.run(analyzer.start_verification(
        image_bytes=b"fake_image_bytes",
        content_type="image/jpeg",
        denomination=500,
        location="Mumbai"
    ))

    assert task_id is not None
    mock_storage.upload_file.assert_called_once_with(b"fake_image_bytes", "image/jpeg", folder="currency_scans")
    mock_delay.assert_called_once_with(task_id, "https://mock-url.com/scan.jpg", 500, "Mumbai")

@patch("tasks.graph_tasks.generate_evidence_task.delay")
def test_graph_evidence_package_dispatches_celery(mock_delay):
    """Verify that start_evidence_package dispatches Celery task."""
    graph_svc = get_graph_service()
    import asyncio
    task_id = asyncio.run(graph_svc.start_evidence_package(cluster_id=101))

    assert task_id is not None
    mock_delay.assert_called_once_with(101, task_id, None)

@patch("tasks.currency_tasks.get_currency_analyzer")
def test_currency_celery_task_runs_async_verification(mock_get_analyzer):
    """Verify that execution of verify_currency_task calls run_verification."""
    mock_analyzer = MagicMock()
    mock_analyzer.run_verification = AsyncMock()
    mock_get_analyzer.return_value = mock_analyzer

    verify_currency_task(
        task_id="test_task_id",
        file_url="https://mock-url.com/scan.jpg",
        denomination=500,
        location="Mumbai"
    )

    mock_analyzer.run_verification.assert_called_once_with(
        task_id="test_task_id",
        file_url="https://mock-url.com/scan.jpg",
        denomination=500,
        location="Mumbai"
    )

@patch("tasks.graph_tasks.get_evidence_service")
def test_graph_celery_task_runs_async_evidence_generation(mock_get_evidence):
    """Verify that execution of generate_evidence_task calls generate_evidence_package."""
    mock_evidence = MagicMock()
    mock_evidence.generate_evidence_package = AsyncMock()
    mock_get_evidence.return_value = mock_evidence

    generate_evidence_task(cluster_id=101, task_id="test_task_id")

    mock_evidence.generate_evidence_package.assert_called_once_with(
        cluster_id=101, 
        task_id="test_task_id", 
        officer_metadata=None
    )
