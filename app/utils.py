# app/utils.py
"""
Common utilities for EODHD MCP Server tools.
"""

import json
import re
from datetime import datetime
from typing import Optional

# Date validation regex
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def err(msg: str) -> str:
    """Return a JSON-formatted error string."""
    return json.dumps({"error": msg}, indent=2)


def valid_date(s: str) -> bool:
    """Validate date string in YYYY-MM-DD format."""
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Optional[str]:
    """
    Validate start and end dates.
    Returns error message if invalid, None if valid.
    """
    if start_date is not None and not valid_date(start_date):
        return "Parameter 'start_date' must be YYYY-MM-DD when provided."

    if end_date is not None and not valid_date(end_date):
        return "Parameter 'end_date' must be YYYY-MM-DD when provided."

    if start_date and end_date:
        if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
            return "'start_date' cannot be after 'end_date'."

    return None


def validate_ticker(ticker: str) -> Optional[str]:
    """
    Validate ticker format.
    Returns error message if invalid, None if valid.
    """
    if not ticker or not isinstance(ticker, str):
        return "Parameter 'ticker' is required and must be a string."
    return None


def validate_exchange(exchange: str) -> Optional[str]:
    """
    Validate exchange code.
    Returns error message if invalid, None if valid.
    """
    if not exchange or not isinstance(exchange, str):
        return "Parameter 'exchange' is required and must be a string (e.g., 'US', 'LSE')."
    return None


def normalize_list_param(param) -> list:
    """
    Normalize a parameter that can be a string or list to a list.
    """
    if param is None:
        return []
    if isinstance(param, str):
        return [s.strip() for s in param.split(",") if s.strip()]
    if isinstance(param, list):
        return [str(s).strip() for s in param if s]
    return []


def truncate(s: str, max_len: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to max_len characters.
    """
    if not s or len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def format_response(data, fmt: str = "json") -> str:
    """
    Format response data as JSON string.
    """
    if data is None:
        return err("No response from API.")

    if isinstance(data, dict) and data.get("error"):
        return json.dumps({"error": data["error"]}, indent=2)

    try:
        return json.dumps(data, indent=2)
    except Exception:
        if isinstance(data, str):
            return json.dumps({"csv": data}, indent=2)
        return err("Unexpected response format from API.")
