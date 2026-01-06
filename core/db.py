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
            import tomllib
            from pathlib import Path
            secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
            if secrets_path.exists():
                with open(secrets_path, "rb") as f:
                    secrets = tomllib.load(f)
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
