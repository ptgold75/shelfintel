# app/pages/3_Register.py
"""Registration page for CannaLinx users."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import datetime
from sqlalchemy import text
from core.db import get_engine
import re

st.set_page_config(page_title="Register | CannaLinx", page_icon="📝", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .registration-header {
        text-align: center;
        padding: 2rem 0;
    }
    .user-type-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border: 2px solid transparent;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .user-type-card:hover {
        border-color: #1a5f2a;
    }
    .user-type-selected {
        border-color: #1a5f2a;
        background: #e8f5e9;
    }
    .form-section {
        background: #ffffff;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: 0 auto;
    }
    .benefit-list {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

st.title("📝 Register for CannaLinx")
st.markdown("Get access to Maryland's most comprehensive cannabis market intelligence platform.")

st.markdown("---")

# User Type Selection
st.subheader("What type of organization are you?")

user_type = st.selectbox(
    "Select your organization type",
    options=["", "Dispensary", "Manufacturer/Grower", "Brand"],
    index=0,
    help="This helps us tailor your dashboard and insights"
)

# Show benefits based on selection
if user_type == "Dispensary":
    st.success("**Dispensary Benefits:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - Compare your menu to competitors
        - Identify product gaps
        - Track price positioning
        """)
    with col2:
        st.markdown("""
        - Monitor nearby dispensaries
        - Category mix analysis
        - Trend alerts
        """)

elif user_type == "Manufacturer/Grower":
    st.success("**Manufacturer Benefits:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - Track distribution coverage
        - Monitor retail pricing
        - Market share insights
        """)
    with col2:
        st.markdown("""
        - Sales territory intelligence
        - Product placement tracking
        - Competitor analysis
        """)

elif user_type == "Brand":
    st.success("**Brand Benefits:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - Brand visibility tracking
        - SKU performance metrics
        - Distribution mapping
        """)
    with col2:
        st.markdown("""
        - Competitive positioning
        - New launch tracking
        - Pricing consistency
        """)

st.markdown("---")

# Registration Form
if user_type:
    st.subheader("Registration Details")

    with st.form("registration_form"):
        # Company Information
        st.markdown("#### Company Information")
        company_name = st.text_input(
            "Company Name *",
            placeholder="Enter your company's legal or trade name"
        )

        # For dispensaries, offer a dropdown of known dispensaries
        linked_dispensary = None
        if user_type == "Dispensary":
            try:
                engine = get_engine()
                with engine.connect() as conn:
                    dispensaries = conn.execute(text("""
                        SELECT DISTINCT name FROM dispensaries ORDER BY name
                    """)).fetchall()
                    disp_names = ["Select your dispensary..."] + [d[0] for d in dispensaries]

                linked_dispensary = st.selectbox(
                    "Link to Dispensary (optional)",
                    options=disp_names,
                    index=0,
                    help="If your dispensary is in our system, select it for immediate access"
                )
                if linked_dispensary == "Select your dispensary...":
                    linked_dispensary = None
            except:
                pass

        # For manufacturers/brands, could link to their brands
        linked_brand = None
        if user_type in ["Manufacturer/Grower", "Brand"]:
            linked_brand = st.text_input(
                "Primary Brand Name (optional)",
                placeholder="Your main brand name as it appears on products",
                help="We'll track this brand across all dispensaries"
            )

        st.markdown("#### Contact Information")

        col1, col2 = st.columns(2)

        with col1:
            contact_name = st.text_input(
                "Contact Name *",
                placeholder="First and Last Name"
            )

            email = st.text_input(
                "Email *",
                placeholder="you@company.com"
            )

        with col2:
            title = st.text_input(
                "Title",
                placeholder="e.g., Owner, Buyer, Sales Manager"
            )

            phone = st.text_input(
                "Phone",
                placeholder="(555) 555-5555"
            )

        st.markdown("#### Additional Information")

        # County/region of interest
        county = st.selectbox(
            "Primary County of Interest",
            options=[
                "All Maryland",
                "Anne Arundel County",
                "Baltimore City",
                "Baltimore County",
                "Carroll County",
                "Cecil County",
                "Frederick County",
                "Harford County",
                "Howard County",
                "Montgomery County",
                "Prince George's County",
                "Washington County",
                "Other"
            ],
            index=0
        )

        # How they heard about us
        referral_source = st.selectbox(
            "How did you hear about CannaLinx?",
            options=[
                "Select...",
                "Industry Event/Conference",
                "Word of Mouth",
                "Search Engine",
                "Social Media",
                "Industry Publication",
                "Other"
            ],
            index=0
        )

        # Comments
        comments = st.text_area(
            "Anything else you'd like us to know?",
            placeholder="Tell us about your specific needs or questions...",
            max_chars=500
        )

        # Terms
        agree_terms = st.checkbox(
            "I agree to receive product updates and industry insights from CannaLinx"
        )

        # Submit button
        submitted = st.form_submit_button("Submit Registration", use_container_width=True)

        if submitted:
            # Validation
            errors = []
            if not user_type:
                errors.append("Please select your organization type")
            if not company_name:
                errors.append("Company name is required")
            if not contact_name:
                errors.append("Contact name is required")
            if not email:
                errors.append("Email is required")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                errors.append("Please enter a valid email address")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Save to database
                try:
                    engine = get_engine()
                    with engine.connect() as conn:
                        # Check if registrations table exists, create if not
                        conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS registrations (
                                id SERIAL PRIMARY KEY,
                                user_type VARCHAR(50) NOT NULL,
                                company_name VARCHAR(255) NOT NULL,
                                contact_name VARCHAR(255) NOT NULL,
                                email VARCHAR(255) NOT NULL,
                                phone VARCHAR(50),
                                title VARCHAR(100),
                                county VARCHAR(100),
                                linked_dispensary VARCHAR(255),
                                linked_brand VARCHAR(255),
                                referral_source VARCHAR(100),
                                comments TEXT,
                                agree_terms BOOLEAN DEFAULT FALSE,
                                created_at TIMESTAMP DEFAULT NOW(),
                                status VARCHAR(50) DEFAULT 'pending'
                            )
                        """))

                        # Insert registration
                        conn.execute(text("""
                            INSERT INTO registrations
                            (user_type, company_name, contact_name, email, phone, title,
                             county, linked_dispensary, linked_brand, referral_source,
                             comments, agree_terms)
                            VALUES
                            (:user_type, :company_name, :contact_name, :email, :phone, :title,
                             :county, :linked_dispensary, :linked_brand, :referral_source,
                             :comments, :agree_terms)
                        """), {
                            "user_type": user_type,
                            "company_name": company_name,
                            "contact_name": contact_name,
                            "email": email,
                            "phone": phone or None,
                            "title": title or None,
                            "county": county if county != "All Maryland" else None,
                            "linked_dispensary": linked_dispensary,
                            "linked_brand": linked_brand or None,
                            "referral_source": referral_source if referral_source != "Select..." else None,
                            "comments": comments or None,
                            "agree_terms": agree_terms
                        })
                        conn.commit()

                    st.success("🎉 **Registration Submitted Successfully!**")
                    st.balloons()
                    st.markdown("""
                    Thank you for registering with CannaLinx!

                    **What's next?**
                    - Our team will review your registration within 24-48 hours
                    - You'll receive an email with your login credentials
                    - Once approved, you'll have full access to your personalized dashboard

                    Questions? Contact us at **support@cannalinx.com**
                    """)

                except Exception as e:
                    st.error(f"Registration failed: {e}")
                    st.info("Please try again or contact support@cannalinx.com")

else:
    st.info("👆 Please select your organization type above to continue with registration.")

# Sidebar info
with st.sidebar:
    st.markdown("### Why Register?")
    st.markdown("""
    CannaLinx provides:

    - **Real-time data** on 100+ dispensaries
    - **190,000+ products** tracked daily
    - **Competitive intelligence** tailored to your role
    - **Custom alerts** for price and product changes

    Registration is free for a limited time!
    """)

    st.markdown("---")
    st.markdown("### Need Help?")
    st.markdown("""
    Contact our team:
    - Email: support@cannalinx.com
    - Phone: (301) 555-0123
    """)
