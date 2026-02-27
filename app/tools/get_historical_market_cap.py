#get_historical_market_cap.py

import json
import re
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_FMT = {"json", "csv"}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _valid_date(d: Optional[str]) -> bool:
    if d is None:
        return True
    if not DATE_RE.match(d):
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_historical_market_cap(
        ticker: str,                        # e.g., "AAPL" or "AAPL.US"
        start_date: Optional[str] = None,   # maps to 'from' (YYYY-MM-DD)
        end_date: Optional[str] = None,     # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",                  # 'json' or 'csv' (API shows json; csv optional)
        api_token: Optional[str] = None,    # per-call override; env token otherwise
    ) -> str:
        """
        Historical Market Capitalization API (GET /api/historical-market-cap/{TICKER})

        Notes:
            - Covers US stocks on NYSE/NASDAQ from 2020 (weekly points).
            - 'ticker' can be SYMBOL or SYMBOL.EXCHANGE (e.g., 'AAPL' or 'AAPL.US').
            - Optional 'from'/'to' filter by YYYY-MM-DD.
            - Each symbol request costs 10 API calls (per docs).

        Returns:
            str: JSON string with weekly market cap data
                 (or {"csv": "..."} if you later adapt make_request to return text for csv).
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required (e.g., 'AAPL' or 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        if not _valid_date(start_date):
            return _err("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            return _err("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                return _err("'start_date' cannot be after 'end_date'.")

        # --- Build URL ---
        # Example: /api/historical-market-cap/AAPL.US?fmt=json&from=2025-03-01&to=2025-04-01
        url = f"{EODHD_API_BASE}/historical-market-cap/{ticker}?fmt={fmt}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If you adapt make_request to return text for fmt='csv', we wrap it here.
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
