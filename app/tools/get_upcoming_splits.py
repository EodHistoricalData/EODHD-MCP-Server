# get_upcoming_splits.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_splits(
        from_date: str | None = None,  # YYYY-MM-DD → maps to 'from'
        to_date: str | None = None,  # YYYY-MM-DD → maps to 'to'
        fmt: str = "json",  # 'json' or 'csv' (API default is csv)
        api_token: str | None = None,  # per-call override; else env EODHD_API_KEY
    ) -> str:
        """

        Get upcoming and recent stock split events.
        Returns split dates, tickers, and split ratios (e.g., 4:1) within a date range (defaults to next 7 days).
        Use when the user asks about stock splits, share splits, or reverse splits.
        For IPO calendar, use get_upcoming_ipos. For dividend calendar, use get_upcoming_dividends.


        Returns:
            Array of split records, each with:
            - code (str): ticker symbol
            - exchange (str): exchange code
            - optionable (str): whether options exist ('0' or '1')
            - date (str): split effective date
            - split (str): split ratio (e.g. '4/1')
            - oldShares (int): pre-split share count
            - newShares (int): post-split share count

        Examples:
            "Stock splits this week" → from_date="2026-03-02", to_date="2026-03-06"
            "Splits in Q1 2026" → from_date="2026-01-01", to_date="2026-03-31"
            "Any splits next month" → from_date="2026-04-01", to_date="2026-04-30"

        
        """
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            raise ToolError("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # Build URL
        url = f"{EODHD_API_BASE}/calendar/splits?1=1"
        if from_date:
            url += _q("from", from_date)
        if to_date:
            url += _q("to", to_date)
        url += _q("fmt", fmt)

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call upstream
        data = await make_request(url)
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        # Format handling
        if fmt == "csv":
            if isinstance(data, str):
                return json.dumps({"fmt": "csv", "data": data}, indent=2)
            raise ToolError("Unexpected CSV response format from API.")

        # fmt == json
        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
