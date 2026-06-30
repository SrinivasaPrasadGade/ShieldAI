import os
import shutil
from pathlib import Path
import sqlite3

def migrate_databases():
    project_root = Path(__file__).resolve().parent.parent.parent
    backend_dir = project_root / "backend"
    data_dir = backend_dir / "data"
    
    canonical_db_path = data_dir / "shield_ai.db"
    
    # Ensure canonical directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    
    duplicate_paths = [
        backend_dir / "shield_ai.db",
        backend_dir / "backend" / "shield_ai.db",
    ]
    
    # If the canonical DB doesn't exist but a duplicate does, move the first one we find
    if not canonical_db_path.exists():
        for dup in duplicate_paths:
            if dup.exists():
                print(f"Moving {dup} to {canonical_db_path}")
                shutil.move(str(dup), str(canonical_db_path))
                break
                
    # If canonical DB now exists, we would ideally merge data here
    # For now, we will just delete the remaining duplicates since they are unused leftovers
    for dup in duplicate_paths:
        if dup.exists() and dup != canonical_db_path:
            print(f"Removing duplicate database at {dup}")
            try:
                dup.unlink()
            except Exception as e:
                print(f"Failed to remove {dup}: {e}")
                
    print(f"Migration complete. Canonical DB is at: {canonical_db_path}")

if __name__ == "__main__":
    migrate_databases()
