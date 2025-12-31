import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_database_url() -> str:
    return st.secrets["DATABASE_URL"]

def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)

def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
