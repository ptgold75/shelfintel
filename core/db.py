import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# ---------------------------------
# Connection URL
# ---------------------------------
def get_database_url() -> str:
    """
    Local + cron: use env var DATABASE_URL
    Streamlit Cloud: also uses env var via Secrets -> env injection (or you can set env locally).
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")

    # Safe debug (no password)
    m = re.search(r"@([^:/]+)", url)
    host = m.group(1) if m else "unknown"
    print("DB HOST:", host)

    return url

# ---------------------------------
# Engine + Session
# ---------------------------------
_engine = None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    url = get_database_url()

    # Use NullPool for Supabase pooler stability
    _engine = create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    return _engine


def get_session():
    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal()
