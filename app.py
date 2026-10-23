"""
app.py - Databricks Sales Analytics Dashboard
Main entry point for local execution and Databricks App deployment.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import db
import ui_utils

# Streamlit Page Configuration
st.set_page_config(
    page_title="Databricks Sales Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply sleek styling
ui_utils.apply_custom_theme()

# Sidebar: Connection Info & Interactive Filters
ui_utils.render_sidebar_connection_status()
filters = ui_utils.render_sidebar_filters()

# Main Header
st.title("📊 Databricks Sales Analytics Dashboard")
st.caption("Real-time intelligence powered by Databricks SQL Warehouse & Delta Lake")

# Quick connection validation check
is_valid, error_msg = db.validate_connection_config()
if not is_valid:
    st.error(f"⚠️ **Databricks Connection Not Configured**: {error_msg}")
    st.markdown(
        """
        ### Quick Setup Steps:
        1. Open the project folder and copy `.env.example` to `.env`.
        2. Set your Databricks SQL Warehouse Server Hostname, HTTP Path, and Personal Access Token (PAT).
        3. Test your connection in terminal using `python test_connection.py`.
        4. Refresh this dashboard!
        """
    )
    st.stop()

# -------------------------------------------------------------
# 1. KPI Cards
# -------------------------------------------------------------
st.markdown("### 📈 Key Performance Indicators")

try:
    with st.spinner("Fetching latest sales metrics from Databricks..."):
        kpi_data = db.get_kpis(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        st.metric(
            label="Total Sales (Completed)",
            value=ui_utils.format_inr(kpi_data["total_sales"]),
            help="Sum of sales_amount for completed and delivered orders",
        )

    with kpi2:
        st.metric(
            label="Total Orders",
            value=f"{kpi_data['total_orders']:,}",
            help="Count of successfully completed orders",
        )

    with kpi3:
        st.metric(
            label="Total Customers",
            value=f"{kpi_data['total_customers']:,}",
            help="Total registered customer catalog count",
        )

    with kpi4:
        st.metric(
            label="Total Products",
            value=f"{kpi_data['total_products']:,}",
            help="Total active products in catalog",
        )

    with kpi5:
        st.metric(
            label="Avg Order Value (AOV)",
            value=ui_utils.format_inr(kpi_data["average_order_value"]),
            help="Completed Sales divided by Completed Orders",
        )

except Exception as e:
    st.error(f"Unable to load KPIs from Databricks SQL: {e}")
    st.stop()

st.markdown("---")

# -------------------------------------------------------------
# 2. Charts & Analytics
# -------------------------------------------------------------
st.markdown("### 📊 Sales Performance & Visualizations")

chart_row1_col1, chart_row1_col2 = st.columns([3, 2])

# Visualization 1: Monthly Sales Trend
with chart_row1_col1:
    st.subheader("Monthly Sales Trend")
    try:
        df_monthly = db.get_monthly_sales_trend(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        if not df_monthly.empty:
            fig_trend = px.line(
                df_monthly,
                x="month_label",
                y="total_sales",
                markers=True,
                labels={"month_label": "Month", "total_sales": "Sales (₹)"},
                title="Revenue Over Time (Completed Orders)",
            )
            fig_trend.update_traces(
                line_color="#FF3621",
                marker=dict(size=8, color="#FF3621"),
                hovertemplate="<b>Month</b>: %{x}<br><b>Sales</b>: ₹%{y:,.2f}<extra></extra>",
            )
            fig_trend.update_layout(
                xaxis_title="Month",
                yaxis_title="Total Sales (₹)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No sales trend data available for the selected filters.")
    except Exception as e:
        st.error(f"Failed to load monthly trend: {e}")

# Visualization 2: Order Status Distribution
with chart_row1_col2:
    st.subheader("Order Status Distribution")
    try:
        df_status = db.get_order_status_distribution(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        if not df_status.empty:
            fig_status = px.pie(
                df_status,
                names="order_status",
                values="order_count",
                hole=0.45,
                title="Orders by Status",
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_status.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Orders: %{value}<br>Share: %{percent}<extra></extra>",
            )
            fig_status.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No order status data available.")
    except Exception as e:
        st.error(f"Failed to load status distribution: {e}")

chart_row2_col1, chart_row2_col2, chart_row2_col3 = st.columns(3)

# Visualization 3: Sales by Product Category
with chart_row2_col1:
    st.subheader("Sales by Category")
    try:
        df_cat = db.get_sales_by_category(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        if not df_cat.empty:
            fig_cat = px.bar(
                df_cat,
                x="category",
                y="total_sales",
                color="category",
                labels={"category": "Category", "total_sales": "Sales (₹)"},
                title="Revenue by Category",
            )
            fig_cat.update_traces(
                hovertemplate="<b>%{x}</b><br>Sales: ₹%{y:,.2f}<extra></extra>"
            )
            fig_cat.update_layout(
                showlegend=False,
                xaxis_title="Category",
                yaxis_title="Sales (₹)",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No category sales data found.")
    except Exception as e:
        st.error(f"Failed to load category sales: {e}")

# Visualization 4: Top 5 Products by Sales
with chart_row2_col2:
    st.subheader("Top 5 Products")
    try:
        df_top = db.get_top_products(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
            limit=5,
        )
        if not df_top.empty:
            fig_top = px.bar(
                df_top.sort_values(by="total_sales", ascending=True),
                x="total_sales",
                y="product_name",
                orientation="h",
                color="total_sales",
                color_continuous_scale="Viridis",
                labels={"total_sales": "Sales (₹)", "product_name": "Product"},
                title="Top 5 Products by Revenue",
            )
            fig_top.update_traces(
                hovertemplate="<b>%{y}</b><br>Sales: ₹%{x:,.2f}<extra></extra>"
            )
            fig_top.update_layout(
                coloraxis_showscale=False,
                xaxis_title="Sales (₹)",
                yaxis_title="",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("No top product data found.")
    except Exception as e:
        st.error(f"Failed to load top products: {e}")

# Visualization 5: Sales by Region
with chart_row2_col3:
    st.subheader("Sales by Region")
    try:
        df_region = db.get_sales_by_region(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            region=filters["region"],
            category=filters["category"],
            status=filters["status"],
        )
        if not df_region.empty:
            fig_reg = px.bar(
                df_region,
                x="region",
                y="total_sales",
                color="region",
                labels={"region": "Region", "total_sales": "Sales (₹)"},
                title="Revenue by Region",
            )
            fig_reg.update_traces(
                hovertemplate="<b>%{x}</b><br>Sales: ₹%{y:,.2f}<extra></extra>"
            )
            fig_reg.update_layout(
                showlegend=False,
                xaxis_title="Region",
                yaxis_title="Sales (₹)",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("No region data found.")
    except Exception as e:
        st.error(f"Failed to load regional sales: {e}")

st.markdown("---")

# Quick link preview to detail pages
st.info("💡 Use the left sidebar to navigate to **Detailed Orders**, **Product Inventory**, and **Customer Directory**.")
