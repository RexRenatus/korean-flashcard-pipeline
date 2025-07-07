#!/usr/bin/env python3
"""
Run database migrations for the Korean Flashcard Pipeline
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

def run_migrations(db_path="pipeline.db", migrations_dir="migrations"):
    """Run all pending migrations on the database"""
    
    # Create database if it doesn't exist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create migrations table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get list of applied migrations
    cursor.execute("SELECT version FROM schema_migrations")
    applied_migrations = {row[0] for row in cursor.fetchall()}
    
    # Get list of migration files
    migrations_path = Path(migrations_dir)
    migration_files = sorted(migrations_path.glob("*.sql"))
    
    # Run each migration that hasn't been applied
    for migration_file in migration_files:
        version = migration_file.stem
        
        if version in applied_migrations:
            print(f"✓ Migration {version} already applied")
            continue
            
        print(f"→ Running migration {version}...")
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
            
        try:
            # Execute migration
            cursor.executescript(migration_sql)
            
            # Record successful migration
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,)
            )
            conn.commit()
            print(f"✓ Migration {version} applied successfully")
            
        except Exception as e:
            conn.rollback()
            print(f"✗ Migration {version} failed: {e}")
            raise
    
    # Show database status
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = cursor.fetchall()
    
    print(f"\n📊 Database tables ({len(tables)} total):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   • {table[0]}: {count} rows")
    
    conn.close()
    print("\n✅ All migrations completed successfully!")


if __name__ == "__main__":
    import sys
    
    # Allow custom database path
    db_path = sys.argv[1] if len(sys.argv) > 1 else "pipeline.db"
    
    # Run migrations
    run_migrations(db_path)