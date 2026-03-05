#get_bulk_fundamentals.py

import json
from typing import Optional, Union
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _q(key: str, val: Optional[str | int]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_bulk_fundamentals(
        exchange: str,                                # e.g. "NASDAQ", "NYSE", "US", "LSE"
        symbols: Optional[str] = None,                # comma-separated list, e.g. "AAPL,MSFT,GOOG"
        offset: Optional[Union[int, str]] = None,     # pagination start (default 0)
        limit: Optional[Union[int, str]] = None,      # max symbols (default 500, max 500)
        version: Optional[str] = None,                # "1.2" for single-symbol-like output
        fmt: str = "json",                            # 'json' (default) or 'csv'
        api_token: Optional[str] = None,              # per-call override
    ) -> str:
        """
        Bulk Fundamentals API
        GET /api/bulk-fundamentals/{EXCHANGE}

        Retrieves fundamentals data for all stocks on an exchange in a single call.
        Includes General, Highlights, Valuation, Technicals, SplitsDividends,
        Earnings (last 4 quarters + 4 years), and Financials sections.

        Args:
            exchange (str): Exchange code (e.g., 'NASDAQ', 'NYSE', 'US', 'LSE').
            symbols (str, optional): Comma-separated list of specific symbols.
            offset (int, optional): Starting position for pagination (default 0).
            limit (int, optional): Number of symbols to return (default 500, max 500).
            version (str, optional): '1.2' for output closer to single-symbol template.
            fmt (str): Response format: 'json' (default) or 'csv'.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Requires Extended Fundamentals subscription plan.
            - API cost: 100 calls per request (or 100 + number of symbols if using symbols param).
            - Stocks only (no ETFs or Mutual Funds).
            - Max pagination limit: 500.
            - Historical data limited to 4 quarters and 4 years.
        """
        if not exchange or not isinstance(exchange, str):
            return _err(
                "Parameter 'exchange' is required and must be a non-empty string "
                "(e.g., 'NASDAQ', 'NYSE', 'US')."
            )

        exchange = exchange.strip().upper()

        allowed_fmt = {"json", "csv"}
        fmt = (fmt or "json").lower()
        if fmt not in allowed_fmt:
            return _err(f"Invalid 'fmt'. Allowed: {sorted(allowed_fmt)}")

        url = f"{EODHD_API_BASE}/bulk-fundamentals/{quote_plus(exchange)}?fmt={fmt}"

        if symbols:
            url += _q("symbols", symbols.strip())

        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                return _err("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                return _err("Parameter 'offset' must be a non-negative integer.")
            url += f"&offset={off}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                return _err("Parameter 'limit' must be a positive integer (max 500).")
            if lim <= 0 or lim > 500:
                return _err("Parameter 'limit' must be between 1 and 500.")
            url += f"&limit={lim}"

        if version:
            url += _q("version", version.strip())

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
