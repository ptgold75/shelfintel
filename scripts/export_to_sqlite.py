#!/usr/bin/env python3
"""Export Supabase data to local SQLite database for offline demos."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from pathlib import Path
from sqlalchemy import text
from core.db import get_engine

# Tables to export
TABLES = [
    "dispensary",
    "raw_menu_item",
    "scrape_run",
    "registrations",
]

def export_to_sqlite():
    """Export all data from Supabase to local SQLite."""

    sqlite_path = Path(__file__).parent.parent / "data" / "offline.db"
    sqlite_path.parent.mkdir(exist_ok=True)

    # Remove old database
    if sqlite_path.exists():
        sqlite_path.unlink()
        print(f"Removed old {sqlite_path}")

    # Connect to Supabase
    print("Connecting to Supabase...")
    pg_engine = get_engine()

    # Connect to SQLite
    print(f"Creating SQLite database at {sqlite_path}...")
    sqlite_conn = sqlite3.connect(str(sqlite_path))

    with pg_engine.connect() as pg_conn:
        for table in TABLES:
            print(f"\nExporting {table}...")

            # Get column info
            try:
                cols_result = pg_conn.execute(text(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                columns = [(row[0], row[1]) for row in cols_result]

                if not columns:
                    print(f"  Skipping {table} - no columns found")
                    continue

                col_names = [c[0] for c in columns]
                print(f"  Columns: {len(col_names)}")

                # Create SQLite table
                sqlite_types = []
                for col_name, pg_type in columns:
                    if 'int' in pg_type:
                        sqlite_type = 'INTEGER'
                    elif pg_type in ('numeric', 'double precision', 'real'):
                        sqlite_type = 'REAL'
                    elif 'bool' in pg_type:
                        sqlite_type = 'INTEGER'
                    else:
                        sqlite_type = 'TEXT'
                    sqlite_types.append(f'"{col_name}" {sqlite_type}')

                create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(sqlite_types)})'
                sqlite_conn.execute(create_sql)

                # Export data
                result = pg_conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = result.fetchall()
                print(f"  Rows: {len(rows)}")

                if rows:
                    placeholders = ", ".join(["?" for _ in col_names])
                    insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'

                    # Convert rows to tuples (handle None, bool, etc.)
                    clean_rows = []
                    for row in rows:
                        clean_row = []
                        for val in row:
                            if isinstance(val, bool):
                                clean_row.append(1 if val else 0)
                            else:
                                clean_row.append(val)
                        clean_rows.append(tuple(clean_row))

                    sqlite_conn.executemany(insert_sql, clean_rows)
                    sqlite_conn.commit()
                    print(f"  Exported {len(rows)} rows")

            except Exception as e:
                print(f"  Error exporting {table}: {e}")
                continue

    # Create indexes for performance
    print("\nCreating indexes...")
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_rmi_dispensary ON raw_menu_item(dispensary_id)',
        'CREATE INDEX IF NOT EXISTS idx_rmi_brand ON raw_menu_item(raw_brand)',
        'CREATE INDEX IF NOT EXISTS idx_rmi_category ON raw_menu_item(raw_category)',
        'CREATE INDEX IF NOT EXISTS idx_disp_active ON dispensary(is_active)',
    ]
    for idx_sql in indexes:
        try:
            sqlite_conn.execute(idx_sql)
        except Exception as e:
            print(f"  Index error: {e}")

    sqlite_conn.commit()
    sqlite_conn.close()

    # Report file size
    size_mb = sqlite_path.stat().st_size / (1024 * 1024)
    print(f"\nDone! SQLite database: {sqlite_path}")
    print(f"Size: {size_mb:.1f} MB")
    print("\nTo use offline mode, set OFFLINE_MODE=1 environment variable or")
    print("add 'OFFLINE_MODE = true' to .streamlit/secrets.toml")


if __name__ == "__main__":
    export_to_sqlite()
