#!/usr/bin/env python3
"""Database migration script to add user_rating column if missing."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "plagiarism_detector.db"

def migrate_database():
    """Add user_rating column to analyses table if it doesn't exist."""
    if not DB_PATH.exists():
        print("Database doesn't exist yet. It will be created on app startup.")
        return
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(analyses)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "user_rating" not in columns:
            print("Adding user_rating column to analyses table...")
            cursor.execute("""
                ALTER TABLE analyses 
                ADD COLUMN user_rating INTEGER DEFAULT 0
            """)
            conn.commit()
            print("✓ Successfully added user_rating column")
        else:
            print("✓ user_rating column already exists")
        
        conn.close()
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    migrate_database()
