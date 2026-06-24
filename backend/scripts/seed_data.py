"""
Seed data script for ShieldAI.

Populates SQLite with realistic demo data:
- ~25 entities (phones, accounts, devices, suspects)
- ~40 relationships
- ~6 fraud clusters
- ~60 geospatial incidents across 15+ Indian cities

Idempotent — safe to run multiple times.
Usage: python scripts/seed_data.py (from backend/ directory)
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_sqlite_connection, init_sqlite_db
from models.task_store import init_task_store


# ── Indian Cities with Coordinates ───────────────────────────
CITIES = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.076, "lng": 72.8777, "pincode": "400001"},
    {"city": "Delhi", "state": "Delhi", "lat": 28.6139, "lng": 77.2090, "pincode": "110001"},
    {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946, "pincode": "560001"},
    {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867, "pincode": "500001"},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707, "pincode": "600001"},
    {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639, "pincode": "700001"},
    {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567, "pincode": "411001"},
    {"city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873, "pincode": "302001"},
    {"city": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462, "pincode": "226001"},
    {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714, "pincode": "380001"},
    {"city": "Chandigarh", "state": "Chandigarh", "lat": 30.7333, "lng": 76.7794, "pincode": "160001"},
    {"city": "Kochi", "state": "Kerala", "lat": 9.9312, "lng": 76.2673, "pincode": "682001"},
    {"city": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577, "pincode": "452001"},
    {"city": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126, "pincode": "462001"},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lng": 83.2185, "pincode": "530001"},
    {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lng": 79.0882, "pincode": "440001"},
    {"city": "Patna", "state": "Bihar", "lat": 25.6093, "lng": 85.1376, "pincode": "800001"},
    {"city": "Guwahati", "state": "Assam", "lat": 26.1445, "lng": 91.7362, "pincode": "781001"},
]


def seed_data():
    """Main seed function — populates all tables."""
    print("🌱 ShieldAI Seed Data Script")
    print("=" * 50)

    # Initialize DB schema
    init_sqlite_db()
    init_task_store()
    print("✅ Database schema initialized")

    with get_sqlite_connection() as conn:
        # Check if data already exists
        existing = conn.execute("SELECT COUNT(*) as cnt FROM entities").fetchone()["cnt"]
        if existing > 0:
            print(f"⚠️  Database already has {existing} entities. Clearing and re-seeding...")
            conn.execute("DELETE FROM incidents")
            conn.execute("DELETE FROM relationships")
            conn.execute("DELETE FROM entities")
            conn.execute("DELETE FROM fraud_clusters")

        # ── Seed Fraud Clusters ──────────────────────────────
        clusters = [
            (1, "Ring Alpha — Delhi Digital Arrest Network", 8, "HIGH", "digital_arrest", "Inter-state", "2024-08-15", "2025-06-20", "active"),
            (2, "Ring Beta — Mumbai Mule Chain", 6, "HIGH", "money_mule", "Inter-state", "2024-11-01", "2025-06-18", "active"),
            (3, "Ring Gamma — Hyderabad KYC Fraud Cell", 5, "MEDIUM", "kyc_fraud", "Local", "2025-01-10", "2025-06-15", "active"),
            (4, "Ring Delta — Cross-border FICN Supply", 4, "HIGH", "ficn_distribution", "Cross-border", "2024-06-01", "2025-05-30", "active"),
            (5, "Ring Epsilon — Bengaluru Investment Scam", 5, "MEDIUM", "investment_fraud", "Inter-state", "2025-02-01", "2025-06-22", "active"),
            (6, "Ring Zeta — Jaipur Lottery Fraud Ring", 3, "LOW", "lottery_scam", "Local", "2025-04-01", "2025-06-10", "disrupted"),
        ]

        conn.executemany(
            """INSERT INTO fraud_clusters (id, cluster_name, size, risk_level, operation_type,
               geographic_span, first_activity, last_activity, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            clusters,
        )
        print(f"✅ Seeded {len(clusters)} fraud clusters")

        # ── Seed Entities ────────────────────────────────────
        entities = [
            # Cluster 1: Delhi Digital Arrest Network
            ("ent-ph-001", "phone", "+919876543210", 0.92, 15, "2024-08-15", "2025-06-20", 1, 1),
            ("ent-ph-002", "phone", "+919123456789", 0.85, 12, "2024-09-01", "2025-06-19", 1, 0),
            ("ent-ac-001", "account", "SBIN0012345678", 0.78, 8, "2024-10-05", "2025-06-18", 1, 0),
            ("ent-dv-001", "device", "IMEI:356938035643809", 0.88, 10, "2024-08-20", "2025-06-20", 1, 1),
            ("ent-su-001", "suspect", "SUSP-DEL-001", 0.95, 20, "2024-08-15", "2025-06-20", 1, 1),
            ("ent-ph-003", "phone", "+918765432109", 0.70, 6, "2025-01-10", "2025-06-15", 1, 0),
            ("ent-ac-002", "account", "HDFC0098765432", 0.65, 5, "2025-02-01", "2025-06-10", 1, 0),
            ("ent-vi-001", "victim", "VIC-DEL-001", 0.10, 1, "2025-06-18", "2025-06-18", 1, 0),

            # Cluster 2: Mumbai Mule Chain
            ("ent-ph-004", "phone", "+919988776655", 0.80, 9, "2024-11-01", "2025-06-18", 2, 1),
            ("ent-ac-003", "account", "ICIC0011223344", 0.75, 7, "2024-11-15", "2025-06-17", 2, 0),
            ("ent-ac-004", "account", "AXIS0055667788", 0.72, 6, "2024-12-01", "2025-06-16", 2, 0),
            ("ent-ph-005", "phone", "+917766554433", 0.68, 5, "2025-01-05", "2025-06-15", 2, 0),
            ("ent-su-002", "suspect", "SUSP-MUM-001", 0.90, 14, "2024-11-01", "2025-06-18", 2, 1),
            ("ent-ac-005", "account", "KOTAK0099887766", 0.60, 4, "2025-03-01", "2025-06-12", 2, 0),

            # Cluster 3: Hyderabad KYC Fraud Cell
            ("ent-ph-006", "phone", "+919543216789", 0.65, 5, "2025-01-10", "2025-06-15", 3, 1),
            ("ent-ph-007", "phone", "+918432167890", 0.55, 3, "2025-02-15", "2025-06-10", 3, 0),
            ("ent-ac-006", "account", "SBI0056781234", 0.50, 3, "2025-03-01", "2025-06-08", 3, 0),
            ("ent-dv-002", "device", "IMEI:490154203237518", 0.60, 4, "2025-01-15", "2025-06-12", 3, 0),
            ("ent-su-003", "suspect", "SUSP-HYD-001", 0.75, 8, "2025-01-10", "2025-06-15", 3, 1),

            # Cluster 4: Cross-border FICN
            ("ent-ph-008", "phone", "+919876012345", 0.85, 7, "2024-06-01", "2025-05-30", 4, 1),
            ("ent-ac-007", "account", "PNB0012349876", 0.70, 4, "2024-08-01", "2025-05-28", 4, 0),
            ("ent-su-004", "suspect", "SUSP-FICN-001", 0.92, 11, "2024-06-01", "2025-05-30", 4, 1),
            ("ent-dv-003", "device", "IMEI:862345678901234", 0.75, 5, "2024-07-15", "2025-05-25", 4, 0),

            # Cluster 5: Bengaluru Investment Scam
            ("ent-ph-009", "phone", "+919012345678", 0.60, 4, "2025-02-01", "2025-06-22", 5, 1),
            ("ent-ac-008", "account", "UTIB0044556677", 0.55, 3, "2025-03-01", "2025-06-20", 5, 0),
            ("ent-ph-010", "phone", "+918901234567", 0.50, 2, "2025-04-01", "2025-06-18", 5, 0),
            ("ent-su-005", "suspect", "SUSP-BLR-001", 0.72, 6, "2025-02-01", "2025-06-22", 5, 1),
            ("ent-ac-009", "account", "KKBK0033445566", 0.48, 2, "2025-04-15", "2025-06-15", 5, 0),
        ]

        conn.executemany(
            """INSERT INTO entities (id, entity_type, value, risk_score, report_count,
               first_seen, last_seen, cluster_id, is_central)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            entities,
        )
        print(f"✅ Seeded {len(entities)} entities")

        # ── Seed Relationships ───────────────────────────────
        relationships = [
            # Cluster 1 relationships
            ("ent-ph-001", "ent-su-001", "called", 5.0, "2024-08-15", "2025-06-20", "RPT-001"),
            ("ent-ph-002", "ent-su-001", "called", 4.0, "2024-09-01", "2025-06-19", "RPT-002"),
            ("ent-su-001", "ent-ac-001", "transacted_with", 8.0, "2024-10-05", "2025-06-18", "RPT-003"),
            ("ent-dv-001", "ent-ph-001", "same_device", 3.0, "2024-08-20", "2025-06-20", None),
            ("ent-dv-001", "ent-ph-002", "same_device", 2.0, "2024-09-15", "2025-06-15", None),
            ("ent-ph-003", "ent-su-001", "called", 2.0, "2025-01-10", "2025-06-15", "RPT-004"),
            ("ent-su-001", "ent-ac-002", "transacted_with", 3.0, "2025-02-01", "2025-06-10", None),
            ("ent-ph-001", "ent-vi-001", "called", 1.0, "2025-06-18", "2025-06-18", "RPT-005"),
            ("ent-ph-003", "ent-ac-001", "transacted_with", 2.0, "2025-03-01", "2025-06-12", None),

            # Cluster 2 relationships
            ("ent-ph-004", "ent-su-002", "called", 6.0, "2024-11-01", "2025-06-18", "RPT-006"),
            ("ent-su-002", "ent-ac-003", "transacted_with", 7.0, "2024-11-15", "2025-06-17", "RPT-007"),
            ("ent-ac-003", "ent-ac-004", "transacted_with", 5.0, "2024-12-01", "2025-06-16", None),
            ("ent-ac-004", "ent-ac-005", "mule_for", 4.0, "2025-01-15", "2025-06-12", "RPT-008"),
            ("ent-ph-005", "ent-su-002", "called", 3.0, "2025-01-05", "2025-06-15", None),
            ("ent-ph-004", "ent-ac-003", "transacted_with", 2.0, "2025-02-01", "2025-06-14", None),
            ("ent-su-002", "ent-ac-005", "transacted_with", 3.0, "2025-03-01", "2025-06-12", None),

            # Cluster 3 relationships
            ("ent-ph-006", "ent-su-003", "called", 3.0, "2025-01-10", "2025-06-15", "RPT-009"),
            ("ent-ph-007", "ent-su-003", "called", 2.0, "2025-02-15", "2025-06-10", None),
            ("ent-su-003", "ent-ac-006", "transacted_with", 4.0, "2025-03-01", "2025-06-08", "RPT-010"),
            ("ent-dv-002", "ent-ph-006", "same_device", 2.0, "2025-01-15", "2025-06-12", None),
            ("ent-dv-002", "ent-ph-007", "same_device", 1.0, "2025-02-20", "2025-06-10", None),

            # Cluster 4 relationships
            ("ent-ph-008", "ent-su-004", "called", 4.0, "2024-06-01", "2025-05-30", "RPT-011"),
            ("ent-su-004", "ent-ac-007", "transacted_with", 5.0, "2024-08-01", "2025-05-28", "RPT-012"),
            ("ent-dv-003", "ent-ph-008", "same_device", 3.0, "2024-07-15", "2025-05-25", None),
            ("ent-su-004", "ent-dv-003", "same_device", 2.0, "2024-07-20", "2025-05-20", None),

            # Cluster 5 relationships
            ("ent-ph-009", "ent-su-005", "called", 3.0, "2025-02-01", "2025-06-22", "RPT-013"),
            ("ent-su-005", "ent-ac-008", "transacted_with", 4.0, "2025-03-01", "2025-06-20", "RPT-014"),
            ("ent-ph-010", "ent-su-005", "called", 2.0, "2025-04-01", "2025-06-18", None),
            ("ent-su-005", "ent-ac-009", "transacted_with", 2.0, "2025-04-15", "2025-06-15", None),
            ("ent-ph-009", "ent-ac-008", "transacted_with", 1.0, "2025-05-01", "2025-06-10", None),

            # Cross-cluster connections
            ("ent-su-001", "ent-su-002", "called", 2.0, "2025-03-15", "2025-06-01", None),
            ("ent-ac-001", "ent-ac-003", "transacted_with", 1.5, "2025-04-01", "2025-05-15", None),
            ("ent-ph-001", "ent-ph-004", "called", 1.0, "2025-05-01", "2025-06-05", None),
        ]

        conn.executemany(
            """INSERT INTO relationships (source_id, target_id, relationship, weight,
               first_seen, last_seen, linked_report_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            relationships,
        )
        print(f"✅ Seeded {len(relationships)} relationships")

        # ── Seed Incidents ───────────────────────────────────
        incident_types = ["scam_call", "ficn", "financial_fraud"]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        severity_weights = [0.2, 0.35, 0.30, 0.15]

        incidents = []
        base_date = datetime(2025, 6, 24)

        for i in range(65):
            city_data = random.choice(CITIES)
            # Add slight coordinate variation
            lat = city_data["lat"] + random.uniform(-0.05, 0.05)
            lng = city_data["lng"] + random.uniform(-0.05, 0.05)
            days_ago = random.randint(0, 30)
            created = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")

            # Weight incident types: more scam_calls
            itype = random.choices(
                incident_types,
                weights=[0.50, 0.20, 0.30],
                k=1,
            )[0]

            severity = random.choices(severities, weights=severity_weights, k=1)[0]

            incidents.append((
                f"RPT-SEED-{i:03d}",
                itype,
                round(lat, 6),
                round(lng, 6),
                city_data["city"],
                city_data["state"],
                city_data["pincode"],
                severity,
                created,
            ))

        conn.executemany(
            """INSERT INTO incidents (report_id, incident_type, lat, lng, city, state, pincode, severity, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            incidents,
        )
        print(f"✅ Seeded {len(incidents)} geospatial incidents")

    print()
    print("=" * 50)
    print("🎉 Seed data complete!")
    print()
    print("Summary:")
    print(f"  • {len(clusters)} fraud clusters")
    print(f"  • {len(entities)} entities (phones, accounts, devices, suspects)")
    print(f"  • {len(relationships)} relationships")
    print(f"  • {len(incidents)} geospatial incidents across {len(CITIES)} cities")
    print()
    print("Start the server with:")
    print("  cd backend && uvicorn main:app --reload --port 8000")
    print("  Then open: http://localhost:8000/docs")


if __name__ == "__main__":
    seed_data()
