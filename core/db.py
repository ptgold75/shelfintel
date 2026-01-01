import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def get_database_url() -> str:
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    raise KeyError("DATABASE_URL is missing (set Streamlit secret or env var)")


@st.cache_resource
def get_engine():
    url = get_database_url()

    connect_args = {
        "sslmode": "require",
        "options": "-csearch_path=public",
    }

    # Supabase transaction pooler (port 6543) → use NullPool per Supabase guidance
    # to avoid issues with persistent pooling in transaction mode.
    if ":6543/" in url or ":6543?" in url:
        return create_engine(
            url,
            pool_pre_ping=True,
            poolclass=NullPool,
            connect_args=connect_args,
        )

    # Direct connection (5432) can use default pool
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_session():
    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal()
