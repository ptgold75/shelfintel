#!/usr/bin/env python3
"""Fetch SEC filings (10-K, 10-Q) for public cannabis companies and parse financials."""

import json
import re
import time
import requests
from datetime import datetime
import psycopg2

# SEC EDGAR API
SEC_BASE = "https://data.sec.gov"
HEADERS = {
    'User-Agent': 'CannLinx Research support@cannlinx.com',
    'Accept': 'application/json',
}

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


def get_companies_with_cik():
    """Get companies that have SEC CIK numbers."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT company_id, name, ticker_us, cik
        FROM public_company
        WHERE cik IS NOT NULL AND cik != ''
    """)
    companies = cur.fetchall()
    cur.close()
    conn.close()
    return companies


def fetch_company_filings(cik):
    """Fetch recent filings for a company from SEC EDGAR."""
    # Pad CIK to 10 digits
    cik_padded = cik.zfill(10)

    url = f"{SEC_BASE}/cik{cik_padded}.json"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching {cik}: {e}")

    return None


def fetch_filing_facts(cik):
    """Fetch company facts (financial data) from SEC EDGAR."""
    cik_padded = cik.zfill(10)

    url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik_padded}.json"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching facts for {cik}: {e}")

    return None


def parse_financial_facts(facts_data, company_id):
    """Parse financial data from SEC company facts."""
    if not facts_data:
        return []

    financials = []

    # Get US-GAAP facts
    us_gaap = facts_data.get('facts', {}).get('us-gaap', {})

    # Key metrics to extract
    metrics = {
        'Revenues': 'revenue_millions',
        'RevenueFromContractWithCustomerExcludingAssessedTax': 'revenue_millions',
        'GrossProfit': 'gross_profit_millions',
        'OperatingIncomeLoss': 'operating_income_millions',
        'NetIncomeLoss': 'net_income_millions',
        'Assets': 'total_assets_millions',
        'Liabilities': 'total_debt_millions',
        'StockholdersEquity': 'total_equity_millions',
        'CashAndCashEquivalentsAtCarryingValue': 'cash_millions',
        'EarningsPerShareBasic': 'eps',
    }

    # Collect data points by period
    periods = {}

    for sec_metric, our_metric in metrics.items():
        if sec_metric in us_gaap:
            units = us_gaap[sec_metric].get('units', {})
            # Get USD values
            usd_values = units.get('USD', units.get('USD/shares', []))

            for item in usd_values:
                # Only get 10-K and 10-Q filings
                form = item.get('form', '')
                if form not in ['10-K', '10-Q']:
                    continue

                end_date = item.get('end')
                fy = item.get('fy')
                fp = item.get('fp')  # FY, Q1, Q2, Q3, Q4
                val = item.get('val')

                if not end_date or val is None:
                    continue

                period_key = (fy, fp)
                if period_key not in periods:
                    periods[period_key] = {
                        'company_id': company_id,
                        'period_type': 'annual' if fp == 'FY' else 'quarterly',
                        'fiscal_year': fy,
                        'fiscal_quarter': None if fp == 'FY' else int(fp[1]) if fp and len(fp) > 1 else None,
                        'period_end_date': end_date,
                    }

                # Convert to millions for large values
                if our_metric != 'eps' and val > 1000000:
                    val = val / 1000000

                periods[period_key][our_metric] = val

    return list(periods.values())


def save_financials(financials):
    """Save financial data to database."""
    if not financials:
        return 0

    conn = get_conn()
    cur = conn.cursor()

    saved = 0
    for f in financials:
        try:
            cur.execute("""
                INSERT INTO company_financials
                (company_id, period_type, fiscal_year, fiscal_quarter, period_end_date,
                 revenue_millions, gross_profit_millions, operating_income_millions,
                 net_income_millions, total_assets_millions, total_debt_millions,
                 total_equity_millions, cash_millions, eps)
                VALUES (%(company_id)s, %(period_type)s, %(fiscal_year)s, %(fiscal_quarter)s,
                        %(period_end_date)s, %(revenue_millions)s, %(gross_profit_millions)s,
                        %(operating_income_millions)s, %(net_income_millions)s,
                        %(total_assets_millions)s, %(total_debt_millions)s,
                        %(total_equity_millions)s, %(cash_millions)s, %(eps)s)
                ON CONFLICT (company_id, period_type, fiscal_year, fiscal_quarter)
                DO UPDATE SET
                    revenue_millions = EXCLUDED.revenue_millions,
                    gross_profit_millions = EXCLUDED.gross_profit_millions,
                    operating_income_millions = EXCLUDED.operating_income_millions,
                    net_income_millions = EXCLUDED.net_income_millions,
                    total_assets_millions = EXCLUDED.total_assets_millions,
                    total_debt_millions = EXCLUDED.total_debt_millions,
                    total_equity_millions = EXCLUDED.total_equity_millions,
                    cash_millions = EXCLUDED.cash_millions,
                    eps = EXCLUDED.eps
            """, {
                'company_id': f.get('company_id'),
                'period_type': f.get('period_type'),
                'fiscal_year': f.get('fiscal_year'),
                'fiscal_quarter': f.get('fiscal_quarter'),
                'period_end_date': f.get('period_end_date'),
                'revenue_millions': f.get('revenue_millions'),
                'gross_profit_millions': f.get('gross_profit_millions'),
                'operating_income_millions': f.get('operating_income_millions'),
                'net_income_millions': f.get('net_income_millions'),
                'total_assets_millions': f.get('total_assets_millions'),
                'total_debt_millions': f.get('total_debt_millions'),
                'total_equity_millions': f.get('total_equity_millions'),
                'cash_millions': f.get('cash_millions'),
                'eps': f.get('eps'),
            })
            saved += 1
        except Exception as e:
            print(f"Error saving: {e}")
            conn.rollback()

    conn.commit()
    cur.close()
    conn.close()

    return saved


def main():
    companies = get_companies_with_cik()
    print(f"Found {len(companies)} companies with SEC CIK numbers")

    for company_id, name, ticker, cik in companies:
        print(f"\n{'='*60}")
        print(f"Processing: {name} ({ticker}) - CIK: {cik}")
        print('='*60)

        # Fetch company facts
        facts = fetch_filing_facts(cik)
        if facts:
            print(f"  Got facts for {facts.get('entityName', name)}")

            # Parse financials
            financials = parse_financial_facts(facts, company_id)
            print(f"  Parsed {len(financials)} financial periods")

            # Save to database
            saved = save_financials(financials)
            print(f"  Saved {saved} records")
        else:
            print(f"  No facts available")

        time.sleep(0.5)  # Be nice to SEC servers

    print("\nDone!")


if __name__ == '__main__':
    main()
