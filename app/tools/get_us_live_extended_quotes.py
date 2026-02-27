#get_us_live_extended_quotes.py

import json
from typing import Iterable, Optional, Sequence, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_FMT = {"json", "csv"}
MAX_PAGE_LIMIT = 100  # per spec
DEFAULT_FMT = "json"


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _normalize_symbols(symbols: Optional[Union[str, Iterable[str]]]) -> list[str]:
    """
    Accepts a single comma-separated string or an iterable of strings.
    Strips whitespace, removes empties, preserves order, and de-duplicates.
    """
    out: list[str] = []
    seen = set()

    if symbols is None:
        return out

    # If passed a single string, support comma-separated list
    if isinstance(symbols, str):
        parts = [p.strip() for p in symbols.split(",")]
    else:
        parts = []
        for s in symbols:
            if s is None:
                continue
            parts.append(str(s).strip())

    for p in parts:
        if not p:
            continue
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_live_extended_quotes(
        symbols: Union[str, Sequence[str]],   # one or more (e.g., "AAPL.US,TSLA.US" or ["AAPL.US","TSLA.US"])
        fmt: str = DEFAULT_FMT,               # 'json' (default) or 'csv'
        page_limit: Optional[int] = None,     # page[limit] (max 100)
        page_offset: Optional[int] = None,    # page[offset] (>= 0)
        api_token: Optional[str] = None,      # per-call override
    ) -> str:
        """
        Live v2 for US Stocks: Extended Quotes (Delayed, exchange-compliant)
        GET /api/us-quote-delayed

        - 1 API call per ticker (batching supported via 's').
        - Returns a per-symbol quote snapshot with last trade, bid/ask (+ sizes & event times),
          rolling averages, 52w high/low, market cap, basic fundamentals, etc.

        Args:
          symbols: A single comma-separated string or a sequence of tickers (e.g., ["AAPL.US","TSLA.US"]).
          fmt: 'json' (default) or 'csv'.
          page_limit: Optional page size; max 100.
          page_offset: Optional offset for pagination; must be >= 0.
          api_token: Optional token; if omitted, env is used via make_request().

        Returns:
          Pretty-printed JSON string on success, or {"error": "..."} on failure.
          If fmt='csv' and your make_request() returns raw text, it's wrapped as {"csv": "..."}.
        """
        # --- Validate inputs ---
        syms = _normalize_symbols(symbols)
        if not syms:
            return _err("Parameter 'symbols' must contain at least one ticker (e.g., 'AAPL.US').")

        fmt = (fmt or DEFAULT_FMT).lower()
        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        if page_limit is not None:
            if not isinstance(page_limit, int) or page_limit <= 0 or page_limit > MAX_PAGE_LIMIT:
                return _err(f"'page_limit' must be an integer between 1 and {MAX_PAGE_LIMIT}.")

        if page_offset is not None:
            if not isinstance(page_offset, int) or page_offset < 0:
                return _err("'page_offset' must be an integer >= 0.")

        # --- Build URL ---
        # Example:
        #   /api/us-quote-delayed?s=AAPL.US,TSLA.US&fmt=json&page[limit]=100&page[offset]=0
        base = f"{EODHD_API_BASE}/us-quote-delayed"
        query = f"?s={','.join(syms)}&fmt={fmt}"

        if page_limit is not None:
            query += f"&page[limit]={page_limit}"
        if page_offset is not None:
            query += f"&page[offset]={page_offset}"
        if api_token:
            query += f"&api_token={api_token}"

        url = f"{base}{query}"

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
            # If make_request() was adapted to return raw text for CSV:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")

