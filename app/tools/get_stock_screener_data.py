#get_stock_screener_data.py

import json
from typing import Optional, Union, List, Any
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _q(key: str, val: Optional[str]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _normalize_filters(filters: Optional[Union[str, List[List[Any]]]]) -> Optional[str]:
    """
    Accepts either:
      - a raw (already-encoded) string like:
        [[\"market_capitalization\",\">\",1000],[\"sector\",\"=\",\"Technology\"]]
      - a python list of lists like:
        [["market_capitalization", ">", 1000], ["sector", "=", "Technology"]]
    Returns a JSON string (not URL-encoded).
    """
    if filters is None or filters == "":
        return None
    if isinstance(filters, str):
        # Assume user passed a JSON-ish string already.
        return filters
    try:
        return json.dumps(filters, separators=(",", ":"))
    except Exception:
        return None


def _normalize_signals(signals: Optional[Union[str, List[str]]]) -> Optional[str]:
    """
    Accepts either a comma-separated string or a list of strings.
    Returns a comma-separated string or None.
    """
    if signals is None or signals == "":
        return None
    if isinstance(signals, str):
        return signals
    # list
    parts = [s for s in signals if isinstance(s, str) and s.strip()]
    return ",".join(parts) if parts else None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def stock_screener(
        filters: Optional[Union[str, List[List[Any]]]] = None,
        signals: Optional[Union[str, List[str]]] = None,
        sort: Optional[str] = None,             # e.g. "market_capitalization.desc"
        limit: int = 50,                         # 1..100
        offset: int = 0,                         # 0..999
        fmt: Optional[str] = None,               # NEW: accept fmt to avoid validation errors
        api_token: Optional[str] = None,         # per-call override (else env)
    ) -> str:
        """
        Stock Market Screener API
        GET /api/screener

        Each request consumes 5 API calls.

        Args:
          - filters: list-of-lists or JSON string
          - signals: list[str] or comma-separated string
          - sort: "field.asc" | "field.desc"
          - limit: 1..100
          - offset: 0..999
          - fmt: optional; Screener is JSON-only. If provided, must be "json".
          - api_token: optional override
        """

        # --- fmt handling (for compatibility with callers passing fmt) ---
        if fmt is not None and fmt.lower() != "json":
            return _err("The Screener endpoint returns JSON only. Use fmt='json' or omit this parameter.")

        # Validate pagination bounds
        if not (1 <= int(limit) <= 100):
            return _err("Parameter 'limit' must be between 1 and 100.")
        if not (0 <= int(offset) <= 999):
            return _err("Parameter 'offset' must be between 0 and 999.")

        filt_str = _normalize_filters(filters)
        if filters is not None and filt_str is None:
            return _err("Invalid 'filters' value. Provide a JSON string or list-of-lists.")

        sig_str = _normalize_signals(signals)
        if signals is not None and (sig_str is None or sig_str.strip() == ""):
            return _err("Invalid 'signals' value. Provide a list of strings or comma-separated string.")

        # Build URL
        url = f"{EODHD_API_BASE}/screener?1=1"
        if sort:
            url += _q("sort", sort)
        url += _q("limit", str(limit))
        url += _q("offset", str(offset))
        if filt_str:
            url += _q("filters", filt_str)
        if sig_str:
            url += _q("signals", sig_str)

        # (We deliberately do NOT append fmt, since the endpoint is JSON-only.)

        if api_token:
            url += _q("api_token", api_token)

        data = await make_request(url)
        if data is None:
            return _err("No response from API.")
        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected JSON response format from API.")
