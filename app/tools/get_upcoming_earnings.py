#get_upcoming_earnings.py

import json
from typing import Optional, Union, List
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _q(key: str, val: Optional[str]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(val)}"


def _normalize_symbols(symbols: Optional[Union[str, List[str]]]) -> Optional[str]:
    if symbols is None:
        return None
    if isinstance(symbols, str):
        s = symbols.strip()
        return s if s else None
    if isinstance(symbols, list):
        flat = [str(x).strip() for x in symbols if str(x).strip()]
        return ",".join(flat) if flat else None
    return None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_earnings(
        start_date: Optional[str] = None,         # maps to from= (YYYY-MM-DD)
        end_date: Optional[str] = None,           # maps to to=   (YYYY-MM-DD)
        symbols: Optional[Union[str, List[str]]] = None,  # 'AAPL.US' or ['AAPL.US','MSFT.US']
        fmt: Optional[str] = "json",              # 'json' or 'csv' (docs default csv)
        api_token: Optional[str] = None,          # per-call override
    ) -> str:
        """
        Get upcoming and recent earnings report dates for stocks.
        Returns scheduled earnings dates, EPS estimates, and actual results when available.
        Filter by specific symbols or a date range (defaults to next 7 days).
        Use when the user asks "when does X report earnings?" or wants an earnings calendar.
        For EPS/revenue trend analysis and analyst revisions, use get_earnings_trends instead.
        For macroeconomic events (GDP, CPI), use get_economic_events instead.


        Examples:
            "Apple earnings schedule" → symbols="AAPL.US"
            "Earnings this week" → start_date="2026-03-02", end_date="2026-03-06"
            "Microsoft and Google earnings" → symbols="MSFT.US,GOOG.US"

        """
        sym_param = _normalize_symbols(symbols)

        # Build base URL
        url = f"{EODHD_API_BASE}/calendar/earnings?1=1"

        # Add parameters:
        if sym_param:
            url += _q("symbols", sym_param)
            # Per spec: when symbols provided, 'from'/'to' are ignored — so we do NOT append them.
        else:
            url += _q("from", start_date)
            url += _q("to", end_date)

        url += _q("fmt", (fmt or "json").lower())

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Hit API
        data = await make_request(url)

        # Normalize output
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):  # e.g., CSV
                return json.dumps({"raw": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
