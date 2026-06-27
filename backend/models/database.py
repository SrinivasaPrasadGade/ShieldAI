import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Load environment variables
load_dotenv()

# ==========================================
# SQLITE CONNECTION & SCHEMA DEFINITIONS
# ==========================================

SQLITE_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,    -- 'phone', 'account', 'device', 'victim', 'suspect'
    value       TEXT NOT NULL,    -- actual phone number / account number / device ID
    risk_score  REAL DEFAULT 0.0,
    report_count INTEGER DEFAULT 0,
    first_seen  TEXT,
    last_seen   TEXT,
    cluster_id  INTEGER,          -- Louvain output community id
    is_central  BOOLEAN DEFAULT 0 -- 1 = mastermind/mule hub
);

CREATE TABLE IF NOT EXISTS relationships (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT REFERENCES entities(id),
    target_id       TEXT REFERENCES entities(id),
    relationship    TEXT NOT NULL, -- 'called', 'transacted_with', 'same_device', 'mule_for'
    weight          REAL DEFAULT 1.0,
    first_seen      TEXT,
    last_seen       TEXT,
    linked_report_id TEXT
);

CREATE TABLE IF NOT EXISTS fraud_clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name    TEXT,         -- "Ring Alpha", etc.
    size            INTEGER DEFAULT 0,
    risk_level      TEXT DEFAULT 'LOW',
    operation_type  TEXT,
    geographic_span TEXT DEFAULT 'Local',
    first_activity  TEXT,
    last_activity   TEXT,
    status          TEXT DEFAULT 'active'  -- 'active', 'disrupted', 'neutralised'
);

CREATE TABLE IF NOT EXISTS incidents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id   TEXT,             -- reference to Firestore fraud_reports/{id}
    incident_type TEXT,           -- 'scam_call', 'ficn', 'financial_fraud'
    lat         REAL,
    lng         REAL,
    city        TEXT,
    state       TEXT,
    pincode     TEXT,
    severity    TEXT,
    created_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_incidents_lat_lng ON incidents(lat, lng);
CREATE INDEX IF NOT EXISTS idx_entities_cluster ON entities(cluster_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
"""

@contextmanager
def get_sqlite_connection():
    """Context manager for obtaining a SQLite database connection."""
    db_path = os.getenv("SQLITE_DB_PATH", "backend/shield_ai.db")
    
    # Ensure directory containing db file exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # return dict-like rows
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_sqlite_db():
    """Initializes the SQLite database with the DDL schema."""
    with get_sqlite_connection() as conn:
        conn.executescript(SQLITE_SCHEMA_DDL)

# ==========================================
# FIRESTORE CLIENT INITIALIZATION
# ==========================================

_firestore_client = None

def get_firestore_client():
    """
    Initializes and returns the Firestore client.
    First attempts to authenticate using the configured credentials file,
    then falls back to Application Default Credentials (ADC).
    """
    global _firestore_client
    if _firestore_client is None:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "backend/firebase-credentials.json")
        
        # Check if the credentials file exists, is a file, and is populated
        if os.path.exists(cred_path) and os.path.isfile(cred_path) and os.path.getsize(cred_path) > 0:
            cred = credentials.Certificate(cred_path)
            try:
                firebase_admin.initialize_app(cred)
            except ValueError:
                # App already initialized
                pass
        else:
            # Fall back to Application Default Credentials
            try:
                firebase_admin.initialize_app()
            except ValueError:
                # App already initialized
                pass
            except Exception as e:
                print(f"Warning: Failed to initialize Firebase ADC: {e}")
        
        try:
            _firestore_client = firestore.client()
        except Exception as e:
            print(f"Warning: Firestore client could not be initialized: {e}")
            _firestore_client = None
            
    return _firestore_client
