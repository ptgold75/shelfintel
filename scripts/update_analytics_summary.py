# scripts/update_analytics_summary.py
"""Update pre-computed analytics summaries."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from sqlalchemy import text
from core.db import get_engine

def update_summaries():
    engine = get_engine()
    today = date.today()
    
    print(f"Updating analytics summaries for {today}...")
    
    with engine.begin() as conn:
        # Clear today's summaries
        conn.execute(text("DELETE FROM analytics_summary WHERE summary_date = :today"), {"today": today})
        
        # 1. Total counts
        print("  Computing totals...")
        conn.execute(text("""
            INSERT INTO analytics_summary (summary_date, summary_type, dimension, value_count)
            VALUES 
                (:today, 'total', 'products', (SELECT COUNT(*) FROM raw_menu_item)),
                (:today, 'total', 'dispensaries', (SELECT COUNT(*) FROM dispensary)),
                (:today, 'total', 'scrape_runs', (SELECT COUNT(*) FROM scrape_run))
        """), {"today": today})
        
        # 2. Brand counts (top 50)
        print("  Computing brand stats...")
        conn.execute(text("""
            INSERT INTO analytics_summary (summary_date, summary_type, dimension, value_count)
            SELECT :today, 'brand', raw_brand, COUNT(*)
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            GROUP BY raw_brand
            ORDER BY COUNT(*) DESC
            LIMIT 50
        """), {"today": today})
        
        # 3. Category counts
        print("  Computing category stats...")
        conn.execute(text("""
            INSERT INTO analytics_summary (summary_date, summary_type, dimension, value_count)
            SELECT :today, 'category', raw_category, COUNT(*)
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL AND raw_category != ''
            GROUP BY raw_category
            ORDER BY COUNT(*) DESC
            LIMIT 50
        """), {"today": today})
        
        # 4. Store product counts
        print("  Computing store stats...")
        conn.execute(text("""
            INSERT INTO analytics_summary (summary_date, summary_type, dimension, value_count)
            SELECT :today, 'store', d.name, COUNT(r.raw_menu_item_id)
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            GROUP BY d.dispensary_id, d.name
        """), {"today": today})
    
    print("✅ Analytics summaries updated!")

if __name__ == "__main__":
    update_summaries()
