#get_historical_stock_prices.py

import json
import re
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_PERIODS = {"d", "w", "m"}          # daily, weekly, monthly (per docs)
ALLOWED_ORDER = {"a", "d"}                 # ascending, descending (per docs)
ALLOWED_FMT = {"json", "csv"}              # default is csv in API, but we default to json here

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _valid_date(s: str) -> bool:
    if not DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_historical_stock_prices(
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "d",
        order: str = "a",
        fmt: str = "json",
        filter: Optional[str] = None,           # e.g., "last_close", "last_volume"
        api_token: Optional[str] = None,        # per-call override
    ) -> str:
        """
        End-Of-Day Historical Stock Market Data (EOD) — spec-aligned.

        Args:
            ticker (str): Symbol in SYMBOL.EXCHANGE format, e.g. 'AAPL.US'.
            start_date (str, optional): 'from' date in YYYY-MM-DD. If omitted, API returns full history (plan limits apply).
            end_date (str, optional): 'to' date in YYYY-MM-DD. If omitted, API returns up to most recent.
            period (str): 'd' (daily), 'w' (weekly), 'm' (monthly). Default 'd'.
            order (str): 'a' (ascending) or 'd' (descending). Default 'a'.
            fmt (str): 'json' or 'csv'. Default 'json'. (API default is csv.)
            filter (str, optional): e.g., 'last_close', 'last_volume' (works with fmt=json; returns a single value).
            api_token (str, optional): Override API token for this call. If not provided, env token is used.

        Returns:
            str: JSON string with data or {"error": "..."}.
                 If fmt='csv', returns CSV text embedded as a JSON string for consistency.
        """
        # --- Validate required/typed params ---
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required and must be a string (e.g., 'AAPL.US').")

        if period not in ALLOWED_PERIODS:
            return _err(f"Invalid 'period'. Allowed values: {sorted(ALLOWED_PERIODS)}")

        if order not in ALLOWED_ORDER:
            return _err(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        if start_date is not None and not _valid_date(start_date):
            return _err("Parameter 'start_date' must be YYYY-MM-DD when provided.")

        if end_date is not None and not _valid_date(end_date):
            return _err("Parameter 'end_date' must be YYYY-MM-DD when provided.")

        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                return _err("'start_date' cannot be after 'end_date'.")

        # --- Build URL per docs ---
        # Base: /api/eod/{ticker}
        # Params: period, order, from, to, fmt, (optional) filter, api_token
        url = f"{EODHD_API_BASE}/eod/{ticker}?period={period}&order={order}&fmt={fmt}"

        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if filter:
            url += f"&filter={filter}"

        # Per-call token override; make_request() appends env token if none present.
        if api_token:
            url += f"&api_token={api_token}"

        # --- Execute request ---
        data = await make_request(url)

        # --- Transport/API errors ---
        if data is None:
            return _err("No response from API.")

        # If fmt=json, API returns JSON. If fmt=csv, httpx/json may return str or dict error.
        # Normalize:
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        # For CSV, make_request() will attempt .json() and fail; but our make_request currently returns response.json().
        # If you need raw CSV support, consider updating make_request to return text for fmt=csv.
        # Until then, we keep fmt=json by default. However, if the API returned a list (json), just dump it.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If fmt=csv and make_request was adapted to return text, 'data' may already be a str.
            if isinstance(data, str):
                # Wrap CSV text into a JSON string for consistent MCP return type (string)
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
