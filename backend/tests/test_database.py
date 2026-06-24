import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from models.database import get_sqlite_connection, init_sqlite_db

def test_sqlite_setup():
    init_sqlite_db()
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        # Query count of entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        assert entity_count >= 0
        
        # Test writing and reading back
        cursor.execute("""
            INSERT INTO entities (id, entity_type, value, risk_score, report_count)
            VALUES ('test_phone_id_pytest', 'phone', '+919999988888', 0.95, 1)
        """)
        
        cursor.execute("SELECT value, risk_score FROM entities WHERE id = 'test_phone_id_pytest'")
        test_node = cursor.fetchone()
        assert test_node['value'] == '+919999988888'
        assert test_node['risk_score'] == 0.95
        
        # Cleanup test entity
        cursor.execute("DELETE FROM entities WHERE id = 'test_phone_id_pytest'")
