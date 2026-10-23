"""
test_connection.py - Utility to test Databricks connectivity and read table counts & schema.
Run this script to verify your .env settings before launching the Streamlit app.

Usage:
    python test_connection.py
"""

import sys
from db import (
    validate_connection_config,
    get_connection_config,
    test_connection_and_tables,
    inspect_schema,
    get_filter_options,
)


def main():
    print("=" * 60)
    print(" Databricks Sales Analytics - Connection Verification")
    print("=" * 60)

    # 1. Check .env configuration presence
    config = get_connection_config()
    is_valid, message = validate_connection_config()

    print(f"\n[1] Configuration Check:")
    print(f"    Server Hostname : {config['server_hostname'] or '[NOT SET]'}")
    print(f"    HTTP Path       : {config['http_path'] or '[NOT SET]'}")
    
    auth_method = "None"
    if config["token"]:
        masked = config["token"][:4] + "..." + config["token"][-4:] if len(config["token"]) > 8 else "***"
        auth_method = f"Personal Access Token ({masked})"
    elif config["auth_type"]:
        auth_method = f"OAuth ({config['auth_type']})"
    elif config["client_id"]:
        auth_method = "OAuth Service Principal (M2M)"
    print(f"    Authentication  : {auth_method}")

    if not is_valid:
        print(f"\n[!] Configuration Incomplete:")
        print(f"    {message}")
        print("\nPlease create a .env file based on .env.example with your Databricks settings.")
        sys.exit(1)

    print("\n[2] Testing SQL Warehouse Connectivity (read-only)...")
    res = test_connection_and_tables()

    if not res["success"]:
        print(f"\n[X] Connection Failed:")
        print(f"    {res['message']}")
        print("\nTroubleshooting tips:")
        print("  - Ensure your SQL Warehouse is RUNNING in Databricks (it may be stopped or auto-suspended).")
        print("  - Check that DATABRICKS_SERVER_HOSTNAME does NOT include 'https://' or path slashes.")
        print("  - Verify that your token has not expired and has SQL Warehouse permissions.")
        print("  - For Databricks Free / Community Edition, ensure table permissions allow SELECT.")
        sys.exit(1)

    print("\n[OK] Connected successfully to Databricks SQL Warehouse!")
    print("\n[3] Table Record Counts:")
    for tbl, count in res["table_counts"].items():
        print(f"    - {tbl:<15}: {count} rows")

    # 4. Inspect columns & statuses
    print("\n[4] Inspecting Table Schemas & Order Statuses...")
    try:
        schemas = inspect_schema()
        for tbl_name, df_cols in schemas.items():
            if "col_name" in df_cols.columns:
                cols = df_cols["col_name"].tolist()
                print(f"    Columns in {tbl_name}: {', '.join(cols[:10])}{'...' if len(cols) > 10 else ''}")

        filters = get_filter_options()
        print(f"\n[5] Filter Values Discovered:")
        print(f"    - Date Range   : {filters['min_date']} to {filters['max_date']}")
        print(f"    - Regions ({len(filters['regions'])}): {', '.join(filters['regions'][:5])}{'...' if len(filters['regions']) > 5 else ''}")
        print(f"    - Categories ({len(filters['categories'])}): {', '.join(filters['categories'][:5])}{'...' if len(filters['categories']) > 5 else ''}")
        print(f"    - Order Statuses: {', '.join(filters['statuses'])}")

    except Exception as e:
        print(f"    Notice: Schema inspection completed with notice: {e}")

    print("\n" + "=" * 60)
    print(" Ready to launch! Run: streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
