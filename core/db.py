import os
import re
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def get_database_url() -> str:
    # In Streamlit Cloud, ALWAYS use secrets.
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]

    # Local fallback for your Mac scripts / cron
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    raise KeyError("DATABASE_URL missing: set Streamlit secret or env var")


@st.cache_resource
def get_engine():
    url = get_database_url()

    # Safe debug: print host only (no password)
    m = re.search(r"@([^:/]+)", url)
    host = m.group(1) if m else "unknown"
    print("DB HOST:", host)

    connect_args = {
        "sslmode": "require",
        "options": "-csearch_path=public",
    }

    # Pooler (6543) => NullPool
    if ":6543/" in url or ":6543?" in url:
        return create_engine(
            url,
            pool_pre_ping=True,
            poolclass=NullPool,
            connect_args=connect_args,
        )

    # Direct (5432)
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_session():
    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal()
