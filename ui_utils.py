"""
ui_utils.py - Reusable UI components, Indian Rupee formatting, and styling helpers for Streamlit.
"""

from typing import Any, Dict, Optional, Tuple
import datetime
import streamlit as st
import db


def format_inr(number: float, include_symbol: bool = True) -> str:
    """
    Formats a numeric amount into Indian Rupee format with standard Indian numbering commas:
    Example: 1234567.89 -> ₹12,34,567.89
    """
    if number is None or pd_is_nan(number):
        return "₹0.00" if include_symbol else "0.00"

    sign = "-" if number < 0 else ""
    abs_num = abs(float(number))
    
    # Split into integer and decimal portions
    formatted_dec = f"{abs_num:.2f}"
    int_part, dec_part = formatted_dec.split(".")
    
    # Apply Indian grouping (last 3 digits, then groups of 2)
    if len(int_part) > 3:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        groups.append(last_three)
        int_part_formatted = ",".join(groups)
    else:
        int_part_formatted = int_part

    symbol = "₹ " if include_symbol else ""
    return f"{sign}{symbol}{int_part_formatted}.{dec_part}"


def pd_is_nan(val: Any) -> bool:
    try:
        import math
        return math.isnan(val)
    except Exception:
        return False


def apply_custom_theme():
    """
    Injects professional CSS styling for cards, metrics, and tables.
    """
    st.markdown(
        """
        <style>
        /* Modern Metric Card Styling */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
            border-color: rgba(255, 107, 74, 0.4);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: #8892b0 !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.65rem !important;
            font-weight: 700 !important;
            color: #f1f5f9 !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* Status Badge */
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-completed {
            background-color: rgba(46, 204, 113, 0.15);
            color: #2ecc71;
            border: 1px solid rgba(46, 204, 113, 0.3);
        }
        .status-pending {
            background-color: rgba(241, 196, 15, 0.15);
            color: #f1c40f;
            border: 1px solid rgba(241, 196, 15, 0.3);
        }
        .status-cancelled {
            background-color: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
            border: 1px solid rgba(231, 76, 60, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_connection_status():
    """
    Renders connection status badge and warehouse info in the sidebar.
    """
    with st.sidebar:
        st.markdown("### 🔌 Databricks Status")
        config = db.get_connection_config()
        is_valid, msg = db.validate_connection_config()

        if not is_valid:
            st.warning("⚠️ Connection details not configured in `.env`")
            with st.expander("Configuration Guide"):
                st.info(
                    "Please copy `.env.example` to `.env` and fill in:\n"
                    "- `DATABRICKS_SERVER_HOSTNAME`\n"
                    "- `DATABRICKS_HTTP_PATH`\n"
                    "- `DATABRICKS_TOKEN`"
                )
        else:
            masked_host = config["server_hostname"]
            st.success(f"Configured: `{masked_host}`")
            st.caption(f"Warehouse Path: `{config['http_path']}`")


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_filters() -> Dict[str, Any]:
    return db.get_filter_options()


def render_sidebar_filters() -> Dict[str, Any]:
    """
    Renders interactive filters in the sidebar:
    - Order date range
    - Region
    - Product Category
    - Order Status
    Returns selected filter values dictionary.
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔍 Filters")

        try:
            filter_data = _get_cached_filters()
        except Exception:
            filter_data = {
                "min_date": datetime.date(2023, 1, 1),
                "max_date": datetime.date.today(),
                "regions": [],
                "categories": [],
                "statuses": [],
            }

        # Date Range Filter
        min_date = filter_data.get("min_date") or datetime.date(2023, 1, 1)
        max_date = filter_data.get("max_date") or datetime.date.today()
        
        date_range = st.date_input(
            "Order Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filter analytics by order date range",
        )

        start_date = None
        end_date = None
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
        elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
            start_date = date_range[0]
            end_date = date_range[0]
        elif date_range:
            start_date = date_range
            end_date = date_range

        # Region Filter
        regions = ["All"] + filter_data.get("regions", [])
        selected_region = st.selectbox("Region", options=regions, index=0)

        # Product Category Filter
        categories = ["All"] + filter_data.get("categories", [])
        selected_category = st.selectbox("Product Category", options=categories, index=0)

        # Order Status Filter
        statuses = ["All"] + filter_data.get("statuses", [])
        selected_status = st.selectbox("Order Status", options=statuses, index=0)

        st.markdown("---")
        if st.button("Reset Filters", use_container_width=True):
            st.rerun()

        return {
            "start_date": start_date,
            "end_date": end_date,
            "region": None if selected_region == "All" else selected_region,
            "category": None if selected_category == "All" else selected_category,
            "status": None if selected_status == "All" else selected_status,
        }
