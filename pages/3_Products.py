"""
pages/3_Products.py - Product Inventory & Stock Management
"""

import streamlit as st
import plotly.express as px
import db
import ui_utils

st.set_page_config(page_title="Products | Databricks Analytics", page_icon="🏷️", layout="wide")
ui_utils.apply_custom_theme()
ui_utils.render_sidebar_connection_status()

st.title("🏷️ Product Inventory & Catalog")
st.caption("Active product stock levels and pricing from workspace.sales_demo.products")

# Verify connection
is_valid, msg = db.validate_connection_config()
if not is_valid:
    st.error(f"⚠️ {msg}")
    st.stop()

# Category filter and search
try:
    filter_data = db.get_filter_options()
    categories = ["All"] + filter_data.get("categories", [])
except Exception:
    categories = ["All"]

col_cat, col_srch = st.columns([1, 2])
with col_cat:
    selected_cat = st.selectbox("Filter Category", options=categories, index=0)
with col_srch:
    search_prod = st.text_input("🔍 Search Products", placeholder="e.g. Phone, Monitor...")

try:
    with st.spinner("Fetching product inventory..."):
        df_prod = db.get_product_inventory(category=selected_cat)

    if not df_prod.empty:
        if search_prod:
            df_prod = df_prod[
                df_prod["product_name"].astype(str).str.lower().str.contains(search_prod.lower(), na=False)
            ]

        # Inventory summary metrics
        total_prods = len(df_prod)
        total_units = int(df_prod["stock_quantity"].sum()) if "stock_quantity" in df_prod.columns else 0
        avg_price = float(df_prod["price"].mean()) if "price" in df_prod.columns else 0.0

        low_stock_threshold = 15
        low_stock_count = int((df_prod["stock_quantity"] < low_stock_threshold).sum()) if "stock_quantity" in df_prod.columns else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Catalog Products", f"{total_prods}")
        m2.metric("Total Stock In Hand", f"{total_units:,} units")
        m3.metric("Avg Product Price", ui_utils.format_inr(avg_price))
        m4.metric("Low Stock Items (<15)", f"{low_stock_count}", delta=f"-{low_stock_count}" if low_stock_count > 0 else "0", delta_color="inverse")

        st.markdown("---")

        # Visual stock breakdown
        if "category" in df_prod.columns and "stock_quantity" in df_prod.columns:
            fig_stock = px.bar(
                df_prod.groupby("category", as_index=False)["stock_quantity"].sum(),
                x="category",
                y="stock_quantity",
                color="category",
                labels={"category": "Category", "stock_quantity": "Units in Stock"},
                title="Stock Volume by Category",
            )
            fig_stock.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_stock, use_container_width=True)

        # Inventory Table
        st.subheader("Inventory Master Table")
        df_display = df_prod.copy()
        if "price" in df_display.columns:
            df_display["Unit Price"] = df_display["price"].apply(ui_utils.format_inr)
            df_display = df_display.drop(columns=["price"])

        df_display = df_display.rename(
            columns={
                "product_id": "Product ID",
                "product_name": "Product Name",
                "category": "Category",
                "stock_quantity": "Stock Quantity",
            }
        )

        st.dataframe(df_display, use_container_width=True, hide_index=True)

    else:
        st.info("No products found matching criteria.")

except Exception as e:
    st.error(f"Error fetching product inventory: {e}")
