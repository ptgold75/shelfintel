#!/usr/bin/env python3
"""Fetch stock prices for public cannabis companies using Yahoo Finance."""

import json
import time
from datetime import datetime, timedelta
import requests
import psycopg2

# Database connection
def get_conn():
    return psycopg2.connect(
        host='db.trteltlgtmcggdbrqwdw.supabase.co',
        database='postgres',
        user='postgres',
        password='Tattershall2020',
        port='5432',
        sslmode='require'
    )


def get_companies():
    """Get all public companies with tickers."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT company_id, name, ticker_us, ticker_ca
        FROM public_company
        WHERE is_active = true
    """)
    companies = cur.fetchall()
    cur.close()
    conn.close()
    return companies


def fetch_yahoo_quote(ticker):
    """Fetch current quote from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        'interval': '1d',
        'range': '5d',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                return result[0]
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")

    return None


def parse_quote_data(quote_data, company_id, ticker):
    """Parse Yahoo Finance quote data."""
    if not quote_data:
        return []

    prices = []

    meta = quote_data.get('meta', {})
    timestamps = quote_data.get('timestamp', [])
    indicators = quote_data.get('indicators', {})
    quote = indicators.get('quote', [{}])[0]

    opens = quote.get('open', [])
    highs = quote.get('high', [])
    lows = quote.get('low', [])
    closes = quote.get('close', [])
    volumes = quote.get('volume', [])

    for i, ts in enumerate(timestamps):
        try:
            price_date = datetime.fromtimestamp(ts).date()
            prices.append({
                'company_id': company_id,
                'ticker': ticker,
                'price_date': price_date,
                'open_price': opens[i] if i < len(opens) else None,
                'high_price': highs[i] if i < len(highs) else None,
                'low_price': lows[i] if i < len(lows) else None,
                'close_price': closes[i] if i < len(closes) else None,
                'volume': volumes[i] if i < len(volumes) else None,
            })
        except Exception as e:
            continue

    return prices


def save_prices(prices):
    """Save stock prices to database."""
    if not prices:
        return 0

    conn = get_conn()
    cur = conn.cursor()

    saved = 0
    for p in prices:
        if p.get('close_price') is None:
            continue

        try:
            cur.execute("""
                INSERT INTO stock_price
                (company_id, ticker, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (%(company_id)s, %(ticker)s, %(price_date)s, %(open_price)s,
                        %(high_price)s, %(low_price)s, %(close_price)s, %(volume)s)
                ON CONFLICT (company_id, price_date)
                DO UPDATE SET
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            """, p)
            saved += 1
        except Exception as e:
            print(f"Error saving price: {e}")
            conn.rollback()

    conn.commit()
    cur.close()
    conn.close()

    return saved


def update_market_cap(company_id, market_cap):
    """Update company market cap."""
    if not market_cap:
        return

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE public_company
        SET market_cap_millions = %s, updated_at = NOW()
        WHERE company_id = %s
    """, (market_cap / 1000000, company_id))
    conn.commit()
    cur.close()
    conn.close()


def main():
    companies = get_companies()
    print(f"Found {len(companies)} public companies")

    for company_id, name, ticker_us, ticker_ca in companies:
        # Try US ticker first, then Canadian
        ticker = ticker_us or ticker_ca
        if not ticker:
            continue

        print(f"\n{name} ({ticker})...")

        quote_data = fetch_yahoo_quote(ticker)
        if quote_data:
            # Get market cap
            meta = quote_data.get('meta', {})
            market_cap = meta.get('marketCap')
            if market_cap:
                update_market_cap(company_id, market_cap)
                print(f"  Market Cap: ${market_cap/1e9:.2f}B")

            # Parse and save prices
            prices = parse_quote_data(quote_data, company_id, ticker)
            saved = save_prices(prices)
            print(f"  Saved {saved} price records")

            # Get current price
            current = meta.get('regularMarketPrice')
            if current:
                print(f"  Current Price: ${current:.2f}")
        else:
            print(f"  No data available")

        time.sleep(0.5)

    print("\nDone!")


if __name__ == '__main__':
    main()
