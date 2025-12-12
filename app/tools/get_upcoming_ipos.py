#get_upcoming_ipos.py

import json
from typing import Optional
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


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_ipos(
        from_date: Optional[str] = None,     # format YYYY-MM-DD (mapped to 'from')
        to_date: Optional[str] = None,       # format YYYY-MM-DD (mapped to 'to')
        fmt: str = "json",                   # 'json' or 'csv' (default per API is csv; we default to json for dev-friendliness)
        api_token: Optional[str] = None,     # per-call override; otherwise env EODHD_API_KEY is used
    ) -> str:
        """
        Upcoming IPOs API (/calendar/ipos)

        Parameters:
          - from_date (YYYY-MM-DD): start date (maps to 'from'); default = today if omitted by server
          - to_date   (YYYY-MM-DD): end date   (maps to 'to');   default = today+7d if omitted by server
          - fmt: 'json' or 'csv' (API default is csv). We default to 'json' for easier consumption.
          - api_token: optional override for per-call token

        Returns:
          - JSON (stringified) when fmt='json'
          - CSV (raw text wrapped as JSON string if the upstream returns text)
        """
        # Normalize/validate fmt
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            return _err("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # Build URL
        url = f"{EODHD_API_BASE}/calendar/ipos?1=1"
        if from_date:
            url += _q("from", from_date)
        if to_date:
            url += _q("to", to_date)
        url += _q("fmt", fmt)

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call
        data = await make_request(url)

        # Handle response
        if data is None:
            return _err("No response from API.")

        # If fmt=csv, many clients of make_request return raw text (str)
        if fmt == "csv":
            if isinstance(data, str):
                # Wrap CSV in a small envelope for consistency
                return json.dumps({"fmt": "csv", "data": data}, indent=2)
            # Unexpected structure
            return _err("Unexpected CSV response format from API.")

        # fmt == json
        try:
            # data should be a dict/list already; ensure string output
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected JSON response format from API.")
