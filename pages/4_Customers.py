"""
pages/4_Customers.py - Customer Directory & Demographics
"""

import streamlit as st
import plotly.express as px
import db
import ui_utils

st.set_page_config(page_title="Customers | Databricks Analytics", page_icon="👥", layout="wide")
ui_utils.apply_custom_theme()
ui_utils.render_sidebar_connection_status()

st.title("👥 Customer Directory & Regional Demographics")
st.caption("Active customer accounts from workspace.sales_demo.customers")

# Verify connection
is_valid, msg = db.validate_connection_config()
if not is_valid:
    st.error(f"⚠️ {msg}")
    st.stop()

# Region filter & search
try:
    filter_data = db.get_filter_options()
    regions = ["All"] + filter_data.get("regions", [])
except Exception:
    regions = ["All"]

col_reg, col_srch = st.columns([1, 2])
with col_reg:
    selected_region = st.selectbox("Filter Region", options=regions, index=0)
with col_srch:
    search_cust = st.text_input("🔍 Search Customers", placeholder="e.g. Rahul, Mumbai, or email...")

try:
    with st.spinner("Loading customers list..."):
        df_cust = db.get_customers(region=selected_region)

    if not df_cust.empty:
        if search_cust:
            term = search_cust.lower()
            df_cust = df_cust[
                df_cust["customer_name"].astype(str).str.lower().str.contains(term, na=False)
                | df_cust["email"].astype(str).str.lower().str.contains(term, na=False)
                | df_cust["city"].astype(str).str.lower().str.contains(term, na=False)
            ]

        # Top metrics
        total_customers = len(df_cust)
        unique_cities = df_cust["city"].nunique() if "city" in df_cust.columns else 0
        unique_regions = df_cust["region"].nunique() if "region" in df_cust.columns else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Customers Listed", f"{total_customers}")
        m2.metric("Unique Cities", f"{unique_cities}")
        m3.metric("Regions Represented", f"{unique_regions}")

        st.markdown("---")

        # Regional Breakdown Chart
        if "region" in df_cust.columns:
            df_reg_counts = df_cust.groupby("region", as_index=False)["customer_id"].count().rename(
                columns={"customer_id": "count"}
            )
            fig_cust_reg = px.bar(
                df_reg_counts,
                x="region",
                y="count",
                color="region",
                labels={"region": "Region", "count": "Customers"},
                title="Customer Distribution by Region",
            )
            fig_cust_reg.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_cust_reg, use_container_width=True)

        # Customer Table
        st.subheader("Customer Profiles")
        df_display = df_cust.rename(
            columns={
                "customer_id": "Customer ID",
                "customer_name": "Full Name",
                "email": "Email Address",
                "city": "City",
                "region": "Region",
            }
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    else:
        st.info("No customers found matching the search criteria.")

except Exception as e:
    st.error(f"Error loading customers from Databricks: {e}")
