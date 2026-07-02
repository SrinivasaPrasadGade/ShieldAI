import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_protected_routes_require_auth():
    """
    Test that accessing protected routes without an auth token returns 401 Unauthorized.
    """
    # /api/graph is a protected prefix according to main.py
    response = client.get("/api/graph/networks")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    # /api/geo is also a protected prefix
    response = client.get("/api/geo/heatmap")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

def test_unprotected_routes_accessible():
    """
    Test that unprotected routes like /health are accessible without auth.
    """
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
