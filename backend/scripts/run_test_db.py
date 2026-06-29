import sys
from datetime import datetime, timezone
from backend.models.database import get_sqlite_connection, get_firestore_client
from backend.models.schemas import FraudReport, VictimLocation, DetoxifyScores

def test_sqlite():
    print("Testing SQLite integration...")
    try:
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # Query count of entities
            cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = cursor.fetchone()[0]
            print(f"  [PASS] Found {entity_count} entities in SQLite database.")
            
            # Query central entities
            cursor.execute("SELECT value, risk_score FROM entities WHERE is_central = 1")
            central_nodes = cursor.fetchall()
            print("  Central Suspect Hubs:")
            for node in central_nodes:
                print(f"    - {node['value']} (Risk: {node['risk_score']})")
                
            # Query relationships
            cursor.execute("SELECT COUNT(*) FROM relationships")
            rel_count = cursor.fetchone()[0]
            print(f"  [PASS] Found {rel_count} relationships in SQLite database.")
            
            # Test writing and reading back
            cursor.execute("""
                INSERT INTO entities (id, entity_type, value, risk_score, report_count)
                VALUES ('test_phone_id', 'phone', '+919999988888', 0.95, 1)
            """)
            print("  [PASS] Successfully inserted test entity in SQLite.")
            
            cursor.execute("SELECT value, risk_score FROM entities WHERE id = 'test_phone_id'")
            test_node = cursor.fetchone()
            assert test_node['value'] == '+919999988888'
            assert test_node['risk_score'] == 0.95
            print("  [PASS] Verified test entity details in SQLite.")
            
            # Cleanup test entity
            cursor.execute("DELETE FROM entities WHERE id = 'test_phone_id'")
            print("  [PASS] Cleaned up SQLite test entity.")
            
        print("SQLite integration tests passed.\n")
    except Exception as e:
        print(f"  [FAIL] SQLite test failed: {e}", file=sys.stderr)
        raise e

def test_firestore():
    print("Testing Firestore integration...")
    try:
        db = get_firestore_client()
        
        # Define a valid FraudReport
        report_data = FraudReport(
            id="test_report_123",
            source="api",
            report_type="digital_arrest",
            description="Scammer pretending to be Customs officer demanded payment under threat of drug case.",
            phone_numbers=["+919876543210"],
            account_numbers=["123456789012"],
            victim_location=VictimLocation(
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",
                lat=19.0760,
                lng=72.8777
            ),
            risk_score=0.92,
            risk_label="HIGH",
            gemini_classification="Matches known drug packet Customs seizure scam script.",
            detoxify_scores=DetoxifyScores(
                toxicity=0.85,
                threat=0.90,
                insult=0.10
            ),
            bert_confidence=0.89,
            scam_script_match=0.94,
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        doc_ref = db.collection("fraud_reports").document(report_data.id)
        
        # 1. Write the document
        print(f"  Writing test document '{report_data.id}' to Firestore...")
        doc_ref.set(report_data.model_dump())
        print("  [PASS] Write operation completed.")
        
        # 2. Read the document
        print("  Reading test document from Firestore...")
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise Exception("Document was not found in Firestore after write!")
            
        retrieved_data = snapshot.to_dict()
        print("  [PASS] Document retrieved successfully.")
        
        # Verify schema field values
        assert retrieved_data["id"] == "test_report_123"
        assert retrieved_data["source"] == "api"
        assert retrieved_data["risk_label"] == "HIGH"
        assert retrieved_data["victim_location"]["city"] == "Mumbai"
        print("  [PASS] Verified document schema details in Firestore.")
        
        # 3. Clean up the document
        print("  Cleaning up test document...")
        doc_ref.delete()
        print("  [PASS] Delete operation completed.")
        
        print("Firestore integration tests passed.\n")
    except Exception as e:
        print(f"  [FAIL] Firestore test failed: {e}", file=sys.stderr)
        raise e

def main():
    try:
        test_sqlite()
        test_firestore()
        print("All database integration tests completed successfully.")
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
