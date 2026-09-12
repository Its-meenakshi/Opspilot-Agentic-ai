from fastapi import FastAPI

from tools.sales_tool import get_sales_summary
from tools.inventory_tool import get_inventory_summary
from tools.finance_tool import get_finance_summary
from tools.supplier_tool import get_supplier_summary

# Create the FastAPI application instance.
# This "app" object is what Uvicorn runs when starting the server.
app = FastAPI(title="OpsPilot Backend")


@app.get("/")
def read_root():
    """
    Health/home endpoint.
    Visiting this URL confirms the OpsPilot backend is up and running.
    """
    return {"status": "ok", "message": "OpsPilot backend is running"}


@app.get("/tools/sales")
def sales_tool_endpoint():
    """
    Test endpoint for the Sales Data Tool.
    Reads data/sales.csv and returns totals, date range, and
    per-product performance for an AI agent to analyze later.
    """
    return get_sales_summary()


@app.get("/tools/inventory")
def inventory_tool_endpoint():
    """
    Test endpoint for the Inventory Data Tool.
    Reads data/inventory.csv and returns stock levels, reorder
    thresholds, and low-stock items for an AI agent to analyze later.
    """
    return get_inventory_summary()


@app.get("/tools/finance")
def finance_tool_endpoint():
    """
    Test endpoint for the Finance Data Tool.
    Reads data/expenses.csv and returns total expenses, date range,
    and category breakdowns for an AI agent to analyze later.
    """
    return get_finance_summary()


@app.get("/tools/suppliers")
def supplier_tool_endpoint():
    """
    Test endpoint for the Supplier Data Tool.
    Reads data/suppliers.csv (cross-referenced with data/products.csv)
    and returns pricing, price changes, lead times, and which products
    each supplier feeds, for an AI agent to analyze later.
    """
    return get_supplier_summary()