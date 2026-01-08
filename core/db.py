import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# ---------------------------------
# Connection URL
# ---------------------------------
def get_database_url() -> str:
    """
    Load DATABASE_URL from:
    1. Environment variable (for cron/scripts)
    2. Streamlit secrets (for Streamlit app)
    3. Local secrets.toml file (fallback)
    """
    url = os.getenv("DATABASE_URL")

    # Try Streamlit secrets if env var not set
    if not url:
        try:
            import streamlit as st
            url = st.secrets["DATABASE_URL"]
        except Exception:
            pass

    # Fallback: read directly from secrets.toml
    if not url:
        try:
            # Try tomllib (Python 3.11+) first, fall back to toml
            try:
                import tomllib
                secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
                if secrets_path.exists():
                    with open(secrets_path, "rb") as f:
                        secrets = tomllib.load(f)
                        url = secrets.get("DATABASE_URL")
            except ImportError:
                import toml
                secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
                if secrets_path.exists():
                    secrets = toml.load(str(secrets_path))
                    url = secrets.get("DATABASE_URL")
        except Exception:
            pass

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

    _engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,  # Recycle connections after 5 minutes
    )
    return _engine


def get_session():
    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal()
