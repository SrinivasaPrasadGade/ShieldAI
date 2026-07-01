import sys
import os
import unittest.mock as mock

# Add backend directory to path so imports work
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import pytest
import tempfile
import shutil

# Set up environment variables for testing
os.environ["SQLITE_DB_PATH"] = "backend/shield_ai_test.db"
os.environ["ENABLE_ZERO_SHOT"] = "false"
os.environ["GEMINI_API_KEY"] = "mock-key"

@pytest.fixture(scope="session", autouse=True)
def test_db_setup():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "shield_ai_test.db")
    os.environ["SQLITE_DB_PATH"] = db_path
    from models.database import init_sqlite_db
    from models.task_store import init_task_store
    init_sqlite_db()
    init_task_store()
    yield
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

# Create mock objects
mock_firestore_client = mock.MagicMock()
mock_storage_bucket = mock.MagicMock()

# Setup firebase_admin module mocks in sys.modules
sys.modules['firebase_admin'] = mock.MagicMock()
sys.modules['firebase_admin.credentials'] = mock.MagicMock()
sys.modules['firebase_admin.firestore'] = mock.MagicMock()
sys.modules['firebase_admin.storage'] = mock.MagicMock()
sys.modules['firebase_admin.auth'] = mock.MagicMock()

# Mock exceptions with a valid BaseException class so 'except FirebaseError:' doesn't throw a TypeError
mock_exceptions = mock.MagicMock()
class MockFirebaseError(Exception): pass
mock_exceptions.FirebaseError = MockFirebaseError
sys.modules['firebase_admin.exceptions'] = mock_exceptions

# Configure the mocked functions
import firebase_admin
import firebase_admin.credentials
import firebase_admin.firestore
import firebase_admin.storage

firebase_admin.firestore.client.return_value = mock_firestore_client
firebase_admin.storage.bucket.return_value = mock_storage_bucket

# Bind attributes to main module mock
firebase_admin.credentials = firebase_admin.credentials
firebase_admin.firestore = firebase_admin.firestore
firebase_admin.storage = firebase_admin.storage
