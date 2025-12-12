#get_mp_indices_list.py

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
    async def mp_indices_list(
        fmt: str = "json",                 # API returns JSON; expose for symmetry
        api_token: Optional[str] = None,   # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: List of Indices with Details
        GET /api/mp/unicornbay/spglobal/list

        Returns end-of-day details for 100+ S&P/Dow Jones indices.
        One request = 10 API calls (Marketplace rules).

        Args:
          - fmt: 'json' (default). (CSV is not documented; keep JSON only.)
          - api_token: optional override API token

        Response:
          JSON string (pretty-printed) or {"error": "..."} on failure.
        """
        fmt = (fmt or "json").lower()
        if fmt != "json":
            return _err("Only JSON is supported for this endpoint.")

        url = f"{EODHD_API_BASE}/mp/unicornbay/spglobal/list?1=1"
        url += _q("fmt", "json")
        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request

        data = await make_request(url)
        if data is None:
            return _err("No response from API.")
        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected JSON response format from API.")
