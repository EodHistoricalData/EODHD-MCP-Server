"""Shared input validation helpers for EODHD MCP tools."""

import re
from datetime import datetime

from fastmcp.exceptions import ToolError

# Ticker/symbol: alphanumeric, dots, hyphens, underscores. 1-50 chars.
# Covers: AAPL.US, EUR.FOREX, BTC-USD.CC, GSPC.INDX, VTI.US
TICKER_RE = re.compile(r"^[A-Za-z0-9._\-]{1,50}$")

# Exchange code: alphanumeric only, 1-20 chars.
EXCHANGE_RE = re.compile(r"^[A-Za-z0-9]{1,20}$")

# Date format: YYYY-MM-DD
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_ticker(ticker: str, param_name: str = "ticker") -> str:
    """Validate and return a sanitized ticker symbol, or raise ToolError."""
    if not ticker or not isinstance(ticker, str):
        raise ToolError(f"Parameter '{param_name}' is required and must be a string (e.g., 'AAPL.US').")
    ticker = ticker.strip()
    if not TICKER_RE.match(ticker):
        raise ToolError(
            f"Parameter '{param_name}' contains invalid characters. "
            f"Allowed: letters, digits, dots, hyphens, underscores (1-50 chars). Got: {ticker!r}"
        )
    return ticker


def validate_exchange(code: str, param_name: str = "exchange_code") -> str:
    """Validate and return a sanitized exchange code, or raise ToolError."""
    if not code or not isinstance(code, str):
        raise ToolError(f"Parameter '{param_name}' is required.")
    code = code.strip()
    if not EXCHANGE_RE.match(code):
        raise ToolError(
            f"Parameter '{param_name}' contains invalid characters. "
            f"Allowed: letters and digits only (1-20 chars). Got: {code!r}"
        )
    return code


def validate_date(value: str | None, param_name: str = "date") -> bool:
    """Validate an optional date string is YYYY-MM-DD format. Returns True if valid or None."""
    if value is None:
        return True
    if not DATE_RE.match(value):
        raise ToolError(f"Parameter '{param_name}' must be in YYYY-MM-DD format when provided.")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ToolError(f"Parameter '{param_name}' is not a valid date: {value!r}")
    return True
