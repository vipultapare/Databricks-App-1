# Databricks Sales Analytics Dashboard 📊

A modular, production-ready Sales Analytics Dashboard built with **Streamlit**, **Databricks SQL Connector**, **Pandas**, and **Plotly**. Connects to your Databricks SQL Warehouse to analyze live sales data from Delta Lake tables.

---

## 1. Architecture & Data Sources

The dashboard queries existing tables in Databricks Free / Community Edition without altering or overwriting them:

| Entity | Fully Qualified Table Name | Purpose |
| :--- | :--- | :--- |
| **Orders** | `workspace.sales_demo.orders` | Transaction ledger, dates, order statuses, sales amounts |
| **Products** | `workspace.sales_demo.products` | Product catalog, pricing, stock levels |
| **Customers** | `workspace.sales_demo.customers` | Customer demographics, cities, regions |

---

## 2. Project Structure

```text
Databricks-APP-Study/
├── .env.example              # Template for Databricks credentials
├── .gitignore                # Protects secrets, cache, and virtual environments
├── requirements.txt          # Python dependencies
├── db.py                     # Databricks SQL connector & query execution module
├── ui_utils.py               # Shared Indian Rupee (₹) formatting & filter widgets
├── test_connection.py        # Read-only connectivity verification script
├── app.py                    # Main Executive Dashboard (KPIs & key charts)
├── README.md                 # Setup & deployment guide
└── pages/
    ├── 1_Sales_Overview.py   # Monthly trends & category/region breakdowns
    ├── 2_Orders.py           # Recent orders ledger, search, & CSV export
    ├── 3_Products.py         # Product inventory & stock levels
    └── 4_Customers.py        # Customer directory & demographics
```

---

## 3. How to Obtain Databricks Connection Details

To connect your local dashboard to your Databricks SQL Warehouse:

1. **Log in to Databricks**:
   - Open your Databricks workspace in the browser.
2. **Open SQL Warehouses**:
   - In the left sidebar, click **SQL Warehouses**.
   - Make sure your SQL Warehouse is **Running** (if stopped or paused, click **Start**).
3. **Find Connection Details**:
   - Click on your active SQL Warehouse name.
   - Click on the **Connection details** tab.
   - Note down:
     - **Server hostname**: (e.g., `community.cloud.databricks.com` or `adb-xxxxxxxx.xx.azuredatabricks.net`). *Do not include `https://` or trailing slashes.*
     - **HTTP path**: (e.g., `/sql/1.0/warehouses/a1b2c3d4e5f6g7h8`).
4. **Generate a Personal Access Token (PAT)**:
   - Click on your profile icon in the top right corner -> **Settings**.
   - Select **Developer** in the left sidebar.
   - Next to **Access tokens**, click **Manage** -> **Generate new token**.
   - Give it a comment (e.g., `Sales App Local`) and copy the generated token (`dapi...`).

---

## 4. Local Setup & Execution Guide

### Step 1: Clone or Navigate to the Project

```powershell
cd c:\POC\Databricks-APP-Study
```

### Step 2: Activate the Python Virtual Environment

If using the pre-configured `.venv`:
```powershell
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows Command Prompt (CMD):
.\.venv\Scripts\activate.bat
```

*(Or create a new environment if starting fresh)*:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```

Open `.env` and enter your details:
```ini
DATABRICKS_SERVER_HOSTNAME=your-databricks-instance.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your_personal_access_token
```

> **Alternative Authentication (OAuth U2M)**:
> If your organization uses SSO and allows browser login:
> ```ini
> DATABRICKS_SERVER_HOSTNAME=your-databricks-instance.cloud.databricks.com
> DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
> DATABRICKS_AUTH_TYPE=databricks-oauth
> ```

### Step 4: Verify Connection & Inspect Tables

Before starting the web server, test your connection and table access:
```powershell
python test_connection.py
```

This will run read-only queries (`SELECT COUNT(*)`) against:
- `workspace.sales_demo.customers`
- `workspace.sales_demo.products`
- `workspace.sales_demo.orders`

And display actual column schemas and distinct order statuses.

### Step 5: Launch the Streamlit App

```powershell
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 5. Local Authentication vs. Databricks App Authentication

| Aspect | Local Development | Databricks App (Deployed) |
| :--- | :--- | :--- |
| **Credentials Storage** | `.env` file on local filesystem (ignored by git) | Databricks App managed secrets & environment injection |
| **Authentication Type** | Personal Access Token (PAT) or interactive browser OAuth | Native App Identity / Service Principal OAuth headers |
| **Server Hostname** | Specified in `.env` | Automatically injected via `DATABRICKS_HOST` |
| **Network Path** | Public internet via HTTPS to Databricks REST API | Intra-workspace internal network route |

The database module [`db.py`](file:///c:/POC/Databricks-APP-Study/db.py) is intentionally designed to check both local variables (`DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_TOKEN`) and Databricks App native variables (`DATABRICKS_HOST`) without requiring code changes between environments.

---

## 6. Features & Highlights

- **Live Databricks SQL Queries**: Aggregates executed in SQL Warehouse for speed and scalability.
- **Indian Rupee Formatting (₹)**: Customized financial formatting across KPIs, charts, and tables.
- **Completed Sales Accuracy**: Correctly filters completed/delivered orders and excludes pending/cancelled orders.
- **Zero Double-Counting**: Careful primary-key joins between orders, customers, and products.
- **Interactive Multi-dimensional Filters**: Filter by order date range, region, category, and status.
- **Multi-page Architecture**: Dedicated pages for executive overview, transaction ledger, product catalog, and customer demographics.
