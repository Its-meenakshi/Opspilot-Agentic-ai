"""
Finance Data Tool
------------------
Reads data/expenses.csv and returns structured financial information
(total expenses, category breakdowns, date range) that an AI agent
can later analyze and reason about.

Follows the same pattern as tools/sales_tool.py and tools/inventory_tool.py:
  1. A `load_expense_rows()` function that reads and validates the CSV.
  2. A `get_finance_summary()` function that aggregates the data into
     a clean dict, handling missing/invalid data gracefully.

This module exposes RAW DATA and CALCULATED METRICS ONLY. It does not
decide what the business should cut, reduce, or change — that judgment
belongs to the AI agent that will consume this data later.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_COLUMNS = {"expense_id", "date", "category", "description", "amount"}


def _find_data_file(filename: str, start: Path, max_levels_up: int = 6) -> Path:
    """
    Searches upward from `start` (this file's own folder) for a `data/<filename>`
    directory, checking each ancestor folder in turn.

    This makes the lookup robust to how deeply nested this tools/ folder is
    inside the project, and to the terminal's current working directory,
    since it is based entirely on this file's own location on disk rather
    than on cwd or a fixed parent-count guess. (Same approach used by
    sales_tool.py and inventory_tool.py for consistency.)

    If nothing is found, falls back to a best-guess default so the
    resulting "file not found" error message still points somewhere sensible.
    """
    current = start
    for _ in range(max_levels_up):
        candidate = current / "data" / filename
        if candidate.exists():
            return candidate
        if current.parent == current:  # reached filesystem root
            break
        current = current.parent

    # Fallback: best-guess default for a clear error message
    return start.parent.parent / "data" / filename


# Resolved once at import time by walking up from this file's location
# until a real data/expenses.csv is found (or falling back to a default guess).
DEFAULT_EXPENSES_CSV_PATH = _find_data_file("expenses.csv", Path(__file__).resolve().parent)


def load_expense_rows(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Reads the expenses CSV and returns validated rows plus any issues found.

    Never raises on bad data — missing file, missing columns, or
    unreadable rows are reported back instead of crashing the caller.
    """
    path = Path(file_path) if file_path else DEFAULT_EXPENSES_CSV_PATH

    if not path.exists():
        return {
            "ok": False,
            "error": f"Expenses data file not found at: {path}",
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
                    expense_id = raw_row["expense_id"].strip()
                    date_value = raw_row["date"].strip()
                    category = raw_row["category"].strip()
                    description = raw_row["description"].strip()
                    amount = float(raw_row["amount"])

                    if not expense_id or not date_value or not category:
                        raise ValueError("empty required field")
                    if amount < 0:
                        raise ValueError("negative amount not allowed")

                    rows.append({
                        "expense_id": expense_id,
                        "date": date_value,
                        "category": category,
                        "description": description,
                        "amount": amount,
                    })
                except (ValueError, KeyError, AttributeError) as e:
                    skipped_rows += 1
                    row_errors.append(f"Row {i}: skipped ({e})")

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read expenses data: {e}",
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


def get_finance_summary(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns an aggregated summary of financial data:
      - total expenses and total transaction records
      - date range covered
      - category breakdown (total amount, transaction count, and
        percentage of total spend per category)
      - the full list of individual expense records
      - any data-quality issues encountered while reading the file

    This is data + calculated metrics only. No recommendations about
    what to cut, reduce, or change are included — the calling agent
    decides what the numbers mean.
    """
    loaded = load_expense_rows(file_path)

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
            "message": "Expenses file was read but contained no valid rows.",
            "summary": None,
            "skipped_rows": loaded["skipped_rows"],
            "row_errors": loaded["row_errors"],
        }

    total_expenses = round(sum(r["amount"] for r in rows), 2)
    total_records = len(rows)
    dates = sorted(r["date"] for r in rows)

    category_breakdown: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        cat = r["category"]
        if cat not in category_breakdown:
            category_breakdown[cat] = {
                "category": cat,
                "total_amount": 0.0,
                "transaction_count": 0,
            }
        category_breakdown[cat]["total_amount"] += r["amount"]
        category_breakdown[cat]["transaction_count"] += 1

    for entry in category_breakdown.values():
        entry["total_amount"] = round(entry["total_amount"], 2)
        entry["percent_of_total"] = (
            round(entry["total_amount"] / total_expenses * 100, 1) if total_expenses > 0 else 0.0
        )

    return {
        "status": "ok",
        "message": None,
        "summary": {
            "total_expenses": total_expenses,
            "total_records": total_records,
            "date_range": {"start": dates[0], "end": dates[-1]},
            "category_breakdown": list(category_breakdown.values()),
            "expense_records": rows,
        },
        "skipped_rows": loaded["skipped_rows"],
        "row_errors": loaded["row_errors"],
    }