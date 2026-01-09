#!/usr/bin/env python3
"""Daily stock alert email sender.

Run daily via cron:
0 8 * * * cd /Users/gleaf/shelfintel && ./venv/bin/python scripts/send_stock_alerts.py

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


def get_stock_changes():
    """Get significant stock price changes from the last trading day."""
    engine = get_engine()

    with engine.connect() as conn:
        # Get latest two trading days of data
        result = conn.execute(text("""
            WITH recent_prices AS (
                SELECT
                    sp.company_id,
                    pc.name as company_name,
                    pc.ticker_us,
                    sp.price_date,
                    sp.close_price,
                    sp.open_price,
                    sp.high_price,
                    sp.low_price,
                    sp.volume,
                    ROW_NUMBER() OVER (PARTITION BY sp.company_id ORDER BY sp.price_date DESC) as rn
                FROM stock_price sp
                JOIN public_company pc ON sp.company_id = pc.company_id
                WHERE sp.price_date >= CURRENT_DATE - INTERVAL '7 days'
                AND pc.is_active = true
            )
            SELECT
                curr.company_name,
                curr.ticker_us,
                curr.close_price as current_price,
                prev.close_price as previous_price,
                curr.price_date as current_date,
                prev.price_date as previous_date,
                curr.volume,
                CASE WHEN prev.close_price > 0
                    THEN ROUND(((curr.close_price - prev.close_price) / prev.close_price * 100)::numeric, 2)
                    ELSE 0
                END as pct_change
            FROM recent_prices curr
            JOIN recent_prices prev ON curr.company_id = prev.company_id AND prev.rn = 2
            WHERE curr.rn = 1
            ORDER BY ABS(CASE WHEN prev.close_price > 0
                THEN ((curr.close_price - prev.close_price) / prev.close_price * 100)
                ELSE 0 END) DESC
        """))

        return [dict(row._mapping) for row in result]


def get_alert_subscribers():
    """Get clients who have opted in to stock alerts."""
    engine = get_engine()

    with engine.connect() as conn:
        # Check if alert_preferences table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'alert_preferences'
            )
        """))
        table_exists = result.scalar()

        if not table_exists:
            # Create the table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alert_preferences (
                    id SERIAL PRIMARY KEY,
                    client_id UUID REFERENCES client(client_id),
                    alert_type VARCHAR(50) NOT NULL,
                    is_enabled BOOLEAN DEFAULT true,
                    threshold_pct DECIMAL DEFAULT 5.0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(client_id, alert_type)
                )
            """))
            conn.commit()
            return []

        # Get subscribers
        result = conn.execute(text("""
            SELECT
                c.client_id,
                c.company_name,
                c.email,
                ap.threshold_pct
            FROM client c
            JOIN alert_preferences ap ON c.client_id = ap.client_id
            WHERE c.is_active = true
            AND ap.alert_type = 'stock_changes'
            AND ap.is_enabled = true
            AND c.email IS NOT NULL
        """))

        return [dict(row._mapping) for row in result]


def format_stock_alert_email(changes, threshold_pct=5.0):
    """Format the stock alert email content."""

    # Filter to significant changes
    significant = [c for c in changes if abs(float(c['pct_change'] or 0)) >= threshold_pct]

    if not significant:
        return None, None

    date_str = datetime.now().strftime("%B %d, %Y")

    # HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%); color: white; padding: 20px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.8; }}
            .content {{ padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #f8f9fa; padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; }}
            td {{ padding: 12px; border-bottom: 1px solid #dee2e6; }}
            .up {{ color: #059669; font-weight: bold; }}
            .down {{ color: #dc2626; font-weight: bold; }}
            .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CannLinx Stock Alert</h1>
            <p>{date_str}</p>
        </div>
        <div class="content">
            <p>The following cannabis stocks had significant price movements:</p>
            <table>
                <tr>
                    <th>Company</th>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>Change</th>
                    <th>Volume</th>
                </tr>
    """

    for stock in significant:
        pct = float(stock['pct_change'] or 0)
        css_class = "up" if pct > 0 else "down"
        arrow = "+" if pct > 0 else ""
        price = float(stock['current_price'] or 0)
        volume = int(stock['volume'] or 0)

        html += f"""
                <tr>
                    <td>{stock['company_name']}</td>
                    <td><strong>{stock['ticker_us'] or 'N/A'}</strong></td>
                    <td>${price:.2f}</td>
                    <td class="{css_class}">{arrow}{pct:.2f}%</td>
                    <td>{volume:,}</td>
                </tr>
        """

    html += """
            </table>
            <p>
                <a href="http://localhost:8501/Investor_Intelligence" style="background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Full Analysis
                </a>
            </p>
        </div>
        <div class="footer">
            <p>CannLinx Market Intelligence | <a href="#">Unsubscribe</a> | <a href="#">Manage Preferences</a></p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text = f"""CannLinx Stock Alert - {date_str}

The following cannabis stocks had significant price movements:

"""
    for stock in significant:
        pct = float(stock['pct_change'] or 0)
        arrow = "+" if pct > 0 else ""
        price = float(stock['current_price'] or 0)
        text += f"- {stock['company_name']} ({stock['ticker_us']}): ${price:.2f} ({arrow}{pct:.2f}%)\n"

    text += "\nView full analysis at: http://localhost:8501/Investor_Intelligence"

    subject = f"CannLinx Stock Alert: {len(significant)} Significant Moves"

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
        # Create log table if needed
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id SERIAL PRIMARY KEY,
                client_id UUID,
                alert_type VARCHAR(50),
                status VARCHAR(20),
                details TEXT,
                sent_at TIMESTAMP DEFAULT NOW()
            )
        """))

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
    print("CANNLINX STOCK ALERT SYSTEM")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Get stock changes
    print("\nFetching stock data...")
    changes = get_stock_changes()
    print(f"Found {len(changes)} stocks with recent data")

    if not changes:
        print("No stock data available. Exiting.")
        return

    # Show summary
    print("\nStock Summary:")
    for stock in changes[:10]:
        pct = float(stock['pct_change'] or 0)
        arrow = "+" if pct > 0 else ""
        print(f"  {stock['ticker_us'] or 'N/A':6} {stock['company_name'][:30]:30} {arrow}{pct:.2f}%")

    # Get subscribers
    print("\nFetching subscribers...")
    subscribers = get_alert_subscribers()
    print(f"Found {len(subscribers)} active subscribers")

    if not subscribers:
        print("No subscribers. Testing with console output only.")
        subject, html, text = format_stock_alert_email(changes, threshold_pct=3.0)
        if subject:
            print(f"\nWould send: {subject}")
            print(f"Content preview:\n{text[:500]}...")
        return

    # Send alerts
    print("\nSending alerts...")
    sent_count = 0

    for sub in subscribers:
        threshold = float(sub.get('threshold_pct') or 5.0)
        result = format_stock_alert_email(changes, threshold_pct=threshold)

        if result is None:
            print(f"  [SKIP] No significant changes for {sub['email']} (threshold: {threshold}%)")
            continue

        subject, html, text = result

        if send_email(sub['email'], subject, html, text):
            log_alert(sub['client_id'], 'stock_changes', 'sent', subject)
            sent_count += 1
        else:
            log_alert(sub['client_id'], 'stock_changes', 'failed', 'SMTP error')

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: Sent {sent_count}/{len(subscribers)} alerts")
    print("=" * 60)


if __name__ == "__main__":
    main()
