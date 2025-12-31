import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from core.db import get_engine
from core.models import Base

st.title("Admin Setup")

if st.button("Create/Verify Tables"):
    engine = get_engine()
    Base.metadata.create_all(engine)
    st.success("✅ Tables created/verified in Supabase.")
