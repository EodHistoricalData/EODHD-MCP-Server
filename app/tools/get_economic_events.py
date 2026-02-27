#get_economic_events.py

import json
from typing import Optional, Union
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_COMPARISON = {None, "mom", "qoq", "yoy"}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _q(key: str, val: Optional[Union[str, int]]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_economic_events(
        start_date: Optional[str] = None,   # maps to from= (YYYY-MM-DD)
        end_date: Optional[str] = None,     # maps to to=   (YYYY-MM-DD)
        country: Optional[str] = None,      # ISO-3166 alpha-2 (e.g., US, GB, DE)
        comparison: Optional[str] = None,   # mom | qoq | yoy
        type: Optional[str] = None,         # free text, e.g. "House Price Index"
        offset: int = 0,                    # 0..1000 (default 0)
        limit: int = 50,                    # 0..1000 (default 50)
        fmt: Optional[str] = "json",        # json (default) | csv (if supported)
        api_token: Optional[str] = None,    # per-call override
    ) -> str:
        """
        Economic Events Data API (/economic-events)

        Returns past/future economic events with optional filters:
        date window, country (ISO2), comparison (mom|qoq|yoy), type text,
        and pagination (offset/limit).
        """
        # --- validate ---
        if comparison not in ALLOWED_COMPARISON:
            return _err("Invalid 'comparison'. Allowed: 'mom', 'qoq', 'yoy' or omit.")
        if not isinstance(offset, int) or not (0 <= offset <= 1000):
            return _err("'offset' must be an integer between 0 and 1000.")
        if not isinstance(limit, int) or not (0 <= limit <= 1000):
            return _err("'limit' must be an integer between 0 and 1000.")
        if country is not None and (not isinstance(country, str) or len(country.strip()) != 2):
            return _err("'country' must be a 2-letter ISO code (e.g., 'US').")

        # --- build URL ---
        # Example:
        # /economic-events?api_token=XXX&fmt=json&from=2025-01-05&to=2025-01-06&country=US&limit=1000
        url = f"{EODHD_API_BASE}/economic-events?1=1"
        url += _q("from", start_date)
        url += _q("to", end_date)
        url += _q("country", country.upper() if country else None)
        url += _q("comparison", comparison)
        url += _q("type", type)
        url += _q("offset", offset)
        url += _q("limit", limit)
        url += _q("fmt", fmt or "json")
        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request

        # --- request ---
        data = await make_request(url)

        # --- return/normalize ---
        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If CSV or unexpected text returned, wrap it
            if isinstance(data, str):
                return json.dumps({"raw": data}, indent=2)
            return _err("Unexpected response format from API.")
