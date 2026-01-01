# app/pages/9_Admin_Setup.py
"""
Admin Setup - Manage dispensaries, run discovery, test scrapes.
"""

import os
import sys
import json
from datetime import datetime, timezone

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from sqlalchemy import text, inspect

from core.db import get_engine, get_session
from core.models import Base, Dispensary, ScrapeRun, RawMenuItem


st.set_page_config(page_title="Admin Setup", page_icon="⚙️", layout="wide")
st.title("⚙️ Admin Setup")

# Tabs for different admin functions
tab_db, tab_discover, tab_dispensaries, tab_scrape = st.tabs([
    "🗄️ Database",
    "🔍 Discover URL",
    "🏪 Dispensaries",
    "🔄 Test Scrape",
])


# ==============================================================================
# TAB 1: Database Management
# ==============================================================================
with tab_db:
    st.header("Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Create/Verify Tables", type="primary"):
            try:
                engine = get_engine()
                Base.metadata.create_all(engine)
                st.success("✅ Tables created/verified successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with col2:
        if st.button("Show Current Tables"):
            try:
                engine = get_engine()
                inspector = inspect(engine)
                tables = inspector.get_table_names(schema="public")
                st.write("**Tables in public schema:**")
                for t in tables:
                    st.write(f"  • {t}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.divider()
    
    # Quick stats
    st.subheader("Quick Stats")
    try:
        db = get_session()
        stats = {
            "Dispensaries": db.query(Dispensary).count(),
            "Scrape Runs": db.query(ScrapeRun).count(),
            "Raw Menu Items": db.query(RawMenuItem).count(),
        }
        cols = st.columns(len(stats))
        for col, (label, count) in zip(cols, stats.items()):
            col.metric(label, count)
        db.close()
    except Exception as e:
        st.warning(f"Could not load stats: {e}")


# ==============================================================================
# TAB 2: URL Discovery
# ==============================================================================
with tab_discover:
    st.header("Discover Dispensary URL")
    st.write("Paste a dispensary menu URL to auto-detect the provider and extract configuration.")
    
    discover_url = st.text_input(
        "Menu URL",
        placeholder="https://www.gleaf.com/stores/maryland/rockville/shop",
        key="discover_url"
    )
    
    if st.button("🔍 Run Discovery", disabled=not discover_url):
        with st.spinner("Running discovery (this may take 30-60 seconds)..."):
            try:
                # Import discovery module
                from ingest.discover_sweed import discover_one
                
                result = discover_one(discover_url, timeout_ms=60000)
                
                # Store in session state for use in dispensary creation
                st.session_state["discovery_result"] = result
                
                # Display results
                st.success(f"✅ Discovery complete!")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Provider", result.get("provider", "unknown"))
                col2.metric("Confidence", f"{result.get('confidence', 0):.0%}")
                col3.metric("API Calls Found", len(result.get("network_samples", [])))
                
                # Extracted IDs
                st.subheader("Extracted Configuration")
                extracted = result.get("extracted", {})
                
                config_cols = st.columns(4)
                config_cols[0].text_input("Store ID", value=extracted.get("store_id") or "", disabled=True)
                config_cols[1].text_input("Tenant ID", value=extracted.get("tenant_id") or "", disabled=True)
                config_cols[2].text_input("Menu Category ID", value=extracted.get("menu_category_id") or "", disabled=True)
                config_cols[3].text_input("API Base", value=extracted.get("api_base") or "", disabled=True)
                
                # Signals
                if result.get("signals"):
                    st.write("**Detection Signals:**", ", ".join(result["signals"]))
                
                # Show raw JSON in expander
                with st.expander("Raw Discovery Result"):
                    st.json(result)
                
                # Quick add button
                if result.get("provider") != "unknown" and extracted.get("store_id"):
                    st.divider()
                    st.subheader("Quick Add Dispensary")
                    
                    quick_name = st.text_input("Dispensary Name", key="quick_name")
                    quick_state = st.text_input("State", value="MD", max_chars=2, key="quick_state")
                    
                    if st.button("➕ Add This Dispensary", type="primary", disabled=not quick_name):
                        try:
                            db = get_session()
                            
                            metadata = {
                                "store_id": extracted.get("store_id"),
                                "tenant_id": extracted.get("tenant_id"),
                                "api_base": extracted.get("api_base"),
                                "menu_category_id": extracted.get("menu_category_id"),
                            }
                            
                            new_disp = Dispensary(
                                name=quick_name,
                                state=quick_state.upper(),
                                menu_url=discover_url,
                                menu_provider=result.get("provider"),
                                provider_metadata=json.dumps(metadata),
                                discovery_confidence=result.get("confidence"),
                                last_discovered_at=datetime.now(timezone.utc),
                            )
                            db.add(new_disp)
                            db.commit()
                            
                            st.success(f"✅ Added dispensary: {quick_name}")
                            st.balloons()
                            db.close()
                        except Exception as e:
                            st.error(f"❌ Error adding dispensary: {e}")
                
            except ImportError as e:
                st.error(f"❌ Discovery module not available. Make sure Playwright is installed: {e}")
            except Exception as e:
                st.error(f"❌ Discovery failed: {e}")
                st.exception(e)


# ==============================================================================
# TAB 3: Dispensary Management
# ==============================================================================
with tab_dispensaries:
    st.header("Manage Dispensaries")
    
    # Add new dispensary form
    with st.expander("➕ Add New Dispensary", expanded=False):
        with st.form("add_dispensary"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Name *", placeholder="gLeaf Rockville")
                new_state = st.text_input("State *", value="MD", max_chars=2)
                new_city = st.text_input("City", placeholder="Rockville")
                new_address = st.text_input("Address", placeholder="123 Main St")
            
            with col2:
                new_url = st.text_input("Menu URL *", placeholder="https://...")
                new_provider = st.selectbox("Provider", ["sweed", "gleaf", "dutchie", "jane", "generic"])
                new_store_id = st.text_input("Store ID (for Sweed)", placeholder="12345")
            
            submitted = st.form_submit_button("Add Dispensary", type="primary")
            
            if submitted:
                if not new_name or not new_url:
                    st.error("Name and Menu URL are required")
                else:
                    try:
                        db = get_session()
                        
                        metadata = {}
                        if new_store_id:
                            metadata["store_id"] = new_store_id
                        
                        disp = Dispensary(
                            name=new_name,
                            state=new_state.upper(),
                            city=new_city or None,
                            address=new_address or None,
                            menu_url=new_url,
                            menu_provider=new_provider,
                            provider_metadata=json.dumps(metadata) if metadata else None,
                        )
                        db.add(disp)
                        db.commit()
                        st.success(f"✅ Added: {new_name}")
                        db.close()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    
    st.divider()
    
    # List existing dispensaries
    st.subheader("Existing Dispensaries")
    
    try:
        db = get_session()
        dispensaries = db.query(Dispensary).order_by(Dispensary.name).all()
        
        if not dispensaries:
            st.info("No dispensaries found. Add one above or use the Discovery tab.")
        else:
            for disp in dispensaries:
                with st.expander(f"{'🟢' if disp.is_active else '🔴'} {disp.name} ({disp.state})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**ID:** `{disp.dispensary_id}`")
                        st.write(f"**URL:** {disp.menu_url}")
                        st.write(f"**Provider:** {disp.menu_provider}")
                        
                        if disp.provider_metadata:
                            try:
                                meta = json.loads(disp.provider_metadata)
                                st.write(f"**Store ID:** {meta.get('store_id', 'N/A')}")
                            except:
                                pass
                        
                        if disp.discovery_confidence:
                            st.write(f"**Discovery Confidence:** {disp.discovery_confidence:.0%}")
                    
                    with col2:
                        # Action buttons
                        if st.button("🗑️ Delete", key=f"del_{disp.dispensary_id}"):
                            db.delete(disp)
                            db.commit()
                            st.success(f"Deleted {disp.name}")
                            st.rerun()
                        
                        if disp.is_active:
                            if st.button("⏸️ Deactivate", key=f"deact_{disp.dispensary_id}"):
                                disp.is_active = False
                                db.commit()
                                st.rerun()
                        else:
                            if st.button("▶️ Activate", key=f"act_{disp.dispensary_id}"):
                                disp.is_active = True
                                db.commit()
                                st.rerun()
        
        db.close()
    except Exception as e:
        st.error(f"❌ Error loading dispensaries: {e}")


# ==============================================================================
# TAB 4: Test Scrape
# ==============================================================================
with tab_scrape:
    st.header("Test Scrape")
    st.write("Run a test scrape for a specific dispensary.")
    
    try:
        db = get_session()
        dispensaries = db.query(Dispensary).filter(
            Dispensary.menu_url.isnot(None),
            Dispensary.is_active == True,
        ).all()
        db.close()
        
        if not dispensaries:
            st.warning("No active dispensaries with URLs found.")
        else:
            disp_options = {f"{d.name} ({d.menu_provider})": d.dispensary_id for d in dispensaries}
            selected = st.selectbox("Select Dispensary", list(disp_options.keys()))
            selected_id = disp_options[selected]
            
            if st.button("🚀 Run Test Scrape", type="primary"):
                with st.spinner("Running scrape..."):
                    try:
                        # Import and run scraper
                        from ingest.run_scrape import scrape_dispensary
                        
                        db = get_session()
                        disp = db.query(Dispensary).filter(Dispensary.dispensary_id == selected_id).first()
                        
                        if disp:
                            result = scrape_dispensary(db, disp)
                            
                            if result["status"] == "success":
                                st.success(f"✅ Scraped {result['items']} items!")
                                st.json(result)
                            else:
                                st.error(f"❌ Scrape failed: {result.get('error')}")
                        else:
                            st.error("Dispensary not found")
                        
                        db.close()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                        st.exception(e)
            
            # Show recent scrape runs
            st.divider()
            st.subheader("Recent Scrape Runs")
            
            try:
                db = get_session()
                recent_runs = db.query(ScrapeRun).filter(
                    ScrapeRun.dispensary_id == selected_id
                ).order_by(ScrapeRun.started_at.desc()).limit(10).all()
                
                if recent_runs:
                    for run in recent_runs:
                        status_icon = "✅" if run.status == "success" else "❌" if run.status == "fail" else "⏳"
                        st.write(
                            f"{status_icon} {run.started_at} - "
                            f"**{run.status}** - "
                            f"{run.records_found or 0} items"
                        )
                        if run.error_message:
                            st.caption(f"Error: {run.error_message[:200]}")
                else:
                    st.info("No scrape runs yet for this dispensary.")
                
                db.close()
            except Exception as e:
                st.warning(f"Could not load scrape history: {e}")
                
    except Exception as e:
        st.error(f"❌ Error: {e}")
