"""
Inventory Data Tool
--------------------
Reads data/inventory.csv and returns structured inventory information
(current stock, reorder levels, low-stock items, waste) that an AI
agent can later analyze and reason about.

Follows the same pattern as tools/sales_tool.py:
  1. A `load_inventory_rows()` function that reads and validates the CSV.
  2. A `get_inventory_summary()` function that aggregates the data into
     a clean dict, handling missing/invalid data gracefully.

This module exposes RAW DATA and CALCULATED METRICS ONLY. It does not
decide what action to take (e.g. "reorder now") — that judgment
belongs to the AI agent that will consume this data later.
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
# until a real data/inventory.csv is found (or falling back to a default guess).
DEFAULT_INVENTORY_CSV_PATH = _find_data_file("inventory.csv", Path(__file__).resolve().parent)

REQUIRED_COLUMNS = {
    "product_id", "current_stock", "reorder_level",
    "avg_daily_usage", "days_of_stock_left", "waste_units_last_30_days",
}


def load_inventory_rows(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Reads the inventory CSV and returns validated rows plus any issues found.

    Never raises on bad data — missing file, missing columns, or
    unreadable rows are reported back instead of crashing the caller.
    """
    path = Path(file_path) if file_path else DEFAULT_INVENTORY_CSV_PATH

    if not path.exists():
        return {
            "ok": False,
            "error": f"Inventory data file not found at: {path}",
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
                    product_id = raw_row["product_id"].strip()
                    current_stock = float(raw_row["current_stock"])
                    reorder_level = float(raw_row["reorder_level"])
                    avg_daily_usage = float(raw_row["avg_daily_usage"])
                    days_of_stock_left = float(raw_row["days_of_stock_left"])
                    waste_units_last_30_days = float(raw_row["waste_units_last_30_days"])

                    if not product_id:
                        raise ValueError("empty product_id")
                    if current_stock < 0 or reorder_level < 0 or avg_daily_usage < 0 or waste_units_last_30_days < 0:
                        raise ValueError("negative value not allowed")

                    rows.append({
                        "product_id": product_id,
                        "current_stock": current_stock,
                        "reorder_level": reorder_level,
                        "avg_daily_usage": avg_daily_usage,
                        "days_of_stock_left": days_of_stock_left,
                        "waste_units_last_30_days": waste_units_last_30_days,
                    })
                except (ValueError, KeyError, AttributeError) as e:
                    skipped_rows += 1
                    row_errors.append(f"Row {i}: skipped ({e})")

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read inventory data: {e}",
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


def get_inventory_summary(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns an aggregated summary of inventory data:
      - total products tracked
      - total current stock and total waste (last 30 days)
      - per-product details, including a calculated `is_low_stock` flag
        (current_stock <= reorder_level)
      - a simple list of low-stock items for convenience
      - any data-quality issues encountered while reading the file

    This is data + calculated metrics only. No restock recommendations,
    priorities, or actions are included — the calling agent decides
    what the numbers mean.
    """
    loaded = load_inventory_rows(file_path)

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
            "message": "Inventory file was read but contained no valid rows.",
            "summary": None,
            "skipped_rows": loaded["skipped_rows"],
            "row_errors": loaded["row_errors"],
        }

    total_products = len(rows)
    total_current_stock = round(sum(r["current_stock"] for r in rows), 2)
    total_waste_units_last_30_days = round(sum(r["waste_units_last_30_days"] for r in rows), 2)

    product_details = []
    low_stock_items = []
    for r in rows:
        is_low_stock = r["current_stock"] <= r["reorder_level"]
        entry = {
            "product_id": r["product_id"],
            "current_stock": r["current_stock"],
            "reorder_level": r["reorder_level"],
            "avg_daily_usage": r["avg_daily_usage"],
            "days_of_stock_left": r["days_of_stock_left"],
            "waste_units_last_30_days": r["waste_units_last_30_days"],
            "is_low_stock": is_low_stock,
        }
        product_details.append(entry)
        if is_low_stock:
            low_stock_items.append(entry)

    return {
        "status": "ok",
        "message": None,
        "summary": {
            "total_products": total_products,
            "total_current_stock": total_current_stock,
            "total_waste_units_last_30_days": total_waste_units_last_30_days,
            "low_stock_count": len(low_stock_items),
            "low_stock_items": low_stock_items,
            "product_details": product_details,
        },
        "skipped_rows": loaded["skipped_rows"],
        "row_errors": loaded["row_errors"],
    }