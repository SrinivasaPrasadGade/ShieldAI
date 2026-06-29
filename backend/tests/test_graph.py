import pytest
import sqlite3
from services.graph_service import get_graph_service
from models.database import get_sqlite_connection, init_sqlite_db

def test_graph_add_and_cluster():
    # Ensure tables are initialized
    init_sqlite_db()
    
    graph_svc = get_graph_service()
    
    # Clean up any potential test entities from previous runs
    with get_sqlite_connection() as conn:
        conn.execute("DELETE FROM entities")
        conn.execute("DELETE FROM relationships")
        conn.execute("DELETE FROM fraud_clusters")
        
    try:
        # Add a small mock network structure to trigger Louvain partitioning (needs >= 3 nodes)
        # We will create a small star network:
        # victim_test_report_1 -> phone_+919900112233
        # victim_test_report_2 -> phone_+919900112233
        # victim_test_report_3 -> phone_+919900112233
        # This makes phone_+919900112233 highly central
        
        graph_svc.add_report_to_graph(
            report_id="test_report_1",
            phone_numbers=["+919900112233"],
            account_numbers=["ACC99000001"],
            description="First test report"
        )
        
        graph_svc.add_report_to_graph(
            report_id="test_report_2",
            phone_numbers=["+919900112233"],
            account_numbers=["ACC99000001"],
            description="Second test report"
        )
        
        graph_svc.add_report_to_graph(
            report_id="test_report_3",
            phone_numbers=["+919900112233"],
            account_numbers=["ACC99000002"],
            description="Third test report"
        )

        # Verify entity nodes are added
        with get_sqlite_connection() as conn:
            # Check victim node
            victim = conn.execute("SELECT id, entity_type FROM entities WHERE id = 'victim_test_report_1'").fetchone()
            assert victim is not None
            assert victim["entity_type"] == "victim"
            
            # Check phone node
            phone = conn.execute("SELECT id, entity_type, risk_score, report_count, cluster_id, is_central FROM entities WHERE id = 'phone_+919900112233'").fetchone()
            assert phone is not None
            assert phone["entity_type"] == "phone"
            assert phone["risk_score"] == 0.9
            assert phone["report_count"] == 3
            
            # Check community detection outputs
            assert phone["cluster_id"] is not None
            # Betweenness centrality of the central hub phone node should be high, making it central
            assert phone["is_central"] == 1
            
            # Check relationship edge
            edge = conn.execute("SELECT weight FROM relationships WHERE source_id = 'phone_+919900112233' AND target_id = 'victim_test_report_1'").fetchone()
            assert edge is not None
            assert edge["weight"] == 1.0
            
            # Check that cluster is synchronized in the fraud_clusters table
            cluster_id = phone["cluster_id"]
            cluster = conn.execute("SELECT cluster_name, risk_level FROM fraud_clusters WHERE id = ?", (cluster_id,)).fetchone()
            assert cluster is not None
            assert "Fraud Ring" in cluster["cluster_name"]
            assert cluster["risk_level"] == "HIGH"
            
    finally:
        # Cleanup
        with get_sqlite_connection() as conn:
            conn.execute("DELETE FROM entities")
            conn.execute("DELETE FROM relationships")
            conn.execute("DELETE FROM fraud_clusters")
