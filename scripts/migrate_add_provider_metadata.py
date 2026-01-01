# scripts/migrate_add_provider_metadata.py
"""
Migration script to add new columns to existing dispensary table.

Run this once after updating models.py if you have an existing database.

Usage:
    python scripts/migrate_add_provider_metadata.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from core.db import get_engine


def migrate():
    engine = get_engine()
    
    migrations = [
        # Add provider_metadata column
        """
        ALTER TABLE dispensary 
        ADD COLUMN IF NOT EXISTS provider_metadata TEXT;
        """,
        
        # Add discovery_confidence column
        """
        ALTER TABLE dispensary 
        ADD COLUMN IF NOT EXISTS discovery_confidence FLOAT;
        """,
        
        # Add last_discovered_at column
        """
        ALTER TABLE dispensary 
        ADD COLUMN IF NOT EXISTS last_discovered_at TIMESTAMP WITH TIME ZONE;
        """,
        
        # Add is_active column with default true
        """
        ALTER TABLE dispensary 
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        """,
        
        # Add updated_at column
        """
        ALTER TABLE dispensary 
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        """,
    ]
    
    with engine.begin() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql.strip()))
                print(f"✅ Executed: {sql[:60].strip()}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"⏭️ Skipped (already exists): {sql[:60].strip()}...")
                else:
                    print(f"❌ Error: {e}")
    
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    migrate()
