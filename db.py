"""
db.py - Databricks SQL Warehouse Connectivity & Query Module
Handles secure connection, query execution, and data retrieval for the Sales Analytics Dashboard.
"""

import os
import threading
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from dotenv import load_dotenv

# Lock to prevent concurrent OAuth authorization handshakes
_connection_lock = threading.Lock()

# Load environment variables from .env file (if present)
load_dotenv()

# Fully Qualified Table Names as defined in Databricks Free Edition
TABLE_CUSTOMERS = os.getenv(
    "CUSTOMERS_TABLE", "workspace.sales_demo.customers"
)
TABLE_PRODUCTS = os.getenv(
    "PRODUCTS_TABLE", "workspace.sales_demo.products"
)
TABLE_ORDERS = os.getenv(
    "ORDERS_TABLE", "workspace.sales_demo.orders"
)



def get_connection_config() -> Dict[str, Any]:
    """Read Databricks SQL connection settings without exposing credentials."""

    server_hostname = (
        os.getenv("DATABRICKS_SERVER_HOSTNAME")
        or os.getenv("DATABRICKS_HOST")
        or ""
    ).strip()

    server_hostname = (
        server_hostname
        .replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
    )

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "").strip()
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "").strip()

    # Databricks Apps provides the warehouse ID as a resource.
    if warehouse_id:
        http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    token = (
        os.getenv("DATABRICKS_TOKEN")
        or os.getenv("DATABRICKS_ACCESS_TOKEN")
        or ""
    ).strip()

    if token.startswith("your_") or "token_here" in token:
        token = ""

    auth_type = os.getenv("DATABRICKS_AUTH_TYPE", "").strip()
    client_id = os.getenv("DATABRICKS_CLIENT_ID", "").strip()
    client_secret = os.getenv("DATABRICKS_CLIENT_SECRET", "").strip()

    return {
        "server_hostname": server_hostname,
        "http_path": http_path,
        "warehouse_id": warehouse_id,
        "token": token,
        "auth_type": auth_type,
        "client_id": client_id,
        "client_secret": client_secret,
        "is_databricks_app": bool(warehouse_id),
    }




def validate_connection_config() -> Tuple[bool, str]:
    config = get_connection_config()

    if not config["server_hostname"]:
        return False, "Missing Databricks workspace hostname."

    if not config["http_path"]:
        return False, "Missing DATABRICKS_HTTP_PATH or DATABRICKS_WAREHOUSE_ID."

    has_token = bool(config["token"])
    has_oauth_u2m = config["auth_type"].lower() == "databricks-oauth"
    has_m2m = bool(config["client_id"] and config["client_secret"])

    if not (has_token or has_oauth_u2m or has_m2m):
        return False, "No supported Databricks authentication method configured."

    return True, "Configuration present"




def get_connection():
    """Connect using app identity in Databricks Apps or OAuth locally."""
    from databricks import sql

    is_valid, error_msg = validate_connection_config()
    if not is_valid:
        raise ValueError(error_msg)

    config = get_connection_config()

    connect_args: Dict[str, Any] = {
        "server_hostname": config["server_hostname"],
        "http_path": config["http_path"],
    }

    if config.get("is_databricks_app"):
        # Use the deployed app's service-principal identity.
        from databricks.sdk.core import Config

        sdk_config = Config()

        if not sdk_config.host:
            raise ValueError(
                "Databricks workspace host is unavailable in the app environment."
            )

        connect_args["server_hostname"] = (
            sdk_config.host.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )
        connect_args["credentials_provider"] = lambda: sdk_config.authenticate

    elif config["auth_type"].lower() == "databricks-oauth":
        # Keep interactive OAuth for local development.
        connect_args["auth_type"] = "databricks-oauth"

        try:
            from databricks.sql.experimental.oauth_persistence import (
                DevOnlyFilePersistence,
            )

            cache_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                ".databricks_oauth_cache.json",
            )
            connect_args["experimental_oauth_persistence"] = (
                DevOnlyFilePersistence(cache_file)
            )
        except Exception:
            pass

    elif config["client_id"] and config["client_secret"]:
        connect_args["client_id"] = config["client_id"]
        connect_args["client_secret"] = config["client_secret"]

    elif config["token"]:
        connect_args["access_token"] = config["token"]

    else:
        raise ValueError(
            "Could not determine Databricks authentication mechanism."
        )

    with _connection_lock:
        return sql.connect(**connect_args)


def run_query(query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Executes a read-only SQL query against Databricks SQL Warehouse and returns a Pandas DataFrame.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Attempt to use pyarrow/pandas fast conversion if supported
        try:
            df = cursor.fetchall_arrow().to_pandas()
        except Exception:
            # Fallback to standard cursor fetch
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            df = pd.DataFrame(rows, columns=cols)

        # Standardize column names to lowercase for consistency
        df.columns = [col.lower() for col in df.columns]
        return df

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def test_connection_and_tables() -> Dict[str, Any]:
    """
    Verifies connection and retrieves record counts for the 3 sales demo tables.
    Read-only test without modifying source tables.
    """
    result: Dict[str, Any] = {
        "success": False,
        "message": "",
        "table_counts": {},
        "server_hostname": "",
        "http_path": "",
    }

    is_valid, validation_msg = validate_connection_config()
    config = get_connection_config()
    result["server_hostname"] = config["server_hostname"]
    result["http_path"] = config["http_path"]

    if not is_valid:
        result["message"] = validation_msg
        return result

    try:
        # Check basic query connectivity
        run_query("SELECT 1 AS connection_test")

        # Query counts for each table
        tables = [
            ("customers", TABLE_CUSTOMERS),
            ("products", TABLE_PRODUCTS),
            ("orders", TABLE_ORDERS),
        ]

        counts = {}
        for alias, table_name in tables:
            try:
                df = run_query(f"SELECT COUNT(*) AS total_count FROM {table_name}")
                counts[alias] = int(df.iloc[0]["total_count"]) if not df.empty else 0
            except Exception as e:
                counts[alias] = f"Error: {str(e)}"

        result["success"] = True
        result["message"] = "Connected successfully to Databricks SQL Warehouse."
        result["table_counts"] = counts

    except Exception as e:
        result["success"] = False
        result["message"] = f"Connection failed: {str(e)}"

    return result


def inspect_schema() -> Dict[str, pd.DataFrame]:
    """
    Inspects and returns the column schema for each table using DESCRIBE.
    """
    tables = {
        "customers": TABLE_CUSTOMERS,
        "products": TABLE_PRODUCTS,
        "orders": TABLE_ORDERS,
    }
    schemas = {}
    for name, tbl in tables.items():
        try:
            schemas[name] = run_query(f"DESCRIBE {tbl}")
        except Exception as e:
            schemas[name] = pd.DataFrame({"error": [str(e)]})
    return schemas


def get_filter_options() -> Dict[str, Any]:
    """
    Fetches available filter values directly from the database tables:
    - Min and Max order dates
    - Unique regions
    - Unique product categories
    - Unique order statuses
    """
    date_query = f"""
        SELECT 
            MIN(order_date) AS min_date,
            MAX(order_date) AS max_date
        FROM {TABLE_ORDERS}
        WHERE order_date IS NOT NULL
    """
    
    region_query = f"""
        SELECT DISTINCT region 
        FROM {TABLE_CUSTOMERS} 
        WHERE region IS NOT NULL AND TRIM(region) != ''
        ORDER BY region
    """

    category_query = f"""
        SELECT DISTINCT category 
        FROM {TABLE_PRODUCTS} 
        WHERE category IS NOT NULL AND TRIM(category) != ''
        ORDER BY category
    """

    status_query = f"""
        SELECT DISTINCT order_status 
        FROM {TABLE_ORDERS} 
        WHERE order_status IS NOT NULL AND TRIM(order_status) != ''
        ORDER BY order_status
    """

    min_date = None
    max_date = None
    regions: List[str] = []
    categories: List[str] = []
    statuses: List[str] = []

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Date range
        try:
            cursor.execute(date_query)
            rows = cursor.fetchall()
            if rows and rows[0][0] is not None:
                min_date = pd.to_datetime(rows[0][0]).date()
                max_date = pd.to_datetime(rows[0][1]).date()
        except Exception:
            pass

        # 2. Regions
        try:
            cursor.execute(region_query)
            rows = cursor.fetchall()
            regions = [str(r[0]) for r in rows if r and r[0]]
        except Exception:
            pass

        # 3. Categories
        try:
            cursor.execute(category_query)
            rows = cursor.fetchall()
            categories = [str(r[0]) for r in rows if r and r[0]]
        except Exception:
            pass

        # 4. Statuses
        try:
            cursor.execute(status_query)
            rows = cursor.fetchall()
            statuses = [str(r[0]) for r in rows if r and r[0]]
        except Exception:
            pass

    except Exception:
        pass
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return {
        "min_date": min_date,
        "max_date": max_date,
        "regions": regions,
        "categories": categories,
        "statuses": statuses,
    }


def _build_where_clause(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    date_col: str = "o.order_date",
    region_col: str = "c.region",
    category_col: str = "p.category",
    status_col: str = "o.order_status",
) -> Tuple[str, Dict[str, Any]]:
    """
    Builds SQL WHERE clause and parameter dictionary safely.
    """
    conditions = []
    params: Dict[str, Any] = {}

    if start_date:
        conditions.append(f"{date_col} >= :start_date")
        params["start_date"] = str(start_date)

    if end_date:
        conditions.append(f"{date_col} <= :end_date")
        params["end_date"] = str(end_date)

    if region and region != "All":
        conditions.append(f"{region_col} = :region")
        params["region"] = region

    if category and category != "All":
        conditions.append(f"{category_col} = :category")
        params["category"] = category

    if status and status != "All":
        conditions.append(f"{status_col} = :status")
        params["status"] = status

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_sql, params


def get_kpis(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculates primary KPI metrics:
    1. Total Sales — sum of sales_amount for completed orders only.
    2. Total Orders — count of completed orders.
    3. Total Customers — count of customers.
    4. Total Products — count of products.
    5. Average Order Value — completed sales divided by completed order count.
    
    Completed order definition: order_status ILIKE '%complete%' OR order_status ILIKE '%delivered%'
    (excluding pending, cancelled, returned).
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    # Condition specifically identifying completed orders
    completed_condition = "(LOWER(o.order_status) IN ('completed', 'complete', 'delivered') OR LOWER(o.order_status) NOT IN ('pending', 'cancelled', 'canceled', 'returned', 'refunded'))"

    query = f"""
        SELECT
            COALESCE(SUM(CASE WHEN {completed_condition} THEN o.sales_amount ELSE 0 END), 0) AS total_sales,
            COALESCE(COUNT(DISTINCT CASE WHEN {completed_condition} THEN o.order_id END), 0) AS total_orders,
            COUNT(DISTINCT o.order_id) AS total_all_orders,
            COUNT(DISTINCT o.customer_id) AS filtered_customers,
            COUNT(DISTINCT o.product_id) AS filtered_products
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql}
    """

    df = run_query(query, params)

    # Also retrieve catalog-wide customer and product counts
    total_cust_df = run_query(f"SELECT COUNT(*) AS cnt FROM {TABLE_CUSTOMERS}")
    total_prod_df = run_query(f"SELECT COUNT(*) AS cnt FROM {TABLE_PRODUCTS}")

    total_customers_catalog = int(total_cust_df.iloc[0]["cnt"]) if not total_cust_df.empty else 0
    total_products_catalog = int(total_prod_df.iloc[0]["cnt"]) if not total_prod_df.empty else 0

    if not df.empty:
        total_sales = float(df.iloc[0]["total_sales"])
        total_orders = int(df.iloc[0]["total_orders"])
        aov = (total_sales / total_orders) if total_orders > 0 else 0.0
        return {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "total_customers": total_customers_catalog,
            "total_products": total_products_catalog,
            "average_order_value": aov,
            "filtered_customers": int(df.iloc[0]["filtered_customers"]),
            "filtered_products": int(df.iloc[0]["filtered_products"]),
        }

    return {
        "total_sales": 0.0,
        "total_orders": 0,
        "total_customers": total_customers_catalog,
        "total_products": total_products_catalog,
        "average_order_value": 0.0,
        "filtered_customers": 0,
        "filtered_products": 0,
    }


def get_monthly_sales_trend(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns monthly aggregated sales for completed orders.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    completed_condition = "(LOWER(o.order_status) IN ('completed', 'complete', 'delivered') OR LOWER(o.order_status) NOT IN ('pending', 'cancelled', 'canceled', 'returned', 'refunded'))"
    extra_filter = f" AND {completed_condition}" if where_sql else f"WHERE {completed_condition}"

    query = f"""
        SELECT 
            DATE_TRUNC('month', CAST(o.order_date AS DATE)) AS month_date,
            DATE_FORMAT(CAST(o.order_date AS DATE), 'yyyy-MM') AS month_label,
            COALESCE(SUM(o.sales_amount), 0) AS total_sales,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql} {extra_filter}
        GROUP BY 1, 2
        ORDER BY month_date ASC
    """
    return run_query(query, params)


def get_sales_by_category(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns sales aggregated by product category for completed orders.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    completed_condition = "(LOWER(o.order_status) IN ('completed', 'complete', 'delivered') OR LOWER(o.order_status) NOT IN ('pending', 'cancelled', 'canceled', 'returned', 'refunded'))"
    extra_filter = f" AND {completed_condition}" if where_sql else f"WHERE {completed_condition}"

    query = f"""
        SELECT 
            COALESCE(p.category, 'Uncategorized') AS category,
            COALESCE(SUM(o.sales_amount), 0) AS total_sales,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql} {extra_filter}
        GROUP BY 1
        ORDER BY total_sales DESC
    """
    return run_query(query, params)


def get_top_products(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 5,
) -> pd.DataFrame:
    """
    Returns the top products ranked by sales amount.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    completed_condition = "(LOWER(o.order_status) IN ('completed', 'complete', 'delivered') OR LOWER(o.order_status) NOT IN ('pending', 'cancelled', 'canceled', 'returned', 'refunded'))"
    extra_filter = f" AND {completed_condition}" if where_sql else f"WHERE {completed_condition}"

    query = f"""
        SELECT 
            p.product_name,
            COALESCE(p.category, 'Unknown') AS category,
            COALESCE(SUM(o.sales_amount), 0) AS total_sales,
            COALESCE(SUM(o.quantity), COUNT(o.order_id)) AS units_sold,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql} {extra_filter}
        GROUP BY 1, 2
        ORDER BY total_sales DESC
        LIMIT {limit}
    """
    return run_query(query, params)


def get_sales_by_region(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns sales aggregated by customer region for completed orders.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    completed_condition = "(LOWER(o.order_status) IN ('completed', 'complete', 'delivered') OR LOWER(o.order_status) NOT IN ('pending', 'cancelled', 'canceled', 'returned', 'refunded'))"
    extra_filter = f" AND {completed_condition}" if where_sql else f"WHERE {completed_condition}"

    query = f"""
        SELECT 
            COALESCE(c.region, 'Unknown') AS region,
            COALESCE(SUM(o.sales_amount), 0) AS total_sales,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql} {extra_filter}
        GROUP BY 1
        ORDER BY total_sales DESC
    """
    return run_query(query, params)


def get_order_status_distribution(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns counts and total value by order status.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    query = f"""
        SELECT 
            COALESCE(o.order_status, 'Unknown') AS order_status,
            COUNT(DISTINCT o.order_id) AS order_count,
            COALESCE(SUM(o.sales_amount), 0) AS total_sales
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql}
        GROUP BY 1
        ORDER BY order_count DESC
    """
    return run_query(query, params)


def get_recent_orders(
    start_date=None,
    end_date=None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Returns recent orders with customer name and product name joined without double-counting.
    """
    where_sql, params = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        region=region,
        category=category,
        status=status,
    )

    query = f"""
        SELECT 
            o.order_id,
            o.order_date,
            c.customer_name,
            c.city,
            c.region,
            p.product_name,
            p.category,
            o.quantity,
            o.sales_amount,
            o.order_status
        FROM {TABLE_ORDERS} o
        LEFT JOIN {TABLE_CUSTOMERS} c ON o.customer_id = c.customer_id
        LEFT JOIN {TABLE_PRODUCTS} p ON o.product_id = p.product_id
        {where_sql}
        ORDER BY o.order_date DESC, o.order_id DESC
        LIMIT {limit}
    """
    return run_query(query, params)


def get_product_inventory(category: Optional[str] = None) -> pd.DataFrame:
    """
    Returns product catalog inventory with stock quantities.
    """
    conditions = []
    params: Dict[str, Any] = {}

    if category and category != "All":
        conditions.append("category = :category")
        params["category"] = category

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT 
            product_id,
            product_name,
            category,
            price,
            stock_quantity
        FROM {TABLE_PRODUCTS}
        {where_sql}
        ORDER BY product_name ASC
    """
    return run_query(query, params)


def get_customers(region: Optional[str] = None) -> pd.DataFrame:
    """
    Returns customer list with city and region.
    """
    conditions = []
    params: Dict[str, Any] = {}

    if region and region != "All":
        conditions.append("region = :region")
        params["region"] = region

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT 
            customer_id,
            customer_name,
            email,
            city,
            region
        FROM {TABLE_CUSTOMERS}
        {where_sql}
        ORDER BY customer_name ASC
    """
    return run_query(query, params)
