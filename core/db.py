import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]
    raise KeyError("Missing DATABASE_URL in Streamlit secrets")


def get_engine():
    url = get_database_url()

    # Supabase expects SSL; also force schema to public
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
