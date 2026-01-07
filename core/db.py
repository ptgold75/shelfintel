import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

# ---------------------------------
# Offline Mode Detection
# ---------------------------------
def is_offline_mode() -> bool:
    """Check if we should use offline SQLite database."""
    # Check environment variable
    if os.getenv("OFFLINE_MODE", "").lower() in ("1", "true", "yes"):
        return True

    # Check Streamlit secrets
    try:
        import streamlit as st
        if st.secrets.get("OFFLINE_MODE", False):
            return True
    except Exception:
        pass

    return False


def get_sqlite_path() -> Path:
    """Get path to local SQLite database."""
    return Path(__file__).parent.parent / "data" / "offline.db"


# ---------------------------------
# Connection URL
# ---------------------------------
def get_database_url() -> str:
    """
    Load DATABASE_URL from:
    1. Offline SQLite (if OFFLINE_MODE is set)
    2. Environment variable (for cron/scripts)
    3. Streamlit secrets (for Streamlit app)
    4. Local secrets.toml file (fallback)
    """
    # Check for offline mode first
    if is_offline_mode():
        sqlite_path = get_sqlite_path()
        if sqlite_path.exists():
            print(f"OFFLINE MODE: Using SQLite at {sqlite_path}")
            return f"sqlite:///{sqlite_path}"
        else:
            print(f"WARNING: Offline mode requested but {sqlite_path} not found!")
            print("Run: python scripts/export_to_sqlite.py")

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

    # SQLite needs different pool settings
    if url.startswith("sqlite"):
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
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
