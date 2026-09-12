"""
Sales Data Tool
----------------
Reads data/sales.csv and returns structured sales information
(totals, date range, and per-product performance) that an AI agent
can later analyze and reason about.

This module intentionally exposes RAW DATA ONLY. It does not decide
which product is "best", "worst", or what action to take — that
judgment belongs to the AI agent that will consume this data later.

Design note: every future tool (inventory_tool, finance_tool,
supplier_tool, customer_tool) should follow this same pattern:
  1. A `load_<name>_data()` function that reads and validates the CSV.
  2. A `get_<name>_summary()` function that aggregates the data into
     a clean dict, handling missing/invalid data gracefully.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

def _find_data_file(filename: str, start: Path, max_levels_up: int = 6) -> Path:
    """
    Searches upward from `start` (this file's own folder) for a `data/<filename>`
    directory, checking each ancestor folder in turn.

    This makes the lookup robust to how deeply nested this tools/ folder is
    inside the project (e.g. backend/tools/ vs backend/backend/tools/), and
    to the terminal's current working directory, since it is based entirely
    on this file's own location on disk rather than on cwd or a fixed
    parent-count guess.

    If nothing is found, falls back to the best-guess default (3 levels up,
    the original assumption) so the resulting "file not found" error message
    still points somewhere sensible.
    """
    current = start
    for _ in range(max_levels_up):
        candidate = current / "data" / filename
        if candidate.exists():
            return candidate
        if current.parent == current:  # reached filesystem root
            break
        current = current.parent

    # Fallback: preserve prior default guess for a clear error message
    return start.parent.parent / "data" / filename


# Resolved once at import time by walking up from this file's location
# until a real data/sales.csv is found (or falling back to a default guess).
DEFAULT_SALES_CSV_PATH = _find_data_file("sales.csv", Path(__file__).resolve().parent)

REQUIRED_COLUMNS = {"date", "product_id", "product_name", "quantity_sold", "unit_price", "revenue"}


def load_sales_rows(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Reads the sales CSV and returns validated rows plus any issues found.

    Never raises on bad data — missing file, missing columns, or
    unreadable rows are reported back instead of crashing the caller.
    """
    path = Path(file_path) if file_path else DEFAULT_SALES_CSV_PATH

    if not path.exists():
        return {
            "ok": False,
            "error": f"Sales data file not found at: {path}",
            "rows": [],
            "skipped_rows": 0,
            "row_errors": [],
        }

    rows: List[Dict[str, Any]] = []
    row_errors: List[str] = []
    skipped_rows = 0

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
                missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
                return {
                    "ok": False,
                    "error": f"CSV is missing required column(s): {sorted(missing)}",
                    "rows": [],
                    "skipped_rows": 0,
                    "row_errors": [],
                }

            for i, raw_row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    quantity_sold = int(raw_row["quantity_sold"])
                    unit_price = float(raw_row["unit_price"])
                    revenue = float(raw_row["revenue"])
                    date_value = raw_row["date"].strip()
                    product_id = raw_row["product_id"].strip()
                    product_name = raw_row["product_name"].strip()

                    if not date_value or not product_id or not product_name:
                        raise ValueError("empty required field")
                    if quantity_sold < 0 or unit_price < 0 or revenue < 0:
                        raise ValueError("negative value not allowed")

                    rows.append({
                        "date": date_value,
                        "product_id": product_id,
                        "product_name": product_name,
                        "quantity_sold": quantity_sold,
                        "unit_price": unit_price,
                        "revenue": revenue,
                    })
                except (ValueError, KeyError, AttributeError) as e:
                    skipped_rows += 1
                    row_errors.append(f"Row {i}: skipped ({e})")

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read sales data: {e}",
            "rows": [],
            "skipped_rows": 0,
            "row_errors": [],
        }

    return {
        "ok": True,
        "error": None,
        "rows": rows,
        "skipped_rows": skipped_rows,
        "row_errors": row_errors,
    }


def get_sales_summary(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns an aggregated summary of sales data:
      - total revenue, total units sold, total transaction records
      - date range covered
      - per-product performance (units sold, revenue, avg unit price, transaction count)
      - any data-quality issues encountered while reading the file

    This is pure data aggregation. No rankings, labels, or recommendations
    are included — the calling agent decides what the numbers mean.
    """
    loaded = load_sales_rows(file_path)

    if not loaded["ok"]:
        return {
            "status": "error",
            "message": loaded["error"],
            "summary": None,
        }

    rows = loaded["rows"]

    if not rows:
        return {
            "status": "empty",
            "message": "Sales file was read but contained no valid rows.",
            "summary": None,
            "skipped_rows": loaded["skipped_rows"],
            "row_errors": loaded["row_errors"],
        }

    total_revenue = round(sum(r["revenue"] for r in rows), 2)
    total_units_sold = sum(r["quantity_sold"] for r in rows)
    total_records = len(rows)
    dates = sorted(r["date"] for r in rows)

    product_performance: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        pid = r["product_id"]
        if pid not in product_performance:
            product_performance[pid] = {
                "product_id": pid,
                "product_name": r["product_name"],
                "units_sold": 0,
                "revenue": 0.0,
                "transaction_count": 0,
            }
        entry = product_performance[pid]
        entry["units_sold"] += r["quantity_sold"]
        entry["revenue"] += r["revenue"]
        entry["transaction_count"] += 1

    # round + add average unit price per product (revenue / units), guarding divide-by-zero
    for entry in product_performance.values():
        entry["revenue"] = round(entry["revenue"], 2)
        entry["avg_unit_price"] = (
            round(entry["revenue"] / entry["units_sold"], 2) if entry["units_sold"] > 0 else 0.0
        )

    return {
        "status": "ok",
        "message": None,
        "summary": {
            "total_revenue": total_revenue,
            "total_units_sold": total_units_sold,
            "total_records": total_records,
            "date_range": {"start": dates[0], "end": dates[-1]},
            "product_performance": list(product_performance.values()),
        },
        "skipped_rows": loaded["skipped_rows"],
        "row_errors": loaded["row_errors"],
    }