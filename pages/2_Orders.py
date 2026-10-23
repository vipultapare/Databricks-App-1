"""
pages/2_Orders.py - Orders Analytics and Transaction Ledger
"""

import streamlit as st
import pandas as pd
import db
import ui_utils

st.set_page_config(page_title="Orders | Databricks Analytics", page_icon="📦", layout="wide")
ui_utils.apply_custom_theme()
ui_utils.render_sidebar_connection_status()
filters = ui_utils.render_sidebar_filters()

st.title("📦 Orders Ledger & Analysis")
st.caption("Live transaction stream joined from orders, customers, and products tables")

# Verify configuration
is_valid, msg = db.validate_connection_config()
if not is_valid:
    st.error(f"⚠️ {msg}")
    st.stop()

# Controls row
row_c1, row_c2, row_c3 = st.columns([2, 1, 1])
with row_c1:
    search_term = st.text_input("🔍 Search by Customer or Product Name", placeholder="e.g. John or Laptop...")
with row_c2:
    row_limit = st.selectbox("Rows to display", options=[25, 50, 100, 200], index=1)
with row_c3:
    st.write("")
    st.write("")
    refresh = st.button("🔄 Refresh Data")

try:
    with st.spinner("Fetching orders from Databricks..."):
        df_orders = db.get_recent_orders(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
            limit=row_limit,
        )

    if not df_orders.empty:
        # Client-side text search filtering
        if search_term:
            term = search_term.lower()
            df_orders = df_orders[
                df_orders["customer_name"].astype(str).str.lower().str.contains(term, na=False)
                | df_orders["product_name"].astype(str).str.lower().str.contains(term, na=False)
                | df_orders["order_id"].astype(str).str.lower().str.contains(term, na=False)
            ]

        # Summary KPIs for displayed orders
        total_disp_orders = len(df_orders)
        total_disp_amount = df_orders["sales_amount"].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Orders Listed", f"{total_disp_orders}")
        m2.metric("Cumulative Amount", ui_utils.format_inr(total_disp_amount))
        m3.metric("Avg Order Size", ui_utils.format_inr(total_disp_amount / total_disp_orders if total_disp_orders else 0))

        st.markdown("---")

        # Format dataframe for clean presentation
        df_display = df_orders.copy()
        if "order_date" in df_display.columns:
            df_display["order_date"] = pd.to_datetime(df_display["order_date"]).dt.strftime("%Y-%m-%d")

        df_display["sales_amount"] = df_display["sales_amount"].apply(ui_utils.format_inr)

        # Rename columns for presentation
        df_display = df_display.rename(
            columns={
                "order_id": "Order ID",
                "order_date": "Date",
                "customer_name": "Customer",
                "city": "City",
                "region": "Region",
                "product_name": "Product",
                "category": "Category",
                "quantity": "Qty",
                "sales_amount": "Amount",
                "order_status": "Status",
            }
        )

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # CSV Download button
        csv_bytes = df_orders.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Orders as CSV",
            data=csv_bytes,
            file_name="databricks_orders.csv",
            mime="text/csv",
        )
    else:
        st.info("No orders found matching the selected filters.")

except Exception as e:
    st.error(f"Error loading orders from Databricks: {e}")
