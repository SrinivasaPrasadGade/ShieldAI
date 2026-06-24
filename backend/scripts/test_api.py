"""
Test script for ShieldAI API endpoints.

Tests all 25 endpoints with valid inputs and error cases.
Run with: python scripts/test_api.py
Note: Requires the server to be running (uvicorn main:app)
"""

import httpx
import asyncio
import time
from typing import Callable, Any

BASE_URL = "http://localhost:8000"
client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

results = {"passed": 0, "failed": 0}


async def run_test(name: str, test_fn: Callable) -> None:
    """Run a single test and report result."""
    print(f"Testing {name}...", end=" ", flush=True)
    start_time = time.monotonic()
    
    try:
        await test_fn()
        duration = (time.monotonic() - start_time) * 1000
        print(f"[{GREEN}PASS{RESET}] ({duration:.0f}ms)")
        results["passed"] += 1
    except Exception as e:
        duration = (time.monotonic() - start_time) * 1000
        print(f"[{RED}FAIL{RESET}] ({duration:.0f}ms) - {str(e)}")
        results["failed"] += 1


def assert_status(response: httpx.Response, expected: int, context: str = ""):
    if response.status_code != expected:
        raise AssertionError(f"Expected status {expected}, got {response.status_code}. {response.text} {context}")


# ── System Tests ─────────────────────────────────────────────

async def test_health():
    r = await client.get("/health")
    assert_status(r, 200)
    data = r.json()
    if data["status"] != "healthy":
        raise AssertionError("System not healthy")


# ── Scam Tests ───────────────────────────────────────────────

async def test_scam_analyze():
    r = await client.post("/api/scam/analyze", json={
        "text": "URGENT: Your CBI arrest warrant is issued. Transfer Rs 50000 to clear your name.",
        "source_phone": "+919876543210"
    })
    assert_status(r, 200)
    data = r.json()
    if "risk_score" not in data or data["risk_label"] not in ("HIGH", "MEDIUM", "LOW"):
        raise AssertionError("Invalid scam analysis schema")

async def test_scam_analyze_empty():
    r = await client.post("/api/scam/analyze", json={"text": "   "})
    assert_status(r, 422, "Should reject empty text")

async def test_scam_alerts():
    r = await client.get("/api/scam/alerts?limit=5")
    assert_status(r, 200)
    if "alerts" not in r.json():
        raise AssertionError("Missing alerts key")

async def test_scam_stats():
    r = await client.get("/api/scam/stats?days=7")
    assert_status(r, 200)
    if "total_analyzed" not in r.json():
        raise AssertionError("Missing total_analyzed")


# ── Graph Tests ──────────────────────────────────────────────

async def test_graph_network():
    r = await client.get("/api/graph/network?limit=10")
    assert_status(r, 200)
    data = r.json()
    if not all(k in data for k in ["nodes", "edges", "clusters"]):
        raise AssertionError("Missing graph keys")

async def test_graph_query_phone():
    r = await client.post("/api/graph/query", json={"phone_number": "+919876543210"})
    assert_status(r, 200)
    if "found" not in r.json():
        raise AssertionError("Missing found key")

async def test_graph_query_empty():
    r = await client.post("/api/graph/query", json={})
    assert_status(r, 422, "Should require at least one field")

async def test_graph_clusters():
    r = await client.get("/api/graph/clusters")
    assert_status(r, 200)

async def test_graph_stats():
    r = await client.get("/api/graph/stats")
    assert_status(r, 200)


# ── Geo Tests ────────────────────────────────────────────────

async def test_geo_incidents():
    r = await client.get("/api/geo/incidents?days=30")
    assert_status(r, 200)
    if "incidents" not in r.json():
        raise AssertionError("Missing incidents")

async def test_geo_heatmap():
    r = await client.get("/api/geo/heatmap")
    assert_status(r, 200)
    if "points" not in r.json():
        raise AssertionError("Missing points")

async def test_geo_hotspots():
    r = await client.get("/api/geo/hotspots?threshold=1")
    assert_status(r, 200)

async def test_geo_city_stats():
    r = await client.get("/api/geo/city-stats")
    assert_status(r, 200)


# ── Citizen Tests ────────────────────────────────────────────

async def test_citizen_chat():
    r = await client.post("/api/citizen/chat", json={
        "message": "I got a call from CBI",
        "session_id": "test-session-1"
    })
    assert_status(r, 200)
    if "response" not in r.json():
        raise AssertionError("Missing chat response")

async def test_citizen_report():
    r = await client.post("/api/citizen/report", json={
        "description": "Someone called me asking for OTP for my SBI account. It was very suspicious.",
        "phone_number": "9876543210",
        "contact_email": "test@example.com"
    })
    assert_status(r, 201)
    data = r.json()
    if "report_id" not in data or "reference_number" not in data:
        raise AssertionError("Missing report ID or reference")
    return data["report_id"]

async def test_citizen_report_invalid_email():
    r = await client.post("/api/citizen/report", json={
        "description": "Suspicious call",
        "contact_email": "not-an-email"
    })
    assert_status(r, 422, "Should reject invalid email")


# ── Risk Tests ───────────────────────────────────────────────

async def test_phone_risk():
    r = await client.post("/api/risk/phone", json={"phone_number": "9876543210"})
    assert_status(r, 200)
    data = r.json()
    if "risk_score" not in data or "risk_label" not in data:
        raise AssertionError("Missing risk fields")

async def test_phone_risk_invalid():
    r = await client.post("/api/risk/phone", json={"phone_number": "123"})
    assert_status(r, 422, "Should reject invalid phone format")


async def main():
    print(f"\n🚀 Running ShieldAI API Tests against {BASE_URL}")
    print("=" * 60)
    
    # Wait for server to be up
    try:
        await client.get("/health")
    except httpx.ConnectError:
        print(f"{RED}Error: Server is not running at {BASE_URL}{RESET}")
        print("Please start the server first: uvicorn main:app")
        return

    # Run tests
    await run_test("System Health", test_health)
    
    print("\n[ Scam Detection ]")
    await run_test("POST /analyze", test_scam_analyze)
    await run_test("POST /analyze (Empty text)", test_scam_analyze_empty)
    await run_test("GET /alerts", test_scam_alerts)
    await run_test("GET /stats", test_scam_stats)
    
    print("\n[ Fraud Graph ]")
    await run_test("GET /network", test_graph_network)
    await run_test("POST /query (Phone)", test_graph_query_phone)
    await run_test("POST /query (Empty)", test_graph_query_empty)
    await run_test("GET /clusters", test_graph_clusters)
    await run_test("GET /stats", test_graph_stats)
    
    print("\n[ Geospatial ]")
    await run_test("GET /incidents", test_geo_incidents)
    await run_test("GET /heatmap", test_geo_heatmap)
    await run_test("GET /hotspots", test_geo_hotspots)
    await run_test("GET /city-stats", test_geo_city_stats)
    
    print("\n[ Citizen Shield ]")
    await run_test("POST /chat", test_citizen_chat)
    report_id = None
    try:
        report_id = await test_citizen_report()
        print(f"[{GREEN}PASS{RESET}] POST /report")
        results["passed"] += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] POST /report - {str(e)}")
        results["failed"] += 1
        
    await run_test("POST /report (Invalid email)", test_citizen_report_invalid_email)
    
    if report_id:
        async def test_report_status():
            r = await client.get(f"/api/citizen/report/{report_id}")
            assert_status(r, 200)
        await run_test(f"GET /report/{{id}}", test_report_status)
        
    print("\n[ Risk Assessment ]")
    await run_test("POST /phone", test_phone_risk)
    await run_test("POST /phone (Invalid)", test_phone_risk_invalid)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Total Tests: {results['passed'] + results['failed']}")
    print(f"Passed: {GREEN}{results['passed']}{RESET}")
    if results["failed"] > 0:
        print(f"Failed: {RED}{results['failed']}{RESET}")
    print("=" * 60)
    
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
