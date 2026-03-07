#get_historical_market_cap.py

import json
import re
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_FMT = {"json", "csv"}

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

        Get historical market capitalization data for a US stock over time.
        Returns weekly market cap data points (from 2020 onward) for NYSE/NASDAQ tickers.
        Filter by date range. Each request consumes 10 API calls.
        Use when the user asks about market cap history, company valuation over time, or market cap trends.
        This is the only tool for historical market cap -- do not confuse with fundamental data or price history.


        Returns:
            Array of weekly data points, each with:
            - date (str): observation date YYYY-MM-DD
            - value (float): market capitalization in USD

        Examples:
            "Apple market cap history in 2025" → ticker="AAPL.US", start_date="2025-01-01", end_date="2025-12-31"
            "Microsoft market cap last 6 months" → ticker="MSFT.US", start_date="2025-09-06", end_date="2026-03-06"
            "Google market cap since 2023" → ticker="GOOG.US", start_date="2023-01-01"

        
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL' or 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

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
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If you adapt make_request to return text for fmt='csv', we wrap it here.
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
