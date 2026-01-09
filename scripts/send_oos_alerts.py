#!/usr/bin/env python3
"""Out of Stock Alert System.

Detects products that have gone out of stock and sends alerts to subscribers.

Run daily via cron:
0 9 * * * cd /Users/gleaf/shelfintel && ./.venv/bin/python scripts/send_oos_alerts.py

Environment variables required:
- SMTP_HOST (default: smtp.gmail.com)
- SMTP_PORT (default: 587)
- SMTP_USER (email sender address)
- SMTP_PASS (app password for email)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

# Email configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'alerts@cannlinx.com')


def get_engine():
    return create_engine(DATABASE_URL)


def ensure_oos_tracking_table():
    """Create table to track product availability over time."""
    engine = get_engine()
    with engine.connect() as conn:
        # Drop and recreate if type mismatch
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_availability_snapshot (
                id SERIAL PRIMARY KEY,
                dispensary_id UUID,
                raw_brand VARCHAR(255),
                raw_name TEXT,
                raw_category VARCHAR(100),
                raw_price DECIMAL,
                snapshot_date DATE DEFAULT CURRENT_DATE,
                is_available BOOLEAN DEFAULT true
            )
        """))
        # Create index for fast lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pas_lookup
            ON product_availability_snapshot (dispensary_id, raw_brand, raw_name, snapshot_date)
        """))
        conn.commit()


def take_availability_snapshot():
    """Take a snapshot of current product availability."""
    engine = get_engine()
    with engine.connect() as conn:
        # Check if we already have today's snapshot
        existing = conn.execute(text("""
            SELECT COUNT(*) FROM product_availability_snapshot
            WHERE snapshot_date = CURRENT_DATE
        """)).scalar()

        if existing > 0:
            print(f"  Already have {existing} records for today")
            return existing

        # Insert today's products
        result = conn.execute(text("""
            INSERT INTO product_availability_snapshot
                (dispensary_id, raw_brand, raw_name, raw_category, raw_price, snapshot_date, is_available)
            SELECT DISTINCT
                r.dispensary_id::uuid,
                r.raw_brand,
                r.raw_name,
                r.raw_category,
                r.raw_price,
                CURRENT_DATE,
                true
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.is_active = true
        """))
        conn.commit()
        return result.rowcount


def detect_out_of_stock():
    """Detect products that were available yesterday but not today."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH yesterday AS (
                SELECT DISTINCT dispensary_id, raw_brand, raw_name, raw_category, raw_price
                FROM product_availability_snapshot
                WHERE snapshot_date = CURRENT_DATE - INTERVAL '1 day'
                AND is_available = true
            ),
            today AS (
                SELECT DISTINCT dispensary_id, raw_brand, raw_name
                FROM product_availability_snapshot
                WHERE snapshot_date = CURRENT_DATE
                AND is_available = true
            )
            SELECT
                y.dispensary_id,
                d.name as store_name,
                d.state,
                d.city,
                y.raw_brand,
                y.raw_name,
                y.raw_category,
                y.raw_price
            FROM yesterday y
            JOIN dispensary d ON y.dispensary_id = d.dispensary_id::uuid
            LEFT JOIN today t ON y.dispensary_id = t.dispensary_id
                AND COALESCE(y.raw_brand, '') = COALESCE(t.raw_brand, '')
                AND y.raw_name = t.raw_name
            WHERE t.dispensary_id IS NULL
            ORDER BY y.raw_brand, d.state, d.name
            LIMIT 500
        """))

        return [dict(row._mapping) for row in result]


def detect_low_distribution(brand, state):
    """Detect when a brand's distribution drops significantly."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH daily_counts AS (
                SELECT
                    snapshot_date,
                    COUNT(DISTINCT dispensary_id) as store_count
                FROM product_availability_snapshot p
                JOIN dispensary d ON p.dispensary_id = d.dispensary_id
                WHERE LOWER(p.raw_brand) = LOWER(:brand)
                AND d.state = :state
                AND p.is_available = true
                AND p.snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY snapshot_date
                ORDER BY snapshot_date
            )
            SELECT
                snapshot_date,
                store_count,
                LAG(store_count) OVER (ORDER BY snapshot_date) as prev_count
            FROM daily_counts
        """), {"brand": brand, "state": state})

        return [dict(row._mapping) for row in result]


def get_oos_subscribers():
    """Get clients who have opted in to out of stock alerts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                c.client_id,
                c.company_name,
                c.email,
                c.allowed_states
            FROM client c
            JOIN alert_preferences ap ON c.client_id = ap.client_id
            WHERE c.is_active = true
            AND ap.alert_type = 'out_of_stock'
            AND ap.is_enabled = true
            AND c.email IS NOT NULL
        """))

        return [dict(row._mapping) for row in result]


def get_client_brands(client_id):
    """Get brands associated with a client (if any)."""
    # For now, return None - would need a client_brands table
    # Could be enhanced to track which brands each client wants to monitor
    return None


def format_oos_email(oos_items, client_name, state_filter=None):
    """Format the out of stock alert email."""

    # Filter by state if specified
    if state_filter:
        oos_items = [item for item in oos_items if item['state'] in state_filter]

    if not oos_items:
        return None

    date_str = datetime.now().strftime("%B %d, %Y")

    # Group by brand
    by_brand = {}
    for item in oos_items:
        brand = item['raw_brand'] or 'Unknown'
        if brand not in by_brand:
            by_brand[brand] = []
        by_brand[brand].append(item)

    # HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 20px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.8; }}
            .content {{ padding: 20px; }}
            .brand-section {{ margin-bottom: 25px; }}
            .brand-name {{ background: #f8f9fa; padding: 10px 15px; font-weight: bold; border-left: 4px solid #dc2626; margin-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #f8f9fa; padding: 10px; text-align: left; font-size: 12px; }}
            td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 13px; }}
            .store {{ font-weight: 500; }}
            .product {{ color: #666; }}
            .price {{ color: #059669; }}
            .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            .summary {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
            .summary strong {{ color: #dc2626; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Out of Stock Alert</h1>
            <p>{date_str}</p>
        </div>
        <div class="content">
            <div class="summary">
                <strong>{len(oos_items)} products</strong> went out of stock across <strong>{len(set(i['dispensary_id'] for i in oos_items))} stores</strong>
            </div>
    """

    for brand, items in sorted(by_brand.items()):
        html += f"""
            <div class="brand-section">
                <div class="brand-name">{brand} ({len(items)} products)</div>
                <table>
                    <tr>
                        <th>Store</th>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Last Price</th>
                    </tr>
        """

        for item in items[:20]:  # Limit per brand
            price = f"${float(item['raw_price']):.2f}" if item['raw_price'] else "N/A"
            html += f"""
                    <tr>
                        <td class="store">{item['store_name']}<br><small>{item['city']}, {item['state']}</small></td>
                        <td class="product">{item['raw_name'][:50]}</td>
                        <td>{item['raw_category'] or 'N/A'}</td>
                        <td class="price">{price}</td>
                    </tr>
            """

        if len(items) > 20:
            html += f"""
                    <tr>
                        <td colspan="4" style="text-align: center; color: #666;">
                            ... and {len(items) - 20} more products
                        </td>
                    </tr>
            """

        html += """
                </table>
            </div>
        """

    html += """
            <p style="margin-top: 20px;">
                <a href="http://localhost:8501/Availability" style="background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Availability Dashboard
                </a>
            </p>
        </div>
        <div class="footer">
            <p>CannLinx Market Intelligence | <a href="#">Manage Alert Preferences</a></p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text = f"""CannLinx Out of Stock Alert - {date_str}

{len(oos_items)} products went out of stock across {len(set(i['dispensary_id'] for i in oos_items))} stores.

"""
    for brand, items in sorted(by_brand.items()):
        text += f"\n{brand} ({len(items)} products):\n"
        for item in items[:10]:
            text += f"  - {item['store_name']}: {item['raw_name'][:40]}\n"
        if len(items) > 10:
            text += f"  ... and {len(items) - 10} more\n"

    text += "\nView details: http://localhost:8501/Availability"

    subject = f"CannLinx Alert: {len(oos_items)} Products Out of Stock"

    return subject, html, text


def send_email(to_email, subject, html_content, text_content):
    """Send an email via SMTP."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"  [SKIP] No SMTP credentials - would send to {to_email}")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        print(f"  [SENT] Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"  [ERROR] Failed to send to {to_email}: {e}")
        return False


def log_alert(client_id, alert_type, status, details=None):
    """Log alert to database."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO alert_log (client_id, alert_type, status, details)
            VALUES (:client_id, :alert_type, :status, :details)
        """), {
            "client_id": client_id,
            "alert_type": alert_type,
            "status": status,
            "details": details
        })
        conn.commit()


def main():
    """Main entry point."""
    print("=" * 60)
    print("CANNLINX OUT OF STOCK ALERT SYSTEM")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Ensure tracking table exists
    print("\nSetting up tracking tables...")
    ensure_oos_tracking_table()

    # Take today's snapshot
    print("Taking availability snapshot...")
    new_products = take_availability_snapshot()
    print(f"Recorded {new_products} products in today's snapshot")

    # Detect out of stock items
    print("\nDetecting out of stock items...")
    oos_items = detect_out_of_stock()
    print(f"Found {len(oos_items)} products that went out of stock")

    if not oos_items:
        print("No out of stock items detected. Exiting.")
        return

    # Show summary by brand
    by_brand = {}
    for item in oos_items:
        brand = item['raw_brand'] or 'Unknown'
        by_brand[brand] = by_brand.get(brand, 0) + 1

    print("\nOut of Stock Summary:")
    for brand, count in sorted(by_brand.items(), key=lambda x: -x[1])[:15]:
        print(f"  {brand[:30]:30} {count:4} products")

    # Get subscribers
    print("\nFetching subscribers...")
    subscribers = get_oos_subscribers()
    print(f"Found {len(subscribers)} active subscribers")

    if not subscribers:
        print("No subscribers. Testing with console output only.")
        result = format_oos_email(oos_items, "Test User")
        if result:
            subject, html, text = result
            print(f"\nWould send: {subject}")
            print(f"Content preview:\n{text[:800]}...")
        return

    # Send alerts
    print("\nSending alerts...")
    sent_count = 0

    for sub in subscribers:
        # Filter by client's allowed states
        state_filter = sub.get('allowed_states')

        result = format_oos_email(oos_items, sub['company_name'], state_filter)

        if result is None:
            print(f"  [SKIP] No OOS items in {sub['company_name']}'s states")
            continue

        subject, html, text = result

        if send_email(sub['email'], subject, html, text):
            log_alert(sub['client_id'], 'out_of_stock', 'sent', subject)
            sent_count += 1
        else:
            log_alert(sub['client_id'], 'out_of_stock', 'failed', 'SMTP error')

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: Sent {sent_count}/{len(subscribers)} alerts")
    print("=" * 60)


if __name__ == "__main__":
    main()
