"""
pages/1_Sales_Overview.py - In-depth Sales Analytics & Category Breakdown
"""

import streamlit as st
import plotly.express as px
import db
import ui_utils

st.set_page_config(page_title="Sales Overview | Databricks Analytics", page_icon="📈", layout="wide")
ui_utils.apply_custom_theme()
ui_utils.render_sidebar_connection_status()
filters = ui_utils.render_sidebar_filters()

st.title("📈 Comprehensive Sales Overview")
st.caption("Detailed trend analysis, category contribution, and geographical distribution")

# Verify connection
is_valid, msg = db.validate_connection_config()
if not is_valid:
    st.error(f"⚠️ {msg}")
    st.stop()

# Load summary metrics
try:
    with st.spinner("Loading sales overview data..."):
        kpi = db.get_kpis(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        df_monthly = db.get_monthly_sales_trend(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        df_cat = db.get_sales_by_category(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        df_reg = db.get_sales_by_region(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )

    # Top summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Completed Sales", ui_utils.format_inr(kpi["total_sales"]))
    col2.metric("Completed Orders", f"{kpi['total_orders']:,}")
    col3.metric("Average Order Value (AOV)", ui_utils.format_inr(kpi["average_order_value"]))

    st.markdown("---")

    # Monthly Trend Area Chart
    st.subheader("Revenue Timeline")
    if not df_monthly.empty:
        fig_timeline = px.area(
            df_monthly,
            x="month_label",
            y="total_sales",
            markers=True,
            labels={"month_label": "Month", "total_sales": "Sales (₹)"},
            title="Monthly Sales Progression",
        )
        fig_timeline.update_traces(
            line_color="#2E7D32",
            hovertemplate="<b>Month</b>: %{x}<br><b>Sales</b>: ₹%{y:,.2f}<extra></extra>",
        )
        fig_timeline.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("No monthly data matches the selected criteria.")

    # Two column breakdown
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Revenue by Category")
        if not df_cat.empty:
            df_cat_display = df_cat.copy()
            df_cat_display["Formatted Sales"] = df_cat_display["total_sales"].apply(ui_utils.format_inr)
            st.dataframe(
                df_cat_display[["category", "order_count", "Formatted Sales"]].rename(
                    columns={"category": "Category", "order_count": "Orders"}
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No category data.")

    with c2:
        st.subheader("Revenue by Region")
        if not df_reg.empty:
            df_reg_display = df_reg.copy()
            df_reg_display["Formatted Sales"] = df_reg_display["total_sales"].apply(ui_utils.format_inr)
            st.dataframe(
                df_reg_display[["region", "order_count", "Formatted Sales"]].rename(
                    columns={"region": "Region", "order_count": "Orders"}
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No regional data.")

except Exception as e:
    st.error(f"Error loading sales overview: {e}")
