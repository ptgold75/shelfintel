import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    # Streamlit Cloud uses st.secrets; locally you may also set env var
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]
    raise KeyError("Missing DATABASE_URL in Streamlit secrets")


@st.cache_resource
def get_engine():
    url = get_database_url()

    # Force schema to public so queries like "FROM dispensary" work reliably
    # Also ensure SSL is required (Supabase expects it)
    connect_args = {
        "sslmode": "require",
        "options": "-csearch_path=public",
    }

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
