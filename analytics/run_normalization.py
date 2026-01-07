#!/usr/bin/env python3
"""Run product normalization on the database.

This script:
1. Loads all products from the database
2. Normalizes and clusters them
3. Generates a deduplication report
4. Optionally creates canonical product mappings
"""

import os
import sys
from pathlib import Path
import tomllib
import json

# Load Streamlit secrets
secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
if secrets_path.exists():
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
        for key, value in secrets.items():
            os.environ[key] = value

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.db import get_engine
from analytics.product_normalizer import ProductNormalizer


def load_products_from_db(limit: int = None) -> list:
    """Load products from the database."""
    engine = get_engine()

    query = """
        SELECT
            r.raw_menu_item_id,
            r.raw_name,
            r.raw_brand,
            r.raw_category,
            r.dispensary_id,
            d.name as dispensary_name,
            d.state,
            r.raw_price
        FROM raw_menu_item r
        JOIN dispensary d ON r.dispensary_id = d.dispensary_id
        WHERE r.observed_at >= NOW() - INTERVAL '7 days'
        AND r.raw_name IS NOT NULL
        AND r.raw_price IS NOT NULL
    """

    if limit:
        query += f" LIMIT {limit}"

    with engine.connect() as conn:
        result = conn.execute(text(query)).fetchall()

    products = []
    for row in result:
        products.append({
            "id": row[0],
            "name": row[1],
            "brand": row[2],
            "category": row[3],
            "dispensary_id": str(row[4]),
            "dispensary_name": row[5],
            "state": row[6],
            "price": float(row[7]) if row[7] else None
        })

    return products


def get_state_counts() -> dict:
    """Get dispensary counts by state."""
    engine = get_engine()

    with engine.connect() as conn:
        # Get counts by state
        states = conn.execute(text("""
            SELECT COALESCE(state, 'MD') as state, COUNT(DISTINCT dispensary_id) as count
            FROM dispensary
            GROUP BY COALESCE(state, 'MD')
            ORDER BY count DESC
        """)).fetchall()

    return {row[0]: row[1] for row in states} if states else {"MD": 0}


def run_normalization(limit: int = None, save_report: bool = True):
    """Run the full normalization process."""
    print("Loading products from database...")
    products = load_products_from_db(limit)
    print(f"Loaded {len(products):,} product observations")

    if not products:
        print("No products found!")
        return

    print("\nNormalizing products...")
    normalizer = ProductNormalizer()
    normalizer.process_products(products)

    print("\nGenerating report...")
    report = normalizer.get_deduplication_report()

    # Print summary
    print("\n" + "="*70)
    print("PRODUCT NORMALIZATION REPORT")
    print("="*70)
    print(f"\nTotal Raw Observations: {report['total_raw_products']:,}")
    print(f"Unique Products (Clusters): {report['total_clusters']:,}")
    print(f"Estimated Duplicates: {report['estimated_duplicates']:,}")
    print(f"Duplicate Rate: {report['duplicate_rate']:.1f}%")
    print(f"\nClusters with Name Variations: {report['clusters_with_name_variations']:,}")

    # State counts
    print("\n" + "-"*70)
    print("DISPENSARY COUNTS BY STATE")
    print("-"*70)
    state_counts = get_state_counts()
    for state, count in state_counts.items():
        print(f"  {state}: {count} dispensaries")

    if report['top_duplicate_clusters']:
        print("\n" + "-"*70)
        print("TOP DUPLICATE CLUSTERS (products with naming variations)")
        print("-"*70)
        for i, cluster in enumerate(report['top_duplicate_clusters'][:10], 1):
            print(f"\n{i}. {cluster['brand']} - {cluster['canonical_name']}")
            print(f"   Size: {cluster['size']} | Category: {cluster['category']}")
            print(f"   Found in {cluster['dispensary_count']} dispensaries | Avg: ${cluster['avg_price']:.2f}")
            print(f"   Name Variations ({len(cluster['name_variations'])}):")
            for var in cluster['name_variations'][:3]:
                print(f"     - {var}")
            if len(cluster['name_variations']) > 3:
                print(f"     ... and {len(cluster['name_variations']) - 3} more")

    if save_report:
        # Save full report
        report_path = Path(__file__).parent.parent / "data" / "normalization_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report saved to: {report_path}")

        # Save canonical products
        canonical = normalizer.export_canonical_products()
        canonical_path = Path(__file__).parent.parent / "data" / "canonical_products.json"
        with open(canonical_path, 'w') as f:
            json.dump(canonical, f, indent=2)
        print(f"Canonical products saved to: {canonical_path}")

    return report, normalizer


def create_normalization_table():
    """Create a table to store normalized product mappings."""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS canonical_products (
                id SERIAL PRIMARY KEY,
                match_key VARCHAR(500) UNIQUE NOT NULL,
                canonical_name VARCHAR(255) NOT NULL,
                canonical_brand VARCHAR(255),
                canonical_category VARCHAR(100),
                canonical_size VARCHAR(50),
                dispensary_count INT DEFAULT 0,
                avg_price DECIMAL(10,2),
                name_variations JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_canonical_products_brand
                ON canonical_products(canonical_brand);
            CREATE INDEX IF NOT EXISTS idx_canonical_products_category
                ON canonical_products(canonical_category);
        """))
        conn.commit()
        print("Created canonical_products table")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run product normalization")
    parser.add_argument("--limit", type=int, help="Limit products to process")
    parser.add_argument("--create-table", action="store_true", help="Create DB table")
    parser.add_argument("--no-save", action="store_true", help="Don't save reports")
    args = parser.parse_args()

    if args.create_table:
        create_normalization_table()

    run_normalization(limit=args.limit, save_report=not args.no_save)
