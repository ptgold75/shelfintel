#!/usr/bin/env python3
"""
Fetch investor news, SEC filings, and press releases for public cannabis companies.

Data Sources:
1. SEC EDGAR - 10-K, 10-Q, 8-K filings (for US-listed companies)
2. Company investor relations pages - Press releases
3. News APIs - Recent company news

Key events to detect:
- Executive changes (CEO, CFO, COO resignations/appointments)
- M&A activity (acquisitions, mergers, divestitures)
- Financials (revenue, earnings beats/misses)
- Legal/regulatory issues
- Facility openings/closings
- Capital raises (debt, equity)
"""

import os
import sys
import re
import json
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text

# SEC EDGAR API
SEC_BASE = "https://data.sec.gov"
SEC_FILINGS_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_HEADERS = {
    'User-Agent': 'CannaLinx Research support@cannalinx.com',
    'Accept': 'application/json',
}

# Event categories to detect in filings
EVENT_KEYWORDS = {
    'executive_change': [
        r'resign(?:ed|ation|ing)',
        r'appoint(?:ed|ment)',
        r'terminat(?:ed|ion)',
        r'chief executive officer',
        r'chief financial officer',
        r'chief operating officer',
        r'CEO|CFO|COO|CTO|CMO',
        r'board of directors',
        r'director.*(?:resign|appoint)',
    ],
    'merger_acquisition': [
        r'acqui(?:re|red|sition)',
        r'merger',
        r'divest(?:ed|iture)',
        r'purchase.*agreement',
        r'business combination',
        r'asset purchase',
        r'stock purchase',
        r'letter of intent',
    ],
    'capital_raise': [
        r'debt.*(?:offering|financing)',
        r'equity.*(?:offering|financing)',
        r'credit.*(?:facility|agreement)',
        r'convertible.*notes?',
        r'private.*placement',
        r'secondary.*offering',
        r'shelf.*registration',
    ],
    'legal_regulatory': [
        r'lawsuit',
        r'litigation',
        r'settlement',
        r'SEC.*(?:investigation|inquiry)',
        r'regulatory.*(?:action|approval)',
        r'license.*(?:granted|revoked|suspended)',
    ],
    'facility_operations': [
        r'facility.*(?:open|clos|expan)',
        r'dispensar(?:y|ies).*(?:open|clos)',
        r'cultivation.*(?:open|clos|expan)',
        r'store.*(?:open|clos)',
        r'new.*location',
    ],
    'financial_results': [
        r'revenue.*(?:increas|decreas|grew|growth)',
        r'earnings.*(?:beat|miss|exceed)',
        r'quarterly.*results',
        r'annual.*results',
        r'guidance.*(?:rais|lower|maintain)',
        r'profitable|profitability',
        r'cash.*flow',
    ],
}

# Company investor relations URLs
INVESTOR_RELATIONS_URLS = {
    'Curaleaf Holdings': 'https://ir.curaleaf.com/news-releases',
    'Green Thumb Industries': 'https://investors.gtigrows.com/news-events/press-releases',
    'Trulieve Cannabis': 'https://investors.trulieve.com/news-releases',
    'Verano Holdings': 'https://investors.verano.com/news-releases',
    'Cresco Labs': 'https://investors.crescolabs.com/news-releases',
    'TerrAscend': 'https://investors.terrascend.com/news-releases',
    'Ayr Wellness': 'https://www.ayrwellness.com/investors/news',
    'Tilray Brands': 'https://ir.tilray.com/news-releases',
    'Canopy Growth': 'https://www.canopygrowth.com/investors/news-releases/',
    'Aurora Cannabis': 'https://investor.auroramj.com/news-and-events/press-releases',
    'Cronos Group': 'https://ir.thecronosgroup.com/press-releases',
    'Ascend Wellness': 'https://ir.awholdings.com/news-releases',
    'Columbia Care': 'https://ir.col-care.com/news-releases',
    'SNDL Inc': 'https://www.sndl.com/investors/news-releases',
    'Vireo Growth': 'https://vireohealth.com/news/',
}


@dataclass
class FilingEvent:
    """Represents a detected event from a filing."""
    company_id: str
    company_name: str
    event_type: str
    event_category: str
    title: str
    summary: str
    source_url: str
    filing_type: Optional[str]
    filing_date: datetime
    detected_at: datetime = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


def get_public_companies() -> List[Dict]:
    """Get all public companies from database."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT company_id, name, ticker_us, ticker_ca, cik, website
            FROM public_company
            WHERE is_active = true
            ORDER BY name
        """))
        return [dict(row._mapping) for row in result]


def fetch_sec_filings(cik: str, filing_types: List[str] = None, count: int = 20) -> List[Dict]:
    """Fetch recent SEC filings for a company."""
    if filing_types is None:
        filing_types = ['10-K', '10-Q', '8-K']

    cik_padded = cik.zfill(10)
    url = f"{SEC_BASE}/submissions/CIK{cik_padded}.json"

    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
        if resp.status_code != 200:
            return []

        data = resp.json()
        filings = []

        recent = data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accessions = recent.get('accessionNumber', [])
        descriptions = recent.get('primaryDocument', [])

        for i, form in enumerate(forms[:100]):  # Check last 100 filings
            if form in filing_types:
                filings.append({
                    'form': form,
                    'filing_date': dates[i] if i < len(dates) else None,
                    'accession': accessions[i].replace('-', '') if i < len(accessions) else None,
                    'document': descriptions[i] if i < len(descriptions) else None,
                    'cik': cik_padded,
                })
                if len(filings) >= count:
                    break

        return filings
    except Exception as e:
        print(f"Error fetching SEC filings for CIK {cik}: {e}")
        return []


def fetch_filing_text(cik: str, accession: str, document: str) -> Optional[str]:
    """Fetch the text content of a specific filing."""
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
        if resp.status_code == 200:
            # Parse HTML to text
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator=' ', strip=True)[:100000]  # Limit to 100k chars
    except Exception as e:
        print(f"Error fetching filing text: {e}")

    return None


def detect_events(text: str, company_name: str) -> List[Tuple[str, str]]:
    """Detect significant events in filing text."""
    events = []
    text_lower = text.lower()

    for category, patterns in EVENT_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Find context around the match
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 200)
                    context = text[start:end].strip()
                    # Clean up context
                    context = re.sub(r'\s+', ' ', context)
                    events.append((category, context))
                    break  # One event per category

    return events


def extract_8k_items(text: str) -> List[str]:
    """Extract item numbers from 8-K filing."""
    items = []
    # 8-K item patterns
    item_patterns = [
        (r'Item\s*1\.01', 'Entry into Material Definitive Agreement'),
        (r'Item\s*1\.02', 'Termination of Material Agreement'),
        (r'Item\s*2\.01', 'Completion of Acquisition/Disposition'),
        (r'Item\s*2\.02', 'Results of Operations and Financial Condition'),
        (r'Item\s*2\.03', 'Creation of Direct Financial Obligation'),
        (r'Item\s*2\.05', 'Cost Associated with Exit Activities'),
        (r'Item\s*2\.06', 'Material Impairments'),
        (r'Item\s*3\.01', 'Notice of Delisting'),
        (r'Item\s*4\.01', 'Changes in Registrant\'s Certifying Accountant'),
        (r'Item\s*5\.01', 'Changes in Control'),
        (r'Item\s*5\.02', 'Departure/Appointment of Directors/Officers'),
        (r'Item\s*5\.03', 'Amendments to Articles/Bylaws'),
        (r'Item\s*7\.01', 'Regulation FD Disclosure'),
        (r'Item\s*8\.01', 'Other Events'),
        (r'Item\s*9\.01', 'Financial Statements and Exhibits'),
    ]

    for pattern, description in item_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            items.append(description)

    return items


def fetch_press_releases(company_name: str, url: str, limit: int = 10) -> List[Dict]:
    """Fetch recent press releases from company IR page."""
    releases = []

    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Common patterns for press release links
        link_patterns = [
            soup.find_all('a', class_=re.compile(r'press|release|news', re.I)),
            soup.find_all('a', href=re.compile(r'press-release|news', re.I)),
            soup.select('.press-release a, .news-item a, .release-item a'),
        ]

        seen_urls = set()
        for links in link_patterns:
            for link in links:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                # Make absolute URL
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)

                title = link.get_text(strip=True)
                if title and len(title) > 10:
                    releases.append({
                        'title': title[:200],
                        'url': href,
                        'company': company_name,
                    })

                if len(releases) >= limit:
                    break
            if len(releases) >= limit:
                break

    except Exception as e:
        print(f"Error fetching press releases for {company_name}: {e}")

    return releases


def create_news_table():
    """Create company_news table if not exists with proper schema."""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_news (
                news_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID REFERENCES public_company(company_id),
                news_type VARCHAR(50) NOT NULL,
                event_category VARCHAR(50),
                title TEXT NOT NULL,
                summary TEXT,
                source_url TEXT,
                filing_type VARCHAR(20),
                published_date TIMESTAMP,
                detected_keywords TEXT[],
                is_significant BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Create index for efficient queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_company_news_company
            ON company_news(company_id, published_date DESC)
        """))

        conn.commit()


def save_news_item(
    company_id: str,
    news_type: str,
    title: str,
    summary: str = None,
    source_url: str = None,
    filing_type: str = None,
    published_date: datetime = None,
    event_category: str = None,
    keywords: List[str] = None,
    is_significant: bool = False
):
    """Save a news item to the database."""
    engine = get_engine()

    with engine.connect() as conn:
        # Check if already exists (by URL)
        if source_url:
            result = conn.execute(text(
                "SELECT news_id FROM company_news WHERE source_url = :url"
            ), {"url": source_url})
            if result.fetchone():
                return None  # Already exists

        news_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO company_news (
                news_id, company_id, news_type, event_category, title, summary,
                source_url, filing_type, published_date, detected_keywords,
                is_significant, created_at
            ) VALUES (
                :news_id, :company_id, :news_type, :event_category, :title, :summary,
                :source_url, :filing_type, :published_date, :keywords,
                :is_significant, NOW()
            )
        """), {
            "news_id": news_id,
            "company_id": company_id,
            "news_type": news_type,
            "event_category": event_category,
            "title": title,
            "summary": summary,
            "source_url": source_url,
            "filing_type": filing_type,
            "published_date": published_date or datetime.now(),
            "keywords": keywords,
            "is_significant": is_significant,
        })
        conn.commit()
        return news_id


def process_sec_filings(company: Dict, days_back: int = 90) -> int:
    """Process SEC filings for a company."""
    cik = company.get('cik')
    if not cik:
        return 0

    company_id = company['company_id']
    company_name = company['name']

    print(f"\n  Fetching SEC filings for {company_name} (CIK: {cik})...")

    filings = fetch_sec_filings(cik, ['10-K', '10-Q', '8-K'], count=10)
    saved = 0

    for filing in filings:
        filing_date = filing.get('filing_date')
        if filing_date:
            try:
                fd = datetime.strptime(filing_date, '%Y-%m-%d')
                if fd < datetime.now() - timedelta(days=days_back):
                    continue  # Skip old filings
            except:
                pass

        form = filing.get('form')
        accession = filing.get('accession')
        document = filing.get('document')

        # Build filing URL
        cik_num = cik.lstrip('0')
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession}/{document}"

        # Create title based on filing type
        title = f"{company_name} files {form}"
        if form == '10-K':
            title = f"{company_name} Annual Report (10-K)"
        elif form == '10-Q':
            title = f"{company_name} Quarterly Report (10-Q)"
        elif form == '8-K':
            title = f"{company_name} Current Report (8-K)"

        # For 8-K filings, try to get more details
        summary = None
        event_category = None
        is_significant = False
        keywords = []

        if form == '8-K':
            # Fetch and parse 8-K content
            text = fetch_filing_text(cik_num, accession, document)
            if text:
                items = extract_8k_items(text)
                if items:
                    summary = "Items: " + ", ".join(items[:3])
                    keywords = items

                    # Mark certain 8-K items as significant
                    significant_items = [
                        'Departure/Appointment of Directors/Officers',
                        'Completion of Acquisition/Disposition',
                        'Changes in Control',
                    ]
                    if any(item in items for item in significant_items):
                        is_significant = True
                        event_category = 'executive_change' if 'Departure' in str(items) else 'merger_acquisition'

            time.sleep(0.5)  # Rate limit

        # Save to database
        news_id = save_news_item(
            company_id=company_id,
            news_type='sec_filing',
            title=title,
            summary=summary,
            source_url=filing_url,
            filing_type=form,
            published_date=datetime.strptime(filing_date, '%Y-%m-%d') if filing_date else None,
            event_category=event_category,
            keywords=keywords if keywords else None,
            is_significant=is_significant,
        )

        if news_id:
            saved += 1
            sig_marker = " [SIGNIFICANT]" if is_significant else ""
            print(f"    + {form} ({filing_date}){sig_marker}")

    return saved


def process_press_releases(company: Dict) -> int:
    """Process press releases from company IR page."""
    company_name = company['name']
    company_id = company['company_id']

    ir_url = INVESTOR_RELATIONS_URLS.get(company_name)
    if not ir_url:
        return 0

    print(f"\n  Fetching press releases for {company_name}...")

    releases = fetch_press_releases(company_name, ir_url, limit=10)
    saved = 0

    for release in releases:
        title = release.get('title', '')
        url = release.get('url', '')

        if not title or not url:
            continue

        # Detect event categories from title
        event_category = None
        is_significant = False

        title_lower = title.lower()
        for category, patterns in EVENT_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower, re.IGNORECASE):
                    event_category = category
                    is_significant = category in ['executive_change', 'merger_acquisition']
                    break
            if event_category:
                break

        news_id = save_news_item(
            company_id=company_id,
            news_type='press_release',
            title=title,
            source_url=url,
            event_category=event_category,
            is_significant=is_significant,
        )

        if news_id:
            saved += 1
            sig_marker = " [SIGNIFICANT]" if is_significant else ""
            print(f"    + {title[:60]}...{sig_marker}")

    return saved


def main():
    """Main function to fetch all investor news."""
    print("=" * 70)
    print("Investor News & SEC Filings Fetcher")
    print("=" * 70)

    # Ensure table exists
    create_news_table()

    companies = get_public_companies()
    print(f"\nProcessing {len(companies)} public companies...")

    total_filings = 0
    total_releases = 0

    for company in companies:
        name = company['name']
        print(f"\n{'='*60}")
        print(f"Processing: {name}")
        print('='*60)

        # Process SEC filings (for companies with CIK)
        filings_saved = process_sec_filings(company)
        total_filings += filings_saved

        # Process press releases
        releases_saved = process_press_releases(company)
        total_releases += releases_saved

        time.sleep(0.5)  # Rate limit between companies

    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  SEC filings saved: {total_filings}")
    print(f"  Press releases saved: {total_releases}")
    print("=" * 70)


if __name__ == '__main__':
    main()
