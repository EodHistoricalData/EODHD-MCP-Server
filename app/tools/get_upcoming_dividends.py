#get_upcoming_dividends.py

import json
from typing import Optional
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
    async def get_upcoming_dividends(
        symbol: Optional[str] = None,          # maps to filter[symbol]
        date_eq: Optional[str] = None,         # maps to filter[date_eq], YYYY-MM-DD
        date_from: Optional[str] = None,       # maps to filter[date_from], YYYY-MM-DD
        date_to: Optional[str] = None,         # maps to filter[date_to],   YYYY-MM-DD
        page_limit: Optional[int] = None,      # maps to page[limit], 1..1000, default 1000
        page_offset: Optional[int] = None,     # maps to page[offset], >=0, default 0
        fmt: str = "json",                     # API supports JSON only
        api_token: Optional[str] = None,       # per-call override; else env EODHD_API_KEY
    ) -> str:
        """
        Historical & Upcoming Dividends API (/calendar/dividends)

        Notes:
          - At least one of 'symbol' or 'date_eq' must be provided.
          - You can combine 'symbol' with 'date_from'/'date_to' to narrow range.
          - Pagination: 'page_limit' (1..1000) and 'page_offset' (>=0).
          - API output is JSON only.
        """

        # --- Validate basic args ---
        fmt = (fmt or "json").lower()
        if fmt != "json":
            return _err("Only 'json' is supported by this tool (fmt must be 'json').")

        if symbol is None and date_eq is None:
            return _err("You must provide at least one of 'symbol' or 'date_eq'.")

        if page_limit is not None:
            if not isinstance(page_limit, int) or not (1 <= page_limit <= 1000):
                return _err("'page_limit' must be an integer between 1 and 1000.")

        if page_offset is not None:
            if not isinstance(page_offset, int) or page_offset < 0:
                return _err("'page_offset' must be a non-negative integer.")

        # --- Build URL ---
        # Base: /api/calendar/dividends?filter[symbol]=...&filter[date_from]=...&page[limit]=...&page[offset]=...&fmt=json
        url = f"{EODHD_API_BASE}/calendar/dividends?1=1"
        url += _q("fmt", fmt)

        # Filters
        url += _q("filter[symbol]", symbol)
        url += _q("filter[date_eq]", date_eq)
        url += _q("filter[date_from]", date_from)
        url += _q("filter[date_to]", date_to)

        # Pagination
        url += _q("page[limit]", page_limit)
        url += _q("page[offset]", page_offset)

        # Token (make_request will add env token if omitted)
        if api_token:
            url += _q("api_token", api_token)

        # --- Request upstream ---
        data = await make_request(url)
        if data is None:
            return _err("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        # --- Return normalized JSON string ---
        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected JSON response format from API.")
