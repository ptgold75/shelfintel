# app/pages/11_Brand_Assets.py
"""Brand Asset Compliance - Track product images across dispensaries."""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from components.nav import render_nav
from collections import defaultdict

st.set_page_config(page_title="Brand Assets - CannLinx", layout="wide")
render_nav()

st.title("Brand Asset Compliance")
st.caption("Review how your products appear across dispensaries and identify image issues")


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DATABASE_URL"])


@st.cache_data(ttl=300)
def get_brands():
    """Get list of brands with images."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, COUNT(*) as cnt
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand <> ''
            GROUP BY UPPER(raw_brand)
            HAVING COUNT(*) >= 5
            ORDER BY cnt DESC
        """))
        return [row[0] for row in result]


@st.cache_data(ttl=300)
def get_product_images(brand: str):
    """Get product images across stores for a brand."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get products with image URLs from raw_json
        result = conn.execute(text("""
            SELECT
                r.raw_name,
                d.name as store_name,
                d.dispensary_id,
                r.raw_json->>'image' as image_url,
                r.raw_json->>'imageUrl' as image_url2,
                r.raw_json->>'photo' as photo_url
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand
            ORDER BY r.raw_name, d.name
        """), {"brand": brand}).fetchall()

        return result


@st.cache_data(ttl=300)
def get_image_summary(brand: str):
    """Get summary of image usage for a brand."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                r.raw_name,
                COUNT(DISTINCT d.dispensary_id) as store_count,
                COUNT(DISTINCT COALESCE(
                    r.raw_json->>'image',
                    r.raw_json->>'imageUrl',
                    r.raw_json->>'photo',
                    'no_image'
                )) as unique_images
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand
            GROUP BY r.raw_name
            ORDER BY unique_images DESC, store_count DESC
        """), {"brand": brand}).fetchall()

        return result


# Brand selector
brands = get_brands()
if not brands:
    st.warning("No brand data available")
    st.stop()

col1, col2 = st.columns([2, 1])
with col1:
    selected_brand = st.selectbox("Select Your Brand", brands, index=0)
with col2:
    view_mode = st.radio("View", ["Summary", "Detailed"], horizontal=True)

if selected_brand:
    st.markdown("---")

    if view_mode == "Summary":
        st.subheader("Image Consistency Summary")
        st.caption("Products with multiple unique images may have inconsistent assets across stores")

        summary = get_image_summary(selected_brand)

        if summary:
            df = pd.DataFrame(summary, columns=["Product", "Stores", "Unique Images"])
            df["Status"] = df["Unique Images"].apply(
                lambda x: "Consistent" if x <= 1 else ("Review Needed" if x <= 3 else "Multiple Versions")
            )

            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                consistent = len(df[df["Status"] == "Consistent"])
                st.metric("Consistent Products", consistent)
            with col2:
                needs_review = len(df[df["Status"] == "Review Needed"])
                st.metric("Need Review", needs_review)
            with col3:
                multiple = len(df[df["Status"] == "Multiple Versions"])
                st.metric("Multiple Versions", multiple)

            st.markdown("---")

            # Filter options
            status_filter = st.multiselect(
                "Filter by Status",
                ["Consistent", "Review Needed", "Multiple Versions"],
                default=["Review Needed", "Multiple Versions"]
            )

            filtered_df = df[df["Status"].isin(status_filter)] if status_filter else df

            st.dataframe(
                filtered_df.style.apply(
                    lambda row: [
                        "background-color: #d4edda" if row["Status"] == "Consistent"
                        else "background-color: #fff3cd" if row["Status"] == "Review Needed"
                        else "background-color: #f8d7da"
                    ] * len(row),
                    axis=1
                ),
                use_container_width=True,
                hide_index=True,
                height=500
            )
        else:
            st.info("No product data found")

    else:  # Detailed view
        st.subheader("Product Image Details")

        images = get_product_images(selected_brand)

        if images:
            # Group by product
            products = defaultdict(list)
            for row in images:
                product_name = row[0]
                store = row[1]
                image_url = row[3] or row[4] or row[5]  # Try different image fields
                products[product_name].append({
                    "store": store,
                    "image_url": image_url
                })

            # Product selector
            product_names = sorted(products.keys())
            selected_product = st.selectbox("Select Product", product_names)

            if selected_product:
                st.markdown("---")
                product_data = products[selected_product]

                # Group by unique image URL
                images_by_url = defaultdict(list)
                for item in product_data:
                    url = item["image_url"] or "No Image"
                    images_by_url[url].append(item["store"])

                st.markdown(f"**{len(images_by_url)} unique image(s) found across {len(product_data)} stores**")

                # Display each unique image
                for i, (url, stores) in enumerate(images_by_url.items()):
                    with st.expander(f"Image Version {i+1} - Used by {len(stores)} store(s)", expanded=(i == 0)):
                        col1, col2 = st.columns([1, 2])

                        with col1:
                            if url and url != "No Image" and url.startswith("http"):
                                try:
                                    st.image(url, width=200)
                                except:
                                    st.caption("Image could not be loaded")
                                    st.code(url[:100] + "..." if len(url) > 100 else url)
                            else:
                                st.info("No image available")

                        with col2:
                            st.markdown("**Stores using this image:**")
                            for store in sorted(stores):
                                st.markdown(f"- {store}")
        else:
            st.info("No image data found")

# Value proposition
st.markdown("---")
st.markdown("""
**Why Image Compliance Matters:**

| Issue | Impact |
|-------|--------|
| **Inconsistent Images** | Confuses customers, damages brand perception |
| **Outdated Photos** | Old packaging still showing in stores |
| **Missing Images** | Products appear unprofessional |
| **Wrong Images** | Competitor or wrong product showing |

**Action Items:**
- Review products with "Multiple Versions" status
- Contact stores using incorrect assets
- Provide updated image assets to dispensary partners
""")
