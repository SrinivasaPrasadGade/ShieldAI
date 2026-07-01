import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

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

CREATE TABLE IF NOT EXISTS reference_sequences (
    year INTEGER PRIMARY KEY,
    counter INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS offline_reports (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    synced BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS currency_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_lat_lng ON incidents(lat, lng);
CREATE INDEX IF NOT EXISTS idx_entities_cluster ON entities(cluster_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
"""

@contextmanager
def get_sqlite_connection():
    """Context manager for obtaining a SQLite database connection."""
    from config import settings
    db_path = settings.sqlite_db_abs_path
    
    # Ensure directory containing db file exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # return dict-like rows
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_sqlite_db():
    """Initializes the SQLite database with the DDL schema."""
    with get_sqlite_connection() as conn:
        conn.executescript(SQLITE_SCHEMA_DDL)

# ==========================================
# FIRESTORE CLIENT INITIALIZATION
# ==========================================

_NOT_INITIALIZED = object()
_firestore_client = _NOT_INITIALIZED

def init_firebase():
    """Initializes the Firebase Admin SDK app using environment variables or ADC."""
    from config import settings
    import json
    import base64
    
    # If app is already initialized, just return
    if firebase_admin._apps:
        return

    cred_path = settings.firebase_credentials_abs_path
    
    # Check if the credentials are provided via environment variables
    if getattr(settings, 'FIREBASE_CREDENTIALS_B64', ''):
        try:
            cred_dict = json.loads(base64.b64decode(settings.FIREBASE_CREDENTIALS_B64).decode('utf-8'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return
        except ValueError:
            pass
        except Exception as e:
            print(f"Warning: Failed to initialize Firebase with FIREBASE_CREDENTIALS_B64: {e}")
            
    if getattr(settings, 'FIREBASE_CREDENTIALS_JSON', ''):
        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return
        except ValueError:
            pass
        except Exception as e:
            print(f"Warning: Failed to initialize Firebase with FIREBASE_CREDENTIALS_JSON: {e}")
            
    # Check if the credentials file exists, is a file, and is populated
    if os.path.exists(cred_path) and os.path.isfile(cred_path) and os.path.getsize(cred_path) > 0:
        cred = credentials.Certificate(cred_path)
        try:
            firebase_admin.initialize_app(cred)
            return
        except ValueError:
            # App already initialized
            return
            
    # Fall back to Application Default Credentials
    try:
        firebase_admin.initialize_app()
    except ValueError:
        # App already initialized
        pass
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase ADC: {e}")


def get_firestore_client():
    """
    Initializes and returns the Firestore client.
    """
    global _firestore_client
    if _firestore_client is _NOT_INITIALIZED:
        init_firebase()
        
        try:
            _firestore_client = firestore.client()
        except Exception as e:
            print(f"Warning: Firestore client could not be initialized: {e}")
            _firestore_client = None
            
    return _firestore_client
