"""
Supplier Data Tool
-------------------
Reads data/suppliers.csv (and optionally cross-references data/products.csv)
to return structured supplier information — pricing, price changes, lead
times, and which products each supplier feeds — that an AI agent can
later analyze and reason about.

Follows the same pattern as sales_tool.py, inventory_tool.py, and
finance_tool.py:
  1. A `load_supplier_rows()` function that reads and validates the CSV.
  2. A `get_supplier_summary()` function that aggregates the data into
     a clean dict, handling missing/invalid data gracefully.

This module exposes RAW DATA and CALCULATED COMPARISON METRICS ONLY
(e.g. price change amount/percent). It does NOT decide which supplier
the business should use — that judgment belongs to the AI agent that
will consume this data later.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_COLUMNS = {
    "supplier_id", "supplier_name", "category_supplied", "unit", "lead_time_days",
    "previous_unit_price", "current_unit_price", "price_change_date",
    "payment_terms", "notes",
}


def _find_data_file(filename: str, start: Path, max_levels_up: int = 6) -> Path:
    """
    Searches upward from `start` (this file's own folder) for a `data/<filename>`
    directory, checking each ancestor folder in turn. Robust to project nesting
    depth and to the terminal's current working directory, since it is based
    entirely on this file's own location on disk. Same approach used by the
    other tools for consistency.
    """
    current = start
    for _ in range(max_levels_up):
        candidate = current / "data" / filename
        if candidate.exists():
            return candidate
        if current.parent == current:  # reached filesystem root
            break
        current = current.parent

    return start.parent.parent / "data" / filename


DEFAULT_SUPPLIERS_CSV_PATH = _find_data_file("suppliers.csv", Path(__file__).resolve().parent)
DEFAULT_PRODUCTS_CSV_PATH = _find_data_file("products.csv", Path(__file__).resolve().parent)


def load_supplier_rows(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Reads the suppliers CSV and returns validated rows plus any issues found.

    Never raises on bad data — missing file, missing columns, or
    unreadable rows are reported back instead of crashing the caller.

    Note: `price_change_date` and `notes` are allowed to be blank (some
    suppliers, e.g. those with stable pricing, legitimately have no
    recorded price-change date) — only structurally required fields
    (IDs, name, prices, lead time) cause a row to be skipped.
    """
    path = Path(file_path) if file_path else DEFAULT_SUPPLIERS_CSV_PATH

    if not path.exists():
        return {
            "ok": False,
            "error": f"Suppliers data file not found at: {path}",
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
                    supplier_id = raw_row["supplier_id"].strip()
                    supplier_name = raw_row["supplier_name"].strip()
                    category_supplied = raw_row["category_supplied"].strip()
                    unit = raw_row["unit"].strip()
                    lead_time_days = int(raw_row["lead_time_days"])
                    previous_unit_price = float(raw_row["previous_unit_price"])
                    current_unit_price = float(raw_row["current_unit_price"])
                    # optional / can legitimately be blank
                    price_change_date = raw_row.get("price_change_date", "").strip() or None
                    payment_terms = raw_row.get("payment_terms", "").strip() or None
                    notes = raw_row.get("notes", "").strip() or None

                    if not supplier_id or not supplier_name:
                        raise ValueError("empty required field")
                    if lead_time_days < 0 or previous_unit_price < 0 or current_unit_price < 0:
                        raise ValueError("negative value not allowed")

                    rows.append({
                        "supplier_id": supplier_id,
                        "supplier_name": supplier_name,
                        "category_supplied": category_supplied,
                        "unit": unit,
                        "lead_time_days": lead_time_days,
                        "previous_unit_price": previous_unit_price,
                        "current_unit_price": current_unit_price,
                        "price_change_date": price_change_date,
                        "payment_terms": payment_terms,
                        "notes": notes,
                    })
                except (ValueError, KeyError, AttributeError) as e:
                    skipped_rows += 1
                    row_errors.append(f"Row {i}: skipped ({e})")

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read suppliers data: {e}",
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


def _load_products_by_supplier(file_path: Optional[Path] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    Best-effort cross-reference: reads data/products.csv and groups product
    id/name pairs by their primary_supplier_id, so each supplier can list
    which products it feeds.

    This is intentionally forgiving — if products.csv is missing, malformed,
    or lacks the expected columns, this simply returns an empty mapping
    rather than failing the whole supplier tool. Supplier data must not
    depend on another CSV being present.
    """
    path = Path(file_path) if file_path else DEFAULT_PRODUCTS_CSV_PATH
    mapping: Dict[str, List[Dict[str, str]]] = {}

    if not path.exists():
        return mapping

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return mapping
            needed = {"product_id", "product_name", "primary_supplier_id"}
            if not needed.issubset(set(reader.fieldnames)):
                return mapping

            for raw_row in reader:
                try:
                    supplier_id = raw_row["primary_supplier_id"].strip()
                    product_id = raw_row["product_id"].strip()
                    product_name = raw_row["product_name"].strip()
                    if not supplier_id or not product_id:
                        continue
                    mapping.setdefault(supplier_id, []).append({
                        "product_id": product_id,
                        "product_name": product_name,
                    })
                except (KeyError, AttributeError):
                    continue
    except Exception:
        return {}

    return mapping


def get_supplier_summary(
    suppliers_file_path: Optional[Path] = None,
    products_file_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Returns an aggregated summary of supplier data:
      - total suppliers and categories represented
      - per-supplier details: pricing (previous/current), calculated
        price_change_amount and price_change_pct, lead time, payment
        terms, notes, and which products it supplies (if products.csv
        is available)
      - reliability/performance data is explicitly reported as
        unavailable, since the current dataset does not include it —
        it is not invented or estimated
      - any data-quality issues encountered while reading the file

    This is data + calculated comparison metrics only. No recommendation
    about which supplier to choose is included — the calling agent
    decides what the numbers mean.
    """
    loaded = load_supplier_rows(suppliers_file_path)

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
            "message": "Suppliers file was read but contained no valid rows.",
            "summary": None,
            "skipped_rows": loaded["skipped_rows"],
            "row_errors": loaded["row_errors"],
        }

    products_by_supplier = _load_products_by_supplier(products_file_path)

    supplier_details = []
    categories = set()
    for r in rows:
        prev = r["previous_unit_price"]
        curr = r["current_unit_price"]
        price_change_amount = round(curr - prev, 4)
        price_change_pct = round((curr - prev) / prev * 100, 2) if prev > 0 else None

        categories.add(r["category_supplied"])

        supplier_details.append({
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "category_supplied": r["category_supplied"],
            "unit": r["unit"],
            "lead_time_days": r["lead_time_days"],
            "previous_unit_price": prev,
            "current_unit_price": curr,
            "price_change_amount": price_change_amount,
            "price_change_pct": price_change_pct,
            "price_change_date": r["price_change_date"],
            "payment_terms": r["payment_terms"],
            "notes": r["notes"],
            "products_supplied": products_by_supplier.get(r["supplier_id"], []),
            "reliability_performance_info": None,  # not present in current dataset
        })

    return {
        "status": "ok",
        "message": None,
        "summary": {
            "total_suppliers": len(rows),
            "categories_supplied": sorted(categories),
            "suppliers": supplier_details,
        },
        "skipped_rows": loaded["skipped_rows"],
        "row_errors": loaded["row_errors"],
        "products_cross_reference_available": bool(products_by_supplier),
    }