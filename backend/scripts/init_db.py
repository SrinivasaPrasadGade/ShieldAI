import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path to allow standalone execution
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import init_sqlite_db, get_sqlite_connection, get_firestore_client
from models.schemas import ScamScript

def seed_sqlite_data():
    """Seeds some initial test entities and relationships into SQLite."""
    print("Seeding SQLite tables...")
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Seed some standard clusters
        clusters = [
            (1, "Ring Alpha", 3, "HIGH", "digital_arrest", "Inter-state", "2026-06-20T10:00:00+00:00", "2026-06-24T12:00:00+00:00", "active"),
            (2, "Ring Beta", 2, "MEDIUM", "kyc_fraud", "Local", "2026-06-22T08:00:00+00:00", "2026-06-24T14:30:00+00:00", "active")
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO fraud_clusters (id, cluster_name, size, risk_level, operation_type, geographic_span, first_activity, last_activity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, clusters)
        
        # 2. Seed some entities (phones, accounts, suspects)
        entities = [
            # Ring Alpha entities
            ("phone_1", "phone", "+919876543210", 0.9, 12, "2026-06-20T10:00:00+00:00", "2026-06-24T12:00:00+00:00", 1, 1),
            ("account_1", "account", "123456789012 (SBI)", 0.85, 8, "2026-06-21T11:00:00+00:00", "2026-06-24T11:30:00+00:00", 1, 0),
            ("victim_1", "victim", "Victim A (Mumbai)", 0.0, 1, "2026-06-24T10:00:00+00:00", "2026-06-24T10:00:00+00:00", 1, 0),
            
            # Ring Beta entities
            ("phone_2", "phone", "+918765432109", 0.6, 4, "2026-06-22T08:00:00+00:00", "2026-06-24T14:30:00+00:00", 2, 1),
            ("account_2", "account", "987654321098 (HDFC)", 0.5, 3, "2026-06-22T09:00:00+00:00", "2026-06-24T14:00:00+00:00", 2, 0)
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO entities (id, entity_type, value, risk_score, report_count, first_seen, last_seen, cluster_id, is_central)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, entities)
        
        # 3. Seed relationships
        relationships = [
            ("phone_1", "victim_1", "called", 1.0, "2026-06-24T10:00:00+00:00", "2026-06-24T10:00:00+00:00", "report_abc123"),
            ("victim_1", "account_1", "transacted_with", 2.0, "2026-06-24T10:15:00+00:00", "2026-06-24T10:30:00+00:00", "report_abc123"),
            ("phone_1", "account_1", "mule_for", 5.0, "2026-06-21T11:00:00+00:00", "2026-06-24T12:00:00+00:00", None),
            
            ("phone_2", "account_2", "mule_for", 2.0, "2026-06-22T09:00:00+00:00", "2026-06-24T14:30:00+00:00", None)
        ]
        cursor.executemany("""
            INSERT INTO relationships (source_id, target_id, relationship, weight, first_seen, last_seen, linked_report_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, relationships)
        
        # 4. Seed incident logs
        incidents = [
            ("report_abc123", "scam_call", 19.0760, 72.8777, "Mumbai", "Maharashtra", "400001", "HIGH", "2026-06-24T10:00:00+00:00"),
            ("report_xyz789", "ficn", 28.6139, 77.2090, "New Delhi", "Delhi", "110001", "CRITICAL", "2026-06-24T11:00:00+00:00")
        ]
        cursor.executemany("""
            INSERT INTO incidents (report_id, incident_type, lat, lng, city, state, pincode, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, incidents)
        
        print("SQLite data seeded successfully.")

def seed_firestore_data():
    """Seeds initial known scam scripts into Cloud Firestore."""
    print("Seeding Firestore scam scripts...")
    db = get_firestore_client()
    if db is None:
        print("Warning: Firestore client could not be initialized. Skipping Firestore seeding.")
        return
    
    scripts = [
        ScamScript(
            id="script_digital_arrest_1",
            scam_type="digital_arrest",
            agency_impersonated="CBI",
            script_text="This is CBI officer Rajesh Kumar. Your Aadhaar card has been linked to a money laundering case involving Jet Airways. You are under digital arrest. You must not close this video call, and you must transfer a security deposit of Rs 5,00,000 for bank account verification.",
            embedding=[0.012, -0.045, 0.089],  # mock embedding values
            reported_count=45,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        ),
        ScamScript(
            id="script_customs_seizure_1",
            scam_type="customs_seizure",
            agency_impersonated="Customs",
            script_text="Greetings, this is Mumbai Customs. A parcel sent from Taiwan containing 50 grams of MDMA (drugs) and 5 passports has been seized in your name. To prevent immediate arrest by local police, you must connect to our legal cell over Skype and verify your financial assets.",
            embedding=[-0.021, 0.034, 0.112],
            reported_count=32,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        ),
        ScamScript(
            id="script_kyc_fraud_1",
            scam_type="kyc_fraud",
            agency_impersonated="TRAI",
            script_text="Attention TRAI user. Your mobile connection will be suspended in 2 hours because a duplicate SIM card has been issued on your Aadhaar card and is sending illegal harassing messages. Please press 9 to speak with our verification agent and submit your bank account details.",
            embedding=[0.054, -0.067, 0.003],
            reported_count=87,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )
    ]
    
    for script in scripts:
        doc_ref = db.collection("scam_scripts").document(script.id)
        # Convert Pydantic model to dictionary
        doc_ref.set(script.model_dump())
        print(f"Firestore script seeded: {script.id}")
    
    print("Firestore scam scripts seeded successfully.")

def main():
    try:
        # Initialize SQLite schema
        print("Initializing SQLite schema...")
        init_sqlite_db()
        print("SQLite schema initialized.")
        
        # Seed SQLite
        seed_sqlite_data()
        
        # Seed Firestore
        seed_firestore_data()
        
        print("\nAll databases initialized and seeded successfully.")
    except Exception as e:
        print(f"Error during database initialization: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
